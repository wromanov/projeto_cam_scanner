"""Snapshot orchestration contract; no capture or temporary files are created."""


class SnapshotService:
    def capture_one(self, target: object) -> object:
        """Try ONVIF HTTP, vendor HTTP, then RTSP frame (future implementation)."""
        raise NotImplementedError
