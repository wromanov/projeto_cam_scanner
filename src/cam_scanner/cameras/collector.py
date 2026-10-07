"""Camera collector contract; no network requests are made by this scaffold."""
from typing import Protocol

from cam_scanner.domain.models import CameraResult, CameraTarget


class CameraCollector(Protocol):
    """Collect read-only information from one camera target."""

    def collect(self, target: CameraTarget) -> CameraResult: ...
