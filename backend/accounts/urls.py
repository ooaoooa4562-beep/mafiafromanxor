from django.urls import path

from . import views

urlpatterns = [
    path('me/', views.me, name='auth_me'),
    path('register/', views.register, name='auth_register'),
    path('login/', views.sign_in, name='auth_login'),
    path('logout/', views.sign_out, name='auth_logout'),
]
