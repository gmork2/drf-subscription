from typing import List, Callable, Dict, Type
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils import timezone

from .signals import default_receiver

logger = logging.getLogger(__name__)


class SubscriptionQuerySet(models.QuerySet):
    def is_generic(self):
        try:
            _meta = getattr(self.model, '_meta')
            return bool(_meta.get_field('object_pk'))
        except FieldDoesNotExist:
            return False

    def subscribable(self, obj: models.Model) -> bool:
        try:
            ct = ContentType.objects.get_for_model(obj.__class__)
            self.get(object_pk=obj, content_type=ct)
        except self.model.DoesNotExist:
            return True

        return False

    def active(self) -> models.QuerySet:
        return self.filter(
            active=True,
        )


class SubscriptionManager(models.Manager):
    def get_queryset(self) -> SubscriptionQuerySet:
        return SubscriptionQuerySet(
            self.model,
            using=self._db
        )

    def with_active_lines(self):
        pass


class SubscriptionLineQuerySet(models.QuerySet):
    def started(self) -> models.QuerySet:
        now = timezone.now()
        return self.filter(
            (models.Q(start__lte=now) & models.Q(end__gt=now)) |
            (models.Q(start__lte=now) & models.Q(end__isnull=True))
        )

    def finished(self) -> models.QuerySet:
        return self.filter(
            models.Q(end__lte=timezone.now())
        )


class SubscriptionLineManager(models.Manager):
    def get_queryset(self) -> SubscriptionLineQuerySet:
        return SubscriptionLineQuerySet(
            self.model,
            using=self._db
        )


class SubscriptionEventQuerySet(models.QuerySet):
    pass


class SubscriptionEventManager(models.Manager):
    def get_queryset(self) -> SubscriptionEventQuerySet:
        return SubscriptionEventQuerySet(
            self.model,
            using=self._db
        )


class ResourceQuerySet(models.QuerySet):
    def active(self) -> models.QuerySet:
        """
        Returns all active resources.

        :return:
        """
        return self.filter(
            active=True,
            subscription_event__subscription_line__subscription__active=True
        ).select_related(
            'subscription_event__subscription_line__subscription'
        )

    def related_objects(self, instance: models.Model) -> models.QuerySet:
        """
        Returns all related resource objects with the instance.

        :param instance:
        :return:
        """
        ct = ContentType.objects.get_for_model(instance)
        return self.filter(
            content_type=ct,
            object_pk=str(instance.id)
        )


class ResourceManager(models.Manager):
    def get_queryset(self) -> ResourceQuerySet:
        return ResourceQuerySet(
            self.model,
            using=self._db
        )

    def related_models(self, **kwargs) -> List[Type[models.Model]]:
        """
        Returns a list with each of the models related to any existing
        active resource.
        """
        qs = self.get_queryset()
        qs = qs.active()
        return [
            ct.model_class()
            for ct in ContentType.objects.filter(
                id__in=qs.values_list('content_type__id', flat=True)
            )
        ]

    def connect_all(self, signal, receiver: Callable = default_receiver) -> None:
        """
        Connects signal with all related models to any existing active
        resource.
        """
        for model_class in self.related_models():
            signal.connect(receiver, sender=model_class)
            logger.info(
                f'Signal {signal}: {model_class} -> {default_receiver}'
            )

    def disconnect_all(
            self,
            signal,
            receiver: Callable = default_receiver
    ) -> Dict[Type[models.Model], bool]:
        """
        Disconnects signal with all related models to any existing active
        resource.
        """
        return {
            model_class: signal.disconnect(receiver, sender=model_class)
            for model_class in self.related_models()
        }

    def exists_resources(self, content_type: ContentType) -> int:
        """
        Checks if exists active resources for content_type.

        :return:
        """
        qs = self.filter(content_type=content_type)
        return qs.active().exists()
