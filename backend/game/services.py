import random

from django.db import transaction
from django.utils import timezone

from rooms.models import Room, RoomPlayer

from .models import GameAction, GameMatch, GameParticipant


class GameRuleError(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status
        super().__init__(message)


def _winner(match):
    living = list(match.participants.filter(is_alive=True))
    mafia = sum(1 for player in living if player.role == 'mafia')
    town = len(living) - mafia
    if mafia == 0:
        return 'town'
    if mafia >= town:
        return 'mafia'
    return ''


def _finish_if_won(match):
    winner = _winner(match)
    if winner:
        match.phase = 'finished'
        match.winner = winner
        match.finished_at = timezone.now()
        match.room.status = 'finished'
        match.room.save(update_fields=['status'])
        match.save(update_fields=['phase', 'winner', 'finished_at'])
    return winner


def start_match(room_code, user):
    with transaction.atomic():
        room = Room.objects.select_for_update().filter(code=room_code).first()
        if room is None:
            raise GameRuleError('Комната не найдена.', 404)
        if room.owner_id != user.id:
            raise GameRuleError('Начать игру может только создатель комнаты.', 403)
        if room.status != 'waiting':
            raise GameRuleError('Эта комната уже запущена или завершена.', 409)
        players = list(RoomPlayer.objects.select_for_update().filter(room=room).select_related('user'))
        if len(players) < 4:
            raise GameRuleError('Для начала партии нужно минимум 4 игрока.', 409)
        if len(players) > room.max_players:
            raise GameRuleError('В комнате превышен лимит игроков.', 409)
        roles = ['mafia'] * max(1, len(players) // 4)
        if len(players) >= 4:
            roles.extend(['doctor', 'detective'])
        roles.extend(['citizen'] * (len(players) - len(roles)))
        random.SystemRandom().shuffle(roles)
        match = GameMatch.objects.create(room=room, phase='night', round_number=1)
        for player, role in zip(players, roles):
            GameParticipant.objects.create(match=match, room_player=player, role=role, is_alive=True)
        room.status = 'playing'
        room.save(update_fields=['status'])
        return match


def _resolve_night(match):
    current = match.actions.filter(round_number=match.round_number)
    mafia_actions = list(current.filter(action_type='mafia').select_related('target'))
    doctor_action = current.filter(action_type='doctor').select_related('target').first()
    detective_action = current.filter(action_type='detective').select_related('target').first()

    victim = None
    if mafia_actions:
        counts = {}
        for action in mafia_actions:
            if action.target_id:
                counts[action.target_id] = counts.get(action.target_id, 0) + 1
        if counts:
            highest = max(counts.values())
            tied = [target_id for target_id, count in counts.items() if count == highest]
            victim = RoomPlayer.objects.filter(pk=random.SystemRandom().choice(tied)).first()

    protected_id = doctor_action.target_id if doctor_action else None
    eliminated = None
    if victim and victim.pk != protected_id:
        victim.is_alive = False
        victim.save(update_fields=['is_alive'])
        GameParticipant.objects.filter(match=match, room_player=victim).update(is_alive=False)
        eliminated = victim.user.nickname or victim.user.username

    winner = _finish_if_won(match)
    if not winner:
        match.phase = 'day'
        match.phase_started_at = timezone.now()
        match.save(update_fields=['phase', 'phase_started_at'])

    return {'eliminated': eliminated, 'protected': bool(victim and victim.pk == protected_id), 'winner': winner}


def _resolve_day(match):
    actions = list(match.actions.filter(round_number=match.round_number, action_type='vote').exclude(target__isnull=True))
    counts = {}
    for action in actions:
        counts[action.target_id] = counts.get(action.target_id, 0) + 1
    eliminated = None
    if counts:
        highest = max(counts.values())
        tied = [target_id for target_id, count in counts.items() if count == highest]
        if len(tied) == 1:
            target = RoomPlayer.objects.filter(pk=tied[0]).first()
            if target:
                target.is_alive = False
                target.save(update_fields=['is_alive'])
                GameParticipant.objects.filter(match=match, room_player=target).update(is_alive=False)
                eliminated = target.user.nickname or target.user.username

    winner = _finish_if_won(match)
    if not winner:
        match.round_number += 1
        match.phase = 'night'
        match.phase_started_at = timezone.now()
        match.save(update_fields=['round_number', 'phase', 'phase_started_at'])
    return {'eliminated': eliminated, 'winner': winner}


def submit_action(room_code, user, target_user_id):
    with transaction.atomic():
        match = GameMatch.objects.select_for_update().select_related('room').filter(room__code=room_code).first()
        if match is None:
            raise GameRuleError('Партия не найдена.', 404)
        if match.phase == 'finished':
            raise GameRuleError('Партия уже завершена.', 409)
        actor = match.participants.select_for_update().filter(room_player__user=user, is_alive=True).select_related('room_player').first()
        if actor is None:
            raise GameRuleError('Ты не являешься живым участником этой партии.', 403)

        if match.phase == 'night':
            if actor.role not in ('mafia', 'doctor', 'detective'):
                raise GameRuleError('У этой роли нет ночного действия.', 403)
            action_type = actor.role
            if actor.role == 'mafia':
                target = match.participants.filter(room_player__user_id=target_user_id, is_alive=True).exclude(role='mafia').select_related('room_player').first()
            else:
                target = match.participants.filter(room_player__user_id=target_user_id, is_alive=True).select_related('room_player').first()
        else:
            action_type = 'vote'
            target = match.participants.filter(room_player__user_id=target_user_id, is_alive=True).select_related('room_player').first()

        if target is None:
            raise GameRuleError('Цель не найдена или уже выбыла.', 400)
        if target.room_player.user_id == user.id and not (match.phase == 'night' and actor.role == 'doctor'):
            raise GameRuleError('Нельзя выбрать самого себя.', 400)

        previous = GameAction.objects.filter(match=match, round_number=match.round_number, action_type=action_type, actor=actor.room_player).first()
        if previous:
            raise GameRuleError('Ты уже сделал ход в этой фазе.', 409)
        GameAction.objects.create(match=match, round_number=match.round_number, action_type=action_type, actor=actor.room_player, target=target.room_player)

        result = {}
        if match.phase == 'night':
            required = match.participants.filter(is_alive=True, role__in=['mafia', 'doctor', 'detective']).count()
            completed = match.actions.filter(round_number=match.round_number, action_type__in=['mafia', 'doctor', 'detective']).count()
            if completed >= required:
                result = _resolve_night(match)
        else:
            required = match.participants.filter(is_alive=True).count()
            completed = match.actions.filter(round_number=match.round_number, action_type='vote').count()
            if completed >= required:
                result = _resolve_day(match)

        response = {'phase': match.phase, 'round': match.round_number, 'result': result}
        if actor.role == 'detective' and action_type == 'detective':
            response['investigation'] = {'is_mafia': target.role == 'mafia'}
        return response
