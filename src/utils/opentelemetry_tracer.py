from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry import trace as trace_api
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenTelemetryTracer:
    def __init__(self):
        self.tracer = None
        self._setup_tracing()
    
    def _setup_tracing(self):
        """Setup OpenTelemetry tracing"""
        try:
            provider = TracerProvider()
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace_api.set_tracer_provider(provider)
            self.tracer = trace_api.get_tracer(__name__)
            logger.info("OpenTelemetry tracing initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {str(e)}")
    
    def start_span(self, name: str):
        """Start a new span"""
        if self.tracer:
            return self.tracer.start_span(name)
        return None
    
    def get_tracer(self):
        """Get the tracer instance"""
        return self.tracer


_opentelemetry_tracer: OpenTelemetryTracer | None = None


def get_opentelemetry_tracer() -> OpenTelemetryTracer:
    global _opentelemetry_tracer
    if _opentelemetry_tracer is None:
        _opentelemetry_tracer = OpenTelemetryTracer()
    return _opentelemetry_tracer
