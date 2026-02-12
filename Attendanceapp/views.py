import math
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from datetime import datetime, date, time, timedelta
from io import BytesIO
import openpyxl
import string, secrets
import pytz

# DRF imports
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import serializers

# Models and serializers
from .models import Employee, Department, Attendance, Permission, User
from .serializers import EmployeeSerializer, PermissionSerializer

User = get_user_model()
IST = pytz.timezone("Asia/Kolkata")


CUTOFF_TIME = time(10, 15)  
ABSENT_TIME = time(12, 0)   

# Geofencing Constants (Office Coordinates and Allowed Radius in Meters)
OFFICE_LAT = 8.1631162
OFFICE_LON = 77.4108498
ALLOWED_RADIUS = 200  # 200 meters

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two coordinates in meters using Haversine formula."""
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c



@csrf_exempt
def login_page(request):
    if request.method == "POST":
        email = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=email, password=password)
        if user and user.is_admin:
            login(request, user)
            return redirect("home_page")
        messages.error(request, "Invalid credentials or not an admin user.")
        return redirect("login")
    return render(request, "login.html")


@login_required(login_url="login")
def logout_page(request):
    logout(request)
    return redirect("login")



@login_required(login_url="login")
def attendance_dashboard(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    employee_filter = request.GET.get("employee", "")
    department_filter = request.GET.get("department", "")

    # Parse start/end dates safely
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today()
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else start
    except ValueError:
        start = end = date.today()

    attendance_qs = Attendance.objects.select_related("employee__user", "employee__department").filter(date__range=(start, end))

    # Apply employee filter (search by employee id or name)
    if employee_filter:
        attendance_qs = attendance_qs.filter(
            Q(employee__employee_id__icontains=employee_filter) |
            Q(employee__user__name__icontains=employee_filter)
        )

    # Filter by department if given (department id)
    if department_filter:
        attendance_qs = attendance_qs.filter(employee__department_id=department_filter)

    attendance_map = {(a.employee_id, a.date): a for a in attendance_qs}

    updated_attendance = []
    employees = Employee.objects.all()
    if department_filter:
        employees = employees.filter(department_id=department_filter)

    current_date = start
    while current_date <= end:
        for emp in employees:
            record = attendance_map.get((emp.id, current_date))
            if record:
                record.approved_permissions = []
                if request.user.is_superuser:
                    permissions = Permission.objects.filter(employee=record.employee, date=record.date)
                    for p in permissions:
                        p.start_time_str = p.start_time.strftime("%I:%M %p") if p.start_time else "-"
                        p.end_time_str = p.end_time.strftime("%I:%M %p") if p.end_time else "-"
                        record.approved_permissions.append(p)
                record.calculated_hours = None
                if not record.check_in:
                    record.status = "Absent"
                    record.check_in_str = "-"
                    record.check_out_str = "-"
                else:
                    local_checkin = record.check_in.astimezone(IST).time()
                    if local_checkin > ABSENT_TIME:
                        record.status = "Absent"
                    elif local_checkin > CUTOFF_TIME:
                        record.status = "Late"
                    else:
                        record.status = "Present"
                    record.check_in_str = record.check_in.astimezone(IST).strftime("%I:%M %p")
                    if record.check_out:
                        record.check_out_str = record.check_out.astimezone(IST).strftime("%I:%M %p")
                        record.calculated_hours = record.working_hours
                    else:
                        record.check_out_str = "-"
                updated_attendance.append(record)
            else:
                # No attendance record → mark as absent
                temp = type("TempAttendance", (), {})()
                temp.employee = emp
                temp.date = current_date
                temp.status = "Absent"
                temp.check_in_str = "-"
                temp.check_out_str = "-"
                temp.calculated_hours = None
                temp.approved_permissions = []
                updated_attendance.append(temp)
        current_date += timedelta(days=1)

    # Summarize attendance counts and total working hours
    total_employees = Employee.objects.count()
    present_count = sum(1 for r in updated_attendance if r.status == "Present")
    absent_count = sum(1 for r in updated_attendance if r.status == "Absent")
    late_count = sum(1 for r in updated_attendance if r.status == "Late")
    total_working_hours = sum(r.calculated_hours for r in updated_attendance if r.calculated_hours)

    context = {
        "attendance": updated_attendance,
        "start_date": start_date or "",
        "end_date": end_date or "",
        "employee_filter": employee_filter,
        "department_filter": int(department_filter) if department_filter else "",
        "departments": Department.objects.all(),
        "total_employees": total_employees,
        "present_count": present_count,
        "absent_count": absent_count,
        "late_count": late_count,
        "total_working_hours": round(total_working_hours, 2),
    }
    return render(request, "home.html", context)

# -------------------------------
# Export Attendance Excel
# -------------------------------

@login_required(login_url="login")
def export_attendance_excel(request):
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    employee_filter = request.GET.get("employee", "")
    department_filter = request.GET.get("department", "")

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else date.today()
    except ValueError:
        start_date = date.today()

    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else start_date
    except ValueError:
        end_date = start_date

    attendance_qs = Attendance.objects.filter(date__range=(start_date, end_date)).select_related(
        "employee__user", "employee__department"
    )

    if employee_filter:
        attendance_qs = attendance_qs.filter(
            Q(employee__employee_id__icontains=employee_filter) |
            Q(employee__user__name__icontains=employee_filter)
        )

    if department_filter:
        attendance_qs = attendance_qs.filter(employee__department_id=department_filter)

    attendance_map = {(a.employee_id, a.date): a for a in attendance_qs}

    employees = Employee.objects.all()
    if department_filter:
        employees = employees.filter(department_id=department_filter)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance Report"
    ws.append([
        "Date", "Employee ID", "Employee Name", "Department",
        "Check In", "Check Out", "Status", "Working Hours", "Permissions", "Remarks"
    ])

    current = start_date
    while current <= end_date:
        for emp in employees:
            record = attendance_map.get((emp.id, current))
            if record:
                if not record.check_in:
                    status = "Absent"
                else:
                    local_checkin = record.check_in.astimezone(IST).time()
                    if local_checkin > ABSENT_TIME:
                        status = "Absent"
                    elif local_checkin > CUTOFF_TIME:
                        status = "Late"
                    else:
                        status = "Present"
                total_hours = record.working_hours if record.working_hours else ""
                permissions_qs = Permission.objects.filter(employee=record.employee, date=record.date)
                permission_str = "\n".join(
                    f"{p.start_time.strftime('%I:%M %p') if p.start_time else '-'}-"
                    f"{p.end_time.strftime('%I:%M %p') if p.end_time else '-'} ({p.status})"
                    for p in permissions_qs
                )
                ws.append([
                    record.date.strftime("%Y-%m-%d"),
                    record.employee.employee_id,
                    record.employee.user.name,
                    record.employee.department.name if record.employee.department else "",
                    record.check_in.astimezone(IST).strftime("%I:%M %p") if record.check_in else "",
                    record.check_out.astimezone(IST).strftime("%I:%M %p") if record.check_out else "",
                    status,
                    total_hours,
                    permission_str.strip(),
                    record.remarks or "",
                ])
            else:
                # No record → Absent row
                ws.append([
                    current.strftime("%Y-%m-%d"),
                    emp.employee_id,
                    emp.user.name,
                    emp.department.name if emp.department else "",
                    "-", "-", "Absent", "", "", "",
                ])
        current += timedelta(days=1)

    # Auto width columns
    for col in ws.columns:
        max_length = max(len(str(cell.value)) for cell in col if cell.value) + 5
        ws.column_dimensions[col[0].column_letter].width = max_length

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"attendance_report_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response

# -------------------------------
# Employee Management Views
# -------------------------------

def employeemanagement(request):
    employees = Employee.objects.select_related("user", "department").all()
    return render(request, "Employeemanagement.html", {"employees": employees})

def generate_random_password(length=6):
    characters = string.ascii_letters + string.digits + "ayowev"
    return "".join(secrets.choice(characters) for _ in range(length))

def add_employee(request):
    # Create departments if not exist
    for name in ["HR", "Developer", "Sales", "Marketing"]:
        Department.objects.get_or_create(name=name)
    departments = Department.objects.all()
    success_message = None

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        department_id = request.POST.get("department")

        if not all([first_name, last_name, email, department_id]):
            messages.error(request, "Please fill all required fields.")
            return render(request, "add_employee.html", {"departments": departments})

        if User.objects.filter(email=email).exists():
            messages.error(request, "User with this email already exists.")
            return render(request, "add_employee.html", {"departments": departments})

        generated_password = generate_random_password()
        user = User(email=email, name=f"{first_name} {last_name}")
        user.set_password(generated_password)
        user.save()

        department = Department.objects.get(id=int(department_id))
        prefix_map = {"HR": "NIMH", "Developer": "NIMD", "Sales": "NIMS", "Marketing": "NIMM"}
        prefix = prefix_map.get(department.name, "NIMX")
        last_employee = Employee.objects.filter(department=department).order_by("-id").first()
        next_number = (int(last_employee.employee_id[-3:]) + 1) if last_employee else 1
        employee_id = f"{prefix}{next_number:03d}"

        Employee.objects.create(
            user=user,
            phone=phone,
            department=department,
            employee_id=employee_id,
            raw_password=generated_password,
        )

        success_message = f"Employee {first_name} {last_name} added! ID: {employee_id} | Password: {generated_password}"

    return render(request, "add_employee.html", {"departments": departments, "success_message": success_message})

def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    departments = Department.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        department_id = request.POST.get("department")

        if not all([name, email, department_id]):
            messages.error(request, "Please fill all required fields.")
        else:
            user = employee.user
            user.name = name
            user.email = email
            user.username = email
            user.save()
            employee.phone = phone
            employee.department = Department.objects.get(id=int(department_id))
            employee.save()
            messages.success(request, f"Employee {name} updated successfully!")

    return render(request, "edit_employee.html", {"employee": employee, "departments": departments})


def delete_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    if request.method == "POST":
        employee.user.delete()
        employee.delete()
        messages.success(request, f"Employee {employee.user.name} deleted successfully!")
        return redirect("employeemanagement")
    return render(request, "delete_employee.html", {"employee": employee})

# -------------------------------
# DRF APIs for Login / Logout / Attendance / Permissions
# -------------------------------

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def login_view(request):
    employee_id = request.data.get("employee_id")
    password = request.data.get("password")

    if not employee_id or not password:
        return Response({"error": "Employee ID and password required"}, status=400)

    try:
        employee = Employee.objects.get(
            Q(employee_id=employee_id) |
            Q(user__email=employee_id) |
            Q(user__name=employee_id)
        )
        user = employee.user

        if not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=401)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "email": user.email,
                "employee_id": employee.employee_id
            }
        })

    except Employee.DoesNotExist:
        return Response({"error": "Employee does not exist"}, status=404)


@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        request.user.auth_token.delete()
        return Response({"message": "Logged out successfully"})
    except Exception:
        return Response({"error": "Logout failed"}, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def today_attendance(request):
    employee = Employee.objects.get(user=request.user)
    today = timezone.now().astimezone(IST).date()
    attendance, _ = Attendance.objects.get_or_create(employee=employee, date=today)
    return Response({
        "employee": {"name": request.user.name, "email": request.user.email},
        "attendance": {
            "date": str(attendance.date),
            "check_in": attendance.check_in.astimezone(IST).strftime("%H:%M") if attendance.check_in else None,
            "check_out": attendance.check_out.astimezone(IST).strftime("%H:%M") if attendance.check_out else None,
            "status": attendance.status,
        },
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_employee_details(request):
    try:
        employee = Employee.objects.get(user=request.user)
        return Response(EmployeeSerializer(employee).data)
    except Employee.DoesNotExist:
        return Response({"error": "Employee profile not found."}, status=404)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_permission_request(request):
    employee = Employee.objects.get(user=request.user)
    data = request.data
    if not all([data.get("start_time"), data.get("end_time"), data.get("reason")]):
        return Response({"error": "All fields are required."}, status=400)
    permission = Permission.objects.create(
        employee=employee,
        date=timezone.now().date(),
        start_time=data["start_time"],
        end_time=data["end_time"],
        reason=data["reason"],
        status="Pending",
    )
    return Response(PermissionSerializer(permission).data, status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_permissions(request):
    employee = Employee.objects.get(user=request.user)
    permissions = Permission.objects.filter(employee=employee).exclude(status="Pending").order_by("-date")
    return Response(PermissionSerializer(permissions, many=True).data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check_in(request):
    employee = Employee.objects.get(user=request.user)
    today = timezone.now().astimezone(IST).date()

    # Geofencing Check
    lat = request.data.get("latitude")
    lon = request.data.get("longitude")

    if lat is None or lon is None:
        return Response({"error": "Location data is required"}, status=400)

    distance = calculate_distance(float(lat), float(lon), OFFICE_LAT, OFFICE_LON)
    if distance > ALLOWED_RADIUS:
        return Response({
            "error": f"You are outside the office range ({round(distance)}m away). Allowed radius is {ALLOWED_RADIUS}m."
        }, status=400)

    attendance, _ = Attendance.objects.get_or_create(employee=employee, date=today)

    if attendance.check_in:
        return Response({"error": "Already checked in"}, status=400)

    utc_now = timezone.now()
    now_ist = utc_now.astimezone(IST)

    cutoff_disable = time(11, 0)  # Disable check-in after 11:00 AM
    if now_ist.time() > cutoff_disable:
        return Response({"error": "Check-in closed after 11:00 AM"}, status=400)

    cutoff_time = CUTOFF_TIME

    attendance.check_in = utc_now
    attendance.status = "Present" if now_ist.time() <= cutoff_time else "Late"
    attendance.save()

    return Response({
        "message": "Checked in successfully",
        "check_in_time": now_ist.strftime("%I:%M %p"),
        "status": attendance.status,
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def check_out(request):
    employee = Employee.objects.get(user=request.user)
    today = timezone.now().astimezone(IST).date()

    # Geofencing Check
    lat = request.data.get("latitude")
    lon = request.data.get("longitude")

    if lat is None or lon is None:
        return Response({"error": "Location data is required"}, status=400)

    distance = calculate_distance(float(lat), float(lon), OFFICE_LAT, OFFICE_LON)
    if distance > ALLOWED_RADIUS:
        return Response({
            "error": f"You are outside the office range ({round(distance)}m away). Allowed radius is {ALLOWED_RADIUS}m."
        }, status=400)

    try:
        attendance = Attendance.objects.get(employee=employee, date=today)
    except Attendance.DoesNotExist:
        return Response({"error": "No check-in record found"}, status=400)

    if attendance.check_out:
        return Response({"error": "Already checked out"}, status=400)

    utc_now = timezone.now()
    attendance.check_out = utc_now
    attendance.save()

    return Response({
        "message": "Checked out",
        "check_out_time": attendance.check_out.astimezone(IST).strftime("%I:%M %p")
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def attendance_history(request):
    employee = request.user.employee
    month = request.GET.get("month")
    records = Attendance.objects.filter(employee=employee)

    if month:
        try:
            year, month_num = map(int, month.split("-"))
            records = records.filter(date__year=year, date__month=month_num)
        except ValueError:
            return Response({"error": "Invalid month format"}, status=400)

    class AttendanceSerializer(serializers.ModelSerializer):
        check_in = serializers.SerializerMethodField()
        check_out = serializers.SerializerMethodField()

        class Meta:
            model = Attendance
            fields = ["date", "check_in", "check_out", "status", "remarks"]

        def get_check_in(self, obj):
            return obj.check_in.astimezone(IST).strftime("%I:%M %p") if obj.check_in else None

        def get_check_out(self, obj):
            return obj.check_out.astimezone(IST).strftime("%I:%M %p") if obj.check_out else None

    return Response(AttendanceSerializer(records.order_by("-date"), many=True).data)



# -------------------------------
# Password Management API
# -------------------------------

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    identifier = request.data.get("employee_id")  # ID, email, or name
    current_password = request.data.get("current_password")
    new_password = request.data.get("new_password")
    confirm_password = request.data.get("confirm_password")

    if not all([identifier, current_password, new_password, confirm_password]):
        return Response({"error": "All fields are required."}, status=400)

    if new_password != confirm_password:
        return Response({"error": "New password and confirm password do not match."}, status=400)

    try:
        employee = Employee.objects.get(
            Q(employee_id=identifier) |
            Q(user__email=identifier) |
            Q(user__name=identifier)
        )
        user = employee.user

        if not user.check_password(current_password):
            return Response({"error": "Current password is incorrect."}, status=400)

        user.set_password(new_password)
        user.save()

        # Optionally store raw password for admin reference
        employee.raw_password = new_password
        employee.save()

        return Response({"message": "Password updated successfully!"}, status=200)

    except Employee.DoesNotExist:
        return Response({"error": "Employee not found."}, status=404)
