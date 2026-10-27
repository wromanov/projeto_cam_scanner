from __future__ import annotations

from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from cam_scanner.domain.models import is_safe_xml_text
from cam_scanner.excel.reader import ExcelReader, _parse_row


def test_row_with_only_extra_column_is_ignored(tmp_path: Path) -> None:
    source = tmp_path / "extra-only-row.xlsx"
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(("IP", "USERNAME", "PASSWORD", "NOTES"))
    worksheet.append((None, None, None, "extra-column-only"))
    workbook.save(source)
    workbook.close()

    batch = ExcelReader().read(source)

    assert batch.total_rows == 0
    assert list(batch.rows) == []


def test_malformed_rows_clear_credentials_and_redact_ip_overlap(tmp_path: Path) -> None:
    source = tmp_path / "malformed-input.xlsx"
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(("IP", "USERNAME", "PASSWORD"))
    worksheet.append(("192.0.2.14", "valid-user", "valid-password"))
    # The malformed IP contains both credentials; it must never become display data.
    worksheet.append(("bad-valid-user-valid-password", "valid-user", "valid-password"))
    # Missing username still leaves a password that overlaps the malformed IP.
    worksheet.append(("bad-password-only", None, "password-only"))
    worksheet.append(("https://embedded-secret@192.0.2.20", "different-user", "different-password"))
    workbook.save(source)
    workbook.close()

    batch = ExcelReader().read(source)
    rows = list(batch.rows)

    assert batch.total_rows == 4
    assert [row.row_id for row in rows] == [2, 3, 4, 5]
    assert rows[0].valid
    assert rows[0].ip == "192.0.2.14"

    overlap, missing_username, url_credentials = rows[1:]
    assert not overlap.valid
    assert overlap.validation_error == "invalid_ip"
    assert overlap.username == overlap.password == ""
    assert overlap.ip == "<invalid>"
    assert "valid-user" not in repr(overlap)
    assert "valid-password" not in repr(overlap)
    assert "valid-user" not in overlap.ip
    assert "valid-password" not in overlap.ip

    assert not missing_username.valid
    assert missing_username.validation_error == "missing_required_value"
    assert missing_username.username == missing_username.password == ""
    assert missing_username.ip == "<invalid>"
    assert "password-only" not in repr(missing_username)
    assert "password-only" not in missing_username.ip

    assert not url_credentials.valid
    assert url_credentials.ip == "<invalid>"
    assert "embedded-secret" not in repr(url_credentials)


@pytest.mark.parametrize(
    "text",
    ["bad\x01text", "bad\x1b[31m", "bad\x85text", "bad\ud800", "x" * 32_768],
    ids=("control", "escape", "c1-control", "surrogate", "oversize"),
)
def test_domain_text_validation_rejects_xml_controls_surrogates_and_oversize(text: str) -> None:
    assert not is_safe_xml_text(text)


@pytest.mark.parametrize("text", ["Câmera – 東京", "linha 1\nlinha 2", "tab\tpermitido"])
def test_domain_text_validation_preserves_valid_unicode_and_xml_whitespace(text: str) -> None:
    assert is_safe_xml_text(text)


def test_invalid_input_cell_isolated_and_credentials_cleared() -> None:
    row = _parse_row(
        7,
        ("192.0.2.7", "operator", "secret\x01"),
        {"ip": 0, "username": 1, "password": 2},
    )

    assert row.row_id == 7
    assert not row.valid
    assert row.validation_error == "invalid_cell_value"
    assert row.username == row.password == ""


@pytest.mark.parametrize(
    ("header", "value", "expected"),
    [
        (("IP", "USERNAME", "PASSWORD", "FABRICANTE"), "HIK", "HIK"),
        (("IP", "USERNAME", "PASSWORD", "FABRICANTE"), "Vendor secret text", "Vendor secret text"),
        (("IP", "USERNAME", "PASSWORD"), "Hikvision", None),
        (("IP", "USERNAME", "PASSWORD", "FABRICANTE"), "Axis " + "x" * 129, None),
    ],
    ids=("recognized-alias-literal", "unknown-literal", "missing-column", "oversized"),
)
def test_manufacturer_hint_is_optional_recognized_only_and_not_in_repr(
    tmp_path: Path,
    header: tuple[str, ...],
    value: str,
    expected: str | None,
) -> None:
    source = tmp_path / "manufacturer-hint.xlsx"
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(header)
    row = ("192.0.2.44", "operator", "password")
    if len(header) == 4:
        row += (value,)
    worksheet.append(row)
    workbook.save(source)
    workbook.close()

    parsed = next(ExcelReader().read(source).rows)

    assert parsed.valid
    assert parsed.manufacturer_hint == expected
    assert "Vendor secret text" not in repr(parsed)
    assert "password" not in repr(parsed)
