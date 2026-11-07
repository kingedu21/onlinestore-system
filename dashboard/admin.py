from django.contrib import admin

from .models import PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ('commission_rate', 'updated_at')
