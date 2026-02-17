from rest_framework import serializers
from django.utils import timezone
import pytz
from .models import Attendance, Employee, Permission, LeaveType, LeaveRequest

# Timezone
IST = pytz.timezone('Asia/Kolkata')


# ✅ Employee Serializer
class EmployeeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    employeeId = serializers.CharField(source="employee_id", read_only=True)
    department = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Employee
        fields = ["employeeId", "name", "email", "phone", "department"]


# ✅ Attendance Serializer
class AttendanceSerializer(serializers.ModelSerializer):
    check_in = serializers.SerializerMethodField()
    check_out = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ["date", "status", "check_in", "check_out", "remarks"]

    def get_check_in(self, obj):
        if obj.check_in:
            aware_time = timezone.localtime(obj.check_in, timezone=IST)
            return aware_time.strftime("%I:%M %p")  # e.g., 05:08 PM
        return None

    def get_check_out(self, obj):
        if obj.check_out:
            aware_time = timezone.localtime(obj.check_out, timezone=IST)
            return aware_time.strftime("%I:%M %p")  # e.g., 05:10 PM
        return None


# ✅ Permission Serializer (⚡ hides "Pending")
class PermissionSerializer(serializers.ModelSerializer):
    employeeName = serializers.CharField(source="employee.user.name", read_only=True)
    employeeId = serializers.CharField(source="employee.employee_id", read_only=True)
    start_time = serializers.TimeField(format="%I:%M %p", input_formats=["%H:%M", "%H:%M:%S"])
    end_time = serializers.TimeField(format="%I:%M %p", input_formats=["%H:%M", "%H:%M:%S"])

    class Meta:
        model = Permission
        fields = [
            "id",
            "employeeId",
            "employeeName",
            "date",
            "start_time",
            "end_time",
            "reason",
            "duration_hours",
        ]
        read_only_fields = ["id", "employeeId", "employeeName"]


# ✅ Leave Type Serializer
class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "name", "max_days_per_year", "requires_approval", "description", "is_active"]


# ✅ Leave Request Serializer
class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.user.name", read_only=True)
    employee_id = serializers.CharField(source="employee.employee_id", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.name", read_only=True, allow_null=True)
    total_days = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee_id",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "start_date",
            "end_date",
            "reason",
            "status",
            "approved_by_name",
            "approved_at",
            "rejection_reason",
            "total_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "employee_id", "employee_name", "status", "approved_by_name", "approved_at", "created_at", "updated_at"]


# ✅ Leave Request Create Serializer (for employee submission)
class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "reason"]
    
    def validate(self, data):
        """Validate leave request dates."""
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError("End date must be after start date")
        return data
