from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rooms.models import Room, RoomPlayer
from .models import Game, PlayerRole, GameAction
from .serializers import GameStateSerializer
from .services import advance_game, start_game


class GameStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, code):
        room = get_object_or_404(Room, code=code)
        game = start_game(room, request.user)
        return Response(GameStateSerializer(game, context={"request": request}).data, status=status.HTTP_201_CREATED)


class GameStateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        room = get_object_or_404(Room, code=code)
        if not RoomPlayer.objects.filter(room=room, user=request.user).exists():
            return Response({"detail": "Ты не состоишь в этой комнате."}, status=status.HTTP_403_FORBIDDEN)
        game = get_object_or_404(Game.objects.prefetch_related("players__player__user", "actions"), room=room)
        return Response(GameStateSerializer(game, context={"request": request}).data)


class GameActionView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, code):
        room = get_object_or_404(Room, code=code)
        if not RoomPlayer.objects.filter(room=room, user=request.user).exists():
            return Response({"detail": "Ты не состоишь в этой комнате."}, status=status.HTTP_403_FORBIDDEN)
        game = get_object_or_404(Game.objects.select_for_update(), room=room)
        actor = get_object_or_404(PlayerRole, game=game, player__user=request.user)
        if game.phase == "finished" or not actor.is_alive:
            return Response({"detail": "Ты не можешь совершить действие."}, status=status.HTTP_409_CONFLICT)
        if game.phase_ends_at and timezone.now() >= game.phase_ends_at:
            return Response({"detail": "Время этой фазы уже закончилось."}, status=status.HTTP_409_CONFLICT)
        action_type = request.data.get("action")
        allowed = {"night": {"mafia": "kill", "doctor": "heal", "detective": "investigate"}, "voting": {"mafia": "vote", "doctor": "vote", "detective": "vote", "civilian": "vote"}}
        expected = allowed.get(game.phase, {}).get(actor.role)
        if action_type != expected:
            return Response({"detail": "Это действие недоступно в текущей фазе."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            target_user_id = int(request.data.get("target_user_id"))
        except (TypeError, ValueError):
            return Response({"detail": "Укажи target_user_id."}, status=status.HTTP_400_BAD_REQUEST)
        target = get_object_or_404(PlayerRole, game=game, player__user_id=target_user_id, is_alive=True)
        if target.pk == actor.pk:
            return Response({"detail": "Нельзя выбрать самого себя."}, status=status.HTTP_400_BAD_REQUEST)
        if action_type == "kill" and target.role == "mafia":
            return Response({"detail": "Мафия не может выбрать своего."}, status=status.HTTP_400_BAD_REQUEST)
        GameAction.objects.update_or_create(
            game=game, actor=actor, phase=game.phase, round_number=game.round_number,
            defaults={"target": target, "action_type": action_type, "result": {}},
        )
        return Response({"accepted": True})


class GameAdvanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, code):
        room = get_object_or_404(Room, code=code)
        if room.owner_id != request.user.id:
            return Response({"detail": "Переводить фазу может только создатель комнаты."}, status=status.HTTP_403_FORBIDDEN)
        game = get_object_or_404(Game, room=room)
        game = advance_game(game)
        return Response(GameStateSerializer(game, context={"request": request}).data)
