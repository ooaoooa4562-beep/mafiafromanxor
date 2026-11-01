import json
import re
import time
from uuid import UUID

import jwt
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from game.models import GameMatch, GameParticipant
from rooms.models import Room, RoomMessage

from .centrifugo import publish


CHANNEL_RE = re.compile(r"^\\$room-([0-9a-fA-F-]{36})-(chat|game|voice-(lobby|finished|dead|living|mafia))$")


def _token_secret():
    return getattr(settings, "CENTRIFUGO_TOKEN_SECRET", "") or None


def _room_and_member(code, user):
    try:
        room_code = UUID(str(code))
    except (ValueError, TypeError):
        return None
    return Room.objects.filter(code=room_code, players__user_id=user.pk).first()


def _allowed_voice_channel(room, user_id):
    match = GameMatch.objects.filter(room=room).first()
    if match is None:
        return "lobby"
    participant = GameParticipant.objects.filter(
        match=match, room_player__user_id=user_id
    ).first()
    if participant is None:
        return None
    if match.phase == "finished":
        return "finished"
    if not participant.is_alive:
        return "dead"
    if match.phase == "day":
        return "living"
    if participant.role == "mafia":
        return "mafia"
    return None


def _message_payload(row):
    user = row.user
    return {
        "id": row.id,
        "user_id": row.user_id,
        "nickname": user.nickname or user.username,
        "content": row.content,
        "created_at": row.created_at.isoformat(),
    }


@require_GET
def connection_token(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "authentication_required"}, status=401)
    secret = _token_secret()
    if not secret:
        return JsonResponse({"detail": "realtime_not_configured"}, status=503)
    token = jwt.encode(
        {"sub": str(request.user.pk), "iat": int(time.time()), "exp": int(time.time()) + 600},
        secret,
        algorithm="HS256",
    )
    response = JsonResponse({"token": token, "url": settings.CENTRIFUGO_PUBLIC_URL})
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def subscription_token(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "authentication_required"}, status=401)
    secret = _token_secret()
    if not secret:
        return JsonResponse({"detail": "realtime_not_configured"}, status=503)

    channel = request.GET.get("channel", "")
    match = CHANNEL_RE.fullmatch(channel)
    if not match:
        return JsonResponse({"detail": "invalid_channel"}, status=400)
    room = _room_and_member(match.group(1), request.user)
    if room is None:
        return JsonResponse({"detail": "permission_denied"}, status=403)

    channel_kind = match.group(2)
    if channel_kind.startswith("voice-"):
        requested_voice_channel = channel_kind.split("-", 1)[1]
        if requested_voice_channel != _allowed_voice_channel(room, request.user.pk):
            return JsonResponse({"detail": "permission_denied"}, status=403)

    token = jwt.encode(
        {
            "sub": str(request.user.pk),
            "channel": channel,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        },
        secret,
        algorithm="HS256",
    )
    response = JsonResponse({"token": token})
    response["Cache-Control"] = "no-store"
    return response



@require_GET
def room_chat_history(request, code):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "authentication_required"}, status=401)
    room = _room_and_member(code, request.user)
    if room is None:
        return JsonResponse({"detail": "room_not_found"}, status=404)
    rows = RoomMessage.objects.filter(room=room).select_related("user").order_by("-created_at", "-id")[:50]
    return JsonResponse({"messages": [_message_payload(row) for row in reversed(list(rows))]})


@require_POST
def send_room_message(request, code):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "authentication_required"}, status=401)
    room = _room_and_member(code, request.user)
    if room is None:
        return JsonResponse({"detail": "room_not_found"}, status=404)
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "invalid_json"}, status=400)
    message = data.get("message") if isinstance(data, dict) else None
    if not isinstance(message, str):
        return JsonResponse({"detail": "invalid_message"}, status=400)
    message = message.strip()
    if not message or len(message) > 1000:
        return JsonResponse({"detail": "message_length_invalid"}, status=400)

    row = RoomMessage.objects.create(room=room, user=request.user, content=message)
    payload = _message_payload(row)
    publish(f"$room-{room.code}-chat", {"type": "chat.message", "message": payload})
    return JsonResponse({"message": payload}, status=201)


@require_POST
def voice_join(request, code):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "authentication_required"}, status=401)
    room = _room_and_member(code, request.user)
    if room is None:
        return JsonResponse({"detail": "room_not_found"}, status=404)
    channel = _allowed_voice_channel(room, request.user.pk)
    if channel is None:
        return JsonResponse({"detail": "voice_channel_unavailable"}, status=403)
    publish(
        f"$room-{room.code}-voice-{channel}",
        {"type": "voice.presence", "user_id": request.user.pk, "state": "joined"},
    )
    return JsonResponse({"channel": channel})


@require_POST
def voice_leave(request, code):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "authentication_required"}, status=401)
    room = _room_and_member(code, request.user)
    if room is None:
        return JsonResponse({"detail": "room_not_found"}, status=404)
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "invalid_json"}, status=400)
    channel = data.get("channel") if isinstance(data, dict) else None
    if channel not in {"lobby", "finished", "dead", "living", "mafia"}:
        return JsonResponse({"detail": "invalid_voice_channel"}, status=400)
    publish(
        f"$room-{room.code}-voice-{channel}",
        {"type": "voice.presence", "user_id": request.user.pk, "state": "left"},
    )
    return JsonResponse({"ok": True})


@require_POST
def voice_signal(request, code):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "authentication_required"}, status=401)
    room = _room_and_member(code, request.user)
    if room is None:
        return JsonResponse({"detail": "room_not_found"}, status=404)
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "invalid_json"}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"detail": "invalid_request"}, status=400)

    channel = _allowed_voice_channel(room, request.user.pk)
    signal_type = data.get("signal_type")
    payload = data.get("payload")
    if channel is None or signal_type not in {"offer", "answer", "ice"} or not isinstance(payload, dict):
        return JsonResponse({"detail": "invalid_signal"}, status=400)
    if len(str(payload)) > 12000:
        return JsonResponse({"detail": "signal_too_large"}, status=400)

    target_id = payload.get("to")
    if not isinstance(target_id, int):
        return JsonResponse({"detail": "invalid_target"}, status=400)
    target_room = Room.objects.filter(
        code=room.code, players__user_id=target_id
    ).first()
    if target_room is None or _allowed_voice_channel(target_room, target_id) != channel:
        return JsonResponse({"detail": "target_not_in_voice_channel"}, status=403)

    required_key = "candidate" if signal_type == "ice" else "description"
    if not isinstance(payload.get(required_key), dict):
        return JsonResponse({"detail": "invalid_signal_payload"}, status=400)
    publish(
        f"$room-{room.code}-voice-{channel}",
        {
            "type": "voice.signal",
            "from_user_id": request.user.pk,
            "signal_type": signal_type,
            "payload": payload,
        },
    )
    return JsonResponse({"ok": True})
