from calendar import monthrange

from django.utils import timezone


class MonthlyEventMixin:
    @property
    def _recurrence(self):
        """
        Returns the number of days in the current month.

        :return:
        """
        days = monthrange(self.start.year, self.start.month)[1]
        return timezone.timedelta(days=days)

    def __iadd__(self, duration: timezone.timedelta):
        """
        Set the start and end date with the value of the first and last
        day of the following month respectively.

        :param duration:
        :return:
        """
        self.start = self.start.replace(day=1) + duration
        days = monthrange(self.start.year, self.start.month)[1]
        self.end = self.start.replace(day=days)

        return self


class DailyEventMixin:
    @property
    def _recurrence(self):
        """

        :return:
        """
        return timezone.timedelta(days=1)

    def __iadd__(self, duration: timezone.timedelta):
        """
        Adds a duration value to the start and end date.

        :param duration:
        :return:
        """
        self.start = self.start + duration
        self.end = self.start + duration

        return self
