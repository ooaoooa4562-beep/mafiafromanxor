import json
from django.db.models import Q
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from rooms.models import Room

from .models import GameMatch
from .services import GameRuleError, start_match, submit_action


def _room_state(room, user):
    players = list(room.players.select_related('user').all())
    match = GameMatch.objects.filter(room=room).prefetch_related('participants__room_player__user').first()
    payload = {
        'room': {
            'code': str(room.code),
            'name': room.name,
            'status': room.status,
            'owner': room.owner.nickname or room.owner.username,
            'max_players': room.max_players,
            'players': [
                {'user_id': p.user_id, 'nickname': p.user.nickname or p.user.username, 'is_ready': p.is_ready,
                 'is_alive': p.is_alive}
                for p in players
            ],
        },
        'game': None,
    }
    if match:
        game = {
            'phase': match.phase,
            'round': match.round_number,
            'winner': match.winner or None,
            'participants': [
                {'user_id': p.room_player.user_id, 'nickname': p.room_player.user.nickname or p.room_player.user.username,
                 'is_alive': p.is_alive}
                for p in match.participants.select_related('room_player__user').all()
            ],
            'my_role': None,
        }
        mine = match.participants.filter(room_player__user=user).first()
        if mine:
            game['my_role'] = mine.role
            if mine.role == 'mafia':
                game['mafia_teammates'] = [
                    p.room_player.user.nickname or p.room_player.user.username
                    for p in match.participants.filter(role='mafia').exclude(pk=mine.pk).select_related('room_player__user')
                ]
        if match.phase == 'finished':
            for item, participant in zip(game['participants'], match.participants.select_related('room_player__user').all()):
                item['role'] = participant.role
        payload['game'] = game
    return payload


def _broadcast(room_code, event_name='room.updated'):
    layer = get_channel_layer()
    if layer:
        async_to_sync(layer.group_send)(f'room_{room_code.hex}', {'type': 'room.event', 'event': event_name})


@require_POST
def start(request, code):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    try:
        room_code = UUID(str(code))
        match = start_match(room_code, request.user)
    except ValueError:
        return JsonResponse({'error': 'room_not_found'}, status=404)
    except GameRuleError as error:
        return JsonResponse({'error': 'game_rule', 'detail': error.message}, status=error.status)
    _broadcast(room_code, 'game.started')
    return JsonResponse({'game': {'phase': match.phase, 'round': match.round_number}}, status=201)


@require_GET
def state(request, code):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    try:
        room_code = UUID(str(code))
    except ValueError:
        return JsonResponse({'error': 'room_not_found'}, status=404)
    room = Room.objects.filter(code=room_code, players__user=request.user).select_related('owner').first()
    if room is None:
        return JsonResponse({'error': 'room_not_found'}, status=404)
    return JsonResponse(_room_state(room, request.user))


@require_POST
def action(request, code):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    try:
        data = json.loads(request.body or '{}')
        if not isinstance(data, dict):
            return JsonResponse({'error': 'invalid_request'}, status=400)
        target_id = int(data.get('target_user_id'))
        room_code = UUID(str(code))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
        return JsonResponse({'error': 'invalid_request'}, status=400)
    try:
        result = submit_action(room_code, request.user, target_id)
    except GameRuleError as error:
        return JsonResponse({'error': 'game_rule', 'detail': error.message}, status=error.status)
    _broadcast(room_code, 'game.updated')
    return JsonResponse(result)


@require_GET
def stats(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    completed = request.user.room_memberships.filter(game_participant__match__phase='finished')
    played = completed.count()
    wins = completed.filter(
        Q(game_participant__role='mafia', game_participant__match__winner='mafia') |
        (~Q(game_participant__role='mafia') & Q(game_participant__match__winner='town'))
    ).count()
    mafia_games = completed.filter(game_participant__role='mafia').count()
    recent = []
    for membership in completed.select_related('game_participant__match__room').order_by('-game_participant__match__finished_at')[:10]:
        participant = membership.game_participant
        match = participant.match
        won = (participant.role == 'mafia' and match.winner == 'mafia') or (participant.role != 'mafia' and match.winner == 'town')
        recent.append({
            'room': match.room.name,
            'role': participant.role,
            'winner': match.winner,
            'result': 'win' if won else 'loss',
            'finished_at': match.finished_at.isoformat() if match.finished_at else None,
        })
    return JsonResponse({
        'played': played,
        'wins': wins,
        'losses': played - wins,
        'win_rate': round((wins / played) * 100, 1) if played else 0,
        'mafia_games': mafia_games,
        'recent_matches': recent,
    })
