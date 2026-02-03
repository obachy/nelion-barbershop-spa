from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db.models import Sum
from django.utils import timezone
from datetime import date
from datetime import time
from datetime import timedelta
from django.utils import timezone
from .models import Client, Staff, Service, Appointment,StaffAttendance, StaffPenalty
from .forms import (
    AppointmentForm,
    ClientForm,
    StaffForm,
    ServiceForm,
    ClientBookingForm,
)

OFFICIAL_START_TIME = time(9, 0)       # 09:00
GRACE_PERIOD_MINUTES = 10
LATE_PENALTY_AMOUNT = 200


# -------------------
# ROLE HELPERS
# -------------------
def is_admin_or_staff(user):
    return user.groups.filter(name__in=['Admin', 'Staff']).exists()

def is_admin(user):
    return user.groups.filter(name='Admin').exists()

def is_staff(user):
    return user.groups.filter(name='Staff').exists()

def is_admin_or_staff(user):
    return user.groups.filter(name__in=['Admin', 'Staff']).exists()

# -------------------
# LOGIN VIEW
# -------------------

class RoleBasedLoginView(LoginView):
    template_name = 'login.html'

    def get_success_url(self):
        user = self.request.user

        if user.groups.filter(name='Admin').exists():
            return reverse_lazy('dashboard')
        elif user.groups.filter(name='Staff').exists():
            return reverse_lazy('appointments')

        return reverse_lazy('login')

# -------------------
# DASHBOARD (ADMIN ONLY)
# -------------------
@login_required
@user_passes_test(is_admin, login_url='/appointments/')
def dashboard(request):
    today = date.today()

    todays_appointments = Appointment.objects.filter(date=today)
    todays_revenue = todays_appointments.filter(
        status='Completed'
    ).aggregate(total=Sum('service__price'))['total'] or 0

    context = {
        'clients': Client.objects.count(),
        'staff': Staff.objects.count(),
        'services': Service.objects.count(),
        'appointments': Appointment.objects.count(),
        'todays_revenue': todays_revenue,
    }

    return render(request, 'dashboard.html', context)

# -------------------
# APPOINTMENTS (ADMIN + STAFF)
# -------------------

@login_required
def book_appointment(request):
    if request.method == 'POST':
        print("POST RECEIVED:", request.POST)

        form = AppointmentForm(request.POST)

        if form.is_valid():
            obj = form.save()
            print("SAVED:", obj)
            return redirect('/appointments/')
        else:
            print("FORM ERRORS:", form.errors)

    else:
        print("GET REQUEST")

    form = AppointmentForm()
    return render(request, 'book_appointment.html', {'form': form})


@login_required
def update_appointment_status(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Pending', 'Completed', 'Cancelled']:
            appointment.status = status
            appointment.save()

    return redirect('/appointments/')

@login_required
def book_appointment(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/appointments/')
    else:
        form = AppointmentForm()

    return render(request, 'book_appointment.html', {'form': form})

@login_required
def edit_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            return redirect('/appointments/')
    else:
        form = AppointmentForm(instance=appointment)

    return render(request, 'edit_appointment.html', {'form': form})

@login_required
def delete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.delete()
    return redirect('/appointments/')

# -------------------
# CLIENTS (ADMIN ONLY)
# -------------------

@login_required
@user_passes_test(is_admin_or_staff, login_url='/appointments/')
def clients_list(request):
    clients = Client.objects.all()
    return render(request, 'clients.html', {'clients': clients})

@login_required
@user_passes_test(is_admin_or_staff, login_url='/appointments/')
def add_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/clients/')
    else:
        form = ClientForm()

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Add Client'
    })

# -------------------
# STAFF (ADMIN ONLY)
# -------------------

@login_required
@user_passes_test(is_admin)
def staff_list(request):
    staff = Staff.objects.all()
    return render(request, 'staff.html', {'staff': staff})

@login_required
@user_passes_test(is_admin)
def add_staff(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
    else:
        form = StaffForm()

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Add Staff'
    })

# -------------------
# SERVICES (ADMIN ONLY)
# -------------------

@login_required
@user_passes_test(is_admin)
def services_list(request):
    services = Service.objects.all()
    return render(request, 'services.html', {'services': services})

@login_required
@user_passes_test(is_admin)
def add_service(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/services/')
    else:
        form = ServiceForm()

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Add Service'
    })

@login_required
@user_passes_test(is_admin)
def edit_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)

    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return redirect('/services/')
    else:
        form = ServiceForm(instance=service)

    return render(request, 'edit_service.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def delete_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    service.delete()
    return redirect('/services/')

@login_required
@user_passes_test(is_admin_or_staff, login_url='/appointments/')
def edit_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect('/clients/')
    else:
        form = ClientForm(instance=client)

    # ✅ THIS RETURN IS REQUIRED
    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Edit Client'
    })

@login_required
def appointments_list(request):
    appointments = Appointment.objects.select_related(
        'client', 'staff', 'service'
    ).order_by('-date', '-time')

    return render(request, 'appointments.html', {
        'appointments': appointments
    })


    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect('/clients/')
   # else:
    #    form = ClientForm(instance=client)

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Edit Client'
    })

def is_admin_or_staff(user):
    return user.groups.filter(name__in=['Admin', 'Staff']).exists()

@login_required
@user_passes_test(is_admin_or_staff)
def staff_attendance_list(request):
    records = StaffAttendance.objects.order_by('-date')
    staff_list = Staff.objects.all()   # 🔴 REQUIRED

    return render(request, 'staff_attendance.html', {
        'records': records,
        'staff_list': staff_list,      # 🔴 REQUIRED
    })

