from cam_scanner.domain.enums import CollectionMethod
from cam_scanner.domain.models import CollectionReport, EvidenceRecord


def _vendor_report(operation: str, protocol: str = "HTTP") -> CollectionReport:
    return CollectionReport(
        evidence=(
            EvidenceRecord(
                field="manufacturer",
                value="Axis",
                source="VENDOR",
                protocol=protocol,
                operation=operation,
            ),
            EvidenceRecord(
                field="model",
                value="M1135",
                source="VENDOR",
                protocol=protocol,
                operation=operation,
            ),
            EvidenceRecord(
                field="serial",
                value="ABC123",
                source="VENDOR",
                protocol=protocol,
                operation=operation,
            ),
        )
    )


def test_vendor_http_operations_are_preserved_as_a_collection_method() -> None:
    report = _vendor_report("POST /axis-cgi/basicdeviceinfo.cgi getAllProperties")

    result = report.to_camera_result("192.0.2.1")

    assert result.collection_method is CollectionMethod.VENDOR_HTTP
    assert result.status.value == "SUCCESS"


def test_vendor_https_operations_are_preserved_as_a_collection_method() -> None:
    report = _vendor_report("POST /axis-cgi/basicdeviceinfo.cgi getAllProperties", "HTTPS")

    result = report.to_camera_result("192.0.2.1")

    assert result.collection_method is CollectionMethod.VENDOR_HTTP
    assert result.status.value == "SUCCESS"


def test_hikvision_keeps_its_existing_collection_method() -> None:
    report = _vendor_report("GET /ISAPI/System/deviceInfo")

    result = report.to_camera_result("192.0.2.1")

    assert result.collection_method is CollectionMethod.HIKVISION_ISAPI
