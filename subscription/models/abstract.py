import warnings
from datetime import datetime, timedelta
from typing import Generator, Optional

from dateutil import rrule

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class AbstractGenericObjectResource(models.Model):
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

    def get_resource_url(self, request=None):
        """
        Return the URL of the related object, derived from its
        ``get_absolute_url`` when available. With a request, the URL is
        made absolute using the request host.

        :param request: optional request used to build an absolute URL.
        :return: the URL path, or None when the object does not define
            ``get_absolute_url``.
        """
        obj = self.content_object
        if obj is None:
            return None

        url_method = getattr(obj, 'get_absolute_url', None)
        if not callable(url_method):
            return None

        path = url_method()
        if not path:
            return None

        if request is not None:
            return request.build_absolute_uri(path)
        return path


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

    @staticmethod
    def now():
        """
        Return an aware or naive datetime.datetime, depending on
        settings.USE_TZ.
        """
        return timezone.now()

    def __contains__(self, date: datetime):
        if not isinstance(date, datetime):
            raise TypeError(
                f'argument "{date}" must be an instance of datetime'
            )
        return \
            self.start <= date if not self.end \
            else self.start <= date < self.end

    def __iadd__(self, duration: timedelta):
        """
        Adds a duration value to the start and end date.

        :param duration:
        :return:
        """
        if self.end:
            self.end = self.end + duration
        self.start = self.start + duration

        return self

    class Meta:
        abstract = True


RRULE_FREQUENCIES = [
    ('SECONDLY', _('Secondly')),
    ('MINUTELY', _('Minutely')),
    ('HOURLY', _('Hourly')),
    ('DAILY', _('Daily')),
    ('WEEKLY', _('Weekly')),
    ('MONTHLY', _('Monthly')),
    ('YEARLY', _('Yearly')),
]

RRULE_FREQUENCY_VALUES = {
    'SECONDLY': rrule.SECONDLY,
    'MINUTELY': rrule.MINUTELY,
    'HOURLY': rrule.HOURLY,
    'DAILY': rrule.DAILY,
    'WEEKLY': rrule.WEEKLY,
    'MONTHLY': rrule.MONTHLY,
    'YEARLY': rrule.YEARLY,
}

RRULE_WEEK_DAYS = {
    'MO': rrule.MO, 'TU': rrule.TU, 'WE': rrule.WE, 'TH': rrule.TH,
    'FR': rrule.FR, 'SA': rrule.SA, 'SU': rrule.SU,
}


