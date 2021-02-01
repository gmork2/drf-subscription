from typing import Generator

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils import timezone


class AbstractInterval(models.Model):
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
    def now():
        """
        Return an aware or naive datetime.datetime, depending on
        settings.USE_TZ.
        """
        return timezone.now()

    class Meta:
        abstract = True


class AbstractPeriodicEvent(AbstractInterval):
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

        if self.subscription_line is None:
            raise ValidationError(
                _('The subscription line cannot be null')
            )
        if self.subscription_line.end and \
                self.start >= self.subscription_line.end:
            raise ValidationError(
                _('The end date of the subscription line must be after the '
                  'end date of the event')
            )
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

    def __lt__(self, interval: AbstractInterval):
        return \
            getattr(interval, 'end') and \
            self.end and \
            self.end < interval.end

    @property
    def events(self) -> Generator['AbstractPeriodicEvent', None, None]:
        """
        It generates subscription events within the interval of the subscription
        line from the current date. If the end date is null, this is
        considered a one-time event and will end on the end date of the
        subscription line.

        If it has an end date but does not have a recurrence
        value, it will also be considered a one-time event.

        :return:
        """
        while not self.end or self.now() < self.end:
            line = self.subscription_line

            event = type(self)(**{
                'start': self.start,
                'subscription_line': line,
                'end': self.end if self < line else line.end
            })
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
