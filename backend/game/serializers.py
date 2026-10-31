from rest_framework import serializers
from .models import Game


class GamePlayerStateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    nickname = serializers.CharField()
    is_alive = serializers.BooleanField()


class GameStateSerializer(serializers.ModelSerializer):
    players = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    my_investigations = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ("phase", "round_number", "phase_ends_at", "winner", "players", "my_role", "my_investigations")

    def get_players(self, obj):
        return [{"user_id": p.player.user_id, "nickname": p.player.user.nickname or p.player.user.username, "is_alive": p.is_alive} for p in obj.players.select_related("player__user")]

    def get_my_role(self, obj):
        role = obj.players.filter(player__user=self.context["request"].user).first()
        return role.role if role else None

    def get_my_investigations(self, obj):
        role = obj.players.filter(player__user=self.context["request"].user).first()
        if not role:
            return []
        return [{"target_user_id": a.target.player.user_id, "role": a.result.get("role")} for a in obj.actions.filter(actor=role, action_type="investigate", result__has_key="role").select_related("target__player")]
