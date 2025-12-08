from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Create or update superuser on deploy"

    def handle(self, *args, **kwargs):
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        name = os.getenv("DJANGO_SUPERUSER_NAME", "Admin")

        if not email or not password:
            self.stdout.write("⚠️ Admin credentials not provided")
            return

        user = User.objects.filter(email=email).first()

        if user:
            # ✅ Force admin flags (VERY IMPORTANT)
            user.is_superuser = True
            user.is_staff = True
            user.is_admin = True
            user.set_password(password)
            user.save()

            self.stdout.write("✅ Superuser UPDATED successfully")
            return

        # ✅ CREATE user with required fields
        user = User.objects.create_user(
            email=email,
            name=name,
            password=password,
        )

        user.is_superuser = True
        user.is_staff = True
        user.is_admin = True
        user.save()

        self.stdout.write("✅ Superuser CREATED successfully")
