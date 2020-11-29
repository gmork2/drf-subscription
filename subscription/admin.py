from django.contrib import admin

from .models import Subscription, SubscriptionLine, SubscriptionEvent, Resource


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('id', 'name', 'content_object', 'active')
    list_filter = ('content_type', 'active')
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


@admin.register(SubscriptionLine)
class SubscriptionLineAdmin(admin.ModelAdmin):
    search_fields = ('description',)
    date_hierarchy = 'start'
    list_display = ('id', 'start', 'end', 'subscription')
    list_filter = ('start', 'end')
    fieldsets = (
        (None, {
            'fields': ('start', 'end', 'subscription',)
        }),
    )


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    search_fields = ('description',)
    date_hierarchy = 'start'
    list_display = ('id', 'start', 'end', 'recurrence', 'subscription_line')
    list_filter = ('start', 'end',)
    fieldsets = (
        (None, {
            'fields': ('start', 'end', 'recurrence', 'subscription_line',)
        }),
    )


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    sortable_by = ('id', 'subscription_event', 'callback', 'content_object')
    search_fields = ('callback',)
    readonly_fields = ('content_object_fields',)
    list_display = ('id', 'subscription_event', 'content_object_fields', 'callback', 'content_object')
    list_filter = ('content_type', 'active')
    fieldsets = (
        (None, {
            'fields': ('subscription_event', 'callback', 'active')
        }),
        ('Resource', {
            'description': 'Resource form',
            'classes': ('wide',),
            'fields': ('content_type', 'object_pk', 'content_object_fields'),  # 'content_object',
        }),
    )
