# Zarr Pyramid Reproject Container

Build:

```bash
docker build -t zarr-pyramid-reproject .
```

Run:

```bash
docker run --rm \
  -e SOURCE_URL="project-moiai-octo/public/octo/v0/ai-gallery/octo-glonet-p1d/2026-05-27/2026-05-27.zarr" \
  -e TARGET_URL="project-moiai-octo/public/octo/v0/ai-gallery/octo-glonet-p1d/2026-05-27/2026-05-27.pyramid.zarr" \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  zarr-pyramid-reproject
```

Optional settings:

```bash
-e AWS_S3_ENDPOINT="minio.dive.edito.eu"
-e DELETE_WORKERS=16
-e LEVELS=5
-e PYRAMID_PROJECTION="equidistant-cylindrical"
-e PYRAMID_RESAMPLING="nearest"
-e PYRAMID_EXTRA_DIM="time"
```

`SOURCE_URL` and `TARGET_URL` can be provided as bare `bucket/path` values.
The container expands source paths to `https://<AWS_S3_ENDPOINT>/bucket/path`
and target paths to `s3://bucket/path`. `AWS_S3_ENDPOINT` defaults to
`minio.dive.edito.eu` when it is not provided. Full `https://...` source URLs
and `s3://...` target URLs are still accepted.

Use `LEVELS` to set the number of pyramid levels.
Use `DELETE_WORKERS` to control how many existing target objects are deleted in
parallel before writing the new output.

The container deletes any existing target `.zarr` prefix, writes the new Zarr v2
pyramid, consolidates metadata, and adds a `_SUCCESS` marker.
