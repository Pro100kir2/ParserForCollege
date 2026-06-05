import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from threading import local
from src.utils.logger import get_logger

logger = get_logger(__name__)


_thread_local = local()


@dataclass
class TraceContext:
    run_id: str
    chunk_id: Optional[str] = None
    worker_id: Optional[int] = None
    document_name: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "chunk_id": self.chunk_id,
            "worker_id": self.worker_id,
            "document": self.document_name,
            "duration_ms": int((time.time() - self.start_time) * 1000)
        }


class Tracer:
    def __init__(self):
        self.current_run_id: Optional[str] = None
    
    def generate_run_id(self) -> str:
        """Generate unique run ID: YYYYMMDD-HHMMSS-<random>"""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        random_suffix = uuid.uuid4().hex[:6]
        return f"{timestamp}-{random_suffix}"
    
    def start_run(self) -> str:
        """Start a new run and return run_id"""
        self.current_run_id = self.generate_run_id()
        logger.info(f"Starting run: {self.current_run_id}")
        return self.current_run_id
    
    def set_chunk_context(self, chunk_id: str):
        """Set chunk context for current thread"""
        if not hasattr(_thread_local, 'context'):
            _thread_local.context = TraceContext(run_id=self.current_run_id or "")
        _thread_local.context.chunk_id = chunk_id
    
    def set_worker_context(self, worker_id: int):
        """Set worker context for current thread"""
        if not hasattr(_thread_local, 'context'):
            _thread_local.context = TraceContext(run_id=self.current_run_id or "")
        _thread_local.context.worker_id = worker_id
    
    def set_document_context(self, document_name: str):
        """Set document context for current thread"""
        if not hasattr(_thread_local, 'context'):
            _thread_local.context = TraceContext(run_id=self.current_run_id or "")
        _thread_local.context.document_name = document_name
        _thread_local.context.start_time = time.time()
    
    def get_context(self) -> Optional[TraceContext]:
        """Get current trace context"""
        return getattr(_thread_local, 'context', None)
    
    def log_with_context(self, message: str, level: str = "info"):
        """Log message with current trace context"""
        context = self.get_context()
        if context:
            log_data = context.to_dict()
            log_data["message"] = message
            if level == "info":
                logger.info(log_data)
            elif level == "error":
                logger.error(log_data)
            elif level == "warning":
                logger.warning(log_data)
            elif level == "debug":
                logger.debug(log_data)
        else:
            logger.info(message)
    
    def clear_context(self):
        """Clear trace context for current thread"""
        if hasattr(_thread_local, 'context'):
            del _thread_local.context


_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer
