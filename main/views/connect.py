from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from main.models import *
import json, jwt, requests
from main.jwt_auth import auth_required
import atlassian_jwt
from sentry_sdk import capture_exception
from app.settings import CONNECT_FILE, BASE_URL


# Connect data
@csrf_exempt
def data(request):
    with open(CONNECT_FILE, 'r') as outfile:
        data = json.load(outfile)
    return JsonResponse(data)


# Install callback
@csrf_exempt
def install(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        header_jwt = request.headers['Authorization'].split('JWT ')[1]
        unverified_header_jwt = jwt.get_unverified_header(header_jwt)
        key_response = requests.get('https://connect-install-keys.atlassian.com/' + unverified_header_jwt['kid'])
        public_key = key_response.content
        expected_audience = BASE_URL
        expected_issuer = data.get('clientKey')
        decoded_jwt = jwt.decode(header_jwt, public_key, audience=expected_audience, issuer=expected_issuer, algorithms=['RS256'])
        if data.get('eventType') == 'installed':
            exists = Client.objects.filter(
                key=data.get('clientKey')
            ).exists()
            if not exists:
                client = Client.objects.create(
                    key=data.get('clientKey'),
                    shared_secret=data.get('sharedSecret'),
                    oauth_client_id=data.get('oauthClientId'),
                    public_key=data.get('publicKey'),
                    base_url=data.get('baseUrl'),
                    display_url=data.get('displayUrl'),
                    display_url_servicedesk=data.get('displayUrlServicedeskHelpCenter'),
                    product_type=data.get('productType'),
                    description=data.get('description'),
                    service_entitlement_number=data.get('serviceEntitlementNumber'),
                )
                if client:
                    return JsonResponse({'message': 'success'}, status=200)
            else:
                client = Client.objects.filter(key=data.get('clientKey')).get()
                client.shared_secret = data.get('sharedSecret')
                client.base_url = data.get('baseUrl')
                client.display_url = data.get('displayUrl')
                client.display_url_servicedesk = data.get('displayUrlServicedeskHelpCenter')
                client.save()
                return JsonResponse({'message': 'success'}, status=200)
        else:
            raise Exception('Wrong event type: ',  data)
    except Exception as e:
        capture_exception(e)
    return JsonResponse({'message': 'error'}, status=500)


# Uninstall callback
@csrf_exempt
def uninstall(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        print(data)
        header_jwt = request.headers['Authorization'].split('JWT ')[1]
        unverified_header_jwt = jwt.get_unverified_header(header_jwt)
        key_response = requests.get('https://connect-install-keys.atlassian.com/' + unverified_header_jwt['kid'])
        public_key = key_response.content
        expected_audience = BASE_URL
        expected_issuer = data.get('clientKey')
        decoded_jwt = jwt.decode(header_jwt, public_key, audience=expected_audience, issuer=expected_issuer, algorithms=['RS256'])
        if data.get('eventType') == 'uninstalled':
            client = Client.objects.get(key=data.get('clientKey'))
            if client:
                if client.delete():
                    return JsonResponse({'message': 'success'}, status=200)
    except Exception as e:
        capture_exception(e)
    return JsonResponse({'message': 'error'}, status=500)
