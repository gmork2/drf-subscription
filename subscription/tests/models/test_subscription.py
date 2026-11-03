from unittest import mock
from datetime import timezone as dt_timezone

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from subscription.models import (
    SubscriptionEvent, MonthlySubscriptionEvent, DailySubscriptionEvent
)


class SubscriptionEventTestCase(TestCase):
    fixtures = ['auth.json', 'contenttypes.json', 'subscription.json']

    def setUp(self):
        super().setUp()
        self.event = SubscriptionEvent.objects.get(id=1)
        self.now = timezone.now()

    def test_recurring_event_with_no_end_date(self):
        self.event.end = None
        self.event.frequency = 'DAILY'
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_intervals_not_overlapping(self):
        self.event.frequency = 'DAILY'
        self.event.count = 10
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(minutes=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_match_end_with_next_start(self):
        self.event.frequency = 'DAILY'
        self.event.count = 10
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(days=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_match_start_and_end(self):
        self.event.frequency = 'DAILY'
        self.event.count = 10
        self.event.start = self.now
        self.event.end = self.now
        self.assertIsNone(self.event.clean())

        self.event.end = self.now + timezone.timedelta(days=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_without_recurrence(self):
        self.event.frequency = None
        self.event.start = self.now
        self.event.end = self.now
        self.assertIsNone(self.event.clean())

    def test_event_intervals_without_end_date(self):
        self.event.frequency = 'DAILY'
        self.event.start = self.now
        self.event.end = None
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_interval_with_no_recurrence_or_end_date(self):
        self.event.frequency = None
        self.event.start = self.now
        self.event.end = None
        self.assertIsNone(self.event.clean())

    def test_event_intervals_overlapping(self):
        self.event.frequency = 'MINUTELY'
        self.event.count = 10
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(days=1)
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_until_before_start(self):
        self.event.frequency = 'DAILY'
        self.event.end = self.now + timezone.timedelta(days=1)
        self.event.until = self.event.start - timezone.timedelta(days=1)
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_invalid_month_day(self):
        self.event.frequency = 'MONTHLY'
        self.event.count = 3
        self.event.end = self.now + timezone.timedelta(hours=1)
        self.event.by_month_day = [0]
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_invalid_week_day(self):
        self.event.frequency = 'WEEKLY'
        self.event.count = 3
        self.event.end = self.now + timezone.timedelta(hours=1)
        self.event.by_week_day = ['XX']
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_start_is_later_than_line_start(self):
        self.event.start = self.now + timezone.timedelta(minutes=1)
        self.event.subscription_line.start = self.now
        self.assertIsNone(self.event.clean())

    def test_event_start_is_equal_than_line_start(self):
        self.event.start = self.now
        self.event.subscription_line.start = self.now
        self.assertIsNone(self.event.clean())

    def test_event_start_is_earlier_than_line_start(self):
        self.event.start = self.now
        self.event.subscription_line.start = self.now + timezone.timedelta(minutes=1)
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_end_is_later_than_line_end(self):
        self.event.end = self.now + timezone.timedelta(days=1)
        self.event.subscription_line.end = self.now + timezone.timedelta(minutes=1)
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_end_is_equal_than_line_end(self):
        self.event.recurrence = None
        self.event.end = self.now + timezone.timedelta(days=1)
        self.event.subscription_line.end = self.now + timezone.timedelta(days=1)
        self.assertIsNone(self.event.clean())

    def test_event_end_is_earlier_than_line_end(self):
        self.event.recurrence = None
        self.event.end = self.now + timezone.timedelta(minutes=1)
        self.event.subscription_line.end = self.now + timezone.timedelta(days=1)
        self.assertIsNone(self.event.clean())

    def test_future_one_time_event(self):
        self.event.frequency = None
        self.event.start = self.now + timezone.timedelta(days=1)
        self.event.end = None
        occurrences = list(self.event.occurrences())
        self.assertEqual(1, len(occurrences))

        self.event.end = self.now + timezone.timedelta(days=2)
        occurrences = list(self.event.occurrences())
        self.assertEqual(1, len(occurrences))

    def test_current_one_time_event(self):
        self.event.frequency = None
        self.event.start = self.now - timezone.timedelta(days=1)
        self.event.end = None
        occurrences = list(self.event.occurrences())
        self.assertEqual(1, len(occurrences))

        self.event.end = self.now + timezone.timedelta(days=1)
        occurrences = list(self.event.occurrences())
        self.assertEqual(1, len(occurrences))

    def test_occurrences_include_past_one_time_event(self):
        self.event.frequency = None
        self.event.start = self.now - timezone.timedelta(days=2)
        self.event.end = self.now - timezone.timedelta(days=1)
        occurrences = list(self.event.occurrences())
        self.assertEqual(1, len(occurrences))
        self.assertEqual(
            occurrences[0].start,
            self.event.start.replace(microsecond=0),
        )

    @mock.patch('django.utils.timezone.now')
    def test_recurring_event_since_past(self, mock_now):
        event = SubscriptionEvent.objects.get(id=2)
        mock_now.return_value = event.start - timezone.timedelta(days=1)
        occurrences = list(event.occurrences())
        self.assertEqual(len(occurrences), 10)

    def test_recurring_event_resized_by_line_end(self):
        self.event.frequency = 'DAILY'
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(days=1)
        self.event.subscription_line.end = \
            self.now + timezone.timedelta(days=2, hours=22)

        occurrences = list(self.event.occurrences())

        self.assertEqual(len(occurrences), 3)
        duration = occurrences[-1].end - occurrences[-1].start
        self.assertEqual(divmod(duration.total_seconds(), 60)[0], 1320)

    @mock.patch('django.utils.timezone.now')
    def test_recurring_event_since_start_date(self, mock_now):
        event = SubscriptionEvent.objects.get(id=2)
        mock_now.return_value = event.start
        occurrences = list(event.occurrences())
        self.assertEqual(len(occurrences), 10)

    def test_occurrences_do_not_mutate_event(self):
        event = SubscriptionEvent.objects.get(id=2)

        first = list(event.occurrences())
        second = list(event.occurrences())

        self.assertEqual(len(first), 10)
        self.assertEqual(len(second), 10)
        self.assertEqual(
            [occurrence.start for occurrence in first],
            [occurrence.start for occurrence in second],
        )

    def test_events_alias_is_deprecated(self):
        event = SubscriptionEvent.objects.get(id=2)
        with self.assertWarns(DeprecationWarning):
            occurrences = list(event.events)
        self.assertEqual(len(occurrences), 10)

    def test_count_limits_occurrences(self):
        self.event.frequency = 'DAILY'
        self.event.count = 3
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(hours=1)
        self.event.subscription_line.end = None
        occurrences = list(self.event.occurrences())
        self.assertEqual(3, len(occurrences))

    def test_until_limits_occurrences(self):
        self.event.frequency = 'DAILY'
        self.event.count = None
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(hours=1)
        self.event.until = self.now + timezone.timedelta(days=2)
        self.event.subscription_line.end = None
        occurrences = list(self.event.occurrences())
        self.assertEqual(3, len(occurrences))

    def test_current_returns_active_occurrence(self):
        self.event.frequency = 'DAILY'
        self.event.start = self.now - timezone.timedelta(days=1)
        self.event.end = self.now + timezone.timedelta(days=1)
        self.event.subscription_line.end = None

        current = self.event.current

        self.assertIsNotNone(current)
        self.assertTrue(self.now in current)

    def test_current_returns_none_before_start(self):
        self.event.frequency = 'DAILY'
        self.event.start = self.now + timezone.timedelta(days=1)
        self.event.end = self.now + timezone.timedelta(days=2)
        self.event.subscription_line.end = None

        self.assertIsNone(self.event.current)

    def test_current_returns_none_after_end(self):
        self.event.frequency = None
        self.event.start = self.now - timezone.timedelta(days=2)
        self.event.end = self.now - timezone.timedelta(days=1)

        self.assertIsNone(self.event.current)

    def test_current_one_time_open_event(self):
        self.event.frequency = None
        self.event.start = self.now - timezone.timedelta(days=1)
        self.event.end = None

        current = self.event.current

        self.assertIsNotNone(current)
        self.assertIsNone(current.end)

    def test_monthly_event_day_31_skips_short_months(self):
        self.event.frequency = 'MONTHLY'
        self.event.start = timezone.datetime(2020, 1, 31, 12, tzinfo=dt_timezone.utc)
        self.event.end = self.event.start + timezone.timedelta(hours=1)
        self.event.subscription_line.end = None
        self.event.count = 4

        occurrences = list(self.event.occurrences())

        # RFC 5545: months without day 31 are skipped, not clamped.
        self.assertEqual(
            [occurrence.start for occurrence in occurrences],
            [
                timezone.datetime(2020, 1, 31, 12, tzinfo=dt_timezone.utc),
                timezone.datetime(2020, 3, 31, 12, tzinfo=dt_timezone.utc),
                timezone.datetime(2020, 5, 31, 12, tzinfo=dt_timezone.utc),
                timezone.datetime(2020, 7, 31, 12, tzinfo=dt_timezone.utc),
            ],
        )

    def test_monthly_event_last_day_uses_negative_month_day(self):
        self.event.frequency = 'MONTHLY'
        self.event.by_month_day = [-1]
        self.event.start = timezone.datetime(2020, 1, 31, 12, tzinfo=dt_timezone.utc)
        self.event.end = self.event.start + timezone.timedelta(hours=1)
        self.event.subscription_line.end = None
        self.event.count = 4

        occurrences = list(self.event.occurrences())

        # Negative month days count from the end of the month.
        self.assertEqual(
            [occurrence.start for occurrence in occurrences],
            [
                timezone.datetime(2020, 1, 31, 12, tzinfo=dt_timezone.utc),
                timezone.datetime(2020, 2, 29, 12, tzinfo=dt_timezone.utc),
                timezone.datetime(2020, 3, 31, 12, tzinfo=dt_timezone.utc),
                timezone.datetime(2020, 4, 30, 12, tzinfo=dt_timezone.utc),
            ],
        )

    def test_weekly_event_by_week_day(self):
        self.event.frequency = 'WEEKLY'
        self.event.by_week_day = ['MO']
        self.event.start = timezone.datetime(2020, 1, 1, 12, tzinfo=dt_timezone.utc)
        self.event.end = self.event.start + timezone.timedelta(hours=1)
        self.event.subscription_line.end = None
        self.event.count = 3

        occurrences = list(self.event.occurrences())

        self.assertEqual(
            [occurrence.start for occurrence in occurrences],
            [
                timezone.datetime(2020, 1, 6, 12, tzinfo=dt_timezone.utc),
                timezone.datetime(2020, 1, 13, 12, tzinfo=dt_timezone.utc),
                timezone.datetime(2020, 1, 20, 12, tzinfo=dt_timezone.utc),
            ],
        )

    def test_daily_event_keeps_local_time_across_dst(self):
        from zoneinfo import ZoneInfo

        madrid = ZoneInfo('Europe/Madrid')
        start = timezone.datetime(2024, 3, 30, 12, tzinfo=madrid)
        self.event.frequency = 'DAILY'
        self.event.start = start
        self.event.end = start + timezone.timedelta(hours=1)
        self.event.subscription_line.end = None
        self.event.count = 3

        occurrences = list(self.event.occurrences())

        self.assertEqual(
            [occurrence.start.hour for occurrence in occurrences],
            [12, 12, 12],
        )
        self.assertEqual(
            occurrences[1].start,
            timezone.datetime(2024, 3, 31, 12, tzinfo=madrid),
        )


class SubscriptionEventProxyTestCase(TestCase):
    def test_daily_proxy_defaults(self):
        event = DailySubscriptionEvent(
            start=timezone.now(),
            end=timezone.now() + timezone.timedelta(hours=1),
            subscription_line_id=1,
            count=10,
        )
        self.assertEqual(event.frequency, 'DAILY')
        self.assertEqual(event.interval, 1)

    def test_monthly_proxy_defaults(self):
        event = MonthlySubscriptionEvent(
            start=timezone.now(),
            end=timezone.now() + timezone.timedelta(hours=1),
            subscription_line_id=1,
            count=10,
        )
        self.assertEqual(event.frequency, 'MONTHLY')
        self.assertEqual(event.interval, 1)
