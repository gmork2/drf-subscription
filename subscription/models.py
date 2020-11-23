from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _


class AbstractEventMixin(models.Model):
    start = models.DateTimeField(verbose_name=_('Start date'))
    end = models.DateTimeField(verbose_name=_('End date'))
    description = models.TextField(
        max_length=2048,
        verbose_name=_('Description'),
        blank=True,
    )

    class Meta:
        abstract = True


class BaseGenericObjectResource(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_pk = models.CharField(
        _('object ID'),
        max_length=255
    )
    content_object = GenericForeignKey(fk_field='object_pk')

    class Meta:
        abstract = True
        indexes = [
            models.Index(
                fields=['content_type', 'object_pk']
            ),
        ]

    def __str__(self):
        return '%s' % self.content_object


class Subscription(BaseGenericObjectResource):
    pass


class SubscriptionLine(AbstractEventMixin):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE
    )


class SubscriptionEvent(AbstractEventMixin):
    subscription_line = models.ForeignKey(
        SubscriptionLine,
        on_delete=models.CASCADE
    )


class Resource(BaseGenericObjectResource):
    subscription_event = models.ForeignKey(
        SubscriptionEvent,
        help_text=_('the subscription plan for these cost details'),
        on_delete=models.CASCADE
    )
