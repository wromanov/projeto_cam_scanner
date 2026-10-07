"""Shared collection service contract."""
from cam_scanner.domain.models import CameraResult, CameraTarget


class InventoryService:
    def collect_one(self, target: CameraTarget) -> CameraResult:
        """Collect one camera using ONVIF-first policy (future implementation)."""
        raise NotImplementedError
