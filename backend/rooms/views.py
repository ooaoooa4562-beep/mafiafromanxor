import json
from uuid import UUID

from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Room, RoomPlayer


def _broadcast_room(code, event='room.updated'):
    layer = get_channel_layer()
    if layer:
        async_to_sync(layer.group_send)(f'room_{code.hex}', {'type': 'room.event', 'event': event})


def _auth_required(request):
    return not request.user.is_authenticated


def _room_payload(room):
    players = list(room.players.select_related('user').all())
    return {
        'id': room.id,
        'name': room.name,
        'code': str(room.code),
        'owner': room.owner.nickname or room.owner.username,
        'max_players': room.max_players,
        'players_count': len(players),
        'players': [
            {'nickname': p.user.nickname or p.user.username, 'is_ready': p.is_ready, 'is_alive': p.is_alive}
            for p in players
        ],
        'is_private': room.is_private,
        'status': room.status,
        'created_at': room.created_at.isoformat(),
    }


@require_http_methods(['GET', 'POST'])
def rooms_collection(request):
    if _auth_required(request):
        return JsonResponse({'error': 'authentication_required'}, status=401)

    if request.method == 'GET':
        rooms = Room.objects.filter(status='waiting', is_private=False).select_related('owner').prefetch_related('players')[:50]
        return JsonResponse({'rooms': [_room_payload(room) for room in rooms]})

    try:
        data = json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({'error': 'invalid_json'}, status=400)
    name = str(data.get('name', '')).strip()
    try:
        max_players = int(data.get('max_players', 10))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid_max_players'}, status=400)
    is_private = data.get('is_private', True)
    if not isinstance(is_private, bool):
        return JsonResponse({'error': 'invalid_is_private'}, status=400)
    if not name or len(name) > 100:
        return JsonResponse({'error': 'name_required', 'detail': 'Название должно содержать от 1 до 100 символов.'}, status=400)
    if not 4 <= max_players <= 16:
        return JsonResponse({'error': 'invalid_max_players', 'detail': 'Допустимо от 4 до 16 игроков.'}, status=400)

    with transaction.atomic():
        current = list(RoomPlayer.objects.select_related('room').filter(user=request.user))
        if any(item.room.status == 'playing' for item in current):
            return JsonResponse({'error': 'already_in_game', 'detail': 'Сначала закончи текущую партию.'}, status=409)
        old_codes = [item.room.code for item in current]
        RoomPlayer.objects.filter(user=request.user).delete()
        room = Room.objects.create(name=name, owner=request.user, max_players=max_players, is_private=is_private)
        RoomPlayer.objects.create(room=room, user=request.user, is_ready=True)
    for old_code in old_codes:
        _broadcast_room(old_code)
    return JsonResponse({'room': _room_payload(room)}, status=201)


@require_http_methods(['POST'])
def join_room(request, code):
    if _auth_required(request):
        return JsonResponse({'error': 'authentication_required'}, status=401)
    try:
        data = json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'error': 'invalid_json'}, status=400)
    try:
        room_code = UUID(str(code))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'room_not_found'}, status=404)

    with transaction.atomic():
        room = Room.objects.select_for_update().filter(code=room_code).first()
        if room is None:
            return JsonResponse({'error': 'room_not_found'}, status=404)
        if room.status != 'waiting':
            return JsonResponse({'error': 'room_unavailable'}, status=409)
        membership = RoomPlayer.objects.filter(room=room, user=request.user).first()
        if membership:
            return JsonResponse({'room': _room_payload(room), 'already_joined': True})
        if room.players.count() >= room.max_players:
            return JsonResponse({'error': 'room_full', 'detail': 'В комнате нет свободных мест.'}, status=409)
        current = list(RoomPlayer.objects.select_related('room').filter(user=request.user))
        if any(item.room.status == 'playing' for item in current):
            return JsonResponse({'error': 'already_in_game', 'detail': 'Сначала закончи текущую партию.'}, status=409)
        old_codes = [item.room.code for item in current]
        RoomPlayer.objects.filter(user=request.user).delete()
        RoomPlayer.objects.create(room=room, user=request.user, is_ready=False)
    for old_code in old_codes:
        _broadcast_room(old_code)
    _broadcast_room(room_code)
    return JsonResponse({'room': _room_payload(room)}, status=200)


@require_POST
def leave_room(request, code):
    if _auth_required(request):
        return JsonResponse({'error': 'authentication_required'}, status=401)
    try:
        room_code = UUID(str(code))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'room_not_found'}, status=404)
    with transaction.atomic():
        room = Room.objects.select_for_update().filter(code=room_code).first()
        if room is None:
            return JsonResponse({'error': 'room_not_found'}, status=404)
        membership = RoomPlayer.objects.select_for_update().filter(room=room, user=request.user).first()
        if membership is None:
            return JsonResponse({'left': True, 'already_left': True})
        if room.status == 'playing':
            return JsonResponse({'error': 'game_in_progress', 'detail': 'Нельзя покинуть комнату во время партии.'}, status=409)
        membership.delete()
        remaining = list(room.players.select_related('user').order_by('joined_at'))
        if not remaining:
            room.delete()
            _broadcast_room(room_code)
            return JsonResponse({'left': True, 'room_deleted': True})
        if room.owner_id == request.user.pk:
            room.owner = remaining[0].user
            room.save(update_fields=['owner'])
    _broadcast_room(room_code)
    return JsonResponse({'left': True})
