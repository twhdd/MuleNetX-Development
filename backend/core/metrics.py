from prometheus_client import (
    Counter
)

API_REQUESTS = Counter(
    "api_requests_total",
    "API Requests"
)
