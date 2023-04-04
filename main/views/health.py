from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def health(_):
    v = 1684568115641
    return JsonResponse({
        'status': 'ok',
        'version': v,
    })