"""ONVIF snapshot provider interface; no snapshot acquisition is implemented."""


class OnvifSnapshotProvider:
    def capture(self, target: object) -> object:
        raise NotImplementedError
