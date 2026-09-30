"""Background check for NEPSE price alerts; WhatsApps any that just crossed their target.

Usage:
    python manage.py check_price_alerts                  # single pass, exits (good for Task Scheduler)
    python manage.py check_price_alerts --interval 60     # loop forever, checking every 60s
"""
import time

from django.core.management.base import BaseCommand

from nodis_app.views import evaluate_price_alerts


class Command(BaseCommand):
    help = "Check active price alerts against live NEPSE prices and WhatsApp any that just triggered."

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=0,
            help='If set, loop forever checking every N seconds instead of running once.',
        )

    def handle(self, *args, **options):
        interval = options['interval']
        while True:
            triggered = evaluate_price_alerts()
            if triggered:
                for alert in triggered:
                    self.stdout.write(self.style.SUCCESS(f"Triggered: {alert['symbol']} - {alert['status_text']}"))
            else:
                self.stdout.write("No new alerts triggered.")
            if interval <= 0:
                break
            time.sleep(interval)
