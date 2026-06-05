from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import psutil
from src.services.parsing_service import ParsingService
from src.utils.logger import get_logger
from src.utils.metrics import MetricsCollector

logger = get_logger(__name__)

app = FastAPI(
    title="RPD Document Parser API",
    description="API for parsing university curriculum documents (RPD)",
    version="1.0.0"
)


class ParseRequest(BaseModel):
    input_path: str = Field(..., description="Path to directory containing RPD documents")
    output_path: Optional[str] = Field(None, description="Optional output directory path")
    async_mode: bool = Field(False, description="Use async processing with workers")


class ParseResponse(BaseModel):
    status: str
    output_files: List[str]
    statistics: dict
    metrics: dict


class ErrorResponse(BaseModel):
    status: str
    error: str


class HealthResponse(BaseModel):
    status: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    uptime: float


class MetricsResponse(BaseModel):
    current: dict
    history: List[dict]
    alerts: List[str]


parsing_service = ParsingService()
metrics_collector = MetricsCollector()
start_time = psutil.boot_time()


@app.get("/")
async def root():
    return {
        "message": "RPD Document Parser API",
        "version": "1.0.0",
        "endpoints": {
            "parse": "/parse",
            "health": "/health",
            "metrics": "/metrics",
            "performance": "/performance"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    uptime = psutil.time.time() - start_time
    
    return HealthResponse(
        status="healthy",
        cpu_usage=cpu_percent,
        memory_usage=memory.percent,
        disk_usage=disk.percent,
        uptime=uptime
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    current_metrics = metrics_collector.get_current_metrics()
    history = metrics_collector.get_history()
    
    alerts = []
    settings = parsing_service.settings
    if metrics_collector.check_alerts(settings.alert_error_threshold, settings.alert_error_window_minutes):
        alerts.append(f"Error threshold exceeded: {settings.alert_error_threshold} errors in {settings.alert_error_window_minutes} minutes")
    
    return MetricsResponse(
        current=current_metrics,
        history=history,
        alerts=alerts
    )


@app.get("/performance")
async def get_performance():
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu": {
            "percent": cpu_percent,
            "count": psutil.cpu_count()
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent
        },
        "process": {
            "pid": os.getpid(),
            "memory_info": dict(psutil.Process(os.getpid()).memory_info()._asdict())
        }
    }


@app.post("/parse", response_model=ParseResponse)
async def parse_documents(request: ParseRequest, background_tasks: BackgroundTasks):
    try:
        logger.info(f"Received parse request for: {request.input_path}")
        
        if not os.path.exists(request.input_path):
            raise HTTPException(status_code=400, detail=f"Input path does not exist: {request.input_path}")
        
        if not os.path.isdir(request.input_path):
            raise HTTPException(status_code=400, detail=f"Input path is not a directory: {request.input_path}")
        
        output_path = request.output_path or "./output"
        
        if request.async_mode:
            result = await parsing_service.process_directory_async(request.input_path, output_path)
        else:
            result = parsing_service.process_directory(request.input_path, output_path)
        
        # Get output files
        output_files = []
        if os.path.exists(output_path):
            for filename in os.listdir(output_path):
                if filename.endswith('.xlsx'):
                    output_files.append(os.path.join(output_path, filename))
        
        current_metrics = metrics_collector.get_current_metrics()
        
        response = ParseResponse(
            status="completed",
            output_files=output_files,
            statistics={
                "processed_files": result.processed_files,
                "failed_files": result.failed_files,
                "failed_file_list": result.failed_file_list,
                "low_confidence_files": result.low_confidence_files,
                "main_literature_count": len(result.main_literature),
                "additional_literature_count": len(result.additional_literature),
                "material_resources_count": len(result.material_resources),
                "extractor_version": result.extractor_version
            },
            metrics=current_metrics
        )
        
        logger.info(f"Parse completed successfully. Output files: {output_files}")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "error": exc.detail}
    )
