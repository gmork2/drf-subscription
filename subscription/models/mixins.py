from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.utils import timezone


class AbstractEventMixin(models.Model):
    start = models.DateTimeField(verbose_name=_('Start date'))
    end = models.DateTimeField(
        verbose_name=_('End date'),
        null=True,
        blank=True
    )
    description = models.TextField(
        max_length=2048,
        verbose_name=_('Description'),
        blank=True,
    )

    def clean(self, *args, **kwargs):
        """
        Checks that the start date is not later than the end date (as
        long as it exists).

        :param args:
        :param kwargs:
        :return:
        """
        if self.end and self.start > self.end:
            raise ValidationError(
                _('The start of the event cannot be after the end.')
            )

    def __contains__(self, date: timezone.datetime):
        if not isinstance(date, timezone.datetime):
            raise TypeError(
                f'argument "{date}" must be an instance of datetime'
            )
        return \
            self.start <= date if not self.end \
            else self.start <= date < self.end

    @staticmethod
    def tz_now():
        return timezone.now()

    class Meta:
        abstract = True
