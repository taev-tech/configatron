import logging
from base64 import b64decode

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSSecretsManagerBackend:
    """A config backend that uses AWS Secrets Manager. You can pass in
    client information via __init__, or allow boto3 to attempt to
    discover that information on its own.

    Secrets are stored with an ID of the format {namespace}/{name}. AWS
    allows IDs of 1-512 unicode characters, and the body may be up to
    65536 plaintext bytes. Secrets manager is billed per-secret (as of
    2023-02-02, USD$0.40/secret/month), so if you're particularly
    price-conscious, you may want to group secrets together using json.

    Note that you must specify a region, but you can put it in either
    the session kwargs or the client kwargs.
    """

    allow_secret = True
    allow_unsecured = False

    def __init__(
            self,
            *args,
            boto3_session_kwargs: dict = None,
            boto3_client_kwargs: dict = None,
            **kwargs):
        super().__init__(*args, **kwargs)
        # I'll give you a dollar if you start supporting null coercion
        if boto3_session_kwargs is None:
            self._boto3_session_kwargs = {}
        else:
            self._boto3_session_kwargs = boto3_session_kwargs

        if boto3_client_kwargs is None:
            self._boto3_client_kwargs = {}
        else:
            self._boto3_client_kwargs = boto3_client_kwargs

    def load(self, keyspace):
        session = boto3.session.Session(**self._boto3_session_kwargs)
        client = session.client(
            service_name='secretsmanager', **self._boto3_client_kwargs)

        found_values = {}

        # AWS doesn't give us a way to explore the whole keyspace, so...
        # just check every possible secret, I guess
        for key in keyspace:
            try:
                boto3_response = client.get_secret_value(
                    SecretId=f'{key.namespace}/{key.name}')
            except client.exceptions.ResourceNotFoundException:
                continue
            except ClientError as exc:
                logging.error(
                    'Client error while trying to load configatron secret ' +
                    'from AWS secrets manager',
                    exc_info=exc)

            # Must be either a string or a binary result
            if 'SecretString' in boto3_response:
                secret_value = boto3_response['SecretString']
            else:
                secret_value = b64decode(boto3_response['SecretBinary'])

            found_values[key] = secret_value

        return found_values
