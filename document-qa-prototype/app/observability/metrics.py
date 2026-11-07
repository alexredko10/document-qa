from prometheus_client import Counter, Gauge, Histogram


HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)

HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
)

HTTP_IN_FLIGHT = Gauge(
    "http_requests_in_flight",
    "HTTP requests currently being processed",
)