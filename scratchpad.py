from app import server

from configatron import ConfigatronLoader
from configatron import configatron
from configatron import Secret
from configatron import config_logger


# Note: ALWAYS kw_only. Slots=True by default.
@configatron(namespace='server')
# Note: the ConfigMeta is optional. This is what implements the __invert__
# method on the class, thereby supporting the shorthand ``(~Config).host``
class Config(metaclass=ConfigMeta):
    host: str
    port: int
    app_secret: Secret[str] = cfg_field(
        # Optional; only if you want to limit to a specific (prioritized) list
        # of backends. By default we'll check all of them, and apply them in
        # precedence order from your ConfigurationLoader
        backends=['foo'],
        lookup_keys=['cookie_secret', 'cookie_secret_old'])
    app_trace: bool = cfg_field(
        # Max refresh intervals are just that -- a max. Backends might refresh
        # values sooner -- for example, if a backend stores an entire namespace
        # in a single structure, it might be refreshed after the minimum of all
        # maximums.
        # Note that not all backends can be changed; for example, environment
        # variables cannot be altered after a process starts. By convention,
        # backends may log a warning using the configuration logger if they
        # don't support refreshing but are requested to do so.
        refresh_after_max=3600)

# Note: need to define a name template for backends, given the namespace. Or
# some way of configuring that or whatever.

# By convention, libraries should never define extra config field params.
# Note that applications can subclass libraries' configs using the same
# namespace, allowing them to modify additional parameters (like backends,
# lookup keys, etc).
# By convention, libraries should always use the ConfigMeta.


def main():
    pass


async def start_server():
    # There are two ways of accessing configs. First, the shorthand way.
    # This requires config classes to use the ConfigMeta. It's more concise.
    server.bind([f'{(~Config).host}:{(~Config).port}'])
    # Second, the functional way. This doesn't require the ConfigMeta, and
    # is slightly more performant if you need to access multiple values from
    # the same config within a particular scope. Note that this will **not**
    # be updated if config values are refreshed during its lifetime; you need
    # to get a new snapshot for the updates to apply.
    cfg = snapshot(Config)


if __name__ == '__main__':
    # Defined in precedence order and chainmapped together
    # Each backend has access to the config as it was loaded by the previous
    cfg_manager = ConfigManager(
        backends=[],
        refresh_after_max=7200)

    with cfg_manager.run_sync():
        main()

    async with cfg_manager.run_async():
        main()
