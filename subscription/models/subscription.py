from typing import Generator, Optional

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings

from .base import BaseGenericObjectResource
from .mixins import AbstractEventMixin
from ..managers import SubscriptionManager, SubscriptionLineManager, SubscriptionEventManager


class Subscription(BaseGenericObjectResource):
    name = models.CharField(
        max_length=128,
        help_text=_('Subscription name')
    )
    active = models.BooleanField(default=True)
    objects = SubscriptionManager()

    def active_lines(self):
        pass

    def activate(self):
        pass

    def deactivate(self):
        pass

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

    class Meta:
        abstract = 'subscription' not in settings.INSTALLED_APPS


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
        Checks that the intervals do not overlap.

        :return:
        """
        if self.recurrence and \
                self.end and \
                self.start + self.recurrence < self.end:
            raise ValidationError(
                _('The start date of the new interval cannot be contained '
                  'in the current interval')
            )
        if self.subscription_line.start > self.start:
            raise ValidationError(
                _('The start date must be after or equal to the start date '
                  'of the subscription line')
            )

        super().clean()

    @property
    def events(self) -> Generator['SubscriptionEvent', None, None]:
        """
        Yields active subscription events.

        :return:
        """
        while (
                timezone.now() <= self.start or
                (self.end and self.start <= timezone.now() < self.end)
        ) and (
                self.start < self.subscription_line.end
        ):
            params = {
                'start': self.start,
                'subscription_line': self.subscription_line,
                'end': self.end
            }
            if self.end:
                params['end'] = self.end \
                    if self.end < self.subscription_line.end \
                    else self.subscription_line.end

            yield SubscriptionEvent(**params)
            if not (self.end and self.recurrence):
                break
            self.__iadd__(self.recurrence)

    @property
    def current_event(self) -> Optional['SubscriptionEvent']:
        now = timezone.now()

        for event in self.events:
            if now in event:
                return event
            elif self.end and now > self.subscription_line.end:
                break

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

    class Meta:
        abstract = 'subscription' not in settings.INSTALLED_APPS
