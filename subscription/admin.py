from django.contrib import admin

from .models import Subscription, SubscriptionLine, Resource


@admin.register(SubscriptionLine)
class SubscriptionLineAdmin(admin.ModelAdmin):
    list_display = ('id', 'start', 'end', 'subscription')
    fieldsets = (
        (None, {
            'fields': ('start', 'end', 'subscription')
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'content_object', 'active')
    fieldsets = (
        (None, {
            'fields': ('name', 'active',)
        }),
        ('Resource', {
            'description': 'Resource form',
            'classes': ('wide',),
            'fields': ('content_type', 'object_pk',),   # 'content_object',
        }),
    )

    @staticmethod
    def content_object(obj):
        return obj.content_object


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
