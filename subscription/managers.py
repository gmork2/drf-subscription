from django.db import models


class SubscriptionQuerySet(models.QuerySet):
    pass


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