class AbstractPeriodicEvent(AbstractInterval):
    """
    An interval within a subscription line that may repeat over time.

    Recurrence is expressed as a subset of the RFC 5545 RRULE
    vocabulary and is powered by ``dateutil.rrule``. When ``frequency``
    is empty, the event happens exactly once.

    Every occurrence spans ``end - start``; occurrences never extend
    past the end of the subscription line.
    """
    subscription_line = None

    frequency = models.CharField(
        _('frequency'),
        max_length=16,
        choices=RRULE_FREQUENCIES,
        null=True,
        blank=True,
        help_text=_(
            'Recurrence rule frequency (RFC 5545). Leave empty for a '
            'one-time event.'
        ),
    )
    interval = models.PositiveIntegerField(
        _('interval'),
        default=1,
        help_text=_('The interval between each frequency iteration.'),
    )
    count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_(
            'How many occurrences are generated. Leave empty for '
            'unlimited (bounded by the end date or the subscription line).'
        ),
    )
    until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            'The latest date an occurrence can start on (inclusive).'
        ),
    )
    by_month_day = models.JSONField(
        _('month days'),
        default=list,
        blank=True,
        help_text=_(
            'List of month days (1-31, negative values count from the '
            'end of the month).'
        ),
    )
    by_week_day = models.JSONField(
        _('week days'),
        default=list,
        blank=True,
        help_text=_(
            'List of week days as two-letter codes (MO, TU, WE, TH, FR, '
            'SA, SU) or integers (0-6, Monday first).'
        ),
    )

    @property
    def recurring(self) -> bool:
        """True when the event follows a recurrence rule."""
        return bool(self.frequency)

    @property
    def duration(self) -> Optional[timedelta]:
        """Length of every occurrence, or None for an open-ended event."""
        if not self.end:
            return None
        return self.end - self.start

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
        if self.recurring and not self.end:
            raise ValidationError(
                _('The end date is mandatory if the event recurs')
            )
        if self.until and self.until <= self.start:
            raise ValidationError(
                _('The until date must be after the start date')
            )
        for day in self.by_month_day:
            try:
                day = int(day)
            except (TypeError, ValueError):
                raise ValidationError(
                    _('Month days must be integers between -31 and 31, '
                      'excluding 0')
                )
            if day == 0 or abs(day) > 31:
                raise ValidationError(
                    _('Month days must be integers between -31 and 31, '
                      'excluding 0')
                )
        for day in self.by_week_day:
            valid = day in RRULE_WEEK_DAYS or (
                isinstance(day, int) and 0 <= day <= 6
            )
            if not valid:
                raise ValidationError(
                    _('Week days must be MO, TU, WE, TH, FR, SA, SU or '
                      'integers between 0 and 6')
                )
        if self.recurring and self.end:
            next_start = self._next_start()
            if next_start is not None and \
                    self.end.replace(microsecond=0) > \
                    next_start.replace(microsecond=0):
                raise ValidationError(
                    _('The start date of the new interval cannot be '
                      'contained in the current interval')
                )
        if self.recurring and not self.until and not self.count and \
                not (self.subscription_line and
                     self.subscription_line.end):
            raise ValidationError(
                _('Recurring events must define until, count, or belong '
                  'to a subscription line with an end date')
            )

    def _rule_until(self) -> Optional[datetime]:
        """
        The inclusive end datetime explicitly set for the recurrence
        rule, or None when the rule is bounded by the subscription
        line instead.

        :return:
        """
        return self.until

    def build_rrule(self) -> rrule.rrule:
        """
        Return the dateutil recurrence rule for this event.

        One-time events are represented as a rule with a single
        occurrence. Rules without an explicit ``until`` are bounded by
        the end date of the subscription line, when it exists.

        :return:
        """
        kwargs = {'dtstart': self.start}
        if self.recurring:
            kwargs.update({
                'freq': RRULE_FREQUENCY_VALUES[self.frequency],
                'interval': self.interval or 1,
            })
            if self.count:
                kwargs['count'] = self.count
            until = self._rule_until()
            if not until:
                line = self.subscription_line
                line_end = getattr(line, 'end', None) \
                    if line is not None else None
                until = line_end
            if until:
                kwargs['until'] = until
            if self.by_month_day:
                kwargs['bymonthday'] = [
                    int(day) for day in self.by_month_day
                ]
            if self.by_week_day:
                kwargs['byweekday'] = [
                    RRULE_WEEK_DAYS[day] if day in RRULE_WEEK_DAYS
                    else int(day)
                    for day in self.by_week_day
                ]
        else:
            kwargs.update({'freq': rrule.YEARLY, 'count': 1})
        return rrule.rrule(**kwargs)

    def _next_start(self) -> Optional[datetime]:
        """
        The start datetime of the occurrence that follows the first
        one, or None when the rule produces no further occurrences.

        :return:
        """
        try:
            return self.build_rrule().after(self.start, inc=False)
        except ValueError:
            return None

    def _make_occurrence(self, start: datetime, end: Optional[datetime]):
        """
        Build a new unsaved instance of this event's class for the
        given occurrence boundaries, carrying the recurrence
        parameters forward.

        :param start:
        :param end:
        :return:
        """
        kwargs = {
            'start': start,
            'end': end,
            'subscription_line': self.subscription_line,
        }
        if self.recurring:
            kwargs.update({
                'frequency': self.frequency,
                'interval': self.interval,
                'by_month_day': self.by_month_day,
                'by_week_day': self.by_week_day,
            })
        return type(self)(**kwargs)

    def occurrences(self) -> Generator['AbstractPeriodicEvent', None, None]:
        """
        Generate every occurrence of this event within the bounds of
        the subscription line, without mutating the instance.

        A one-time event yields a single occurrence. Open-ended
        one-time events run until the end of the subscription line
        (and stay open when the line is open too).

        :return:
        """
        line = self.subscription_line
        line_end = getattr(line, 'end', None) if line is not None else None
        duration = self.duration

        for start in self.build_rrule():
            end = start + duration if duration is not None else None
            if line_end is not None:
                if start.replace(microsecond=0) >= \
                        line_end.replace(microsecond=0):
                    break
                if end is None or end > line_end:
                    end = line_end
            yield self._make_occurrence(start, end)

    @property
    def current(self) -> Optional['AbstractPeriodicEvent']:
        """
        Return the occurrence active right now, or None when the event
        has not started yet, has already finished, or its rule has no
        occurrence at this point in time.

        :return:
        """
        now = self.now()
        try:
            start = self.build_rrule().before(now, inc=True)
        except ValueError:
            return None
        if start is None:
            return None

        line = self.subscription_line
        if line is not None and line.start is not None and \
                start.replace(microsecond=0) < \
                line.start.replace(microsecond=0):
            return None

        duration = self.duration
        line_end = getattr(line, 'end', None) if line is not None else None
        end = start + duration if duration is not None else None
        if line_end is not None and (end is None or end > line_end):
            end = line_end

        if end is not None and now >= end:
            return None
        return self._make_occurrence(start, end)

    @property
    def events(self) -> Generator['AbstractPeriodicEvent', None, None]:
        """
        Deprecated alias of :meth:`occurrences`.

        :return:
        """
        warnings.warn(
            "'events' is deprecated and will be removed in a future "
            "release; use 'occurrences()' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        yield from self.occurrences()

    def __lt__(self, interval: AbstractInterval):
        return \
            getattr(interval, 'end') and \
            self.end and \
            self.end < interval.end

    class Meta:
        abstract = True
