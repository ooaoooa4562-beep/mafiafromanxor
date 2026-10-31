from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notify_voice_phase_change(room_code):
    layer = get_channel_layer()
    if layer is None:
        return
    for channel in ("lobby", "town", "mafia", "dead"):
        async_to_sync(layer.group_send)(
            f"voice_{room_code.hex}_{channel}",
            {"type": "voice.phase_changed"},
        )
        async_to_sync(layer.group_send)(
            f"chat_{room_code.hex}_{channel}",
            {"type": "chat.phase_changed"},
        )
