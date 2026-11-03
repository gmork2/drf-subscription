from datetime import timedelta

from django.db import migrations, models


def convert_recurrence_to_rule(recurrence):
    """
    Convert a legacy ``recurrence`` DurationField value into the
    equivalent (frequency, interval) rule pair.
    """
    if recurrence is None:
        return None, 1
    if isinstance(recurrence, str):
        parts = recurrence.split()
        days = int(parts[0]) if len(parts) > 1 else 0
        hours, minutes, seconds = parts[-1].split(':')
        total = timedelta(
            days=days,
            hours=int(hours),
            minutes=int(minutes),
            seconds=float(seconds),
        ).total_seconds()
    elif isinstance(recurrence, (int, float)):
        total = timedelta(microseconds=recurrence).total_seconds()
    else:
        total = recurrence.total_seconds()

    if total == 0:
        return 'DAILY', 1
    if total % 604800 == 0:
        return 'WEEKLY', int(total // 604800)
    if total % 86400 == 0:
        days = int(total // 86400)
        if 28 <= days <= 31:
            return 'MONTHLY', 1
        if days in (365, 366):
            return 'YEARLY', 1
        return 'DAILY', days
    if total % 3600 == 0:
        return 'HOURLY', int(total // 3600)
    if total % 60 == 0:
        return 'MINUTELY', int(total // 60)
    return 'SECONDLY', int(total)


def forwards(apps, schema_editor):
    """
    Migrate legacy ``recurrence`` values into the new recurrence rule
    fields. The legacy column is read with raw SQL because it is
    removed later in this same migration.
    """
    SubscriptionEvent = apps.get_model('subscription', 'SubscriptionEvent')
    connection = schema_editor.connection

    columns = [
        column.name
        for column in connection.introspection.get_table_description(
            connection.cursor(), SubscriptionEvent._meta.db_table
        )
    ]
    if 'recurrence' not in columns:
        return

    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT id, recurrence FROM {SubscriptionEvent._meta.db_table}'
        )
        rows = cursor.fetchall()

    for event_id, recurrence in rows:
        frequency, interval = convert_recurrence_to_rule(recurrence)
        if frequency is None:
            continue
        SubscriptionEvent.objects.filter(pk=event_id).update(
            frequency=frequency,
            interval=interval,
        )


def backwards(apps, schema_editor):
    # The old recurrence DurationField cannot be rebuilt faithfully for
    # every rule (e.g. monthly rules have no fixed duration), so this
    # migration is not reversible.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('subscription', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionevent',
            name='by_month_day',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    'List of month days (1-31, negative values count from '
                    'the end of the month).'
                ),
                verbose_name='month days',
            ),
        ),
        migrations.AddField(
            model_name='subscriptionevent',
            name='by_week_day',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    'List of week days as two-letter codes (MO, TU, WE, TH, '
                    'FR, SA, SU) or integers (0-6, Monday first).'
                ),
                verbose_name='week days',
            ),
        ),
        migrations.AddField(
            model_name='subscriptionevent',
            name='count',
            field=models.PositiveIntegerField(
                blank=True,
                help_text=(
                    'How many occurrences are generated. Leave empty for '
                    'unlimited (bounded by the end date or the subscription '
                    'line).'
                ),
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='subscriptionevent',
            name='frequency',
            field=models.CharField(
                blank=True,
                choices=[
                    ('SECONDLY', 'Secondly'),
                    ('MINUTELY', 'Minutely'),
                    ('HOURLY', 'Hourly'),
                    ('DAILY', 'Daily'),
                    ('WEEKLY', 'Weekly'),
                    ('MONTHLY', 'Monthly'),
                    ('YEARLY', 'Yearly'),
                ],
                help_text=(
                    'Recurrence rule frequency (RFC 5545). Leave empty for '
                    'a one-time event.'
                ),
                max_length=16,
                null=True,
                verbose_name='frequency',
            ),
        ),
        migrations.AddField(
            model_name='subscriptionevent',
            name='interval',
            field=models.PositiveIntegerField(
                default=1,
                help_text=(
                    'The interval between each frequency iteration.'
                ),
                verbose_name='interval',
            ),
        ),
        migrations.AddField(
            model_name='subscriptionevent',
            name='until',
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    'The latest date an occurrence can start on '
                    '(inclusive).'
                ),
                null=True,
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name='subscriptionevent',
            name='recurrence',
        ),
        migrations.CreateModel(
            name='DailySubscriptionEvent',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('subscription.subscriptionevent',),
        ),
        migrations.CreateModel(
            name='MonthlySubscriptionEvent',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('subscription.subscriptionevent',),
        ),
        migrations.AlterField(
            model_name='resource',
            name='id',
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='id',
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
        migrations.AlterField(
            model_name='subscriptionevent',
            name='id',
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
        migrations.AlterField(
            model_name='subscriptionline',
            name='id',
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
    ]
