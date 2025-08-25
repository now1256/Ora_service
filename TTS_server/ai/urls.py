"""
"""
from django.urls import path
from . import views

urlpatterns = [
    path("tts", views.tts, name="tts"),
    path("set_gpt_weights", views.set_gpt_weights, name="set_gpt_weights"),
    path("set_sovits_weights", views.set_sovits_weights, name="set_sovits_weights"),
    path("set_refer_audio", views.set_refer_audio, name="set_refer_audio"),
    path("health", views.health, name="health"),
    path('api/convert-tts/', views.convert_tts, name='convert_tts'),
]