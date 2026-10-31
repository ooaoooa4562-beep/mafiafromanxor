from django.urls import path

from . import views

urlpatterns = [
    path('rooms/<uuid:code>/start/', views.start, name='game_start'),
    path('rooms/<uuid:code>/state/', views.state, name='game_state'),
    path('rooms/<uuid:code>/action/', views.action, name='game_action'),
]
