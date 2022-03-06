class ConfigatronInternalError(Exception):
    """Raised when something happens that violates an expected invariant
    (or any other behavior that definitely indicates a bug within
    configatron itself).
    """


class ConfigatronError(Exception):
    """Base exception class used for errors from client code."""


class ConfigNotLoaded(ConfigatronError):
    """Raised when client code tries to access a config VALUE before
    it's been loaded.
    """
