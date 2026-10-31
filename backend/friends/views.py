import json

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import Friendship


def _user_data(user):
    return {'id': user.pk, 'username': user.username, 'nickname': user.nickname or user.username}


@require_GET
def friends_list(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    rows = Friendship.objects.filter(
        Q(sender=request.user, status='accepted') | Q(receiver=request.user, status='accepted') |
        Q(sender=request.user, status='pending') | Q(receiver=request.user, status='pending')
    ).select_related('sender', 'receiver').order_by('-updated_at')
    result = {'friends': [], 'incoming': [], 'outgoing': []}
    for row in rows:
        other = row.receiver if row.sender_id == request.user.id else row.sender
        item = {'request_id': row.pk, 'user': _user_data(other), 'created_at': row.created_at.isoformat()}
        if row.status == 'accepted':
            result['friends'].append(item)
        elif row.receiver_id == request.user.id:
            result['incoming'].append(item)
        else:
            result['outgoing'].append(item)
    return JsonResponse(result)


@require_POST
def send_request(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    try:
        data = json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)
    username = str(data.get('username', '')).strip()
    User = get_user_model()
    target = User.objects.filter(username__iexact=username).first()
    if target is None:
        return JsonResponse({'error': 'user_not_found'}, status=404)
    if target.pk == request.user.pk:
        return JsonResponse({'error': 'cannot_add_self'}, status=400)
    existing = Friendship.objects.filter(
        Q(sender=request.user, receiver=target) | Q(sender=target, receiver=request.user)
    ).first()
    if existing:
        if existing.status == 'accepted':
            return JsonResponse({'error': 'already_friends'}, status=409)
        if existing.status == 'pending':
            return JsonResponse({'error': 'request_already_exists'}, status=409)
        if existing.status == 'blocked':
            return JsonResponse({'error': 'friendship_blocked'}, status=403)
        existing.delete()
    friendship = Friendship.objects.create(sender=request.user, receiver=target)
    return JsonResponse({'request_id': friendship.pk, 'user': _user_data(target), 'status': friendship.status}, status=201)


@require_POST
def respond_request(request, request_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    try:
        data = json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid_json'}, status=400)
    decision = data.get('decision')
    if decision not in ('accept', 'reject'):
        return JsonResponse({'error': 'invalid_decision'}, status=400)
    friendship = Friendship.objects.filter(pk=request_id, receiver=request.user, status='pending').first()
    if friendship is None:
        return JsonResponse({'error': 'request_not_found'}, status=404)
    friendship.status = 'accepted' if decision == 'accept' else 'rejected'
    friendship.save(update_fields=['status', 'updated_at'])
    return JsonResponse({'status': friendship.status, 'user': _user_data(friendship.sender)})


@require_POST
def block_user(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication_required'}, status=401)
    if user_id == request.user.pk:
        return JsonResponse({'error': 'cannot_block_self'}, status=400)
    User = get_user_model()
    target = User.objects.filter(pk=user_id).first()
    if target is None:
        return JsonResponse({'error': 'user_not_found'}, status=404)
    Friendship.objects.filter(
        Q(sender=request.user, receiver=target) | Q(sender=target, receiver=request.user)
    ).delete()
    Friendship.objects.create(sender=request.user, receiver=target, status='blocked')
    return JsonResponse({'status': 'blocked', 'user': _user_data(target)})
