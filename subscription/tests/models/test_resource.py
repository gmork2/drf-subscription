from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from subscription.models import Resource, Subscription, SubscriptionEvent


class ResourceTestCase(TestCase):
    fixtures = ['auth.json', 'contenttypes.json', 'subscription.json']

    def test_is_ready(self):
        resource = Resource.objects.get(pk=1)
        self.assertTrue(resource.is_ready)

    def test_is_ready_false_when_subscription_inactive(self):
        Subscription.objects.filter(pk=1).update(active=False)
        resource = Resource.objects.get(pk=1)
        self.assertFalse(resource.is_ready)

    def test_is_ready_false_when_resource_inactive(self):
        resource = Resource.objects.get(pk=1)
        resource.active = False
        self.assertFalse(resource.is_ready)

    def test_get_values_from_related_object(self):
        resource = Resource.objects.get(pk=1)
        model_class = resource.content_type.model_class()
        values = resource.get_values_from_related_object(model_class)
        self.assertIsInstance(values, dict)
        self.assertEqual(values['username'], 'user')

    def test_clean_raises_for_missing_object(self):
        ct = ContentType.objects.get_for_model(User)
        event = SubscriptionEvent.objects.get(pk=1)
        resource = Resource(subscription_event=event, content_type=ct, object_pk='999999')
        with self.assertRaises(ValidationError):
            resource.clean()

    def test_clean_raises_for_unknown_fields(self):
        resource = Resource.objects.get(pk=1)
        resource.content_object_fields = "{'nonexistent_field': 1}"
        with self.assertRaises(ValidationError):
            resource.clean()
