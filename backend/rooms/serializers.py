from rest_framework import serializers
from .models import Room, RoomPlayer


class RoomPlayerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    nickname = serializers.SerializerMethodField()

    class Meta:
        model = RoomPlayer
        fields = ("user_id", "nickname", "is_ready", "joined_at")

    def get_nickname(self, obj):
        return obj.user.nickname or obj.user.username


class RoomSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    players = RoomPlayerSerializer(source="members", many=True, read_only=True)
    player_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ("name", "code", "owner_name", "max_players", "is_private", "status", "created_at", "players", "player_count")
        read_only_fields = ("code", "owner_name", "status", "created_at", "players", "player_count")

    def get_owner_name(self, obj):
        return obj.owner.nickname or obj.owner.username

    def get_player_count(self, obj):
        return obj.members.count()

    def validate_max_players(self, value):
        if not 4 <= value <= 16:
            raise serializers.ValidationError("В комнате должно быть от 4 до 16 мест.")
        return value

    def create(self, validated_data):
        return Room.objects.create(owner=self.context["request"].user, **validated_data)
