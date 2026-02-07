from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, time, timedelta
from django.views.decorators.csrf import csrf_protect
from .models import (
    Client,
    Staff,
    Service,
    Appointment,
    StaffAttendance,
    StaffPenalty,
)

from .forms import (
    AppointmentForm,
    ClientForm,
    StaffForm,
    ServiceForm,
)

# ======================
# ROLE HELPERS
# ======================

def is_admin(user):
    return user.groups.filter(name='Admin').exists()

def is_staff(user):
    return user.groups.filter(name='Staff').exists()

def is_admin_or_staff(user):
    return user.groups.filter(name__in=['Admin', 'Staff']).exists()

# ======================
# LOGIN
# ======================

class RoleBasedLoginView(LoginView):
    template_name = 'login.html'

    def get_success_url(self):
        user = self.request.user
        if is_admin(user):
            return reverse_lazy('dashboard')
        if is_staff(user):
            return reverse_lazy('appointments')
        return reverse_lazy('login')

# ======================
# DASHBOARD
# ======================

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    today = date.today()

    todays_revenue = Appointment.objects.filter(
        date=today,
        status='Completed'
    ).aggregate(
        total=Sum('service__price')
    )['total'] or 0

    context = {
        'clients': Client.objects.count(),
        'staff': Staff.objects.count(),
        'services': Service.objects.count(),
        'appointments': Appointment.objects.count(),
        'todays_revenue': todays_revenue,
        'is_admin': is_admin(request.user),
    }

    return render(request, 'dashboard.html', context)

# ======================
# APPOINTMENTS
# ======================

@login_required
@user_passes_test(is_admin_or_staff)
def appointments_list(request):
    appointments = Appointment.objects.select_related(
        'client', 'staff', 'service'
    ).order_by('-date', '-time')

    return render(request, 'appointments.html', {
        'appointments': appointments
    })
@login_required
@user_passes_test(is_admin_or_staff)
def edit_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            return redirect('/appointments/')
    else:
        form = AppointmentForm(instance=appointment)

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Edit Appointment'
    })

@login_required
@user_passes_test(is_admin_or_staff)
def book_appointment(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.status = 'Pending'
            appointment.save()
            return redirect('/appointments/')
    else:
        form = AppointmentForm()

    return render(request, 'book_appointment.html', {'form': form})

@login_required
@user_passes_test(is_admin_or_staff)
def update_appointment_status(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Pending', 'Completed', 'Cancelled']:
            appointment.status = status
            appointment.save()

    return redirect('/appointments/')

@login_required
@user_passes_test(is_admin)
def delete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.delete()
    return redirect('/appointments/')

# ======================
# CLIENTS
# ======================

@login_required
@user_passes_test(is_admin_or_staff)
def clients_list(request):
    clients = Client.objects.all().order_by('name')
    return render(request, 'clients.html', {'clients': clients})
@login_required
@user_passes_test(is_admin_or_staff)
def edit_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect('/clients/')
    else:
        form = ClientForm(instance=client)

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Edit Client'
    })

@login_required
@user_passes_test(is_admin_or_staff)
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

# ======================
# STAFF
# ======================

@login_required
@user_passes_test(is_admin)
def staff_list(request):
    staff = Staff.objects.all().order_by('name')
    return render(request, 'staff.html', {'staff': staff})

@login_required
@user_passes_test(is_admin)
def add_staff(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/staff/')
    else:
        form = StaffForm()

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Add Staff'
    })

# ======================
# SERVICES
# ======================

@login_required
@user_passes_test(is_admin)
def services_list(request):
    services = Service.objects.all().order_by('name')
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
def delete_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    service.delete()
    return redirect('/services/')

# ======================
# STAFF ATTENDANCE
# ======================

OFFICIAL_START_TIME = time(9, 0)
GRACE_PERIOD_MINUTES = 10
LATE_PENALTY_AMOUNT = 200

@login_required
@user_passes_test(is_admin_or_staff)
def staff_attendance_list(request):
    records = StaffAttendance.objects.select_related('staff').order_by('-date')
    staff_list = Staff.objects.all()

    return render(request, 'staff_attendance.html', {
        'records': records,
        'staff_list': staff_list,
        'today': date.today(),
    })

@login_required
@user_passes_test(is_admin_or_staff)
def staff_check_in(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    today = timezone.localdate()
    now_time = timezone.localtime().time()

    attendance, created = StaffAttendance.objects.get_or_create(
        staff=staff,
        date=today,
        defaults={'check_in': now_time}
    )

    late_limit = (
        datetime.combine(today, OFFICIAL_START_TIME) +
        timedelta(minutes=GRACE_PERIOD_MINUTES)
    ).time()

    if now_time > late_limit:
        attendance.is_late = True
        attendance.save()

        StaffPenalty.objects.get_or_create(
            staff=staff,
            date=today,
            defaults={
                'amount': LATE_PENALTY_AMOUNT,
                'reason': 'Late arrival'
            }
        )

    return redirect('/staff/attendance/')

@login_required
@user_passes_test(is_admin_or_staff)
def staff_check_out(request, attendance_id):
    attendance = get_object_or_404(StaffAttendance, id=attendance_id)
    attendance.check_out = timezone.localtime().time()
    attendance.save()
    return redirect('/staff/attendance/')
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

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Edit Service'
    })

@csrf_protect
def client_booking(request):
    if request.method == 'POST':
        form = ClientBookingForm(request.POST)
        if form.is_valid():
            # Create or get client
            client, _ = Client.objects.get_or_create(
                phone=form.cleaned_data['phone'],
                defaults={
                    'name': form.cleaned_data['name'],
                    'email': form.cleaned_data['email']
                }
            )

            # Create appointment
            Appointment.objects.create(
                client=client,
                staff=form.cleaned_data['staff'],
                service=form.cleaned_data['service'],
                date=form.cleaned_data['date'],
                time=form.cleaned_data['time'],
                status='Pending'
            )

            return render(request, 'booking_success.html')

    else:
        form = ClientBookingForm()

    return render(request, 'client_booking.html', {
        'form': form
    })
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

    staff_data = [
        {'id': staff.id, 'name': staff.name}
        for staff in available_staff
    ]

    return JsonResponse({'staff': staff_data})
