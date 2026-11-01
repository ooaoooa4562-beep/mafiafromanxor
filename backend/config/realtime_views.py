import re
import time
from uuid import UUID

import jwt
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from game.models import GameMatch, GameParticipant
from rooms.models import Room


CHANNEL_RE = re.compile(r"^\\$room:([0-9a-fA-F-]{36}):(chat|game|voice:(lobby|finished|dead|living|mafia))$")


def _token_secret():
    secret = getattr(settings, "CENTRIFUGO_TOKEN_SECRET", "")
    if not secret:
        return None
    return secret


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
    response = JsonResponse({"token": token})
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
    try:
        room_code = UUID(match.group(1))
    except ValueError:
        return JsonResponse({"detail": "invalid_channel"}, status=400)

    room = Room.objects.filter(code=room_code, players__user_id=request.user.pk).first()
    if room is None:
        return JsonResponse({"detail": "permission_denied"}, status=403)

    channel_kind = match.group(2)
    if channel_kind.startswith("voice:"):
        requested_voice_channel = channel_kind.split(":", 1)[1]
        game = GameMatch.objects.filter(room=room).first()
        if game is None:
            allowed_voice_channel = "lobby"
        else:
            participant = GameParticipant.objects.filter(
                match=game, room_player__user_id=request.user.pk
            ).first()
            if participant is None:
                allowed_voice_channel = None
            elif game.phase == "finished":
                allowed_voice_channel = "finished"
            elif not participant.is_alive:
                allowed_voice_channel = "dead"
            elif game.phase == "day":
                allowed_voice_channel = "living"
            elif participant.role == "mafia":
                allowed_voice_channel = "mafia"
            else:
                allowed_voice_channel = None
        if requested_voice_channel != allowed_voice_channel:
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
