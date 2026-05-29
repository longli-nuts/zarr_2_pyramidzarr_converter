# Zarr Pyramid Reproject Container

Build:

```bash
docker build -t zarr-pyramid-reproject .
```

Run:

```bash
docker run --rm \
  -e SOURCE_URL="https://minio.dive.edito.eu/project-moiai-octo/public/octo/v0/ai-gallery/octo-glonet-p1d/2026-05-27/2026-05-27.zarr" \
  -e TARGET_URL="s3://project-moiai-octo/public/octo/v0/ai-gallery/octo-glonet-p1d/2026-05-27/2026-05-27.pyramid.zarr" \
  -e AWS_S3_ENDPOINT="minio.dive.edito.eu" \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  zarr-pyramid-reproject
```

Optional settings:

```bash
-e PYRAMID_LEVELS=5
-e PYRAMID_PROJECTION="equidistant-cylindrical"
-e PYRAMID_RESAMPLING="nearest"
-e PYRAMID_EXTRA_DIM="time"
```

The container deletes any existing target `.zarr` prefix, writes the new Zarr v2
pyramid, consolidates metadata, and adds a `_SUCCESS` marker.
