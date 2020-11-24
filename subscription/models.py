from typing import Generator
import ast

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils import timezone

from rest_framework import serializers

from .managers import ResourceManager, SubscriptionManager, SubscriptionLineManager, SubscriptionEventManager


class AbstractEventMixin(models.Model):
    start = models.DateTimeField(verbose_name=_('Start date'))
    end = models.DateTimeField(verbose_name=_('End date'))
    description = models.TextField(
        max_length=2048,
        verbose_name=_('Description'),
        blank=True,
    )

    def clean(self, *args, **kwargs):
        """
        Checks that the start date is not later than the end date.

        :param args:
        :param kwargs:
        :return:
        """
        if self.start > self.end:
            raise ValidationError(
                _('The start of the event cannot be after the end.')
            )

    class Meta:
        abstract = True


class BaseGenericObjectResource(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_pk = models.CharField(
        _('object ID'),
        max_length=255
    )
    content_object = GenericForeignKey(fk_field='object_pk')

    class Meta:
        abstract = True
        indexes = [
            models.Index(
                fields=['content_type', 'object_pk']
            ),
        ]

    def __str__(self):
        return '%s' % self.content_object


class Subscription(BaseGenericObjectResource):
    name = models.CharField(
        max_length=128,
        help_text=_('Subscription name')
    )
    active = models.BooleanField(default=True)
    objects = SubscriptionManager()

    def active_lines(self):
        pass

    def __str__(self):
        related_object = super().__str__()
        return '%s (%s): %s -> %s' % (
            self.__class__.__name__,
            self.pk,
            self.name,
            related_object
        )


class SubscriptionLine(AbstractEventMixin):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE
    )
    objects = SubscriptionLineManager()

    def __str__(self):
        return '%s (%s): %s [%s - %s]' % (
            self.__class__.__name__,
            self.pk,
            self.subscription.name,
            self.start,
            self.end
        )


class SubscriptionEvent(AbstractEventMixin):
    recurrence = models.DurationField(
        null=True,
        blank=True
    )
    subscription_line = models.ForeignKey(
        SubscriptionLine,
        on_delete=models.CASCADE
    )
    objects = SubscriptionEventManager()

    def clean(self):
        """

        :return:
        """
        if not self.end and self.recurrence:
            raise ValidationError(
                _('The end date is mandatory if there is recurrence')
            )
        if self.recurrence and (self.start + self.recurrence < self.end):
            raise ValidationError(
                _('The start date of the new interval cannot be contained '
                  'in the current interval')
            )
        super().clean()

    @property
    def events(self) -> Generator['SubscriptionEvent', None, None]:
        """
        Yields future subscription events whose start date is later
        than the current one.

        :return:
        """
        while self.start > timezone.now():
            params = {
                'start': self.start,
                'end': self.end,
                'subscription_line': self.subscription_line
            }
            yield SubscriptionEvent(**params)
            if not (self.end and self.recurrence):
                break
            self.__iadd__(self.recurrence)

    def __iadd__(self, duration: timezone.timedelta):
        """
        Adds a duration value to the start and end date.

        :param duration:
        :return:
        """
        if self.end:
            self.end = self.end + duration
        self.start = self.start + duration

        return self

    def __str__(self):
        return '%s (%s): %s [%s - %s]' % (
            self.__class__.__name__,
            self.pk,
            self.subscription_line.subscription.name,
            self.start,
            self.end
        )


class Resource(BaseGenericObjectResource):
    subscription_event = models.ForeignKey(
        SubscriptionEvent,
        help_text=_('the subscription plan for these cost details'),
        on_delete=models.CASCADE
    )
    content_object_fields = models.TextField(
        blank=True,
        help_text=_(
            'Warning: this field may contain sensitive information'
            'from other models'
        ),
    )
    callback = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text=_('Dotted path to callable object')
    )
    objects = ResourceManager()

    def get_values_from_related_object(self, model_class: models.Model) -> dict:
        """
        Returns a dict with the values of the fields of the related
        model.

        :param model_class:
        :return:
        """
        from .serializers import GenericSerializer

        return GenericSerializer.from_model(
            model_class,
            [*ast.literal_eval(self.content_object_fields)]
            if self.content_object_fields else serializers.ALL_FIELDS,
            self.content_object
        ).data

    def __str__(self):
        related_object = super().__str__()
        return '%s (%s): %s -> %s' % (
            self.__class__.__name__,
            self.pk,
            self.subscription_event.subscription_line.subscription.name,
            related_object
        )
