import main.jwt_atlassian as atlassian_jwt
from main.models import Client, User
from django.core.exceptions import PermissionDenied
import json
from sentry_sdk import capture_exception

class ConnectAuth(atlassian_jwt.Authenticator):
    def __init__(self):
        super(ConnectAuth, self).__init__()

    def get_shared_secret(self, client_key):
        #tenant_info = Client.objects.filter(key=client_key).latest('created_at')
        tenant_info = Client.objects.get(key=client_key)
        return tenant_info.shared_secret


def auth_required(function):
    connect_auth = ConnectAuth()
    def wrapper(request, *args, **kwargs):
        try:
            claims = connect_auth.authenticate(
                request.method,
                request.build_absolute_uri(),
                request.headers,
                json.loads(request.body.decode('utf-8'))
            )
            client = Client.objects.get(key=claims['iss'])
            user, _ = User.objects.get_or_create(client=client, user_id=claims['sub'])
            if client:
                kwargs['client'] = client
                kwargs['claims'] = claims
                kwargs['user'] = user
                return function(request, *args, **kwargs)
        except Exception as e:
            capture_exception(e)
            pass
        raise PermissionDenied
    return wrapper
