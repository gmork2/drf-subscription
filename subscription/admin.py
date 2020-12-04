from django.contrib import admin
from django.utils.translation import gettext as _
from django.core.handlers.wsgi import WSGIRequest
from django.db.models.signals import post_save
from django.contrib.messages import constants

from .managers import SubscriptionQuerySet, ResourceQuerySet
from .models import Subscription, SubscriptionLine, SubscriptionEvent, Resource
from .signals import default_receiver


def activate(
    modeladmin: 'SubscriptionAdmin',
    request: WSGIRequest,
    queryset: SubscriptionQuerySet
):
    for instance in queryset:
        instance.activate()
    modeladmin.message_user(request, _('Total activated: %s' % queryset.count()))


activate.short_description = "Activate a subscription"


def connect(
    modeladmin: 'SubscriptionAdmin',
    request: WSGIRequest,
    queryset: ResourceQuerySet
) -> None:
    for instance in queryset:
        model_class = instance.content_type.model_class()
        post_save.connect(default_receiver, sender=model_class)

    modeladmin.message_user(request, _('Done!'))


connect.short_description = "Connect signals"


def disconnect(
    modeladmin: 'SubscriptionAdmin',
    request: WSGIRequest,
    queryset: ResourceQuerySet
) -> None:
    for instance in queryset:
        model_class = instance.content_type.model_class()
        if not post_save.disconnect(default_receiver, sender=model_class):
            modeladmin.message_user(
                request,
                _('Unable to disconnect: %s' % model_class),
                level=constants.ERROR
            )


disconnect.short_description = "Disconnect signals"


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
    actions = (activate,)

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
            'fields': ('start', 'end', 'subscription', 'description',)
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
            'fields': ('start', 'end', 'recurrence', 'subscription_line', 'description',)
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
    actions = (connect, disconnect,)
