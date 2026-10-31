import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST


def _payload(request):
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _user_payload(user):
    return {
        'id': user.pk,
        'username': user.username,
        'nickname': user.nickname or user.username,
        'avatar': user.avatar.url if user.avatar else None,
    }


@ensure_csrf_cookie
@require_http_methods(['GET'])
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False})
    return JsonResponse({'authenticated': True, 'user': _user_payload(request.user)})


@require_POST
def register(request):
    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'error': 'invalid_json'}, status=400)
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))
    nickname = str(data.get('nickname', '')).strip()[:30]
    if len(username) < 3 or len(username) > 150:
        return JsonResponse({'error': 'invalid_username', 'detail': 'Логин должен содержать от 3 до 150 символов.'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'weak_password', 'detail': 'Пароль должен содержать минимум 8 символов.'}, status=400)
    User = get_user_model()
    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({'error': 'username_taken'}, status=409)
    candidate = User(username=username, nickname=nickname or username)
    try:
        validate_password(password, user=candidate)
    except ValidationError as error:
        return JsonResponse({'error': 'weak_password', 'detail': list(error.messages)}, status=400)
    user = User.objects.create_user(username=username, password=password, nickname=nickname or username)
    login(request, user)
    return JsonResponse({'user': _user_payload(user)}, status=201)


@require_POST
def sign_in(request):
    data = _payload(request)
    if not isinstance(data, dict):
        return JsonResponse({'error': 'invalid_json'}, status=400)
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'error': 'invalid_credentials', 'detail': 'Неверный логин или пароль.'}, status=400)
    login(request, user)
    return JsonResponse({'user': _user_payload(user)})


@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({'ok': True})
