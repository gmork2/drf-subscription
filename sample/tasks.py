from celery import shared_task

from subscription.tasks import dispatch_due_resources


@shared_task
def dispatch_subscription_resources():
    """
    Periodic task that runs due subscription resources.
    """
    return dispatch_due_resources()
