from prometheus_client import Counter, Histogram, Gauge, start_http_server
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PrometheusMetrics:
    def __init__(self):
        self.documents_processed_total = Counter(
            'documents_processed_total',
            'Total number of documents processed',
            ['section_type']
        )
        
        self.documents_failed_total = Counter(
            'documents_failed_total',
            'Total number of documents that failed to process'
        )
        
        self.document_processing_seconds = Histogram(
            'document_processing_seconds',
            'Time spent processing documents',
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0]
        )
        
        self.duplicates_found_total = Counter(
            'duplicates_found_total',
            'Total number of duplicates found',
            ['section_type']
        )
        
        self.entries_extracted_total = Counter(
            'entries_extracted_total',
            'Total number of entries extracted',
            ['section_type']
        )
        
        self.confidence_score = Histogram(
            'confidence_score',
            'Confidence scores for section extraction',
            ['section_type'],
            buckets=[0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        )
        
        self.active_workers = Gauge(
            'active_workers',
            'Number of active workers'
        )
        
        self.processing_queue_size = Gauge(
            'processing_queue_size',
            'Size of processing queue'
        )
    
    def start_metrics_server(self, port: int = 8001):
        """Start Prometheus metrics server"""
        try:
            start_http_server(port)
            logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {str(e)}")


_prometheus_metrics: PrometheusMetrics | None = None


def get_prometheus_metrics() -> PrometheusMetrics:
    global _prometheus_metrics
    if _prometheus_metrics is None:
        _prometheus_metrics = PrometheusMetrics()
    return _prometheus_metrics
