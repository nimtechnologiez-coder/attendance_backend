from django.contrib import admin
from .models import Employee, Department, LeaveType, LeaveRequest

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "get_name", "phone", "department", "raw_password")

    def get_name(self, obj):
        return obj.user.first_name
    get_name.short_description = "Employee Name"

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name")

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "max_days_per_year", "requires_approval", "is_active")
    list_filter = ("is_active", "requires_approval")
    search_fields = ("name",)

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "start_date", "end_date", "total_days", "status", "created_at")
    list_filter = ("status", "leave_type", "start_date")
    search_fields = ("employee__user__name", "employee__employee_id")
    readonly_fields = ("total_days", "created_at", "updated_at")
    
    fieldsets = (
        ("Leave Information", {
            "fields": ("employee", "leave_type", "start_date", "end_date", "reason", "total_days")
        }),
        ("Status", {
            "fields": ("status", "approved_by", "approved_at", "rejection_reason")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )
