"""Domain error categories; sanitization is implemented in a later phase."""


class CameraScannerError(Exception):
    """Base exception for application-level errors."""


class ConfigurationError(CameraScannerError):
    """Invalid or unsupported local configuration."""


class CollectionError(CameraScannerError):
    """A camera collection operation failed."""
