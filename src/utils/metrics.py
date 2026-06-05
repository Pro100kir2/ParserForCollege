import time
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ErrorRecord:
    timestamp: datetime
    file_name: str
    error_message: str


@dataclass
class ProcessingMetrics:
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    start_time: datetime = None
    end_time: datetime = None
    errors: List[ErrorRecord] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)
    
    def start(self):
        with self._lock:
            self.start_time = datetime.now()
            self.total_files = 0
            self.processed_files = 0
            self.failed_files = 0
            self.errors.clear()
    
    def finish(self):
        with self._lock:
            self.end_time = datetime.now()
    
    def record_success(self):
        with self._lock:
            self.processed_files += 1
    
    def record_failure(self, file_name: str, error_message: str):
        with self._lock:
            self.failed_files += 1
            self.errors.append(ErrorRecord(
                timestamp=datetime.now(),
                file_name=file_name,
                error_message=error_message
            ))
    
    def get_execution_time(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
    
    def get_error_rate(self) -> float:
        with self._lock:
            total = self.processed_files + self.failed_files
            if total == 0:
                return 0.0
            return (self.failed_files / total) * 100
    
    def get_recent_errors(self, window_minutes: int = 10) -> List[ErrorRecord]:
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        with self._lock:
            return [e for e in self.errors if e.timestamp >= cutoff]
    
    def should_alert(self, threshold: int, window_minutes: int) -> bool:
        recent_errors = self.get_recent_errors(window_minutes)
        return len(recent_errors) >= threshold


class MetricsCollector:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.current_metrics = ProcessingMetrics()
                    cls._instance.history: List[ProcessingMetrics] = []
        return cls._instance
    
    def start_processing(self):
        self.current_metrics.start()
        logger.info("Metrics collection started")
    
    def finish_processing(self):
        self.current_metrics.finish()
        self.history.append(self.current_metrics)
        logger.info(f"Metrics collection finished. Execution time: {self.current_metrics.get_execution_time():.2f}s")
    
    def record_success(self):
        self.current_metrics.record_success()
    
    def record_failure(self, file_name: str, error_message: str):
        self.current_metrics.record_failure(file_name, error_message)
        logger.error(f"Recorded failure for {file_name}: {error_message}")
    
    def get_current_metrics(self) -> Dict:
        return {
            "total_files": self.current_metrics.total_files,
            "processed_files": self.current_metrics.processed_files,
            "failed_files": self.current_metrics.failed_files,
            "execution_time": self.current_metrics.get_execution_time(),
            "error_rate": self.current_metrics.get_error_rate(),
            "recent_errors_count": len(self.current_metrics.get_recent_errors())
        }
    
    def check_alerts(self, threshold: int, window_minutes: int) -> bool:
        if self.current_metrics.should_alert(threshold, window_minutes):
            recent_errors = self.current_metrics.get_recent_errors(window_minutes)
            logger.warning(f"ALERT: {len(recent_errors)} errors in last {window_minutes} minutes (threshold: {threshold})")
            return True
        return False
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        recent = self.history[-limit:]
        return [
            {
                "processed_files": m.processed_files,
                "failed_files": m.failed_files,
                "execution_time": m.get_execution_time(),
                "error_rate": m.get_error_rate(),
                "timestamp": m.start_time.isoformat() if m.start_time else None
            }
            for m in recent
        ]
