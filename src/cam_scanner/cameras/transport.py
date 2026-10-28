"""Target-bound, read-only Requests and Zeep transport for one collection row."""
from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import parse_qsl, quote, urlsplit

import requests
from requests.adapters import HTTPAdapter
from requests.utils import parse_dict_header

from cam_scanner.domain.errors import normalize_collection_error

if TYPE_CHECKING:
    from cam_scanner.application.collection_context import CollectionContext

SOAP_BODY_LIMIT = 1024 * 1024
_WSSE_NAMESPACE = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-wssecurity-secext-1.0.xsd"
)
_WSU_NAMESPACE = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-wssecurity-utility-1.0.xsd"
)
_WSSE_PASSWORD_DIGEST = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-username-token-profile-1.0#PasswordDigest"
)
_WSSE_BASE64_BINARY = (
    "http://docs.oasis-open.org/wss/2004/01/"
    "oasis-200401-wss-soap-message-security-1.0#Base64Binary"
)
_SOAP_ENVELOPE_NAMESPACES = frozenset({
    "http://www.w3.org/2003/05/soap-envelope",
    "http://schemas.xmlsoap.org/soap/envelope/",
})
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
_HTTP_AUTH_COMPONENTS = frozenset({
    "snapshot_onvif", "snapshot_vendor", "vendor_axis", "vendor_dahua",
    "vendor_hanwha", "vendor_panasonic", "vendor_hikvision",
})
_SNAPSHOT_COMPONENTS = frozenset({"snapshot_onvif", "snapshot_vendor"})
_AUTH_FAMILIES = {
    "onvif_device": "ONVIF",
    "onvif_media": "ONVIF",
    "snapshot_onvif": "ONVIF",
    "snapshot_vendor": "VENDOR_HIKVISION",
    "vendor_axis": "VENDOR_AXIS",
    "vendor_dahua": "VENDOR_DAHUA",
    "vendor_hanwha": "VENDOR_SAMSUNG/HANWHA",
    "vendor_panasonic": "VENDOR_PANASONIC",
    "vendor_hikvision": "VENDOR_HIKVISION",
}
_RETRYABLE_HTTP_STATUSES = frozenset({502, 503, 504})
_RETRYABLE_SOAP_OPERATIONS = frozenset({
    "GetDeviceInformation", "GetProfiles", "GetSnapshotUri", "GetStreamUri",
})


class TargetRejected(ValueError):
    """A URL is outside the exact target/component transport policy."""


class ResponseTooLarge(ValueError):
    """A bounded network response exceeded its approved limit."""


def _discard_auth_challenge_body(response: requests.Response, limit: int) -> None:
    """Discard irrelevant challenge bytes without letting Requests buffer them."""
    declared = response.headers.get("content-length")
    if declared is not None:
        try:
            length = int(declared)
        except ValueError as error:
            response.close()
            raise ResponseTooLarge("invalid authentication challenge content length") from error
        if length < 0 or length > limit:
            response.close()
            raise ResponseTooLarge("authentication challenge body too large")
    response.close()
    response._content = b""
    response._content_consumed = True


def _digest_challenge_supported(
    request: requests.PreparedRequest, response: requests.Response
) -> bool:
    """Accept only Digest challenges this request's auth hook can replay."""
    digest_handler = False
    for hook in request.hooks.get("response", ()):
        owner = getattr(hook, "__self__", None)
        supports_challenge = getattr(owner, "supports_challenge", None)
        if callable(supports_challenge):
            return bool(supports_challenge(response))
        if isinstance(owner, requests.auth.HTTPDigestAuth):
            digest_handler = True
    if not digest_handler:
        return False

    raw_headers = getattr(response.raw, "headers", None)
    getlist = getattr(raw_headers, "getlist", None)
    values = getlist("www-authenticate") if callable(getlist) else None
    if not values:
        value = response.headers.get("www-authenticate")
        values = [value] if isinstance(value, str) else []
    supported_algorithms = {"MD5", "MD5-SESS"}
    for value in values:
        if not isinstance(value, str):
            continue
        scheme, separator, parameters = value.strip().partition(" ")
        if not separator or scheme.casefold() != "digest":
            continue
        challenge = parse_dict_header(parameters)
        algorithm = str(challenge.get("algorithm", "MD5")).upper()
        qop_value = challenge.get("qop")
        qop = (
            {part.strip().casefold() for part in str(qop_value).split(",")}
            if qop_value
            else set()
        )
        if (
            challenge.get("realm")
            and challenge.get("nonce")
            and algorithm in supported_algorithms
            and (not qop or "auth" in qop)
        ):
            return True
    return False


