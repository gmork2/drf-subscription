from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from subscription.models import SubscriptionLine
from subscription.models.mixins import AbstractEventMixin


class AbstractEventMixinTestCase(TestCase):
    fixtures = ['0001_tests.json']

    def setUp(self):
        super().setUp()
        self.obj = SubscriptionLine.objects.first()
        if not issubclass(self.obj.__class__, AbstractEventMixin):
            self.skipTest(
                f"The object class [{self.obj.__class__}] must inherit "
                f"from AbstractEventMixin"
            )
        self.now = timezone.now()

    def test_mixin_must_be_abstract(self):
        event = AbstractEventMixin()
        self.assertTrue(event._meta.abstract)

    def test_event_start_is_prev_end(self):
        self.obj.start = self.now
        self.obj.end = self.now + timezone.timedelta(seconds=1)
        self.assertIsNone(self.obj.clean())

    def test_event_start_is_same_end(self):
        self.obj.start = self.now
        self.obj.end = self.now
        self.assertIsNone(self.obj.clean())

    def test_event_start_is_later_end(self):
        self.obj.start = self.now + timezone.timedelta(seconds=1)
        self.obj.end = self.now
        self.assertRaises(ValidationError, self.obj.clean)

    def test_event_contains_date(self):
        self.obj.start = self.now - timezone.timedelta(days=1)
        self.obj.end = self.now + timezone.timedelta(days=1)
        self.assertTrue(self.now in self.obj)

    def test_event_contains_start_date(self):
        self.obj.start = self.now
        self.obj.end = self.now + timezone.timedelta(days=1)
        self.assertTrue(self.now in self.obj)

    def test_event_contains_end_date(self):
        self.obj.start = self.now - timezone.timedelta(days=1)
        self.obj.end = self.now
        self.assertFalse(self.now in self.obj)

    def test_event_not_contains_prev_date(self):
        self.obj.start = self.now + timezone.timedelta(days=1)
        self.obj.end = self.now + timezone.timedelta(days=2)
        self.assertFalse(self.now in self.obj)

    def test_event_not_contains_later_date(self):
        self.obj.start = self.now - timezone.timedelta(days=2)
        self.obj.end = self.now - timezone.timedelta(days=1)
        self.assertFalse(self.now in self.obj)

    def test_event_contains_raise_type_error_exception(self):
        self.obj.start = self.now - timezone.timedelta(days=1)
        self.obj.end = self.now + timezone.timedelta(days=1)
        self.assertRaises(TypeError, self.obj.__contains__, None)
        self.assertRaises(TypeError, self.obj.__contains__, '2021-01-01 18:25:34.894188+00:00')
