from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from subscription.models import (
    Resource,
    Subscription,
    SubscriptionEvent,
    SubscriptionLine,
)


def make_user(username):
    return User.objects.create_user(username=username, password='pass')


def make_subscription(user, active=True):
    ct = ContentType.objects.get_for_model(User)
    return Subscription.objects.create(
        name='test',
        active=active,
        content_type=ct,
        object_pk=str(user.pk),
    )


def make_line(subscription, start, end):
    return SubscriptionLine.objects.create(
        subscription=subscription,
        start=start,
        end=end,
    )


def make_event(line, start, end):
    return SubscriptionEvent.objects.create(
        subscription_line=line,
        start=start,
        end=end,
    )


def make_resource(user, event, active=True):
    ct = ContentType.objects.get_for_model(User)
    return Resource.objects.create(
        subscription_event=event,
        content_type=ct,
        object_pk=str(user.pk),
        callback=None,
        active=active,
    )


def make_chain(user, subscription_active=True, resource_active=True):
    now = timezone.now()
    subscription = make_subscription(user, active=subscription_active)
    line = make_line(subscription, now - timedelta(days=1), now + timedelta(days=1))
    event = make_event(line, now - timedelta(days=1), now + timedelta(days=1))
    resource = make_resource(user, event, active=resource_active)
    return subscription, line, event, resource


class SubscriptionManagerTestCase(TestCase):
    def test_is_generic(self):
        self.assertTrue(Subscription.objects.is_generic())

    def test_subscribable_returns_true_when_not_subscribed(self):
        user = make_user('free')
        self.assertTrue(Subscription.objects.subscribable(user))

    def test_subscribable_returns_false_when_subscribed(self):
        user = make_user('paid')
        make_subscription(user)
        self.assertFalse(Subscription.objects.subscribable(user))

    def test_active_includes_future_line_with_event(self):
        subscription, _, _, _ = make_chain(make_user('active'))
        self.assertIn(subscription, Subscription.objects.active())

    def test_active_excludes_inactive_subscription(self):
        subscription, _, _, _ = make_chain(make_user('inactive'), subscription_active=False)
        self.assertNotIn(subscription, Subscription.objects.active())

    def test_active_excludes_past_line(self):
        now = timezone.now()
        subscription = make_subscription(make_user('past'))
        line = make_line(subscription, now - timedelta(days=2), now - timedelta(days=1))
        make_event(line, now - timedelta(days=2), now - timedelta(days=1))
        self.assertNotIn(subscription, Subscription.objects.active())

    def test_active_excludes_line_without_event(self):
        now = timezone.now()
        subscription = make_subscription(make_user('noevent'))
        make_line(subscription, now - timedelta(days=1), now + timedelta(days=1))
        self.assertNotIn(subscription, Subscription.objects.active())


class SubscriptionLineManagerTestCase(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.subscription = make_subscription(make_user('line'))

    def test_started(self):
        started = make_line(self.subscription, self.now - timedelta(days=1), self.now + timedelta(days=1))
        open_ended = make_line(self.subscription, self.now - timedelta(days=1), None)
        future = make_line(self.subscription, self.now + timedelta(days=1), self.now + timedelta(days=2))
        past = make_line(self.subscription, self.now - timedelta(days=2), self.now - timedelta(days=1))

        queryset = SubscriptionLine.objects.started()
        self.assertIn(started, queryset)
        self.assertIn(open_ended, queryset)
        self.assertNotIn(future, queryset)
        self.assertNotIn(past, queryset)

    def test_finished(self):
        finished = make_line(self.subscription, self.now - timedelta(days=2), self.now - timedelta(days=1))
        ongoing = make_line(self.subscription, self.now - timedelta(days=1), self.now + timedelta(days=1))
        open_ended = make_line(self.subscription, self.now - timedelta(days=1), None)

        queryset = SubscriptionLine.objects.finished()
        self.assertIn(finished, queryset)
        self.assertNotIn(ongoing, queryset)
        self.assertNotIn(open_ended, queryset)


class SubscriptionEventManagerTestCase(TestCase):
    def test_current(self):
        now = timezone.now()
        subscription = make_subscription(make_user('event'))
        line = make_line(subscription, now - timedelta(days=1), now + timedelta(days=1))
        current_event = make_event(line, now - timedelta(days=1), now + timedelta(days=1))
        past_event = make_event(line, now - timedelta(days=3), now - timedelta(days=2))

        queryset = SubscriptionEvent.objects.current(line.pk)
        self.assertIn(current_event, queryset)
        self.assertNotIn(past_event, queryset)


class ResourceManagerTestCase(TestCase):
    def test_active(self):
        _, _, _, active = make_chain(make_user('a'), subscription_active=True, resource_active=True)
        _, _, _, inactive_sub = make_chain(make_user('b'), subscription_active=False, resource_active=True)
        _, _, _, inactive_res = make_chain(make_user('c'), subscription_active=True, resource_active=False)

        queryset = Resource.objects.active()
        self.assertIn(active, queryset)
        self.assertNotIn(inactive_sub, queryset)
        self.assertNotIn(inactive_res, queryset)

    def test_related_objects(self):
        _, _, _, resource_a = make_chain(make_user('ua'))
        _, _, _, resource_b = make_chain(make_user('ub'))

        queryset = Resource.objects.related_objects(resource_a.content_object)
        self.assertIn(resource_a, queryset)
        self.assertNotIn(resource_b, queryset)

    def test_related_models(self):
        make_chain(make_user('models'))
        self.assertIn(User, Resource.objects.related_models())

    def test_exists_resources(self):
        make_chain(make_user('exists'))
        user_ct = ContentType.objects.get_for_model(User)
        other_ct = ContentType.objects.get_for_model(Subscription)
        self.assertTrue(Resource.objects.exists_resources(user_ct))
        self.assertFalse(Resource.objects.exists_resources(other_ct))
