from django.urls import path

from .views import (
    create_guest_player,
    create_match,
    health,
    match_detail,
    player_detail,
    record_move,
    surrender_match,
)

urlpatterns = [
    path('health/', health, name='health'),
    path('players/guest/', create_guest_player, name='create-guest-player'),
    path('players/<uuid:player_id>/', player_detail, name='player-detail'),
    path('matches/', create_match, name='create-match'),
    path('matches/<uuid:match_id>/', match_detail, name='match-detail'),
    path('matches/<uuid:match_id>/moves/', record_move, name='record-move'),
    path('matches/<uuid:match_id>/surrender/', surrender_match, name='surrender-match'),
]