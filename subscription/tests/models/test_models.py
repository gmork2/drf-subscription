from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from subscription.models import SubscriptionEvent


class SubscriptionEventTestCase(TestCase):
    fixtures = ['0001_tests.json']

    def setUp(self):
        super().setUp()
        self.event = SubscriptionEvent.objects.first()

    def test_event_intervals_not_overlapping(self):
        now = timezone.now()
        self.event.recurrence = timezone.timedelta(days=1)
        self.event.start = now
        self.event.end = now + timezone.timedelta(minutes=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_match_end_with_next_start(self):
        now = timezone.now()
        self.event.recurrence = timezone.timedelta(days=1)
        self.event.start = now
        self.event.end = now + timezone.timedelta(days=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_match_start_and_end(self):
        now = timezone.now()
        self.event.recurrence = timezone.timedelta(days=0)
        self.event.start = now
        self.event.end = now
        self.assertIsNone(self.event.clean())

        self.event.recurrence = timezone.timedelta(days=1)
        self.assertIsNone(self.event.clean())

    def test_event_intervals_without_recurrence(self):
        now = timezone.now()
        self.event.recurrence = None
        self.event.start = now
        self.event.end = now
        self.assertIsNone(self.event.clean())

    def test_event_intervals_without_end_date(self):
        now = timezone.now()
        self.event.recurrence = timezone.timedelta(days=1)
        self.event.start = now
        self.event.end = None
        self.assertIsNone(self.event.clean())

    def test_event_interval_with_no_recurrence_or_end_date(self):
        now = timezone.now()
        self.event.recurrence = None
        self.event.start = now
        self.event.end = None
        self.assertIsNone(self.event.clean())

    def test_event_intervals_overlapping(self):
        now = timezone.now()
        self.event.recurrence = timezone.timedelta(minutes=1)
        self.event.start = now
        self.event.end = now + timezone.timedelta(days=1)
        self.assertRaises(ValidationError, self.event.clean)
