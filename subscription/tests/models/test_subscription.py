from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from subscription.models import SubscriptionEvent


class SubscriptionEventTestCase(TestCase):
    fixtures = ['0001_tests.json']

    def setUp(self):
        super().setUp()
        self.event = SubscriptionEvent.objects.get(id=1)
        self.now = timezone.now()

    def test_recurring_event_with_no_end_date(self):
        self.event.end = None
        self.event.recurrence = timezone.timedelta(days=1)
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_intervals_not_overlapping(self):
        self.event.recurrence = timezone.timedelta(days=1)
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(minutes=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_match_end_with_next_start(self):
        self.event.recurrence = timezone.timedelta(days=1)
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(days=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_match_start_and_end(self):
        self.event.recurrence = timezone.timedelta(days=0)
        self.event.start = self.now
        self.event.end = self.now
        self.assertIsNone(self.event.clean())

        self.event.recurrence = timezone.timedelta(days=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_without_recurrence(self):
        self.event.recurrence = None
        self.event.start = self.now
        self.event.end = self.now
        self.assertIsNone(self.event.clean())

    def test_event_intervals_without_end_date(self):
        self.event.recurrence = timezone.timedelta(days=1)
        self.event.start = self.now
        self.event.end = None
        self.assertRaises(ValidationError, self.event.clean)

    def test_event_interval_with_no_recurrence_or_end_date(self):
        self.event.recurrence = None
        self.event.start = self.now
        self.event.end = None
        self.assertIsNone(self.event.clean())

    def test_event_intervals_overlapping(self):
        self.event.recurrence = timezone.timedelta(minutes=1)
        self.event.start = self.now
        self.event.end = self.now + timezone.timedelta(days=1)
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
        self.event.recurrence = None
        self.event.start = self.now + timezone.timedelta(days=1)
        self.event.end = None
        events = list(self.event.events)
        self.assertEqual(1, len(events))

        self.event.end = self.now + timezone.timedelta(days=2)
        events = list(self.event.events)
        self.assertEqual(1, len(events))

    def test_current_one_time_event(self):
        self.event.recurrence = None
        self.event.start = self.now - timezone.timedelta(days=1)
        self.event.end = None
        events = list(self.event.events)
        self.assertEqual(1, len(events))

        self.event.end = self.now + timezone.timedelta(days=1)
        events = list(self.event.events)
        self.assertEqual(1, len(events))

    def test_ended_one_time_event(self):
        self.event.recurrence = None
        self.event.start = self.now - timezone.timedelta(days=2)
        self.event.end = self.now - timezone.timedelta(days=1)
        events = list(self.event.events)
        self.assertEqual(0, len(events))

    def test_recurring_event_from_past(self):
        event = SubscriptionEvent.objects.get(id=2)
        event.tz_now = lambda: event.start - timezone.timedelta(days=1)
        events = list(event.events)
        self.assertEqual(len(events), 10)

        event = SubscriptionEvent.objects.get(id=3)
        event.tz_now = lambda: event.start - timezone.timedelta(days=1)
        events = list(event.events)
        self.assertEqual(len(events), 3)

        duration = events[-1].end - events[-1].start
        self.assertEqual(divmod(duration.total_seconds(), 60)[0], 1320)
