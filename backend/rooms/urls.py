from django.urls import path
from .views import RoomDetailView, RoomJoinView, RoomLeaveView, RoomListCreateView, RoomReadyView

urlpatterns = [
    path("", RoomListCreateView.as_view(), name="room-list-create"),
    path("<uuid:code>/", RoomDetailView.as_view(), name="room-detail"),
    path("<uuid:code>/join/", RoomJoinView.as_view(), name="room-join"),
    path("<uuid:code>/ready/", RoomReadyView.as_view(), name="room-ready"),
    path("<uuid:code>/leave/", RoomLeaveView.as_view(), name="room-leave"),
]
