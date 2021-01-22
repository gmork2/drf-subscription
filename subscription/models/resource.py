from typing import Callable, ClassVar

import ast

from django.db import models
from django.db.models.signals import post_save, ModelSignal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.conf import settings

from rest_framework import serializers

from .base import BaseGenericObjectResource
from .subscription import SubscriptionEvent
from ..managers import ResourceManager
from ..signals import default_receiver
from ..validators import ImportCallBackValidator


class Resource(BaseGenericObjectResource):
    INCLUDE_HIDDEN: ClassVar[bool] = True

    receiver: Callable = default_receiver
    signal: ModelSignal = post_save

    subscription_event = models.ForeignKey(
        SubscriptionEvent,
        on_delete=models.CASCADE,
    )
    content_object_fields = models.TextField(
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

        return GenericSerializer.from_model(
            model_class,
            [*ast.literal_eval(self.content_object_fields)]
            if self.content_object_fields else serializers.ALL_FIELDS,
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
            self.subscription_event.current_event and \
            self.subscription_event.subscription_line.subscription.active and \
            self.active

    def clean(self):
        """

        :return:
        """
        if self.content_object is None:
            missing = f'{self.content_type} id={self.object_pk}'
            raise ValidationError(
                _(f'Referenced object <{missing}> does not exist')
            )

        if self.content_object_fields:
            try:
                fields = ast.literal_eval(self.content_object_fields)
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

    def save(self, *args, **kwargs):
        """
        Fills content_object_fields with a dictionary that contains the
        field-value pair of the related model, in addition to connecting
        the default receiver with that class through the signal, prior
        to saving the instance.

        :param args:
        :param kwargs:
        :return:
        """
        model_class = self.content_type.model_class()
        self.content_object_fields = self.get_values_from_related_object(model_class)
        if self._state.adding:
            self.signal.connect(self.receiver, sender=model_class)
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
