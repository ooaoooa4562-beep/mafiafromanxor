from django.contrib import admin
from .models import Room, RoomPlayer


class RoomPlayerInline(admin.TabularInline):
    model = RoomPlayer
    extra = 0
    readonly_fields = ("joined_at",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "owner", "status", "is_private", "max_players", "created_at")
    list_filter = ("status", "is_private", "created_at")
    search_fields = ("name", "code", "owner__username", "owner__nickname")
    readonly_fields = ("code", "created_at")
    inlines = (RoomPlayerInline,)


@admin.register(RoomPlayer)
class RoomPlayerAdmin(admin.ModelAdmin):
    list_display = ("room", "user", "is_ready", "joined_at")
    list_filter = ("is_ready",)
    search_fields = ("room__name", "user__username", "user__nickname")
