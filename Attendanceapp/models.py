
import datetime
import pytz
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ----------------------------
# Custom User Manager
# ----------------------------
class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, name, password, **extra_fields)


# ----------------------------
# Custom User Model
# ----------------------------
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email


# ----------------------------
# Department Model
# ----------------------------
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# ----------------------------
# Employee Model
# ----------------------------
class Employee(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=20, unique=True, editable=False)
    phone = models.CharField(max_length=15, blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    raw_password = models.CharField(max_length=50, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.employee_id:
            last_employee = Employee.objects.order_by("-id").first()
            next_id = (last_employee.id + 1) if last_employee else 1
            self.employee_id = f"EMP{next_id:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} - {self.user.name}"


# ----------------------------
# Helper function for default date
# ----------------------------
def default_date():
    return timezone.now().date()


# ----------------------------
# Permission Model
# ----------------------------
class Permission(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=default_date)
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        return f"{self.employee.user.name} - {self.date} ({self.status})"

    @property
    def duration_hours(self):
        """Safe duration calculation (handles both str and datetime.time)."""
        start_time = self.start_time
        end_time = self.end_time

        if isinstance(start_time, str):
            try:
                start_time = datetime.datetime.strptime(start_time, "%H:%M:%S").time()
            except ValueError:
                start_time = datetime.datetime.strptime(start_time, "%H:%M").time()
        
        if isinstance(end_time, str):
            try:
                end_time = datetime.datetime.strptime(end_time, "%H:%M:%S").time()
            except ValueError:
                end_time = datetime.datetime.strptime(end_time, "%H:%M").time()

        start = datetime.datetime.combine(self.date, start_time)
        end = datetime.datetime.combine(self.date, end_time)

        return round((end - start).total_seconds() / 3600, 2)


# ----------------------------
# Attendance Model
# ----------------------------
class Attendance(models.Model):
    STATUS_CHOICES = [
        ("Present", "Present"),
        ("Absent", "Absent"),
        ("Late", "Late"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField(default=default_date)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Absent")
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("employee", "date")

    def save(self, *args, **kwargs):
        """Auto-assign status and remarks based on check-in time."""
        IST = pytz.timezone("Asia/Kolkata")

        if self.check_in:
            check_in_ist = self.check_in.astimezone(IST)
            check_in_time = check_in_ist.time()

            if check_in_time > datetime.time(10, 0):
                self.status = "Late"
                if not self.remarks:
                    self.remarks = f"Checked in at {check_in_time.strftime('%H:%M')} IST (Late)"
            else:
                self.status = "Present"
                if not self.remarks:
                    self.remarks = f"Checked in at {check_in_time.strftime('%H:%M')} IST (On time)"
        else:
            self.status = "Absent"
            if not self.remarks:
                self.remarks = "No check-in recorded"

        super().save(*args, **kwargs)

    @property
    def working_hours(self):
        """Calculate working hours after subtracting approved permissions."""
        if self.check_in and self.check_out:
            total_time = self.check_out - self.check_in

            # Subtract approved permission hours (if any)
            permissions = Permission.objects.filter(
                employee=self.employee,
                date=self.date,
                status="Approved",
            )
            for p in permissions:
                # Handle string time format gracefully
                p_start = p.start_time
                p_end = p.end_time
                
                if isinstance(p_start, str):
                    try:
                        p_start = datetime.datetime.strptime(p_start, "%H:%M:%S").time()
                    except ValueError:
                        p_start = datetime.datetime.strptime(p_start, "%H:%M").time()
                        
                if isinstance(p_end, str):
                    try:
                        p_end = datetime.datetime.strptime(p_end, "%H:%M:%S").time()
                    except ValueError:
                        p_end = datetime.datetime.strptime(p_end, "%H:%M").time()

                start = datetime.datetime.combine(self.date, p_start)
                end = datetime.datetime.combine(self.date, p_end)

                # Make start/end timezone aware if check_in/check_out are aware
                if timezone.is_aware(self.check_in):
                    start = timezone.make_aware(start)
                    end = timezone.make_aware(end)

                total_time -= (end - start)

            return round(total_time.total_seconds() / 3600, 2)
        return 0


# ----------------------------
# Leave Management Models
# ----------------------------

class LeaveType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    max_days_per_year = models.IntegerField(default=12)
    requires_approval = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.max_days_per_year} days/year)"


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.user.name} - {self.leave_type.name} ({self.status})"

    @property
    def total_days(self):
        """Calculate total number of leave days."""
        return (self.end_date - self.start_date).days + 1

    def clean(self):
        """Validate leave request."""
        from django.core.exceptions import ValidationError
        
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError("End date must be after start date")
            
            # Check for overlapping leaves
            overlapping = LeaveRequest.objects.filter(
                employee=self.employee,
                status__in=['Pending', 'Approved']
            ).exclude(pk=self.pk)
            
            for leave in overlapping:
                if not (self.end_date < leave.start_date or self.start_date > leave.end_date):
                    raise ValidationError(
                        f"Leave request overlaps with existing leave from {leave.start_date} to {leave.end_date}"
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
