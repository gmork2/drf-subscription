from typing import Optional

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.conf import settings

from .base import BaseGenericObjectResource
from .mixins import MonthlyEventMixin, DailyEventMixin
from .abstract import AbstractInterval, AbstractPeriodicEvent
from ..managers import SubscriptionManager, SubscriptionLineManager, SubscriptionEventManager


class Subscription(BaseGenericObjectResource):
    name = models.CharField(
        max_length=128,
        help_text=_('Subscription name')
    )
    active = models.BooleanField(default=True)
    objects = SubscriptionManager()

    def __str__(self):
        related_object = super().__str__()
        return '%s (%s): %s -> %s' % (
            self.__class__.__name__,
            self.pk,
            self.name,
            related_object
        )

    class Meta:
        abstract = 'subscription' not in settings.INSTALLED_APPS


class SubscriptionLine(AbstractInterval):
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

    class Meta:
        abstract = 'subscription' not in settings.INSTALLED_APPS


class SubscriptionEvent(AbstractPeriodicEvent):
    subscription_line = models.ForeignKey(
        SubscriptionLine,
        on_delete=models.CASCADE
    )
    objects = SubscriptionEventManager()

    def clean(self):
        """
        Checks that the intervals do not overlap.

        :return:
        """
        if self.subscription_line.start > self.start:
            raise ValidationError(
                _('The start date must be after or equal to the start date '
                  'of the subscription line')
            )
        if self.end and \
                self.subscription_line.end and \
                self.end > self.subscription_line.end:
            raise ValidationError(
                _('The end date must be earlier or equal than the end date '
                  'of the subscription line')
            )
        if self.subscription_line.end and \
                self.start >= self.subscription_line.end:
            raise ValidationError(
                _('The start date must be earlier or equal than the end date '
                  'of the subscription line')
            )
        super().clean()

    @property
    def current_event(self) -> Optional['SubscriptionEvent']:
        now = self.now()

        for event in self.events:
            if now in event:
                return event
            elif self.end and now > self.subscription_line.end:
                break

    def __str__(self):
        return '%s (%s): %s [%s - %s]' % (
            self.__class__.__name__,
            self.pk,
            self.subscription_line.subscription.name,
            self.start,
            self.end
        )

    def __len__(self):
        if self.end:
            return self.end - self.start
        return float('inf')

    class Meta:
        abstract = 'subscription' not in settings.INSTALLED_APPS
        unique_together = ('start', 'end', 'subscription_line')
        get_latest_by = ('start',)


class MonthlySubscriptionEvent(MonthlyEventMixin, SubscriptionEvent):
    class Meta:
        proxy = True


class DailySubscriptionEvent(DailyEventMixin, SubscriptionEvent):
    class Meta:
        proxy = True
