import json
import os

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def ice_servers(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    raw = os.environ.get('MAFIA_ICE_SERVERS', '').strip()
    if raw:
        try:
            servers = json.loads(raw)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'invalid_ice_server_config'}, status=500)
        if not isinstance(servers, list) or not servers or not all(isinstance(item, dict) and item.get('urls') for item in servers):
            return JsonResponse({'error': 'invalid_ice_server_config'}, status=500)
    else:
        servers = [{'urls': 'stun:stun.l.google.com:19302'}]
    response = JsonResponse({'ice_servers': servers})
    response['Cache-Control'] = 'no-store'
    return response
