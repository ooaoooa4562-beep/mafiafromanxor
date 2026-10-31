from django.contrib import admin
from .models import Game, GameAction, PlayerRole


class PlayerRoleInline(admin.TabularInline):
    model = PlayerRole
    extra = 0
    readonly_fields = ("role", "is_alive")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("room", "phase", "round_number", "winner", "phase_ends_at")
    list_filter = ("phase", "winner")
    inlines = (PlayerRoleInline,)


@admin.register(GameAction)
class GameActionAdmin(admin.ModelAdmin):
    list_display = ("game", "actor", "action_type", "target", "phase", "round_number")
    list_filter = ("action_type", "phase", "round_number")
