from django.contrib import admin

from .models import Resource


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription_event', 'content_object_fields', 'callback', 'content_object')
    fieldsets = (
        (None, {
            'fields': ('subscription_event', 'content_object_fields', 'callback')
        }),
        ('Resource', {
            'description': 'Resource form',
            'classes': ('wide',),
            'fields': ('content_type', 'object_pk',),  # 'content_object',
        }),
    )