@login_required
@user_passes_test(is_admin_or_staff)
def add_attendance(request):
    form = StaffAttendanceForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('/staff/attendance/')
    return render(request, 'add_form.html', {'form': form, 'title': 'Add Attendance'})

@login_required
@user_passes_test(is_staff)
def request_leave(request):
    form = StaffLeaveForm(request.POST or None)
    if form.is_valid():
        leave = form.save(commit=False)
        leave.staff = request.user.staff
        leave.save()
        return redirect('/')
    return render(request, 'add_form.html', {'form': form, 'title': 'Request Leave'})

@login_required
@user_passes_test(is_admin)
def staff_penalties(request):
    penalties = StaffPenalty.objects.all()
    return render(request, 'staff_penalties.html', {'penalties': penalties})

@login_required
@user_passes_test(is_admin)
def staff_report(request, staff_id):
    staff = Staff.objects.get(id=staff_id)

    attendance_count = StaffAttendance.objects.filter(staff=staff).count()
    leave_days = StaffLeave.objects.filter(staff=staff, approved=True).count()
    penalties_total = StaffPenalty.objects.filter(staff=staff).aggregate(
        total=Sum('amount')
    )['total'] or 0

    return render(request, 'staff_report.html', {
        'staff': staff,
        'attendance_count': attendance_count,
        'leave_days': leave_days,
        'penalties_total': penalties_total,
    })
@login_required
@user_passes_test(is_admin_or_staff)
def staff_attendance_list(request):
    records = StaffAttendance.objects.order_by('-date')

from .forms import ClientBookingForm
from .models import Appointment, Client
def client_booking(request):
    print("👉 client_booking view HIT:", request.method)
    print("📦 POST DATA:", request.POST)

    # 1️⃣ Get date & time from GET (AJAX) or POST (submit)
    selected_date = request.GET.get('date') or request.POST.get('date')
    selected_time = request.GET.get('time') or request.POST.get('time')

    # 2️⃣ Default: all staff
    available_staff = Staff.objects.all()

    # 3️⃣ Exclude staff already booked
    if selected_date and selected_time:
        booked_staff_ids = Appointment.objects.filter(
            date=selected_date,
            time=selected_time
        ).values_list('staff_id', flat=True)

        available_staff = Staff.objects.exclude(id__in=booked_staff_ids)

    # 4️⃣ Create form
    form = ClientBookingForm(request.POST or None)
    form.fields['staff'].queryset = available_staff

    # 5️⃣ Validate once
    is_valid = form.is_valid()
    print("🧪 FORM IS VALID:", is_valid)
    print("❌ FORM ERRORS:", form.errors.as_json())

    # 6️⃣ Handle POST
    if request.method == 'POST' and is_valid:
        client, _ = Client.objects.get_or_create(
            phone=form.cleaned_data['phone'],
            defaults={
                'name': form.cleaned_data['name'],
                'email': form.cleaned_data['email'],
            }
        )

        Appointment.objects.create(
            client=client,
            staff=form.cleaned_data['staff'],
            service=form.cleaned_data['service'],
            date=selected_date,
            time=selected_time,
            status='Pending'
        )

        return redirect('/booking-success/')

    # 7️⃣ Render page
    return render(request, 'client_booking.html', {
        'form': form,
        'selected_date': selected_date,
        'selected_time': selected_time
    })

from django.http import JsonResponse

def ajax_available_staff(request):
    date = request.GET.get('date')
    time = request.GET.get('time')

    if not date or not time:
        return JsonResponse({'staff': []})

    booked_staff_ids = Appointment.objects.filter(
        date=date,
        time=time
    ).values_list('staff_id', flat=True)

    available_staff = Staff.objects.exclude(id__in=booked_staff_ids)

    data = [
        {'id': staff.id, 'name': staff.name}
        for staff in available_staff
    ]

    return JsonResponse({'staff': data})

def is_admin_or_staff(user):
    return user.groups.filter(name__in=['Admin', 'Staff']).exists()

@login_required
@user_passes_test(is_admin_or_staff)
def staff_attendance_list(request):
    today = timezone.localdate()

    staff_list = Staff.objects.all()
    attendance_map = {
        a.staff_id: a
        for a in StaffAttendance.objects.filter(date=today)
    }

    return render(request, 'staff_attendance.html', {
        'staff_list': staff_list,
        'attendance_map': attendance_map,
        'today': today,
    })

@login_required
def staff_check_in(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)

    today = timezone.localdate()
    now_time = timezone.localtime().time()

    attendance, created = StaffAttendance.objects.get_or_create(
        staff=staff,
        date=today
    )

    if attendance.check_in is None:
        attendance.check_in = now_time

        late_limit_minutes = OFFICIAL_START_TIME.hour * 60 + OFFICIAL_START_TIME.minute + GRACE_PERIOD_MINUTES
        now_minutes = now_time.hour * 60 + now_time.minute

        if now_minutes > late_limit_minutes:
            attendance.is_late = True
            attendance.save()

            StaffPenalty.objects.get_or_create(
                staff=staff,
                attendance=attendance,
                defaults={
                    'amount': LATE_PENALTY_AMOUNT,
                    'reason': 'Late arrival'
                }
            )
        else:
            attendance.save()

    return redirect('/staff/attendance/')

@login_required
def staff_check_out(request, attendance_id):
    attendance = get_object_or_404(StaffAttendance, id=attendance_id)
    attendance.check_out = timezone.localtime().time()
    attendance.save()
    return redirect('/staff/attendance/')
