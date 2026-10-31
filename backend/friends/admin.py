from django.contrib import admin
from .models import Friendship


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'sender',
        'receiver',
        'status',
        'created_at',
    )

    list_filter = ('status', 'created_at')

    search_fields = (
        'sender__username',
        'sender__nickname',
        'receiver__username',
        'receiver__nickname',
    )