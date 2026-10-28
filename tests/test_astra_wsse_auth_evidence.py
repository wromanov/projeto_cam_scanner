from __future__ import annotations

import base64
import hashlib
import xml.etree.ElementTree as ET

import pytest

from cam_scanner.cameras.transport import _soap_has_wsse_credentials

SOAP12 = "http://www.w3.org/2003/05/soap-envelope"
WSSE = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-wssecurity-secext-1.0.xsd"
)
WSU = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-wssecurity-utility-1.0.xsd"
)
PASSWORD_DIGEST = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-username-token-profile-1.0#PasswordDigest"
)
BASE64_BINARY = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-soap-message-security-1.0#Base64Binary"
)


def _username_token_request(
    username: str = "synthetic-viewer",
    password: str = "synthetic-secret",
    *,
    nonce: bytes = b"synthetic-nonce",
    created: str = "2026-10-28T04:00:00Z",
    password_type: str = PASSWORD_DIGEST,
) -> bytes:
    envelope = ET.Element(f"{{{SOAP12}}}Envelope")
    header = ET.SubElement(envelope, f"{{{SOAP12}}}Header")
    security = ET.SubElement(header, f"{{{WSSE}}}Security")
    token = ET.SubElement(security, f"{{{WSSE}}}UsernameToken")
    ET.SubElement(token, f"{{{WSSE}}}Username").text = username
    digest = base64.b64encode(
        hashlib.sha1(nonce + created.encode("utf-8") + password.encode("utf-8")).digest()
    ).decode("ascii")
    ET.SubElement(token, f"{{{WSSE}}}Password", {"Type": password_type}).text = digest
    ET.SubElement(
        token,
        f"{{{WSSE}}}Nonce",
        {"EncodingType": BASE64_BINARY},
    ).text = base64.b64encode(nonce).decode("ascii")
    ET.SubElement(token, f"{{{WSU}}}Created").text = created
    body = ET.SubElement(envelope, f"{{{SOAP12}}}Body")
    ET.SubElement(body, "{http://www.onvif.org/ver10/device/wsdl}GetDeviceInformation")
    return ET.tostring(envelope, encoding="utf-8")


def test_wsse_auth_evidence_requires_valid_username_token_bound_to_row_credentials() -> None:
    request = _username_token_request()

    assert _soap_has_wsse_credentials(request, "synthetic-viewer", "synthetic-secret")
    assert not _soap_has_wsse_credentials(request, "other-account", "synthetic-secret")
    assert not _soap_has_wsse_credentials(request, "synthetic-viewer", "wrong-secret")


def test_bare_username_token_xml_does_not_count_as_wsse_authentication() -> None:
    bare_token = (
        f'<wsse:UsernameToken xmlns:wsse="{WSSE}">'
        "<wsse:Username>synthetic-viewer</wsse:Username>"
        "<wsse:Password>not-a-digest</wsse:Password>"
        "</wsse:UsernameToken>"
    ).encode()

    assert not _soap_has_wsse_credentials(
        bare_token, "synthetic-viewer", "synthetic-secret"
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"password_type": f"{WSSE}#PasswordText"},
        {"nonce": b""},
        {"created": ""},
    ],
)
def test_wsse_auth_evidence_rejects_incomplete_or_unsupported_tokens(
    kwargs: dict[str, object],
) -> None:
    request = _username_token_request(**kwargs)  # type: ignore[arg-type]

    assert not _soap_has_wsse_credentials(request, "synthetic-viewer", "synthetic-secret")
