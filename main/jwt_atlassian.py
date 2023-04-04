"""Authenticate an HTTP request that contains an Atlassian-style JWT token.

Atlassian-style JWT tokens include a `qsh` claim which stands for query string
hash. See `Understanding JWT for Atlassian Connect`_ for more details.

.. Understanding JWT for Atlassian Connect
   _https://developer.atlassian.com/blog/2015/01/understanding-jwt/
"""

import abc
import jwt as jwt
from jwt import DecodeError
from .url_utils import hash_url, parse_query_params

class Authenticator(object):
    """An abstract base class for authenticating Atlassian Connect requests.

    Subclasses *must* implement the `get_shared_secret` method.

    Example:
        Subclass this abstract base class to provide authentication to an
        Atlassian Connect Addon.

        import atlassian_jwt

        class MyAddon(atlassian_jwt.Authenticator):
            def __init__(self, tenant_info_store):
                super(MyAddon, self).__init__()
                self.tenant_info_store = tenant_info_store

            def get_shared_secret(self, client_key):
                tenant_info = self.tenant_info_store.get(client_key)
                return tenant_info['sharedSecret']

        my_auth = MyAddon(tenant_info_store)
        try:
            client_key = my_auth.authenticate(http_method, url, headers)
            # authentication succeeded
        except atlassian_jwt.DecodeError:
            # authentication failed
            pass
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, algorithms=('HS256',), leeway=10):
        self.algorithms = algorithms
        self.leeway = leeway

    @abc.abstractmethod
    def get_shared_secret(self, client_key):
        """Get the shared secret associtated with the client key.

        Subclasses of this abstract base class *must* implement this method.

        Use the client key to retrieve the shared secret (presumably) from a
        persistent store of which this abstract base class does not need to
        know the details.

        This is the shared secret that was used to sign the JWT token and can
        be used to verify its authenticity.

        Args:
            client_key (string): client key

        Returns:
            string: shared secret used to sign the JWT token
        """
        print(1)
        raise NotImplementedError

    def authenticate(self, http_method, url, headers=None, body=None):
        """Extract the JWT token from the `Authorization` header, or if not
        found there then the `jwt` query parameter.

        Args:
            http_method (string): HTTP method

            url (string): URL

            headers (dict): incoming request headers. The header name
                `Authorization` is case-insensitive. The token type `JWT` in
                the `Authorization` header is case-insensitive.

        Returns:
            string: client key (the `iss` claim from the JWT token)

        Raises:
            DecodeError: If neither `headers` nor the query parameteters in
                `url` contain a JWT token. Or if `qsh` claim does not match
                expected value.

        .. _Exposing a service:
           https://developer.atlassian.com/static/connect/docs/latest/concepts/authentication.html#exposing    
        """
        token = self._get_token(
            headers=headers,
            query_params=parse_query_params(url),
            body=body)

        claims = jwt.decode(token, verify=False, algorithms=self.algorithms,
                            options={"verify_signature": False})
        
        if http_method != 'POST':
            if claims['qsh'] != hash_url(http_method, url):
                raise DecodeError('qsh does not match')

        # verify shared secret
        token_content = jwt.decode(
            token,
            audience=claims.get('aud'),
            key=self.get_shared_secret(claims['iss']),
            algorithms=self.algorithms,
            leeway=self.leeway)

        # return client key
        return claims

    @staticmethod
    def _get_token(headers=None, query_params=None, body=None):
        if body:
            value = body.get('jwt')
            if value:
                return value

        if headers:
            for name, value in headers.items():
                if name.lower() == 'authorization':
                    parts = value.split()
                    if len(parts) > 1 and parts[0].lower() == 'jwt':
                        return parts[1]

        if query_params and 'jwt' in query_params:
            value = query_params['jwt']
            return value if isinstance(value, str) else value[0]

        raise DecodeError('JWT token not found')
