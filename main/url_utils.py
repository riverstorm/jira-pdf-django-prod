"""Helper functions for dealing with URLs.
"""
from hashlib import sha256

try:
    from urllib.parse import quote, urlparse, parse_qs
except ImportError:
    from urllib import quote
    from urlparse import urlparse, parse_qs


def hash_url(http_method, url):
    """Hash a URL to create a value suitable for a `qsh` claim.

    See `Creating a query string hash`_ for more info.

    Args:
        http_method (string): HTTP method that will be used for the ensuing
            request.
        url (string): URL to hash. Must be relative to the host base URL found
            in the tenant information.

    Returns:
        string: suitable to be used as the value of a `qsh` claim in a JWT
            token.

    .. _Creating a query string hash:
       https://developer.atlassian.com/static/connect/docs/latest/concepts/understanding-jwt.html#qsh    
    """
    canonical_request = canonicalize_request(http_method, url)
    return sha256(canonical_request.encode('utf8')).hexdigest()


def canonicalize_request(http_method, url):
    """Form a `canonical-request` as defined in `Creating a query string hash`_

    Example:
        Give then following request

            GET "/path/to/service?zee_last=param&repeated=parameter 1&first=param&repeated=parameter 2"

        the canonical request is

            GET&/path/to/service&first=param&repeated=parameter%201,parameter%202&zee_last=param

    Args:
        http_method (string): HTTP method that will be used for the ensuing
            request.
        url (string): URL to hash. Must be relative to the host base URL found
            in the tenant information.

    Returns:
        string: canonical request

    .. _Creating a query string hash:
       https://developer.atlassian.com/static/connect/docs/latest/concepts/understanding-jwt.html#qsh
    """

    # This code ensures that in python 2 if you pass a unicode string with ascii
    # characters that it will be converted into a str. If you pass a unicode
    # str with non-ascii characters then its not a valid URL so we just error
    # out.
    #
    # The python URL libraries only support parsing and encoding URLs when
    # passed in as a str. In Python 2 this is an ascii string and in Python 3
    # its unicode.
    #
    # This does't mean our code doesn't support unicode. URLs must have i18n
    # characters encoded as ASCII using either Punycode or percent encoding.
    # We only accept valid encoded URLs, that is, URLs you could actually send
    # in a HTTP request.
    try:
        # Python 2 has str and unicode strings.
        if isinstance(url, unicode):
            url = url.encode()
    except NameError:
        # Python 3.
        pass

    # We want to treat '//path' as a path, not a hostname, so we must strip
    # out leading slashes before using urlparse:
    parsed_url = urlparse(url.lstrip('/'))

    def canonicalize_uri():
        path = parsed_url.path.strip('/').replace('&', quote('&'))
        yield '/' + path
        if parsed_url.params:
            # path params (not to be confused with query params)
            yield ';' + parsed_url.params

    def canonicalize_qs():
        parameters = parse_qs(parsed_url.query, keep_blank_values=True)
        for k, v in parameters.items():
            if k == 'jwt':
                continue
            # This incorrectly sorts the values by their `unquoted` values. It
            # should be sorting by the encoded values but the AC implementation
            # has a bug (JWT-20).
            yield quote(k, '~'), ','.join([quote(s, '~') for s in sorted(v)])

    canonical_uri = ''.join(canonicalize_uri())
    canonical_qs = '&'.join('='.join(x) for x in sorted(canonicalize_qs()))
    return '%s&%s&%s' % (http_method.upper(), canonical_uri, canonical_qs)


def parse_query_params(url):
    """Parse query parameters from a URL's query string.

    Args:
        url (string): URL from which to parse query parameters

    Returns:
        dict: the query parameters. Dictionary keys are query parameter names.
            Dictionary values are lists of string query parameter values as the
            same query parameter name can be listed multiple time in a URL's
            query string.

    .. _Creating a query string hash:
       https://developer.atlassian.com/static/connect/docs/latest/concepts/understanding-jwt.html#qsh
    """    
    return parse_qs(urlparse(url).query)