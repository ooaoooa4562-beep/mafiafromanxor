from django.urls import path

from . import views

urlpatterns = [
    path('', views.friends_list, name='friends_list'),
    path('requests/', views.send_request, name='friend_request'),
    path('requests/<int:request_id>/respond/', views.respond_request, name='friend_respond'),
    path('<int:user_id>/block/', views.block_user, name='friend_block'),
]
