# 安裝所需依賴:
# pip install fastapi uvicorn opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp-proto-grpc

from fastapi import FastAPI, HTTPException
import time
import random
import logging
import threading
import datetime
from typing import Optional

# OpenTelemetry 導入
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import os

# 環境變量設置 (可選)
OTEL_SERVICE_NAME = os.environ["OTEL_SERVICE_NAME"] 
if not OTEL_SERVICE_NAME:
    OTEL_SERVICE_NAME = "simple-fastapi-demo"  # 服務名稱
# Jaeger OTLP gRPC 端口 (可選，根據您的環境進行設置)
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"]  # Jaeger OTLP gRPC 端口
if not OTEL_EXPORTER_OTLP_ENDPOINT:
    OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4317"  # 默認端口

# 自定義日誌格式器
class CustomFormatter(logging.Formatter):
    def format(self, record):
        # 獲取當前span的上下文
        span_context = trace.get_current_span().get_span_context()
        
        # 獲取trace_id和span_id (如果有的話)
        trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else ""
        span_id = f"{span_context.span_id:016x}" if span_context.is_valid else ""
        
        # 獲取ISO時間戳
        iso_time = datetime.datetime.now().isoformat()
        
        # 獲取線程ID
        thread_id = threading.get_ident()
        
        # 創建標準格式的日誌消息
        log_msg = record.getMessage()
        
        # 使用[%s]格式包裝每個字段
        formatted_msg = f"[{iso_time}] [{record.levelname}] [{thread_id}] [trace_id={trace_id}, span_id={span_id}] [{log_msg}]"
        
        return formatted_msg

# 設置日誌
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())
logger.addHandler(handler)

# 設置 OpenTelemetry
resource = Resource(attributes={
    SERVICE_NAME: OTEL_SERVICE_NAME
})

# 設置 OTLP 導出器
otlp_exporter = OTLPSpanExporter(
    endpoint=OTEL_EXPORTER_OTLP_ENDPOINT,  # 使用您的 Jaeger OTLP gRPC 端口
    insecure=True
)

# 設置 TracerProvider
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

# 獲取追蹤器
tracer = trace.get_tracer(__name__)

# 創建 FastAPI 應用
app = FastAPI(title="FastAPI OpenTelemetry Example")

# 簡單的封裝函數，替代 with tracer.start_as_current_span
def traced_span(name):
    return tracer.start_as_current_span(name)

@app.get("/success")
async def success_endpoint():
    with traced_span("success_operation"):
        # 模擬一些處理時間
        time.sleep(random.uniform(0.1, 0.3))
        
        # 獲取當前 span 並添加一些屬性
        current_span = trace.get_current_span()
        current_span.set_attribute("endpoint.status", "success")
        current_span.set_attribute("operation.duration", "fast")
        
        # 記錄日誌消息
        logger.info("Success Endpoint was be called")
        logger.info("Completing success operation, returning 200 status code")
        
        return {"message": "Success", "status": "ok"}

@app.get("/error")
async def error_endpoint():
    with traced_span("error_operation"):
        # 模擬一些處理時間
        time.sleep(random.uniform(0.1, 0.5))
        
        # 獲取當前 span 並添加一些屬性
        current_span = trace.get_current_span()
        current_span.set_attribute("endpoint.status", "error")
        current_span.set_attribute("error.type", "simulated_failure")
        
        # 添加一個事件到 span
        current_span.add_event("error_triggered", {"reason": "manual_simulation"})
        
        # 設置 span 狀態為錯誤
        current_span.set_status(trace.Status(trace.StatusCode.ERROR))
        
        # 記錄日誌消息
        logger.info("Error Endpoint was be called")
        logger.error("Simulated error occurred, returning status code 500")
        
        # 拋出 HTTP 異常
        raise HTTPException(status_code=500, detail="Simulated error occurred")

# 將FastAPI應用程序設置為OpenTelemetry追蹤
FastAPIInstrumentor.instrument_app(app)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=8000)