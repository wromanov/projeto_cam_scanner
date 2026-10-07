"""Manufacturer snapshot provider interface; vendor HTTP is not implemented."""


class ManufacturerSnapshotProvider:
    def capture(self, target: object) -> object:
        raise NotImplementedError
