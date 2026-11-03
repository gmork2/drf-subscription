import logging

from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_migrate
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


class SubscriptionConfig(AppConfig):
    name = 'subscription'

    def ready(self):
        import subscription.signals  # noqa

        if 'subscription' not in settings.INSTALLED_APPS:
            return

        # Connect resource signals after migrations run, when the
        # database is guaranteed to exist. Accessing the DB during
        # ready() would fail (or warn) while the app registry is still
        # being populated.
        post_migrate.connect(
            self._connect_resources_on_migrate,
            sender=self,
            dispatch_uid='subscription.connect_resources_on_migrate',
        )

    def _connect_resources_on_migrate(self, sender, **kwargs):
        try:
            self._connect_resources()
        except (OperationalError, ProgrammingError, ImproperlyConfigured):
            # Signals are re-connected by the admin actions or by the
            # dynamic connection on Resource.save.
            logger.debug('Unable to connect resource signals: DB not ready')

    def _connect_resources(self):
        """
        Connect the post_save signal of every model related to an
        active resource to the default receiver. Idempotent: repeated
        calls do not stack duplicate receivers (dispatch_uid).
        """
        from .models import Resource
        from .models.decorators import (
            DEFAULT_SIGNAL, DEFAULT_RECEIVER, signal_uid,
        )

        for model_class in Resource.objects.related_models():
            DEFAULT_SIGNAL.connect(
                DEFAULT_RECEIVER,
                sender=model_class,
                dispatch_uid=signal_uid(model_class),
            )
            logger.info(
                'Signal %s: %s -> %s',
                DEFAULT_SIGNAL,
                model_class,
                DEFAULT_RECEIVER.__name__,
            )
