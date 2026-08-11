FROM python:3.14-slim

RUN useradd --system --uid 10001 --home-dir /nonexistent conformesh
COPY --chown=10001:10001 conformesh_spike/pipeline_cli.py /opt/conformesh/pipeline_cli.py

USER 10001:10001
WORKDIR /work
ENTRYPOINT ["python", "/opt/conformesh/pipeline_cli.py"]
