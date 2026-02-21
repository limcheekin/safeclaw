from prometheus_client import Counter, Histogram
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from safeclaw.config.settings import settings

# Prometheus Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    ["method", "endpoint"]
)

CERBOS_CALL_DURATION_SECONDS = Histogram(
    "cerbos_call_duration_seconds",
    "Duration of calls to Cerbos PDP in seconds",
    ["action", "resource"]
)

CERBOS_DECISION_CACHE_HIT_TOTAL = Counter(
    "cerbos_decision_cache_hit_total",
    "Total number of Cerbos decision cache hits",
    ["resource", "action"]
)

CERBOS_DECISION_TOTAL = Counter(
    "cerbos_decision_total",
    "Total number of Cerbos decisions",
    ["result", "resource", "action"]
)

# OpenTelemetry Setup
def configure_telemetry() -> None:
    resource = Resource.create(attributes={
        ResourceAttributes.SERVICE_NAME: settings.MCP_SERVER_NAME,
        ResourceAttributes.SERVICE_VERSION: "0.1.0",
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.APP_ENV,
    })

    trace.set_tracer_provider(TracerProvider(resource=resource))
    # In a real setup, we would add OTLP exporter here.
    # For now, we rely on auto-instrumentation or manual spans.

tracer = trace.get_tracer(__name__)
