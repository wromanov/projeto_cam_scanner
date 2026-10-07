"""Domain exceptions used to classify expected collection failures."""


class CameraScannerError(Exception):
    """Base exception for application-level errors."""


class ConfigurationError(CameraScannerError):
    """Invalid or unsupported local configuration."""


class CollectionError(CameraScannerError):
    """A camera collection operation failed."""


class InvalidInputError(CameraScannerError):
    """The target supplied for a collection is invalid."""
