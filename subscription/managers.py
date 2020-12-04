from typing import List, Callable, Dict, Type
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import models

from .signals import default_receiver

logger = logging.getLogger(__name__)


class SubscriptionQuerySet(models.QuerySet):
    def is_generic(self):
        try:
            _meta = getattr(self.model, '_meta')
            return bool(_meta.get_field('object_pk'))
        except FieldDoesNotExist:
            return False

    def active_lines(self):
        pass

    def subscribable(self, obj: models.Model) -> bool:
        try:
            ct = ContentType.objects.get_for_model(obj.__class__)
            self.get(object_pk=obj, content_type=ct)
        except self.model.DoesNotExist:
            return True

        return False


class SubscriptionManager(models.Manager):
    def get_queryset(self) -> SubscriptionQuerySet:
        return SubscriptionQuerySet(
            self.model,
            using=self._db
        )


class SubscriptionLineQuerySet(models.QuerySet):
    pass


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
    def is_active(self) -> models.QuerySet:
        return self.filter(
            active=True,
            subscription_event__subscription_line__subscription__active=True
        ).select_related(
            'subscription_event__subscription_line__subscription'
        )


class ResourceManager(models.Manager):
    def get_queryset(self) -> ResourceQuerySet:
        return ResourceQuerySet(
            self.model,
            using=self._db
        )

    def related_objects(self, instance: models.Model) -> models.QuerySet:
        ct = ContentType.objects.get_for_model(instance)
        return self.filter(
            content_type=ct,
            object_pk=str(instance.id)
        )

    def related_models(self, **kwargs) -> List[Type[models.Model]]:
        """
        Returns a list with each of the models related to any existing
        active resource.
        """
        qs = self.get_queryset()
        qs = qs.is_active()
        return [
            ct.model_class()
            for ct in ContentType.objects.filter(
                id__in=qs.values_list('content_type__id', flat=True)
            )
        ]

    def connect(self, signal, receiver: Callable = default_receiver) -> None:
        """
        Connects signal with all related models to any existing active
        resource.
        """
        for model_class in self.related_models():
            signal.connect(receiver, sender=model_class)
            logger.info(
                f'Signal {signal}: {model_class} -> {default_receiver}'
            )

    @staticmethod
    def disconnect(
        signal,
        related_models: list[models.Model],
        receiver: Callable = default_receiver
    ) -> Dict[Type[models.Model, bool]]:
        """
        Disconnects signal for the provided related models.
        """
        return {
            model_class: signal.disconnect(receiver, sender=model_class)
            for model_class in related_models
        }

