from typing import Generator

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils import timezone


class AbstractEventMixin(models.Model):
    start = models.DateTimeField(verbose_name=_('Start date'))
    end = models.DateTimeField(
        verbose_name=_('End date'),
        null=True,
        blank=True
    )

    def clean(self, *args, **kwargs):
        """
        Checks that the start date is not later than the end date (as
        long as it exists).

        :param args:
        :param kwargs:
        :return:
        """
        if self.end and self.start > self.end:
            raise ValidationError(
                _('The start of the event cannot be after the end.')
            )

    def __contains__(self, date: timezone.datetime):
        if not isinstance(date, timezone.datetime):
            raise TypeError(
                f'argument "{date}" must be an instance of datetime'
            )
        return \
            self.start <= date if not self.end \
                else self.start <= date < self.end

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

    @staticmethod
    def tz_now():
        """
        Return an aware or naive datetime.datetime, depending on
        settings.USE_TZ.
        """
        return timezone.now()

    class Meta:
        abstract = True


class PeriodicEventMixin(AbstractEventMixin):
    subscription_line = None
    recurrence = models.DurationField(
        null=True,
        blank=True
    )

    def clean(self):
        """

        :return:
        """
        super().clean()

        if not self.end and self.recurrence:
            raise ValidationError(
                _('The end date is mandatory if self.recurrence is not null')
            )
        if self.recurrence and \
                self.end and \
                self.start + self.recurrence < self.end:
            raise ValidationError(
                _('The start date of the new interval cannot be contained '
                  'in the current interval')
            )

    @property
    def events(self) -> Generator['PeriodicEventMixin', None, None]:
        """
        Yields active subscription events.

        :return:
        """
        while not self.end or self.tz_now() < self.end:
            if self.subscription_line.end and \
                    self.start >= self.subscription_line.end:
                break

            end = self.end \
                if self.end and self.subscription_line.end and \
                   self.end < self.subscription_line.end \
                else self.subscription_line.end

            params = {
                'start': self.start,
                'subscription_line': self.subscription_line,
                'end': end
            }

            event = type(self)(**params)

            try:
                event.clean()
            except ValidationError:
                break
            else:
                yield event
                if not (self.end and self.recurrence):
                    break

            self.__iadd__(self.recurrence)

    class Meta:
        abstract = True
