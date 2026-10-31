from django.db import transaction
from django.db.models import Count, F
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Room, RoomPlayer
from .serializers import RoomSerializer


class RoomListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = Room.objects.filter(is_private=False, status="waiting").annotate(
            member_count=Count("members")
        ).filter(member_count__lt=F("max_players")).prefetch_related("members__user", "owner")
        return Response(RoomSerializer(rooms, many=True).data)

    def post(self, request):
        serializer = RoomSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        room = serializer.save()
        RoomPlayer.objects.create(room=room, user=request.user)
        return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)


class RoomDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        room = get_object_or_404(Room.objects.prefetch_related("members__user", "owner"), code=code)
        is_member = RoomPlayer.objects.filter(room=room, user=request.user).exists()
        if room.is_private and not is_member:
            return Response({"detail": "Комната не найдена."}, status=status.HTTP_404_NOT_FOUND)
        return Response(RoomSerializer(room).data)


class RoomJoinView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, code):
        room = get_object_or_404(Room.objects.select_for_update(), code=code)
        if room.status != "waiting":
            return Response({"detail": "Игра уже началась."}, status=status.HTTP_409_CONFLICT)
        membership, created = RoomPlayer.objects.get_or_create(room=room, user=request.user)
        if created and room.members.count() > room.max_players:
            membership.delete()
            return Response({"detail": "В комнате нет свободных мест."}, status=status.HTTP_409_CONFLICT)
        return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)


class RoomReadyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, code):
        room = get_object_or_404(Room, code=code, status="waiting")
        membership = get_object_or_404(RoomPlayer, room=room, user=request.user)
        value = request.data.get("is_ready", True)
        if not isinstance(value, bool):
            return Response({"detail": "is_ready должен быть true или false."}, status=status.HTTP_400_BAD_REQUEST)
        membership.is_ready = value
        membership.save(update_fields=["is_ready"])
        return Response({"is_ready": membership.is_ready})


class RoomLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, code):
        room = get_object_or_404(Room.objects.select_for_update(), code=code)
        if room.status == "playing":
            return Response({"detail": "Нельзя покинуть комнату во время партии."}, status=status.HTTP_409_CONFLICT)
        membership = get_object_or_404(RoomPlayer, room=room, user=request.user)
        if room.owner_id == request.user.id:
            successor = RoomPlayer.objects.filter(room=room).exclude(user=request.user).select_related("user").order_by("joined_at").first()
            if successor:
                room.owner = successor.user
                room.save(update_fields=["owner"])
            else:
                room.delete()
                return Response({"deleted": True})
        membership.delete()
        return Response({"left": True})
