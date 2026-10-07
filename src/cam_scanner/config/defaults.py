"""Safe configuration defaults, independent of machine-specific paths."""
DEFAULT_SETTINGS = {
    "collection": {
        "connect_timeout_seconds": 3,
        "request_timeout_seconds": 7,
        "onvif_budget_seconds": 15,
        "manufacturer_budget_seconds": 10,
        "camera_soft_deadline_seconds": 45,
        "max_retries": 1,
        "retry_backoff_seconds": 1,
    },
    "concurrency": {
        "default_max_workers": 8,
        "min_workers": 1,
        "max_workers": 32,
        "max_concurrent_rtsp": 2,
    },
}
