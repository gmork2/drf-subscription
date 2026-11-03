class MonthlyEventMixin:
    """
    Recurrence mixin for proxy events that happen once a month.

    Occurrences keep the month day of the first occurrence (RFC 5545
    MONTHLY semantics), instead of snapping to the first day of the
    month as previous versions did.
    """
    frequency = 'MONTHLY'
    interval = 1

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('frequency', self.frequency)
        kwargs.setdefault('interval', self.interval)
        super().__init__(*args, **kwargs)


class DailyEventMixin:
    """
    Recurrence mixin for proxy events that happen every day (RFC 5545
    DAILY semantics).
    """
    frequency = 'DAILY'
    interval = 1

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('frequency', self.frequency)
        kwargs.setdefault('interval', self.interval)
        super().__init__(*args, **kwargs)
