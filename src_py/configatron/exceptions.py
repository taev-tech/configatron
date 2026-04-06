class ConfigatronInternalError(Exception):
    """Raised when something happens that violates an expected invariant
    (or any other behavior that definitely indicates a bug within
    configatron itself).
    """


class ConfigatronException(Exception):
    """Base exception class used for errors from client code."""


class MissingConcreteConfigs(ConfigatronException):
    """Raised when verifying the config registry, if there aren't
    concrete configs defined for every abstract config class.
    """


class MultipleConcreteConfigsForAbstract(ConfigatronException):
    """Raised when an application defines multiple concrete configs for
    the same abstract config class.
    """


class MissingAbstractFields(ConfigatronException, TypeError):
    """Raised when a concrete config class is missing abstract fields,
    and therefore doesn't satisfy the abstract config protocol.
    """


class ConfigNotLoaded(ConfigatronException):
    """Raised when client code tries to access a config VALUE before
    it's been loaded.
    """


class DuplicateConfigNamespace(ConfigatronException):
    """Raised if two registered config classes attempt to use the same
    namespace.
    """
