import random
from collections import Counter
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from rooms.models import Room, RoomPlayer
from .models import Game, GameAction, PlayerRole

PHASE_SECONDS = {"night": 60, "day": 90, "voting": 45}


def _check_winner(game):
    alive = list(game.players.filter(is_alive=True).values_list("role", flat=True))
    mafia = alive.count("mafia")
    town = len(alive) - mafia
    if mafia == 0:
        game.phase, game.winner = "finished", "town"
    elif mafia >= town:
        game.phase, game.winner = "finished", "mafia"
    if game.phase == "finished":
        game.phase_ends_at = None
        game.room.status = "finished"
        game.room.save(update_fields=["status"])
        game.save(update_fields=["phase", "winner", "phase_ends_at"])
        return True
    return False


@transaction.atomic
def start_game(room, user):
    room = Room.objects.select_for_update().get(pk=room.pk)
    if room.owner_id != user.pk:
        raise ValidationError("Начать игру может только создатель комнаты.")
    if room.status != "waiting":
        raise ValidationError("Комната уже запущена или завершена.")
    members = list(RoomPlayer.objects.select_for_update().filter(room=room).select_related("user"))
    if len(members) < 4:
        raise ValidationError("Для начала игры нужно минимум 4 игрока.")
    if any(not member.is_ready for member in members):
        raise ValidationError("Все игроки должны подтвердить готовность.")
    roles = ["mafia"] * max(1, len(members) // 4)
    if len(members) >= 4:
        roles.append("detective")
    if len(members) >= 5:
        roles.append("doctor")
    roles.extend(["civilian"] * (len(members) - len(roles)))
    random.SystemRandom().shuffle(roles)
    game = Game.objects.create(room=room, phase="night", phase_ends_at=timezone.now() + timedelta(seconds=PHASE_SECONDS["night"]))
    PlayerRole.objects.bulk_create([PlayerRole(game=game, player=member, role=role) for member, role in zip(members, roles)])
    room.status = "playing"
    room.save(update_fields=["status"])
    return game


@transaction.atomic
def advance_game(game):
    game = Game.objects.select_for_update().select_related("room").get(pk=game.pk)
    if game.phase == "finished":
        return game
    if game.phase_ends_at and timezone.now() < game.phase_ends_at:
        raise ValidationError("Время текущей фазы ещё не закончилось.")

    if game.phase == "night":
        actions = list(game.actions.filter(phase="night", round_number=game.round_number).select_related("target"))
        kills = Counter(a.target_id for a in actions if a.action_type == "kill")
        heals = {a.target_id for a in actions if a.action_type == "heal"}
        if kills:
            target_id, votes = kills.most_common(1)[0]
            if votes > len([a for a in actions if a.action_type == "kill"]) / 2 and target_id not in heals:
                game.players.filter(pk=target_id).update(is_alive=False)
        for action in actions:
            if action.action_type == "investigate":
                action.result = {"role": action.target.role}
                action.save(update_fields=["result"])
        if _check_winner(game):
            return game
        game.phase = "day"
    elif game.phase == "day":
        game.phase = "voting"
    elif game.phase == "voting":
        votes = Counter(game.actions.filter(phase="voting", round_number=game.round_number).values_list("target_id", flat=True))
        if votes:
            target_id, count = votes.most_common(1)[0]
            if list(votes.values()).count(count) == 1:
                game.players.filter(pk=target_id).update(is_alive=False)
        if _check_winner(game):
            return game
        game.round_number += 1
        game.phase = "night"

    game.phase_ends_at = timezone.now() + timedelta(seconds=PHASE_SECONDS[game.phase])
    game.save(update_fields=["phase", "round_number", "phase_ends_at"])
    return game
