#!/usr/bin/env python3
"""
Open a remote XIHE/GLONET Zarr, create an ndpyramid reprojection pyramid,
and write the result directly to S3/MinIO.

Required environment variables:
  SOURCE_URL
  TARGET_URL
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY

SOURCE_URL and TARGET_URL may be full URLs or bare bucket/path values. Bare
source paths are expanded with AWS_S3_ENDPOINT, which defaults to
minio.dive.edito.eu, and bare target paths are expanded to s3://bucket/path.

Optional environment variables:
  AWS_SESSION_TOKEN
  AWS_S3_ENDPOINT (default: minio.dive.edito.eu)
  DELETE_WORKERS (default: 16)
  LEVELS (default: 5)
  PYRAMID_PROJECTION
  PYRAMID_RESAMPLING
  PYRAMID_EXTRA_DIM
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse


SUCCESS_MARKER = "_SUCCESS"
DELETE_WORKERS = int(os.environ.get("DELETE_WORKERS", "16"))


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def endpoint_url():
    endpoint = os.environ.get("AWS_S3_ENDPOINT", "minio.dive.edito.eu")
    if endpoint.startswith("http"):
        return endpoint
    return f"https://{endpoint}"


def has_uri_scheme(value):
    return bool(urlparse(value).scheme)


def normalize_source_url(value):
    value = value.strip()
    if has_uri_scheme(value):
        return value
    return f"{endpoint_url().rstrip('/')}/{value.strip('/')}"


def normalize_target_url(value):
    value = value.strip()
    if has_uri_scheme(value):
        return value
    return f"s3://{value.strip('/')}"


def parse_s3_uri(uri):
    uri = normalize_target_url(uri)
    if not uri.startswith("s3://"):
        raise ValueError(f"Expected s3:// target URI, got: {uri}")

    bucket_and_key = uri[len("s3://"):].strip("/")
    bucket, prefix = bucket_and_key.split("/", 1)
    prefix = prefix.strip("/")

    if not prefix.endswith(".zarr"):
        raise ValueError(f"Target must be a .zarr prefix: {uri}")

    return bucket, prefix


def s3_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url(),
        aws_access_key_id=required_env("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=required_env("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
        config=Config(max_pool_connections=DELETE_WORKERS),
    )


def s3_store(uri):
    import s3fs

    bucket, prefix = parse_s3_uri(uri)
    filesystem = s3fs.S3FileSystem(
        client_kwargs={"endpoint_url": endpoint_url()},
        key=required_env("AWS_ACCESS_KEY_ID"),
        secret=required_env("AWS_SECRET_ACCESS_KEY"),
        token=os.environ.get("AWS_SESSION_TOKEN"),
    )
    return s3fs.S3Map(root=f"{bucket}/{prefix}", s3=filesystem, check=False)


def delete_existing_output(uri):
    bucket, prefix = parse_s3_uri(uri)
    client = s3_client()
    keys = []

    for page in client.get_paginator("list_objects_v2").paginate(
        Bucket=bucket,
        Prefix=f"{prefix}/",
    ):
        keys.extend(item["Key"] for item in page.get("Contents", []))

    if not keys:
        return

    workers = min(DELETE_WORKERS, len(keys))
    print(
        f"Deleting existing output: s3://{bucket}/{prefix}/ "
        f"({len(keys)} objects, {workers} workers)"
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(client.delete_object, Bucket=bucket, Key=key)
            for key in keys
        ]
        for index, future in enumerate(as_completed(futures), start=1):
            future.result()
            if index % 100 == 0 or index == len(keys):
                print(f"  Deleted {index}/{len(keys)}")


def add_success_marker(uri):
    bucket, prefix = parse_s3_uri(uri)
    key = f"{prefix}/{SUCCESS_MARKER}"
    s3_client().put_object(Bucket=bucket, Key=key, Body=b"", ContentType="text/plain")
    print(f"[OK] Added marker: s3://{bucket}/{key}")


def prepare_dataset(source_url):
    import rioxarray  # noqa: F401 - enables the .rio accessor
    import xarray as xr

    ds = xr.open_zarr(source_url, chunks={}, consolidated=True)
    ds = ds.rio.write_crs("EPSG:4326")
    ds = ds.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude")
    return ds


def print_dataset_summary(ds):
    print("Input dataset:")
    print(ds)
    print("\nVariables:")
    for name, data_array in ds.data_vars.items():
        print(f"  - {name}: dims={data_array.dims}, shape={data_array.shape}")


def int_env(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return int(value)


def main():
    source_url = normalize_source_url(required_env("SOURCE_URL"))
    target_url = normalize_target_url(required_env("TARGET_URL"))
    levels = int_env("LEVELS", 5)
    projection = os.environ.get("PYRAMID_PROJECTION", "equidistant-cylindrical")
    resampling = os.environ.get("PYRAMID_RESAMPLING", "nearest")
    extra_dim = os.environ.get("PYRAMID_EXTRA_DIM", "time")

    from dask.diagnostics import ProgressBar
    from ndpyramid import pyramid_reproject

    started = time.perf_counter()

    print(f"Opening input: {source_url}")
    open_started = time.perf_counter()
    ds = prepare_dataset(source_url)
    open_seconds = time.perf_counter() - open_started
    print_dataset_summary(ds)
    print(f"Opened/prepared metadata in {open_seconds:.2f} seconds")

    print(
        "Creating pyramid: "
        f"levels={levels}, projection={projection}, "
        f"resampling={resampling}, extra_dim={extra_dim}"
    )
    pyramid_started = time.perf_counter()
    pyramid = pyramid_reproject(
        ds,
        levels=levels,
        projection=projection,
        resampling=resampling,
        extra_dim=extra_dim,
    )
    pyramid_seconds = time.perf_counter() - pyramid_started
    print(f"Created pyramid task graph in {pyramid_seconds:.2f} seconds")

    print(f"Writing output: {target_url}")
    delete_existing_output(target_url)
    write_started = time.perf_counter()
    with ProgressBar():
        pyramid.to_zarr(
            s3_store(target_url),
            zarr_format=2,
            consolidated=True,
            mode="w",
        )
    write_seconds = time.perf_counter() - write_started
    add_success_marker(target_url)

    elapsed = time.perf_counter() - started
    print(f"Write time: {write_seconds:.2f} seconds")
    print(f"Total time: {elapsed:.2f} seconds")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
