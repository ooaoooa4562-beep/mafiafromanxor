from django.urls import path
from .views import GameActionView, GameAdvanceView, GameStartView, GameStateView

urlpatterns = [
    path("<uuid:code>/start/", GameStartView.as_view(), name="game-start"),
    path("<uuid:code>/state/", GameStateView.as_view(), name="game-state"),
    path("<uuid:code>/action/", GameActionView.as_view(), name="game-action"),
    path("<uuid:code>/advance/", GameAdvanceView.as_view(), name="game-advance"),
]