def _retryable_operation(
    component: str, method: str, options: dict[str, Any]
) -> bool:
    if method == "GET":
        return component in _BODY_LIMITS
    if method != "POST" or component not in {"onvif_device", "onvif_media"}:
        return False
    return _soap_operation_name(options.get("data")) in _RETRYABLE_SOAP_OPERATIONS


def _soap_operation_name(payload: object) -> str | None:
    if not isinstance(payload, (bytes, str)):
        return None
    try:
        root = ET.fromstring(payload)
    except (ET.ParseError, TypeError, ValueError):
        return None
    body = next(
        (element for element in root.iter()
         if isinstance(element.tag, str) and element.tag.rsplit("}", 1)[-1] == "Body"),
        None,
    )
    if body is None:
        return None
    operation = next((item for item in body if isinstance(item.tag, str)), None)
    return operation.tag.rsplit("}", 1)[-1] if operation is not None else None


def _soap_has_wsse_credentials(
    payload: object, username: object, password: object
) -> bool:
    """Prove this bounded SOAP request carries this row's valid PasswordDigest."""
    if isinstance(payload, str):
        try:
            payload = payload.encode("utf-8")
        except UnicodeEncodeError:
            return False
    if (not isinstance(payload, bytes) or not 0 < len(payload) <= SOAP_BODY_LIMIT
            or not isinstance(username, str) or not username
            or not isinstance(password, str) or not password
            or b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper()):
        return False
    try:
        root = ET.fromstring(payload)
    except (ET.ParseError, TypeError, ValueError):
        return False
    envelope_namespace = (
        root.tag[1:].split("}", 1)[0]
        if isinstance(root.tag, str) and root.tag.startswith("{") else None
    )
    if (envelope_namespace not in _SOAP_ENVELOPE_NAMESPACES
            or root.tag != f"{{{envelope_namespace}}}Envelope"):
        return False
    header_tag = f"{{{envelope_namespace}}}Header"
    body_tag = f"{{{envelope_namespace}}}Body"
    headers = [item for item in root if item.tag == header_tag]
    bodies = [item for item in root if item.tag == body_tag]
    if len(headers) != 1 or len(bodies) != 1:
        return False
    security_tag = f"{{{_WSSE_NAMESPACE}}}Security"
    security_headers = [item for item in headers[0] if item.tag == security_tag]
    if len(security_headers) != 1:
        return False
    token_tag = f"{{{_WSSE_NAMESPACE}}}UsernameToken"
    username_tag = f"{{{_WSSE_NAMESPACE}}}Username"
    password_tag = f"{{{_WSSE_NAMESPACE}}}Password"
    nonce_tag = f"{{{_WSSE_NAMESPACE}}}Nonce"
    created_tag = f"{{{_WSU_NAMESPACE}}}Created"
    tokens = [item for item in security_headers[0] if item.tag == token_tag]
    if len(tokens) != 1:
        return False
    values: dict[str, list[ET.Element]] = {}
    for child in tokens[0]:
        values.setdefault(child.tag, []).append(child)
    if any(len(values.get(tag, ())) != 1 for tag in (
        username_tag, password_tag, nonce_tag, created_tag
    )):
        return False
    username_element = values[username_tag][0]
    password_element = values[password_tag][0]
    nonce_element = values[nonce_tag][0]
    created_element = values[created_tag][0]
    if username_element.text != username:
        return False
    if password_element.attrib.get("Type") != _WSSE_PASSWORD_DIGEST:
        return False
    if nonce_element.attrib.get("EncodingType") != _WSSE_BASE64_BINARY:
        return False
    if (not isinstance(password_element.text, str)
            or not isinstance(nonce_element.text, str)
            or not isinstance(created_element.text, str)
            or not created_element.text or len(created_element.text) > 128):
        return False
    try:
        nonce = base64.b64decode(nonce_element.text, validate=True)
        submitted_digest = base64.b64decode(password_element.text, validate=True)
        expected_digest = hashlib.sha1(
            nonce + created_element.text.encode("utf-8") + password.encode("utf-8")
        ).digest()
    except (ValueError, UnicodeEncodeError):
        return False
    if not 0 < len(nonce) <= 1024 or len(submitted_digest) != hashlib.sha1().digest_size:
        return False
    return hmac.compare_digest(submitted_digest, expected_digest)


