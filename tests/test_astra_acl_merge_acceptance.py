"""ASTRA focal acceptance for monotonic field evidence merge.

The production flow has no Viewer/Operator/Admin role-to-operation interface.
These tests therefore cover the real report merge contract only; they do not
provide a test-owned ACL or claim an ACL acceptance result.
"""
from __future__ import annotations

from cam_scanner.domain.models import (
    CollectionReport,
    EvidenceRecord,
)

_TARGET_USERNAME = "merge-fixture-account-canary"
_TARGET_PASSWORD = "merge-fixture-credential-canary"


def _has_sensitive_evidence(report: CollectionReport) -> bool:
    sensitive = (_TARGET_USERNAME.casefold(), _TARGET_PASSWORD.casefold())
    return any(
        secret in record.value.casefold()
        for record in report.evidence
        for secret in sensitive
    )


def _provenance_signature(
    report: CollectionReport,
) -> tuple[tuple[str, tuple[tuple[str, str, str | None, str | None], ...]], ...]:
    """Make order and provenance observable without emitting evidence values."""
    return tuple(
        (
            field_name,
            tuple(
                (record.value, record.source, record.protocol, record.operation)
                for record in records
            ),
        )
        for field_name, records in report.provenance
    )


def _assert_provenance_content(report: CollectionReport) -> None:
    expected = (
        (
            "hardware_id",
            (
                ("HW-ID-FIXTURE-02", "FIXTURE", "ONVIF", "GetDeviceInformation"),
                ("HW-ID-OBSERVED-01", "ONVIF", "ONVIF", "GetDeviceInformation"),
            ),
        ),
        (
            "mac",
            (
                ("02:00:00:00:00:01", "VENDOR", "HTTPS", "GET /cgi-bin/getinfo"),
                ("02:00:00:00:00:02", "FIXTURE", "HTTPS", "GET /cgi-bin/getinfo"),
            ),
        ),
    )
    actual = tuple(
        (field_name, tuple(sorted(records)))
        for field_name, records in _provenance_signature(report)
    )
    if actual != expected:
        raise AssertionError("merged evidence provenance is incomplete or contains invalid data")


def test_partial_conflicting_and_empty_evidence_merge_is_monotonic_in_both_orders() -> None:
    observed = CollectionReport(
        evidence=(
            EvidenceRecord(
                field="hardware_id",
                value="HW-ID-OBSERVED-01",
                source="ONVIF",
                protocol="ONVIF",
                operation="GetDeviceInformation",
            ),
            EvidenceRecord(
                field="mac",
                value="02:00:00:00:00:01",
                source="VENDOR",
                protocol="HTTPS",
                operation="GET /cgi-bin/getinfo",
            ),
        )
    )
    conflicting_partial = CollectionReport(
        evidence=(
            EvidenceRecord(
                field="hardware_id",
                value="HW-ID-FIXTURE-02",
                source="FIXTURE",
                protocol="ONVIF",
                operation="GetDeviceInformation",
            ),
            EvidenceRecord(
                field="mac",
                value="02:00:00:00:00:02",
                source="FIXTURE",
                protocol="HTTPS",
                operation="GET /cgi-bin/getinfo",
            ),
            EvidenceRecord(
                field="hardware_id",
                value=_TARGET_USERNAME,
                source="FIXTURE",
                protocol="ONVIF",
                operation="GetDeviceInformation",
            ),
            EvidenceRecord(
                field="hardware_id",
                value=_TARGET_PASSWORD,
                source="FIXTURE",
                protocol="ONVIF",
                operation="GetDeviceInformation",
            ),
        )
    ).validated_for_target((_TARGET_USERNAME, _TARGET_PASSWORD))
    empty = CollectionReport()

    # Empty and secret-bearing follow-up reports must not erase prior values;
    # valid conflicting observations remain as evidence in either merge order.
    left_to_right = observed.merged(empty).merged(conflicting_partial)
    right_to_left = conflicting_partial.merged(empty).merged(observed)

    for merged in (left_to_right, right_to_left):
        if _has_sensitive_evidence(merged):
            raise AssertionError("target credential entered merged evidence")
        if merged.values_for("hardware_id") != (
            "HW-ID-FIXTURE-02",
            "HW-ID-OBSERVED-01",
        ):
            raise AssertionError("valid hardware ID evidence was lost or reordered")
        if merged.values_for("mac") != (
            "02:00:00:00:00:01",
            "02:00:00:00:00:02",
        ):
            raise AssertionError("valid MAC evidence was lost or reordered")
        if merged.conflicts != ("hardware_id", "mac"):
            raise AssertionError("conflicting evidence was not retained")

    _assert_provenance_content(left_to_right)
    _assert_provenance_content(right_to_left)
    if _provenance_signature(left_to_right) != _provenance_signature(right_to_left):
        raise AssertionError("merged evidence provenance depends on merge order")
