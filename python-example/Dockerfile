FROM python:3.13.3-alpine3.21

RUN pip install fastapi uvicorn opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp-proto-grpc

COPY . /app

WORKDIR /app

EXPOSE 8000

ENTRYPOINT [ "python", "main.py" ]