from django.contrib import admin

from .models import GameAction, GameMatch, GameParticipant


class GameParticipantInline(admin.TabularInline):
    model = GameParticipant
    extra = 0
    readonly_fields = ('room_player', 'role', 'is_alive')


@admin.register(GameMatch)
class GameMatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'phase', 'round_number', 'winner', 'started_at', 'finished_at')
    list_filter = ('phase', 'winner', 'started_at')
    search_fields = ('room__name', 'room__code')
    inlines = (GameParticipantInline,)


@admin.register(GameAction)
class GameActionAdmin(admin.ModelAdmin):
    list_display = ('match', 'round_number', 'action_type', 'actor', 'target', 'created_at')
    list_filter = ('action_type', 'round_number')
