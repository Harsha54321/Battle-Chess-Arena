from django.contrib import admin

from .models import GameMatch, GameMove, PlayerProfile

@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
	list_display = ('username', 'rating', 'level', 'coins', 'is_suspended', 'created_at')
	list_filter = ('is_suspended',)
	search_fields = ('username', 'id')
	readonly_fields = ('id', 'created_at', 'updated_at')


admin.site.register(GameMatch)
admin.site.register(GameMove)
