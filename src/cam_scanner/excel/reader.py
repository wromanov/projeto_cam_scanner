"""ExcelReader boundary; input XLSX processing is deferred."""


class ExcelReader:
    def read(self, path: object) -> object:
        raise NotImplementedError
