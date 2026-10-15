"""Bosch identity collection currently falls back to generic ONVIF.

Bosch's public RCP+ over CGI note documents reading a camera name, but does not
document a bounded native operation that supplies the identity fields required
by this collector (manufacturer, model, and serial). Do not issue a speculative
RCP+ command; report the vendor gap so the caller can continue with ONVIF.
"""
from __future__ import annotations

from typing import Any

from cam_scanner.domain.models import (
    CameraResult,
    CameraTarget,
    CollectionAttempt,
    CollectionReport,
)


class BoschAdapter:
    """Report the absence of documented vendor identity collection, without I/O."""

    def collect(self, target: CameraTarget, *, context: Any = None) -> CameraResult:
        return self.collect_report(target, context=context).to_camera_result(target.ip)

    def collect_report(self, target: CameraTarget, *, context: Any = None) -> CollectionReport:
        """Return a skipped vendor attempt; VendorFirstCollector then uses ONVIF."""
        del target  # no endpoint is called and no target data is retained
        del context
        return CollectionReport().with_attempt(
            CollectionAttempt(
                stage="VALIDATE",
                operation="collect",
                outcome="SKIPPED",
                error_category="ENDPOINT_UNSUPPORTED",
            )
        )
