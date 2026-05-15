from django.core.management.base import BaseCommand

from accounts.oracle_client import ensure_schema


class Command(BaseCommand):
    help = "Create or update the AgriVision Oracle schema."

    def handle(self, *args, **options):
        ensure_schema()
        self.stdout.write(self.style.SUCCESS("Oracle schema is ready."))
