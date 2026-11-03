from typing import Callable, ClassVar

import json

from django.db import models
from django.db.models.signals import post_save, ModelSignal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.conf import settings

from rest_framework import serializers

from .abstract import AbstractGenericObjectResource
from .subscription import SubscriptionEvent
from .decorators import connect_signal
from ..managers import ResourceManager
from ..signals import default_receiver
from ..validators import ImportCallBackValidator


class Resource(AbstractGenericObjectResource):
    INCLUDE_HIDDEN: ClassVar[bool] = True
    signal: ClassVar[ModelSignal] = post_save
    receiver: ClassVar[Callable] = default_receiver

    subscription_event = models.ForeignKey(
        SubscriptionEvent,
        on_delete=models.CASCADE,
    )
    content_object_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            'key-value pair with the values of the current instance of '
            'the related model'
        ),
    )
    callback = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text=_('Dotted path to callable object'),
        validators=[ImportCallBackValidator()]
    )
    webhook_url = models.URLField(
        null=True,
        blank=True,
        help_text=_(
            'Optional external URL (http/https) that receives a signed '
            'POST with the resource payload when the resource is executed.'
        ),
    )
    webhook_secret = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text=_(
            'Shared secret used to sign webhook requests (HMAC-SHA256 of '
            'the body, sent in the X-Subscription-Signature header).'
        ),
    )
    webhook_headers = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Extra HTTP headers sent with the webhook request.'),
    )
    active = models.BooleanField(default=True)
    objects = ResourceManager()

    def get_values_from_related_object(self, model_class: models.Model) -> dict:
        """
        Returns a dict with the values of the fields of the related
        model.

        :param model_class:
        :return:
        """
        from subscription.serializers import GenericSerializer

        fields = self.content_object_fields
        if isinstance(fields, dict):
            field_names = list(fields.keys())
        elif fields:
            try:
                field_names = [*json.loads(fields)]
            except (ValueError, TypeError):
                field_names = serializers.ALL_FIELDS
        else:
            field_names = serializers.ALL_FIELDS

        return GenericSerializer.from_model(
            model_class,
            field_names,
            self.content_object
        ).data

    @property
    def is_ready(self) -> bool:
        """
        Returns True if this resource meets the conditions to execute
        the callback.

        :return:
        """
        return \
            self.subscription_event.current is not None and \
            self.subscription_event.subscription_line.subscription.active and \
            self.active

    @property
    def payload(self) -> dict:
        """
        The snapshot of the related object as a dict, used as the
        webhook body.

        :return:
        """
        fields = self.content_object_fields
        if not fields:
            return {}
        if isinstance(fields, dict):
            return fields
        try:
            data = json.loads(fields)
        except (ValueError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}

    def clean(self):
        """

        :return:
        """
        if self.content_object is None:
            missing = f'{self.content_type} id={self.object_pk}'
            raise ValidationError(
                _(f'Referenced object <{missing}> does not exist')
            )

        if self.webhook_url:
            allowed_hosts = getattr(
                settings, 'SUBSCRIPTION_WEBHOOK_ALLOWED_HOSTS', None
            )
            if allowed_hosts:
                from urllib.parse import urlparse

                hostname = urlparse(self.webhook_url).hostname
                if hostname not in allowed_hosts:
                    raise ValidationError(
                        _(f'Webhook host "{hostname}" is not allowed')
                    )

        if self.content_object_fields:
            try:
                if isinstance(self.content_object_fields, dict):
                    fields = self.content_object_fields
                else:
                    fields = json.loads(self.content_object_fields)
                if not isinstance(fields, dict):
                    raise ValidationError(
                        _(f'malformed node or string: "{self.content_object_fields}"')
                    )
                cls = self.content_type.model_class()
                model_fields = [
                    f.name
                    for f in cls._meta.get_fields(
                        include_hidden=self.INCLUDE_HIDDEN
                    )
                ]
                unknown = set(fields.keys()) - set(model_fields)
                if unknown:
                    raise ValidationError(
                        _(f'Unknown related fields: {unknown}')
                    )
            except ValueError as e:
                raise ValidationError(e)

    @connect_signal(signal=post_save, receiver=default_receiver)
    def save(self, *args, **kwargs):
        """
        Fills content_object_fields with a dictionary that contains the
        field-value pair of the related model.

        :param args:
        :param kwargs:
        :return:
        """
        model_class = self.content_type.model_class()
        self.content_object_fields = self.get_values_from_related_object(
            model_class
        )

        return super().save(*args, **kwargs)

    def __str__(self):
        related_object = super().__str__()
        return '%s (%s): %s -> %s' % (
            self.__class__.__name__,
            self.pk,
            self.subscription_event.subscription_line.subscription.name,
            related_object
        )

    class Meta:
        abstract = 'subscription' not in settings.INSTALLED_APPS


class ResourceExecution(models.Model):
    """
    Audit record for every callback/webhook execution attempt of a
    resource. Failed attempts are kept so retries can be tracked.
    """
    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_RUNNING, _('Running')),
        (STATUS_SUCCEEDED, _('Succeeded')),
        (STATUS_FAILED, _('Failed')),
    ]

    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='executions',
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    scheduled_for = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            'Start of the event occurrence this execution was scheduled '
            'for. Used for idempotency.'
        ),
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=1)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = 'subscription' not in settings.INSTALLED_APPS
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['resource', 'status']),
            models.Index(fields=['resource', 'scheduled_for', 'status']),
        ]

    def __str__(self):
        return '%s (%s): %s [%s]' % (
            self.__class__.__name__,
            self.pk,
            self.resource,
            self.status,
        )
