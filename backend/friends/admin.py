from django.contrib import admin
from .models import Friendship


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("sender__username", "receiver__username", "sender__nickname", "receiver__nickname")
