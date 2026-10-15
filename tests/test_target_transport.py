"""Offline checks for the target-bound Requests/Zeep path."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from cam_scanner.application.collection_context import CollectionContext
from cam_scanner.cameras.transport import (
    ControlledOnvifClient,
    TargetRejected,
    TargetTransportPolicy,
)
from cam_scanner.domain.models import CameraTarget


def _context(port: int | None = None) -> CollectionContext:
    rules = () if port is None else (SimpleNamespace(
        target="127.0.0.1", component="onvif_device", protocol="http", host=None,
        port=port,
    ),)
    return CollectionContext(
        CameraTarget("127.0.0.1", "operator", "secret"),
        SimpleNamespace(transport_rules=rules),
        transport_factory=TargetTransportPolicy,
    )


def test_transport_rejects_cross_target_credentials_and_unapproved_http() -> None:
    context = _context()
    try:
        assert context.transport.authorize(
            "onvif_device", "https://127.0.0.1:443/onvif/device_service"
        )
        for url in (
            "http://127.0.0.1:80/onvif/device_service",
            "https://127.0.0.2:443/onvif/device_service",
            "https://operator:secret@127.0.0.1/onvif/device_service",
            "https://127.0.0.1/onvif/device_service#fragment",
            "https://example.com/onvif/device_service",
        ):
            with pytest.raises(TargetRejected):
                context.transport.authorize("onvif_device", url)
    finally:
        context.close()


def test_real_zeep_uses_local_wsdl_and_guarded_requests_before_soap_io() -> None:
    observed: list[tuple[str, bytes]] = []
    soap = (b'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
            b'xmlns:tds="http://www.onvif.org/ver10/device/wsdl">'
            b'<s:Body><tds:GetDeviceInformationResponse>'
            b'<tds:Manufacturer>Axis</tds:Manufacturer><tds:Model>M1</tds:Model>'
            b'<tds:FirmwareVersion>1.0</tds:FirmwareVersion>'
            b'<tds:SerialNumber>S1</tds:SerialNumber>'
            b'<tds:HardwareId>H1</tds:HardwareId>'
            b'</tds:GetDeviceInformationResponse></s:Body></s:Envelope>')

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            observed.append((self.path, body))
            self.send_response(200)
            self.send_header("Content-Type", "application/soap+xml")
            self.send_header("Content-Length", str(len(soap)))
            self.end_headers()
            self.wfile.write(soap)

        def log_message(self, *_args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    context = _context(server.server_port)
    try:
        assert context.auth.begin("ONVIF", "primary")
        client = ControlledOnvifClient(context, authenticated=True)
        assert observed == []  # Construction and WSDL imports do not call the camera.
        response = client.devicemgmt().GetDeviceInformation()
        assert response.Manufacturer == "Axis"
        assert len(observed) == 1
        assert observed[0][0] == "/onvif/device_service"
        assert b"UsernameToken" in observed[0][1]
        assert context.auth.allows_authenticated_request("ONVIF")
        assert context.auth.physical_exchanges == 1
        session = context.transport._sessions[("onvif_device", "ONVIF", True)]
        assert session.trust_env is False
        assert session.proxies == {}
    finally:
        context.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_real_zeep_discovers_only_authorized_media_xaddr() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = (b'<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" '
                    b'xmlns:tds="http://www.onvif.org/ver10/device/wsdl" '
                    b'xmlns:tt="http://www.onvif.org/ver10/schema"><s:Body>'
                    b'<tds:GetCapabilitiesResponse><tds:Capabilities>'
                    b'<tt:Media><tt:XAddr>http://127.0.0.1:'
                    + str(self.server.server_port).encode() + b'/onvif/media</tt:XAddr>'
                    b'</tt:Media></tds:Capabilities></tds:GetCapabilitiesResponse>'
                    b'</s:Body></s:Envelope>')
            self.send_response(200)
            self.send_header("Content-Type", "application/soap+xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    context = _context(server.server_port)
    try:
        result = ControlledOnvifClient(context, authenticated=False).devicemgmt().GetCapabilities(
            Category="All"
        )
        assert result.Media.XAddr.endswith("/onvif/media")
        assert context.transport.media_address is None  # Media has no approved rule.
    finally:
        context.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
