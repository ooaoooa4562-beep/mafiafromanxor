from django.urls import path

from . import views

urlpatterns = [
    path('', views.rooms_collection, name='rooms_collection'),
    path('<uuid:code>/join/', views.join_room, name='join_room'),
]