class _BoundedResponse:
    """Enforce the same limit for streamed and eager callers; charge body time."""

    def __init__(self, response: requests.Response, context: CollectionContext,
                 source: str, limit: int,
                 retry: Callable[[Exception], requests.Response | None] | None = None) -> None:
        self._response = response
        self._context = context
        self._source = source
        self._limit = limit
        self._retry = retry
        self._cached: bytes | None = None
        self._validate_declared_length(response)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def content(self) -> bytes:
        if self._cached is None:
            return b"".join(self.iter_content(chunk_size=65536))
        return self._cached

    def iter_content(self, chunk_size: int = 65536, **kwargs: Any) -> Any:
        if self._cached is None:
            self._load_body(chunk_size, kwargs)
        assert self._cached is not None
        for offset in range(0, len(self._cached), chunk_size):
            yield self._cached[offset:offset + chunk_size]

    def _load_body(self, chunk_size: int, kwargs: dict[str, Any]) -> None:
        body = bytearray()
        while True:
            response = self._response
            self._validate_declared_length(response)
            last_charged = self._context.monotonic()
            try:
                for chunk in response.iter_content(chunk_size=chunk_size, **kwargs):
                    now = self._context.monotonic()
                    self._context.charge_operation(
                        self._source, max(0.0, now - last_charged)
                    )
                    last_charged = now
                    self._context.check(self._source)
                    if not isinstance(chunk, bytes):
                        raise ResponseTooLarge("invalid response chunk")
                    body.extend(chunk)
                    if len(body) > self._limit:
                        raise ResponseTooLarge("response too large")
            except requests.exceptions.SSLError:
                self._context.mark_tls_failure()
                self._charge_tail(last_charged)
                response.close()
                raise
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
                self._charge_tail(last_charged)
                response.close()
                if self._retry is None:
                    raise
                replacement = self._retry(error)
                if replacement is None:
                    raise
                self._response = replacement
                body.clear()
                continue
            except BaseException:
                self._charge_tail(last_charged)
                response.close()
                raise
            self._charge_tail(last_charged)
            self._cached = bytes(body)
            return

    def _charge_tail(self, last_charged: float) -> None:
        now = self._context.monotonic()
        self._context.charge_operation(
            self._source, max(0.0, now - last_charged)
        )

    def _validate_declared_length(self, response: requests.Response) -> None:
        declared = response.headers.get("content-length")
        if declared is None:
            return
        try:
            length = int(declared)
        except (TypeError, ValueError) as error:
            response.close()
            raise ResponseTooLarge("invalid content length") from error
        if length < 0 or length > self._limit:
            response.close()
            raise ResponseTooLarge("response too large")

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
        if self.authenticated:
            family = _AUTH_FAMILIES.get(self.component)
            if family is None or not context.auth.allows_authenticated_attempt(family):
                raise TargetRejected("authenticated attempt was not authorized")
            if (self.component in _SNAPSHOT_COMPONENTS
                    and not context.auth.allows_authenticated_request(family)):
                raise TargetRejected("snapshot requires an accepted authentication scope")
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
        started = context.monotonic()
        context.auth.record_physical_exchange()
        authorization = request.headers.get("Authorization")
        credential_sent = (
            self.authenticated
            and isinstance(authorization, str)
            and bool(authorization.strip())
        )
        if (self.authenticated and self.component.startswith("onvif_")
                and _soap_has_wsse_credentials(
                    request.body, context.target.username, context.target.password
                )):
            credential_sent = True
        try:
            response = super().send(request, **kwargs)
            family = _AUTH_FAMILIES.get(self.component, self.component.upper())
            digest_challenge = (
                self.authenticated
                and self.component in _HTTP_AUTH_COMPONENTS
                and response.status_code == 401
                and "Authorization" not in request.headers
                and _digest_challenge_supported(request, response)
            )
            if digest_challenge:
                try:
                    _discard_auth_challenge_body(response, _BODY_LIMITS[self.component])
                except ResponseTooLarge:
                    context.auth.observe_http(
                        response.status_code, family, authenticated=self.authenticated
                    )
                    raise
            observed_authenticated = credential_sent or (
                self.authenticated
                and response.status_code == 401
                and not digest_challenge
            )
            context.auth.observe_http(
                response.status_code, family,
                authenticated=observed_authenticated,
                challenge=digest_challenge,
            )
            return response
        except requests.exceptions.SSLError:
            context.mark_tls_failure()
            raise
        finally:
            context.charge_operation(self.source, max(0.0, context.monotonic() - started))


