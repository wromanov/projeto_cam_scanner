"""ExcelWriter boundary; output XLSX generation is deferred."""


class ExcelWriter:
    def write(self, path: object) -> object:
        raise NotImplementedError
