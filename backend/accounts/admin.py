from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    list_display = (
        'id',
        'username',
        'nickname',
        'telegram_id',
        'is_active',
    )

    search_fields = (
        'username',
        'nickname',
        'telegram_id',
        'telegram_username',
    )

    list_filter = (
        'is_active',
        'telegram_is_verified',
        'is_staff',
    )