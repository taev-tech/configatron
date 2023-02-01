from app import server

from configatron import ConfigatronLoader
from configatron import configatron
from configatron import secret
from configatron import unsecured


@configatron(namespace='server')
class Config:
    host: str = unsecured()
    port: int = unsecured()
    app_secret: str = secret(name='cookie_secret')
    app_trace: bool = unsecured(dynamic=True)

# Note: need to define a name template for backends, given the namespace. Or
# some way of configuring that or whatever.

# Will want two ways of setting the backend. One as just normal metadata on
# the fields and @configurators themselves (useful for first-party config),
# and another for third-party config that can be done elsewhere as an override.

# Will want to move the primary/secondary switch into the loading logic


def main():
    pass


async def start_server():
    # How to load configs?
    server.bind([f'{Config.host}:{Config.port}'])


if __name__ == '__main__':
    # Defined in precedence order and chainmapped together
    # Each backend has access to the config as it was loaded by the previous
    config_loader = ConfigatronLoader(backends=[])
    with config_loader.load():
        main()
