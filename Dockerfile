FROM mambaorg/micromamba:1.5.10

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml \
    && micromamba clean -a -y

WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER reproject_zarr_to_s3.py /app/reproject_zarr_to_s3.py

ENTRYPOINT ["python", "/app/reproject_zarr_to_s3.py"]
