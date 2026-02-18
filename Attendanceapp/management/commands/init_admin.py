import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Creates a superuser if CREATE_SUPERUSER environment variable is True"

    def handle(self, *args, **options):
        if os.environ.get("CREATE_SUPERUSER") == "True":
            User = get_user_model()
            email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
            name = os.environ.get("DJANGO_SUPERUSER_NAME", "Admin User")
            password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Admin@123")

            if not User.objects.filter(email=email).exists():
                User.objects.create_superuser(
                    email=email,
                    name=name,
                    password=password
                )
                self.stdout.write(self.style.SUCCESS(f"✅ Superuser ({email}) created"))
            else:
                self.stdout.write(self.style.NOTICE(f"ℹ️ Superuser ({email}) already exists"))
        else:
            self.stdout.write(self.style.WARNING("CREATE_SUPERUSER is not True. Skipping admin creation."))
