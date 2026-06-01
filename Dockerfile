FROM mambaorg/micromamba:1.5.10

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml \
    && micromamba run -n base python -c "import numpy, xarray, ndpyramid; print('numpy', numpy.__version__); print('xarray', xarray.__version__); print('ndpyramid', getattr(ndpyramid, '__version__', 'unknown'))" \
    && micromamba clean -a -y

WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER reproject_zarr_to_s3.py /app/reproject_zarr_to_s3.py

ENTRYPOINT ["micromamba", "run", "-n", "base", "python", "/app/reproject_zarr_to_s3.py"]
