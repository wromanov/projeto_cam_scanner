"""Safe embedded defaults; values are independent of install/CWD paths."""
from types import MappingProxyType

DEFAULT_SETTINGS = MappingProxyType({
    "collection": MappingProxyType({
        "connect_timeout_seconds": 3,
        "request_timeout_seconds": 7,
        "onvif_budget_seconds": 15,
        "manufacturer_budget_seconds": 10,
        "camera_soft_deadline_seconds": 45,
        "max_retries": 0,
        "retry_backoff_seconds": 1,
    }),
    "concurrency": MappingProxyType({
        "default_max_workers": 8,
        "min_workers": 1,
        "max_workers": 32,
        "max_concurrent_rtsp": 1,
    }),
    "snapshot": MappingProxyType({
        "http_timeout_seconds": 10,
        "rtsp_open_timeout_seconds": 8,
        "rtsp_first_frame_timeout_seconds": 5,
        "thumbnail_width": 320,
        "thumbnail_height": 180,
        "jpeg_quality": 75,
        "keep_temporary_files": False,
    }),
    "logging": MappingProxyType({
        "level": "INFO",
        "retention_days": 30,
        "max_file_size_mb": 10,
    }),
    "transport": MappingProxyType({"rules": ()}),
})
