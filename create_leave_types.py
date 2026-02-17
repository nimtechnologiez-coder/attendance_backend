# Run this script to create default leave types
# python manage.py shell < create_leave_types.py

from Attendanceapp.models import LeaveType

# Create default leave types
leave_types_data = [
    {
        "name": "Sick Leave",
        "max_days_per_year": 12,
        "requires_approval": True,
        "description": "For medical emergencies and health issues",
    },
    {
        "name": "Casual Leave",
        "max_days_per_year": 10,
        "requires_approval": True,
        "description": "For personal work and short breaks",
    },
    {
        "name": "Earned Leave",
        "max_days_per_year": 15,
        "requires_approval": True,
        "description": "Accumulated leave for vacation",
    },
    {
        "name": "Maternity Leave",
        "max_days_per_year": 180,
        "requires_approval": True,
        "description": "For expecting mothers",
    },
    {
        "name": "Paternity Leave",
        "max_days_per_year": 15,
        "requires_approval": True,
        "description": "For new fathers",
    },
]

for leave_data in leave_types_data:
    leave_type, created = LeaveType.objects.get_or_create(
        name=leave_data["name"],
        defaults={
            "max_days_per_year": leave_data["max_days_per_year"],
            "requires_approval": leave_data["requires_approval"],
            "description": leave_data["description"],
        }
    )
    if created:
        print(f"✅ Created: {leave_type.name}")
    else:
        print(f"ℹ️  Already exists: {leave_type.name}")

print("\n✅ Leave types setup complete!")