class TargetTransportPolicy:
    """Exact IP, scheme, component and port authorization with isolated sessions."""

    def __init__(self, context: CollectionContext, *,
                 session_factory: Any = requests.Session) -> None:
        self.context = context
        self._session_factory = session_factory
        self._sessions: dict[tuple[str, str, bool], requests.Session] = {}
        self.media_address: str | None = None

    def _rules(self) -> tuple[Any, ...]:
        plan = getattr(self.context.config, "transport_plan", None)
        if plan is not None:
            return plan.rules
        # Legacy HTTP remains loadable, but cannot activate without a pre-I/O plan.
        # Preserve explicit RTSP rules: the centralized HTTP profile must not
        # silently disable the separately governed media transport.
        return tuple(rule for rule in getattr(self.context.config, "transport_rules", ())
                     if getattr(rule, "protocol", None) != "http")

    def policy_metadata(self, component: str, url: str) -> dict[str, str | None]:
        """Return closed sanitized policy metadata for the actual request scheme."""
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        plan = getattr(self.context.config, "transport_plan", None)
        entry = (plan.for_target(self.context.target.ip, component)
                 if plan is not None else None)
        metadata = getattr(entry, "metadata", None)
        if metadata is not None and metadata.scheme == scheme:
            return {
                "policy_id": metadata.policy_id,
                "authorization_ref": metadata.authorization_ref,
                "auth_mode": metadata.auth_mode,
                "scheme": scheme,
            }
        return {
            "policy_id": "HTTPS_DEFAULT" if scheme == "https" else "LEGACY_EXACT",
            "authorization_ref": None,
            "auth_mode": "NONE" if scheme == "https" else "EXISTING",
            "scheme": scheme,
        }

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
        rules = self._rules()
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
        rules = self._rules()
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
        metadata = self.policy_metadata(component, url)
        if metadata["policy_id"] not in {"HTTPS_DEFAULT", "LEGACY_EXACT"}:
            if metadata["scheme"] == "http" and component not in {
                "vendor_axis", "vendor_dahua", "vendor_hanwha",
                "vendor_panasonic", "vendor_hikvision",
            }:
                raise TargetRejected("HTTP profile is limited to native vendor components")
            if metadata["auth_mode"] == "PUBLIC_NONE" and authenticated:
                raise TargetRejected("public transport policy forbids authentication")
        if method.upper() not in {"GET", "POST"}:
            raise TargetRejected("unsupported method")
        options["allow_redirects"] = False
        options["verify"] = True
        options["stream"] = True
        options["proxies"] = {}
        request_method = method.upper()
        request_options = dict(options)
        retry_eligible = _retryable_operation(component, request_method, request_options)
        operation_id = object()
        session = self._session(component, source, authenticated)
        while True:
            self.context.check(source)
            request_options["timeout"] = self.context.request_timeout(source)
            try:
                response = session.request(request_method, url, **request_options)
            except requests.exceptions.SSLError:
                self.context.mark_tls_failure()
                raise
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if not self._retry(source, retry_eligible, operation_id):
                    raise
                continue
            if response.status_code in _RETRYABLE_HTTP_STATUSES:
                response.close()
                if self._retry(source, retry_eligible, operation_id):
                    continue
            bounded = _BoundedResponse(
                response, self.context, source, _BODY_LIMITS[component],
                retry=(
                    lambda error: self._retry_after_body(
                        session, request_method, url, request_options, source,
                        retry_eligible, operation_id, error,
                    )
                ),
            )
            # Resolve any streaming retry while status and headers are still hidden
            # from callers, so they classify the final response consistently.
            _ = bounded.content
            return bounded

    def _retry_after_body(
        self,
        session: requests.Session,
        method: str,
        url: str,
        options: dict[str, Any],
        source: str,
        eligible: bool,
        operation_id: object,
        error: Exception,
    ) -> requests.Response | None:
        if isinstance(error, requests.exceptions.SSLError) or not isinstance(
            error, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
        ):
            return None
        if not self._retry(source, eligible, operation_id):
            return None
        request_options = dict(options)
        request_options["timeout"] = self.context.request_timeout(source)
        return session.request(method, url, **request_options)

    def _retry(self, source: str, eligible: bool, operation_id: object) -> bool:
        budget = self.context.budget
        if not budget.retry_allowed(source, eligible=eligible, operation_id=operation_id):
            return False
        delay = getattr(self.context.config, "retry_backoff_seconds", 1)
        if not self.context.wait_for_retry(source, delay):
            return False
        budget.record_retry(source, operation_id=operation_id)
        return True

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
        return _RestrictedService(
            service,
            component,
            self.context,
            authenticated=self.authenticated,
        )


class _RestrictedService:
    _ALLOWED: ClassVar[dict[str, frozenset[str]]] = {"onvif_device": frozenset({"GetCapabilities", "GetSystemDateAndTime",
                                           "GetDeviceInformation"}),
                "onvif_media": frozenset({"GetProfiles", "GetSnapshotUri", "GetStreamUri"})}

    def __init__(
        self,
        service: Any,
        component: str,
        context: CollectionContext,
        *,
        authenticated: bool,
    ) -> None:
        self._service = service
        self._component = component
        self._context = context
        self._authenticated = authenticated
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
                _, _, protocol_code = normalize_collection_error(error, stage="SOAP")
                self._context.auth.observe_soap(
                    protocol_code or getattr(error, "code", None),
                    authenticated=self._authenticated,
                )
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
