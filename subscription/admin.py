from django.contrib import admin
from django.utils.translation import gettext as _
from django.core.handlers.wsgi import WSGIRequest
from django.contrib.messages import constants
from django.db.models import QuerySet

from .managers import SubscriptionQuerySet, ResourceQuerySet
from .models import Subscription, SubscriptionLine, SubscriptionEvent, Resource
from .signals import callback_receiver


def activate(
        modeladmin: admin.ModelAdmin,
        request: WSGIRequest,
        queryset: QuerySet
):
    queryset.update(active=True)
    model = queryset.model
    model.objects.connect(model.signal, model.receiver, model)
    modeladmin.message_user(request, _('Total activated: %s' % queryset.count()))


activate.short_description = _("Activate a subscription or resource")


def deactivate(
        modeladmin: admin.ModelAdmin,
        request: WSGIRequest,
        queryset: QuerySet
):
    queryset.update(active=False)
    model = queryset.model
    model.objects.disconnect(model.signal, model.receiver, model)
    modeladmin.message_user(request, _('Total deactivated: %s' % queryset.count()))


deactivate.short_description = _("Deactivate a subscription or resource")


def run_callback(
        modeladmin: 'SubscriptionAdmin',
        request: WSGIRequest,
        queryset: SubscriptionQuerySet
):
    for instance in queryset:
        callback_receiver(
            sender=modeladmin.__class__,
            instance=instance,
            queryset=queryset
        )
        modeladmin.message_user(request, _('Done!'))


run_callback.short_description = _("Run callback")


def connect(
        modeladmin: 'SubscriptionAdmin',
        request: WSGIRequest,
        queryset: ResourceQuerySet
) -> None:

    for instance in queryset:

        receiver = instance.__class__.receiver
        signal = instance.__class__.signal
        model_class = instance.content_type.model_class()
        signal.connect(receiver, sender=model_class)

    modeladmin.message_user(request, _('Done!'))


connect.short_description = _("Connect signals")


def disconnect(
        modeladmin: 'SubscriptionAdmin',
        request: WSGIRequest,
        queryset: ResourceQuerySet
) -> None:

    for instance in queryset:

        receiver = instance.__class__.receiver
        signal = instance.__class__.signal
        model_class = instance.content_type.model_class()

        if not signal.disconnect(receiver, sender=model_class):
            modeladmin.message_user(
                request,
                _('Unable to disconnect: %s' % model_class),
                level=constants.ERROR
            )
        else:
            modeladmin.message_user(request, _('Done!'))


disconnect.short_description = _("Disconnect signals")


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
            'fields': ('content_type', 'object_pk',),  # 'content_object',
        }),
    )
    actions = (activate, deactivate)

    @staticmethod
    def content_object(obj):
        return obj.content_object


@admin.register(SubscriptionLine)
class SubscriptionLineAdmin(admin.ModelAdmin):
    date_hierarchy = 'start'
    list_display = ('id', 'start', 'end', 'subscription')
    list_filter = ('start', 'end')
    fieldsets = (
        (None, {
            'fields': ('start', 'end', 'subscription')
        }),
    )


@admin.register(SubscriptionEvent)
class SubscriptionEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'start'
    list_display = ('id', 'start', 'end', 'recurrence', 'subscription_line')
    list_filter = ('start', 'end',)
    fieldsets = (
        (None, {
            'fields': ('start', 'end', 'recurrence', 'subscription_line')
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
    actions = (activate, deactivate, run_callback, connect, disconnect,)
