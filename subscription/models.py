from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .managers import ResourceManager, SubscriptionManager, SubscriptionLineManager, SubscriptionEventManager


class AbstractEventMixin(models.Model):
    start = models.DateTimeField(verbose_name=_('Start date'))
    end = models.DateTimeField(verbose_name=_('End date'))
    description = models.TextField(
        max_length=2048,
        verbose_name=_('Description'),
        blank=True,
    )

    def clean(self, *args, **kwargs):
        """
        Checks that the start date is not later than the end date.

        :param args:
        :param kwargs:
        :return:
        """
        if self.start > self.end:
            raise ValidationError(
                _('The start of the event cannot be after the end.')
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
    name = models.CharField(
        max_length=128,
        help_text=_('Subscription name')
    )
    active = models.BooleanField(default=True)
    objects = SubscriptionManager()

    def active_lines(self):
        pass


class SubscriptionLine(AbstractEventMixin):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE
    )
    objects = SubscriptionLineManager()


class SubscriptionEvent(AbstractEventMixin):
    recurrence = models.DurationField(
        null=True,
        blank=True
    )
    subscription_line = models.ForeignKey(
        SubscriptionLine,
        on_delete=models.CASCADE
    )
    objects = SubscriptionEventManager()

    def clean(self):
        """

        :return:
        """
        if not self.end and self.recurrence:
            raise ValidationError(
                _('The end date is mandatory if there is recurrence')
            )
        if self.recurrence and (self.start + self.recurrence < self.end):
            raise ValidationError(
                _('The start date of the new interval cannot be contained '
                  'in the current interval')
            )
        super().clean()


class Resource(BaseGenericObjectResource):
    subscription_event = models.ForeignKey(
        SubscriptionEvent,
        help_text=_('the subscription plan for these cost details'),
        on_delete=models.CASCADE
    )
    data = models.TextField(
        blank=True,
        help_text=_(
            'Warning: this field may contain sensitive information'
            'from other models'
        ),
    )
    callback = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        help_text=_('Dotted path to callable object')
    )
    objects = ResourceManager()
