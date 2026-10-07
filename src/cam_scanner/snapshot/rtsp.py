"""RTSP frame provider interface; no RTSP session is opened."""


class RtspFrameProvider:
    def capture(self, target: object) -> object:
        raise NotImplementedError
