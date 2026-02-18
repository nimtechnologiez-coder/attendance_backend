import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from Attendanceapp.models import Employee

class Command(BaseCommand):
    help = "Creates a superuser and associated Employee profile if CREATE_SUPERUSER is True"

    def handle(self, *args, **options):
        if os.environ.get("CREATE_SUPERUSER") == "True":
            User = get_user_model()
            email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
            name = os.environ.get("DJANGO_SUPERUSER_NAME", "Admin User")
            password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Admin@123")

            # 1. Ensure Superuser exists
            user, created = User.objects.get_or_create(email=email, defaults={'name': name})
            if created:
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.is_admin = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f"✅ Superuser ({email}) created"))
            else:
                self.stdout.write(self.style.NOTICE(f"ℹ️ Superuser ({email}) already exists"))

            # 2. Ensure associated Employee profile exists for frontend login
            if not Employee.objects.filter(user=user).exists():
                Employee.objects.create(
                    user=user,
                    employee_id="ADMIN001",  # Robust ID for admin login
                    phone="0000000000",
                    raw_password=password
                )
                self.stdout.write(self.style.SUCCESS("✅ Employee profile created for Admin"))
            else:
                self.stdout.write(self.style.NOTICE("ℹ️ Employee profile for Admin already exists"))
        else:
            self.stdout.write(self.style.WARNING("CREATE_SUPERUSER is not True. Skipping admin creation."))
