from typing import List

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db import models


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
    pass


class ResourceManager(models.Manager):
    def get_queryset(self) -> ResourceQuerySet:
        return ResourceQuerySet(
            self.model,
            using=self._db
        )

    def related_object(self, instance: models.Model):
        ct = ContentType.objects.get_for_model(instance)
        return self.filter(
            content_type=ct,
            object_pk=str(instance.id)
        )

    def related_models(self, **kwargs) -> List[models.Model]:
        return [
            ct.model_class()
            for ct in ContentType.objects.filter(
                id__in=self.values_list('content_type__id', flat=True)
            )
        ]


