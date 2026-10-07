"""ONVIF-first adapter interface only; no ONVIF client is instantiated."""
from typing import Protocol


class OnvifAdapter(Protocol):
    def collect(self, target: object) -> object: ...
