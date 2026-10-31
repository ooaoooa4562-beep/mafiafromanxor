import json
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import Room, RoomPlayer


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
            {'user_id': p.user_id, 'nickname': p.user.nickname or p.user.username, 'is_ready': p.is_ready, 'is_alive': p.is_alive}
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
        # Lock the concrete auth model row; request.user itself is a SimpleLazyObject.
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        RoomPlayer.objects.filter(user=request.user).delete()
        room = Room.objects.create(name=name, owner=request.user, max_players=max_players, is_private=is_private)
        RoomPlayer.objects.create(room=room, user=request.user, is_ready=True)
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
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        room = Room.objects.select_for_update().filter(code=room_code).first()
        if room is None:
            return JsonResponse({'error': 'room_not_found'}, status=404)
        if room.status != 'waiting':
            return JsonResponse({'error': 'room_unavailable'}, status=409)
        existing = RoomPlayer.objects.filter(room=room, user=request.user).first()
        if existing:
            return JsonResponse({'room': _room_payload(room), 'already_joined': True})
        if room.players.count() >= room.max_players:
            return JsonResponse({'error': 'room_full', 'detail': 'В комнате больше нет свободных мест.'}, status=409)
        # A player has one active room at a time. Switching rooms releases the old seat.
        RoomPlayer.objects.filter(user=request.user).delete()
        RoomPlayer.objects.create(room=room, user=request.user)
    return JsonResponse({'room': _room_payload(room)}, status=200)


@require_http_methods(['POST'])
def leave_room(request, code):
    if _auth_required(request):
        return JsonResponse({'error': 'authentication_required'}, status=401)
    try:
        room_code = UUID(str(code))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'room_not_found'}, status=404)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        room = Room.objects.filter(code=room_code).first()
        if room is None:
            return JsonResponse({'error': 'room_not_found'}, status=404)
        removed, _ = RoomPlayer.objects.filter(room=room, user=request.user).delete()
        players_count = room.players.count()
    return JsonResponse({'ok': True, 'removed': bool(removed), 'players_count': players_count})
