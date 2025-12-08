from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = "Create superuser once using env variables"

    def handle(self, *args, **options):
        if os.environ.get("CREATE_SUPERUSER") != "True":
            self.stdout.write("Superuser creation disabled")
            return

        User = get_user_model()

        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Admin@123")
        name = os.environ.get("DJANGO_SUPERUSER_NAME", "Super Admin")

        if User.objects.filter(email=email).exists():
            self.stdout.write("✅ Superuser already exists")
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            name=name
        )

        self.stdout.write("✅ Superuser CREATED successfully")
