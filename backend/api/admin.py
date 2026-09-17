from django.contrib import admin

from .models import GameMatch, GameMove, PlayerProfile

admin.site.register(PlayerProfile)
admin.site.register(GameMatch)
admin.site.register(GameMove)
# Register your models here.
