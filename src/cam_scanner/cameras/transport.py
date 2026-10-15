"""Target-bound, read-only Requests and Zeep transport for one collection row."""
from __future__ import annotations

import ipaddress
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import parse_qsl, quote, urlsplit

import requests
from requests.adapters import HTTPAdapter

if TYPE_CHECKING:
    from cam_scanner.application.collection_context import CollectionContext

SOAP_BODY_LIMIT = 1024 * 1024
_COMPONENTS = frozenset({
    "onvif_device", "onvif_media", "snapshot_onvif", "snapshot_vendor",
    "vendor_axis", "vendor_dahua", "vendor_hanwha", "vendor_panasonic",
    "vendor_hikvision", "rtsp",
})
_BODY_LIMITS = {
    "onvif_device": SOAP_BODY_LIMIT, "onvif_media": SOAP_BODY_LIMIT,
    "snapshot_onvif": 8 * SOAP_BODY_LIMIT, "snapshot_vendor": 8 * SOAP_BODY_LIMIT,
    "vendor_axis": 64 * 1024, "vendor_hanwha": 64 * 1024,
    "vendor_dahua": 16 * 1024, "vendor_panasonic": 16 * 1024,
    "vendor_hikvision": 64 * 1024,
}


class TargetRejected(ValueError):
    """A URL is outside the exact target/component transport policy."""


class ResponseTooLarge(ValueError):
    """A bounded network response exceeded its approved limit."""


class _BoundedResponse:
    """Enforce the same limit for streamed and eager callers; charge body time."""

    def __init__(self, response: requests.Response, context: CollectionContext,
                 source: str, limit: int) -> None:
        self._response = response
        self._context = context
        self._source = source
        self._limit = limit
        self._cached: bytes | None = None
        declared = response.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > limit:
                    response.close()
                    raise ResponseTooLarge("response too large")
            except ValueError as error:
                response.close()
                raise ResponseTooLarge("invalid content length") from error

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def content(self) -> bytes:
        if self._cached is None:
            return b"".join(self.iter_content(chunk_size=65536))
        return self._cached

    def iter_content(self, chunk_size: int = 65536, **kwargs: Any) -> Any:
        if self._cached is not None:
            for offset in range(0, len(self._cached), chunk_size):
                yield self._cached[offset:offset + chunk_size]
            return
        body = bytearray()
        started = time.monotonic()
        try:
            for chunk in self._response.iter_content(chunk_size=chunk_size, **kwargs):
                self._context.check(self._source)
                if not isinstance(chunk, bytes):
                    raise ResponseTooLarge("invalid response chunk")
                body.extend(chunk)
                if len(body) > self._limit:
                    raise ResponseTooLarge("response too large")
                yield chunk
            self._cached = bytes(body)
        finally:
            self._context.charge_operation(self._source, max(0.0, time.monotonic() - started))

    def close(self) -> None:
        self._response.close()


