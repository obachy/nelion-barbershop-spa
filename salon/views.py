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
from django.db.models import Count, Sum, F, DecimalField, ExpressionWrapper, Q, Value
from django.db.models.functions import Coalesce, Cast
from datetime import datetime
from django.contrib import messages
from decimal import Decimal
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
    appointments = Appointment.objects.all()

    return render(request, 'appointments.html', {
        'appointments': appointments,
        'is_admin': request.user.groups.filter(name='Admin').exists(),
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
def staff_attendance_list(request):
    today = timezone.localdate()

    staff_list = Staff.objects.all()

    # Get today's attendance
    attendances = StaffAttendance.objects.filter(date=today)

    # Build dictionary: {staff_id: attendance_object}
    attendance_map = {a.staff_id: a for a in attendances}

    context = {
        'staff_list': staff_list,
        'attendance_map': attendance_map,
        'today': today,
    }

    return render(request, 'staff_attendance.html', context)

@login_required
def staff_check_in(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    today = timezone.localdate()
    now_time = timezone.localtime().time()

    StaffAttendance.objects.get_or_create(
        staff=staff,
        date=today,
        defaults={'check_in': now_time}
    )

    return redirect('staff_attendance')

@login_required
def staff_check_out(request, attendance_id):
    attendance = get_object_or_404(StaffAttendance, id=attendance_id)
    attendance.check_out = timezone.localtime().time()
    attendance.save()

    return redirect('staff_attendance')

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
# salon/views.py
@login_required
@user_passes_test(is_admin)
def staff_commission_report(request):

    selected_month = request.GET.get('month')
    selected_year = request.GET.get('year')

    # default month/year
    if not selected_month:
        selected_month = date.today().month
    if not selected_year:
        selected_year = date.today().year

    appointments = Appointment.objects.filter(
        status='Completed',
        date__month=selected_month,
        date__year=selected_year
    )

    report = (
        Staff.objects
        .annotate(
            completed_jobs=Count(
                'appointment',
                filter=Q(
                    appointment__status='Completed',
                    appointment__date__month=selected_month,
                    appointment__date__year=selected_year
                )
            ),
            total_sales=Coalesce(
                Sum(
                    'appointment__service__price',
                    filter=Q(
                        appointment__status='Completed',
                        appointment__date__month=selected_month,
                        appointment__date__year=selected_year
                    )
                ),
                0,
                output_field=DecimalField()
            )
        )
    )

    return render(request, 'staff_commission.html', {
        'report': report,
        'selected_month': selected_month,
        'selected_year': selected_year,
    })


from decimal import Decimal
from django.contrib import messages

@login_required
def complete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if appointment.status == 'Completed':
        messages.info(request, "Already completed.")
        return redirect('/appointments/')

    appointment.status = 'Completed'

    service_price = Decimal(str(appointment.service.price))
    commission_rate = Decimal(str(appointment.staff.commission))

    commission_amount = (service_price * commission_rate) / Decimal('100')

    appointment.commission_earned = commission_amount
    appointment.save()

    messages.success(
        request,
        f"Completed! Commission Earned: KES {commission_amount}"
    )

    return redirect('/appointments/')
