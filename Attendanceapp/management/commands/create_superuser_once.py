from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Create superuser only if it does not exist"

    def handle(self, *args, **kwargs):
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not email or not password:
            self.stdout.write("⚠️ Admin credentials not provided")
            return

        user = User.objects.filter(email=email).first()

        if user:
            # ✅ FORCE admin flags (VERY IMPORTANT)
            user.is_superuser = True
            user.is_staff = True
            user.is_admin = True
            user.set_password(password)
            user.save()

            self.stdout.write("✅ Superuser flags UPDATED")
            return

        user = User.objects.create_user(
            email=email,
            password=password,
        )

        user.is_superuser = True
        user.is_staff = True
        user.is_admin = True
        user.save()

        self.stdout.write("✅ Superuser CREATED successfully")
