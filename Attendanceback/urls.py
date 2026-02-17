
# from django.contrib import admin
# from django.urls import path
# from Attendanceapp import views
# from Attendanceapp.views import attendance_history

# urlpatterns = [
#     path("admin/", admin.site.urls),                
#     path("login/", views.login_page, name="login"), 
#     path("", views.login_page, name="home"), 
#     path("home/", views.attendance_dashboard, name="home_page"),
#     path("employeemanagement/", views.employeemanagement, name="employeemanagement"),
#     path("employee/add/", views.add_employee, name="add_employee"),
#     path("employee/<int:employee_id>/edit/", views.edit_employee, name="edit_employee"),
#     path("employee/<int:employee_id>/delete/", views.delete_employee, name="delete_employee"),
#     path("export-attendance/", views.export_attendance_excel, name="export_attendance_excel"),
   

#     # ✅ API Endpoints
#     path("admin/", admin.site.urls),
#     path("api/accounts/login/", views.login_view, name="api_login"),
#     path("api/attendance/today/", views.today_attendance, name="today_attendance"),
#     path("api/attendance/checkin/", views.check_in, name="check_in"),
#     path("api/attendance/checkout/", views.check_out, name="check_out"),
#     path('api/attendance/history/', attendance_history, name='attendance-history'),
   
    
# ]

from django.contrib import admin
from django.urls import path
from Attendanceapp import views
from Attendanceapp.views import attendance_history

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Web pages
    path("", views.login_page, name="home"),
    path("login/", views.login_page, name="login"),
    path("home/", views.attendance_dashboard, name="home_page"),

    path("employeemanagement/", views.employeemanagement, name="employeemanagement"),
    path("employee/add/", views.add_employee, name="add_employee"),
    path("employee/<int:employee_id>/edit/", views.edit_employee, name="edit_employee"),
    path("employee/<int:employee_id>/delete/", views.delete_employee, name="delete_employee"),
    path("export-attendance/", views.export_attendance_excel, name="export_attendance_excel"),

    # ✅✅✅ API ROUTES (THIS IS THE FIX)
    path("api/accounts/login/", views.login_view, name="api_login"),
    path("api/accounts/forgot-password/", views.forgot_password, name="forgot_password"),

    path("api/employee/me/", views.get_employee_details, name="employee-details"),

    path("api/attendance/today/", views.today_attendance),
    path("api/attendance/checkin/", views.check_in),
    path("api/attendance/checkout/", views.check_out),
    path("api/attendance/history/", attendance_history),

    path("api/permission/create/", views.create_permission_request),
    path("api/permission/list/", views.list_permissions),

    # Leave Management APIs
    path("api/leave/types/", views.list_leave_types, name="leave_types"),
    path("api/leave/request/", views.create_leave_request, name="create_leave_request"),
    path("api/leave/my-requests/", views.my_leave_requests, name="my_leave_requests"),
    path("api/leave/balance/", views.leave_balance, name="leave_balance"),
    path("api/leave/pending/", views.pending_leave_requests, name="pending_leave_requests"),
    path("api/leave/<int:leave_id>/approve/", views.approve_leave_request, name="approve_leave"),
    path("api/leave/<int:leave_id>/reject/", views.reject_leave_request, name="reject_leave"),

    # Leave Management Template Views (Django Admin Web Interface)
    path("leave-management/", views.leave_management, name="leave_management"),
    path("leave/<int:leave_id>/approve-web/", views.approve_leave_web, name="approve_leave_web"),
    path("leave/<int:leave_id>/reject-web/", views.reject_leave_web, name="reject_leave_web"),
]