class _GuardedAdapter(HTTPAdapter):
    def __init__(self, policy: TargetTransportPolicy, component: str, source: str,
                 authenticated: bool) -> None:
        super().__init__(max_retries=0)
        self.policy = policy
        self.component = component
        self.source = source
        self.authenticated = authenticated

    def send(self, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        context = self.policy.context
        context.check(self.source)
        self.policy.authorize(self.component, request.url or "")
        if context.auth.state in {
            context.auth.AUTH_REJECTED_FINAL, context.auth.AUTHORIZATION_DENIED,
        } and self.authenticated:
            raise TargetRejected("authentication stopped")
        if request.method not in {"GET", "POST"}:
            raise TargetRejected("unsupported method")
        if self.component.startswith("onvif_") and request.method != "POST":
            raise TargetRejected("unsupported ONVIF method")
        connect, read = context.request_timeout(self.source)
        requested = kwargs.get("timeout")
        if isinstance(requested, tuple) and len(requested) == 2:
            connect, read = min(connect, requested[0]), min(read, requested[1])
        kwargs["timeout"] = (connect, read)
        kwargs["verify"] = True
        kwargs["proxies"] = {}
        started = time.monotonic()
        context.auth.record_physical_exchange()
        try:
            response = super().send(request, **kwargs)
            family = ({"onvif_device": "ONVIF", "onvif_media": "ONVIF",
                       "snapshot_onvif": "ONVIF", "snapshot_vendor": "VENDOR_HIKVISION",
                       "vendor_hanwha": "VENDOR_SAMSUNG/HANWHA"}
                      .get(self.component, self.component.upper()))
            context.auth.observe_http(
                response.status_code, family,
                authenticated=self.authenticated,
                challenge=(self.authenticated and response.status_code == 401
                           and "Authorization" not in request.headers
                           and "www-authenticate" in response.headers),
            )
            return response
        finally:
            context.charge_operation(self.source, max(0.0, time.monotonic() - started))


class TargetTransportPolicy:
    """Exact IP, scheme, component and port authorization with isolated sessions."""

    def __init__(self, context: CollectionContext, *,
                 session_factory: Any = requests.Session) -> None:
        self.context = context
        self._session_factory = session_factory
        self._sessions: dict[tuple[str, str, bool], requests.Session] = {}
        self.media_address: str | None = None

    def authorize(self, component: str, url: str) -> str:
        if component not in _COMPONENTS or not isinstance(url, str) or not 0 < len(url) <= 2048:
            raise TargetRejected("unsupported transport component or URL")
        try:
            credentials = tuple(
                value
                for value in (self.context.target.username, self.context.target.password)
                if value
            )
            if any(
                secret.casefold() in url.casefold()
                or quote(secret, safe="").casefold() in url.casefold()
                for secret in credentials
            ):
                raise ValueError
            parsed = urlsplit(url)
            scheme = parsed.scheme.lower()
            if scheme not in {"https", "http", "rtsp", "rtsps"} or not parsed.netloc:
                raise ValueError
            if parsed.username is not None or parsed.password is not None or parsed.fragment:
                raise ValueError
            if any(key.casefold() in {"user", "username", "password", "passwd", "pwd",
                                          "token", "auth", "authorization"}
                   for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
                raise ValueError
            if parsed.hostname is None or parsed.hostname.endswith("."):
                raise ValueError
            target_ip = ipaddress.ip_address(self.context.target.ip)
            host_ip = ipaddress.ip_address(parsed.hostname)
            port = (parsed.port if parsed.port is not None else
                    {"https": 443, "http": 80, "rtsp": 554, "rtsps": 322}[scheme])
            if not 1 <= port <= 65535 or not parsed.path.startswith("/"):
                raise ValueError
        except (ValueError, TypeError) as error:
            raise TargetRejected("invalid target URL") from error
        if component == "rtsp" and scheme not in {"rtsp", "rtsps"}:
            raise TargetRejected("invalid RTSP protocol")
        if component != "rtsp" and scheme not in {"http", "https"}:
            raise TargetRejected("invalid HTTP protocol")
        rules = getattr(self.context.config, "transport_rules", ())
        explicitly_allowed = any(
            getattr(rule, "target", None) == self.context.target.ip
            and getattr(rule, "component", None) == component
            and str(getattr(rule, "protocol", "")).lower() == scheme
            and getattr(rule, "port", None) == port
            and (host_ip == target_ip and getattr(rule, "host", None) in {None, "", parsed.hostname}
                 or getattr(rule, "host", None) == parsed.hostname)
            for rule in rules
        )
        if host_ip != target_ip and not explicitly_allowed:
            raise TargetRejected("destination differs from target IP")
        if not explicitly_allowed and not (scheme == "https" and port == 443):
            raise TargetRejected("transport requires explicit authorization")
        return url

    def endpoint(self, component: str, protocol: str | None = None, path: str = "/") -> str:
        if component not in _COMPONENTS:
            raise TargetRejected("unsupported transport component")
        rules = getattr(self.context.config, "transport_rules", ())
        configured = [rule for rule in rules if getattr(rule, "target", None) == self.context.target.ip
                      and getattr(rule, "component", None) == component]
        if protocol is None:
            protocol = ("http" if configured and all(
                str(getattr(rule, "protocol", "")).lower() == "http"
                for rule in configured) else "https")
        matching = [rule for rule in configured if getattr(rule, "target", None) == self.context.target.ip
                    and getattr(rule, "component", None) == component
                    and str(getattr(rule, "protocol", "")).lower() == protocol.lower()]
        if protocol.lower() != "https" and not matching:
            raise TargetRejected("transport requires explicit authorization")
        port = matching[0].port if matching else 443
        address = ipaddress.ip_address(getattr(matching[0], "host", None)
                                       or self.context.target.ip) if matching else ipaddress.ip_address(self.context.target.ip)
        host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        result = f"{protocol.lower()}://{host}:{port}{path}"
        return self.authorize(component, result)

    def set_media_address(self, value: object) -> None:
        if not isinstance(value, str):
            raise TargetRejected("missing Media XAddr")
        self.media_address = self.authorize("onvif_media", value)

    def _session(self, component: str, source: str, authenticated: bool) -> requests.Session:
        key = (component, source, authenticated)
        if key not in self._sessions:
            session = self._session_factory()
            session.trust_env = False
            session.proxies.clear()
            adapter = _GuardedAdapter(self, component, source, authenticated)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            self.context.register(session)
            self._sessions[key] = session
        return self._sessions[key]

    def request(self, component: str, method: str, url: str, *, source: str,
                authenticated: bool = True, **options: Any) -> requests.Response:
        if component == "rtsp":
            raise TargetRejected("RTSP uses the bounded decoder")
        self.context.check(source)
        self.authorize(component, url)
        if method.upper() not in {"GET", "POST"}:
            raise TargetRejected("unsupported method")
        options["allow_redirects"] = False
        options["verify"] = True
        options["stream"] = True
        options["proxies"] = {}
        options["timeout"] = self.context.request_timeout(source)
        response = self._session(component, source, authenticated).request(
            method, url, **options
        )
        return _BoundedResponse(response, self.context, source, _BODY_LIMITS[component])

    def zeep_transport(self, component: str, *, authenticated: bool) -> Any:
        from zeep.transports import Transport

        policy = self
        source = "ONVIF"
        session = self._session(component, source, authenticated)
        wsdl_root = _wsdl_root().resolve()

        class BoundedZeepTransport(Transport):
            def load(self, url: str) -> bytes:
                if urlsplit(url).scheme in {"http", "https"}:
                    raise TargetRejected("remote WSDL/import forbidden")
                path = Path(url.removeprefix("file:///"))
                resolved = path.resolve()
                if not resolved.is_relative_to(wsdl_root):
                    raise TargetRejected("WSDL/import outside packaged resources")
                return super().load(url)

            def post(self, address: str, message: bytes, headers: dict[str, str]) -> Any:
                if len(message) > SOAP_BODY_LIMIT:
                    raise ResponseTooLarge("SOAP request too large")
                response = policy.request(component, "POST", address, source=source,
                                          authenticated=authenticated, data=message,
                                          headers=headers)
                try:
                    declared = response.headers.get("content-length")
                    if declared is not None and int(declared) > SOAP_BODY_LIMIT:
                        raise ResponseTooLarge("SOAP response too large")
                    body = bytearray()
                    for chunk in response.iter_content(chunk_size=65536):
                        policy.context.check(source)
                        body.extend(chunk)
                        if len(body) > SOAP_BODY_LIMIT:
                            raise ResponseTooLarge("SOAP response too large")
                    if bytes(body) != response.content:
                        raise ResponseTooLarge("inconsistent SOAP response")
                    return response
                finally:
                    response.close()

        return BoundedZeepTransport(session=session)


def _wsdl_root() -> Path:
    import onvif

    return Path(onvif.__file__).parent / "wsdl"


class ControlledOnvifClient:
    """Only the approved Device/Media operations, with no constructor I/O."""

    def __init__(self, context: CollectionContext, *, authenticated: bool) -> None:
        self.context = context
        self.authenticated = authenticated

    def devicemgmt(self) -> Any:
        return self._service("onvif_device", "ver10/device/wsdl/devicemgmt.wsdl",
                             "{http://www.onvif.org/ver10/device/wsdl}DeviceBinding",
                             self.context.transport.endpoint("onvif_device", path="/onvif/device_service"))

    def media(self) -> Any:
        address = self.context.transport.media_address
        if address is None:
            raise TargetRejected("Media XAddr was not discovered")
        return self._service("onvif_media", "ver10/media/wsdl/media.wsdl",
                             "{http://www.onvif.org/ver10/media/wsdl}MediaBinding", address)

    def _service(self, component: str, wsdl: str, binding: str, address: str) -> Any:
        from zeep import Client, Settings
        from zeep.wsse.username import UsernameToken

        self.context.check("ONVIF")
        self.context.transport.authorize(component, address)
        settings = Settings(forbid_dtd=True, forbid_entities=True,
                            forbid_external=True, xml_huge_tree=False)
        token = (UsernameToken(self.context.target.username, self.context.target.password,
                               use_digest=True) if self.authenticated else None)
        client = Client(str(_wsdl_root() / wsdl),
                        transport=self.context.transport.zeep_transport(
                            component, authenticated=self.authenticated),
                        settings=settings, wsse=token)
        service = client.create_service(binding, address)
        return _RestrictedService(service, component, self.context)


class _RestrictedService:
    _ALLOWED: ClassVar[dict[str, frozenset[str]]] = {"onvif_device": frozenset({"GetCapabilities", "GetSystemDateAndTime",
                                           "GetDeviceInformation"}),
                "onvif_media": frozenset({"GetProfiles", "GetSnapshotUri", "GetStreamUri"})}

    def __init__(self, service: Any, component: str, context: CollectionContext) -> None:
        self._service = service
        self._component = component
        self._context = context
        self.operator = type("Operator", (), {"address": getattr(service, "_binding_options", {}).get("address")})()

    def __getattr__(self, name: str) -> Any:
        if name not in self._ALLOWED[self._component]:
            raise AttributeError(name)
        operation = getattr(self._service, name)

        def call(*args: Any, **kwargs: Any) -> Any:
            self._context.check("ONVIF")
            try:
                result = operation(*args, **kwargs)
            except Exception as error:
                self._context.auth.observe_soap(getattr(error, "code", None),
                                                authenticated=name != "GetCapabilities")
                raise
            if name == "GetCapabilities":
                media = getattr(result, "Media", None)
                xaddr = getattr(media, "XAddr", None)
                if xaddr is not None:
                    try:
                        self._context.transport.set_media_address(xaddr)
                    except TargetRejected:
                        pass  # Discovery remains evidence; Media cannot be used.
            return result

        return call
