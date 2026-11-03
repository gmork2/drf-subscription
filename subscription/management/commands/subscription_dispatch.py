from django.core.management.base import BaseCommand

from subscription.tasks import dispatch_due_resources


class Command(BaseCommand):
    help = (
        'Dispatch every active resource whose event occurrence is active '
        'and pending execution. Use this from cron when Celery is not '
        'available.'
    )

    def handle(self, *args, **options):
        results = dispatch_due_resources()

        self.stdout.write(self.style.SUCCESS(
            f"Dispatched: {len(results['dispatched'])}"
        ))
        self.stdout.write(
            f"Skipped (already executed): {len(results['skipped'])}"
        )
        if results['failed']:
            self.stdout.write(self.style.ERROR(
                f"Failed: {len(results['failed'])} "
                f"({results['failed']})"
            ))
