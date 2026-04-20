# Configatron

Configatron is a configuration management framework suitable for both
application and library code. It separates the abstract configuration
definition from the concrete implementation that loads config values,
making it easy for configuration consumers (or library developers) to
focus on business logic, while nevertheless giving devops (or library users)
fine-grained control over config value storage and retrieval, including the
ability to annotate fields as ``Secret``.

## Getting started

Configatron is available as ``configatron`` on pypi, ex via
``pip install configatron`` or ``uv add configatron``.

Async support requires ``anyio``, which will be included automatically if you
specify the ``async`` extra, (ex ``pip install configatron[async]`` or
``uv add configatron[async]``).

For more information, check out the documentation!

## At a glance

A simple example of library usage of an abstract config class:

```python
from typing import Protocol

from configatron import CfgMeta
from configatron import Secret


class MyLibraryConfig(Protocol, metaclass=CfgMeta):
    host: str
    port: int
    app_secret: Secret[str]


async def my_library_code(server):
    # Alternate spelling: ``config = get_active_cfg(MyLibraryConfig)``
    # (don't forget to import ``configatron.manager.get_active_cfg``)
    config = ~MyLibraryConfig

    async with server.bind([f'{config.host}:{config.port}']):
        # Concise inline references are supported
        await server.set_secret((~MyLibraryConfig).app_secret)
```

And its concrete counterpart in application code:

```python
import anyio
from configatron import CfgField
from configatron import CfgManager
from configatron import CfgSource
from configatron import Configatron
from configatron.prebaked.backends.env_vars import EnvVarBackend
from configatron.prebaked.backends.tomlfile import TomlFileBackend
from dcei import ext_dataclass
from dcei import ext_field
from my_library import MyLibraryConfig
from my_library import my_library_code


@ext_dataclass(Configatron(namespace='my.app'))
class MyConfigImpl(MyLibraryConfig):
    # By default, we'll search all backends for the field name, ex
    # ``host`` and ``port``, respectively
    host: str
    port: int
    # Specifying the source backend is optional; only if you want to limit to
    # a specific (prioritized) list of backends, or have aliases for the field
    # names. By default we'll check all of them, and apply them in
    # precedence order from your CfgManager
    app_secret: str = ext_field(CfgField(
        CfgSource(
            backend='env_vars',
            # The env var backend interprets this as ``MY_APP_COOKIE_SECRET``,
            # using the config class' namespace
            lookup_keys=['COOKIE_SECRET'])))


class MyServerObject:

    # During startup
    def on_app_start(self):
        cfg_manager = CfgManager(
            MyConfigImpl,
            backends={
                'config_file': TomlFileBackend('my_config.toml'),
                'env_vars': EnvVarBackend()})
        cfg_manager.load_once_sync()

        # The loaded config is now available to the application code that
        # requires it
        anyio.run(my_library_code, self)
```

**Note that the same class can be both an abstract config class and its own
concrete implementation.** For example:

```python
@ext_dataclass(Configatron(namespace='my.app'))
class MyApplicationConfig(metaclass=CfgMeta):
    ...
```

### Runtime type support

Configatron ``CfgManager`` objects support a ``type_coercer`` parameter to
allow for easy integration with runtime type libraries like pydantic.

### Custom backends

Defining custom backends is easy:

```python
from typing import Any

from configatron.backends import CfgBackend
from configatron.backends import KeyspaceSummary
from configatron.types import CfgFieldDesc


class SecretsManagerBackend(CfgBackend):
    """A custom config backend that contacts a cloud provider's secrets
    manager.
    """
    ALLOW_SECRET = True
    ALLOW_PLAINTEXT = False

    def load_sync(
            self,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        """Required to support sync loading, optional for async-only.
        """
        raise NotImplementedError('Your implementation goes here!')

    async def load_async(
            self,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        """Required to support async loading, optional for sync-only.
        """
        raise NotImplementedError('Your implementation goes here!')
```

## Full documentation

Full docs are available on the corresponding project page on Taev Codespace.
