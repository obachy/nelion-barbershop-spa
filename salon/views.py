from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.urls import reverse_lazy
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, time, timedelta
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Sum, F, DecimalField, ExpressionWrapper, Q, Value
from django.db.models.functions import Coalesce, Cast
from datetime import date, time, datetime, timedelta
from django.contrib import messages
from decimal import Decimal
import json
from django.core.serializers.json import DjangoJSONEncoder
from .models import (
    Client,
    Staff,
    Service,
    Appointment,
    StaffAttendance,
    StaffPenalty,
    Appointment,
    Expense,
    Invoice,
    InvoiceItem,
    Department,

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
            return reverse_lazy('dashboard')
        return reverse_lazy('login')

# ======================
# DASHBOARD
# ======================

@login_required
@user_passes_test(is_admin_or_staff)
def dashboard(request):
    today = date.today()

    todays_revenue = Appointment.objects.filter(
        date=today,
        status='Completed'
    ).aggregate(total=Sum('service__price'))['total'] or 0

    # Staff performance this month
    staff_performance = (
        Appointment.objects.filter(
            status='Completed',
            date__month=today.month,
            date__year=today.year
        )
        .values('staff__name')
        .annotate(total_jobs=Count('id'))
        .order_by('-total_jobs')
    )

    staff_labels = []
    staff_jobs = []

    for item in staff_performance:
        staff_labels.append(item['staff__name'] or 'Unknown')
        staff_jobs.append(item['total_jobs'])

    # Income per day this month
    daily_income = (
        Appointment.objects.filter(
            status='Completed',
            date__month=today.month,
            date__year=today.year
        )
        .values('date')
        .annotate(total_income=Sum('service__price'))
        .order_by('date')
    )

    daily_labels = []
    daily_sales = []

    for item in daily_income:
        daily_labels.append(item['date'].strftime('%d %b'))
        daily_sales.append(float(item['total_income'] or 0))

    # Income per month this year
    monthly_labels = []
    monthly_sales = []

    for month in range(1, 13):
        total = Appointment.objects.filter(
            status='Completed',
            date__month=month,
            date__year=today.year
        ).aggregate(total=Sum('service__price'))['total'] or 0

        monthly_labels.append(date(today.year, month, 1).strftime('%b'))
        monthly_sales.append(float(total))

            # Staff attendance this month
    attendance_data = []

    for staff_member in Staff.objects.all().order_by('name'):
        present_days = StaffAttendance.objects.filter(
            staff=staff_member,
            date__month=today.month,
            date__year=today.year
        ).count()

        attendance_data.append({
            'staff': staff_member.name,
            'days': present_days,
        })

    attendance_labels = [item['staff'] for item in attendance_data]
    attendance_days = [item['days'] for item in attendance_data]


    # Staff commission this month
    commission_labels = []
    commission_totals = []

    for staff_member in Staff.objects.all().order_by('name'):
        completed_appointments = Appointment.objects.filter(
            staff=staff_member,
            status='Completed',
            date__month=today.month,
            date__year=today.year
        ).select_related('service')

        total_commission = Decimal('0')

        for appointment in completed_appointments:
            service_price = Decimal(str(appointment.service.price or 0))
            commission_percent = Decimal(str(appointment.service.commission_percent or 0))
            commission_amount = Decimal(str(appointment.service.commission_amount or 0))

            if commission_amount == 0 and commission_percent > 0:
                commission_amount = (service_price * commission_percent) / Decimal('100')

            total_commission += commission_amount

        commission_labels.append(staff_member.name)
        commission_totals.append(float(total_commission))

    paid_invoice_total = Decimal('0')
    unpaid_invoice_total = Decimal('0')

    for invoice in Invoice.objects.all():
        invoice_total = Decimal(str(invoice.total_amount()))

        if invoice.status == 'Paid':
            paid_invoice_total += invoice_total

        if invoice.status == 'Unpaid':
             unpaid_invoice_total += invoice_total 

    context = {
        'clients': Client.objects.count(),
        'staff': Staff.objects.count(),
        'services': Service.objects.count(),
        'appointments': Appointment.objects.count(),
        'todays_revenue': todays_revenue,

        'staff_labels': json.dumps(staff_labels, cls=DjangoJSONEncoder),
        'staff_jobs': json.dumps(staff_jobs, cls=DjangoJSONEncoder),

        'daily_labels': json.dumps(daily_labels, cls=DjangoJSONEncoder),
        'daily_sales': json.dumps(daily_sales, cls=DjangoJSONEncoder),

        'monthly_labels': json.dumps(monthly_labels, cls=DjangoJSONEncoder),
        'monthly_sales': json.dumps(monthly_sales, cls=DjangoJSONEncoder),

                'attendance_labels': json.dumps(attendance_labels, cls=DjangoJSONEncoder),
        'attendance_days': json.dumps(attendance_days, cls=DjangoJSONEncoder),

        'commission_labels': json.dumps(commission_labels, cls=DjangoJSONEncoder),
        'commission_totals': json.dumps(commission_totals, cls=DjangoJSONEncoder),

        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),

        'paid_invoice_total': paid_invoice_total,
        'unpaid_invoice_total': unpaid_invoice_total,
    }

    return render(request, 'dashboard.html', context)

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
@user_passes_test(is_admin_or_staff)
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
@user_passes_test(is_admin_or_staff)
def services_list(request):
    services = Service.objects.all().order_by('name')
    return render(request, 'services.html', {'services': services})

@login_required
@user_passes_test(is_admin)
def add_service(request):
    staff_list = Staff.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')

    if request.method == 'POST':
        name = request.POST.get('name')
        price = Decimal(str(request.POST.get('price') or 0))
        duration = int(request.POST.get('duration') or 0)

        commission_percent = Decimal(str(request.POST.get('commission_percent') or 0))
        commission_amount = Decimal(str(request.POST.get('commission_amount') or 0))

        department_id = request.POST.get('department') or None
        staff_ids = request.POST.getlist('staff')

        if commission_amount == 0 and commission_percent > 0:
            commission_amount = (price * commission_percent) / Decimal('100')

        service = Service.objects.create(
            department_id=department_id,
            name=name,
            price=price,
            duration=duration,
            commission_percent=commission_percent,
            commission_amount=commission_amount,
        )

        service.staff.set(staff_ids)

        messages.success(request, "Service added successfully.")
        return redirect('/services/')

    return render(request, 'add_service.html', {
        'staff_list': staff_list,
        'departments': departments,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })

@login_required
@user_passes_test(is_admin)
def delete_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    service.delete()

    messages.success(request, "Service deleted successfully.")
    return redirect('/services/')

# ======================
# STAFF ATTENDANCE
# ======================

OFFICIAL_START_TIME = time(8, 30)
GRACE_PERIOD_MINUTES = 10
LATE_PENALTY_AMOUNT = 50

@login_required
@user_passes_test(is_admin_or_staff)
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
@user_passes_test(is_admin_or_staff)
def staff_check_in(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)

    local_now = timezone.localtime(timezone.now())
    today = local_now.date()
    now_time = local_now.time()

    late_limit = time(8, 30)  # 8:30 AM Kenya time

    attendance, created = StaffAttendance.objects.get_or_create(
        staff=staff,
        date=today,
        defaults={
            'check_in': now_time,
            'is_late': now_time > late_limit,
        }
    )

    if created:
        if attendance.is_late:
            StaffPenalty.objects.get_or_create(
                staff=staff,
                attendance=attendance,
                defaults={
                    'amount': 50,
                    'reason': 'Late arrival after 8:30 AM',
                }
            )

            messages.warning(
                request,
                f"{staff.name} checked in late at {now_time.strftime('%I:%M %p')}."
            )
        else:
            messages.success(
                request,
                f"{staff.name} checked in on time at {now_time.strftime('%I:%M %p')}."
            )
    else:
        messages.info(request, f"{staff.name} already checked in today.")

    return redirect('/staff/attendance/')
   
@login_required
@user_passes_test(is_admin_or_staff)
def staff_check_out(request, attendance_id):
    attendance = get_object_or_404(StaffAttendance, id=attendance_id)
    attendance.check_out = timezone.localtime().time()
    attendance.save()

    return redirect('staff_attendance')


@csrf_protect
def client_booking(request):

    if request.method == "POST":
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        service_id = request.POST.get('service')
        staff_id = request.POST.get('staff')
        date = request.POST.get('date')
        time = request.POST.get('time')

        # Create or get client
        client, _ = Client.objects.get_or_create(
            phone=phone,
            defaults={'name': name, 'email': email}
        )

        # Create appointment
        Appointment.objects.create(
            client=client,
            service_id=service_id,
            staff_id=staff_id,
            date=date,
            time=time,
            status='Pending'
        )

        return render(request, 'booking_success.html')

    services = Service.objects.all()
    staff = Staff.objects.all()

    return render(request, 'client_booking.html', {
        'services': services,
        'staff': staff
    })

def ajax_available_staff(request):
    date = request.GET.get('date')
    time = request.GET.get('time')

    booked = Appointment.objects.filter(
        date=date,
        time=time
    ).values_list('staff_id', flat=True)

    available = Staff.objects.exclude(id__in=booked)

    data = [
        {'id': s.id, 'name': s.name}
        for s in available
    ]

    return JsonResponse({'staff': data})

# salon/views.py
@login_required
@user_passes_test(is_admin)
def staff_commission_report(request):
    today = date.today()

    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    staff_data = []

    for staff in Staff.objects.all():
        completed_appointments = Appointment.objects.filter(
            staff=staff,
            status='Completed',
            date__month=selected_month,
            date__year=selected_year
        ).select_related('service')

        completed_jobs = completed_appointments.count()

        total_sales = sum(
            Decimal(str(appointment.service.price or 0))
            for appointment in completed_appointments
        )

        commission_earned = sum(
            Decimal(str(appointment.service.commission_amount or 0))
            if Decimal(str(appointment.service.commission_amount or 0)) > 0
            else (
                Decimal(str(appointment.service.price or 0)) *
                Decimal(str(appointment.service.commission_percent or 0))
            ) / Decimal('100')
            for appointment in completed_appointments
)

        staff_data.append({
            'staff': staff.name,
            'jobs': completed_jobs,
            'sales': total_sales,
            'commission_rate': 'Percent + Amount',
            'commission_earned': commission_earned,
        })

    return render(request, 'commission/staff_commission.html', {
        'staff_data': staff_data,
        'selected_month': selected_month,
        'selected_year': selected_year,
    })


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

@login_required
def walk_in_customer(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        service_id = request.POST.get('service')
        staff_id = request.POST.get('staff')
        payment_method = request.POST.get('payment_method') or 'Cash'

        client, created = Client.objects.get_or_create(
            phone=phone,
            defaults={
                'name': name,
                'email': ''
            }
        )

        Appointment.objects.create(
            client=client,
            service_id=service_id,
            staff_id=staff_id,
            date=date.today(),
            time=timezone.localtime().time(),
            payment_method=payment_method,
            status='Pending'
            
        )

        return redirect('/appointments/')

    services = Service.objects.all()
    staff = Staff.objects.all()

    return render(request, 'walk_in.html', {
        'services': services,
        'staff': staff
    })

@login_required
@user_passes_test(is_admin)
def staff_work_history(request):
    today = date.today()

    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    staff_reports = []

    staff_list = Staff.objects.all().order_by('name')

    for staff in staff_list:
        completed_appointments = Appointment.objects.filter(
            staff=staff,
            status='Completed',
            date__month=selected_month,
            date__year=selected_year
        ).select_related('client', 'service').order_by('date', 'time')

        work_items = []
        daily_totals = {}

        month_total_sales = Decimal('0')
        month_total_commission = Decimal('0')

        for appointment in completed_appointments:
            service_price = Decimal(str(appointment.service.price or 0))
            commission_percent = Decimal(str(appointment.service.commission_percent or 0))
            commission_amount = Decimal(str(appointment.service.commission_amount or 0))

            # If fixed commission amount is not set, calculate from percentage
            if commission_amount == 0 and commission_percent > 0:
                commission_amount = (service_price * commission_percent) / Decimal('100')

            work_items.append({
                'date': appointment.date,
                'time': appointment.time,
                'client': appointment.client.name,
                'service': appointment.service.name,
                'sales': service_price,
                'commission_percent': commission_percent,
                'commission_amount': commission_amount,
            })

            day_key = appointment.date

            if day_key not in daily_totals:
                daily_totals[day_key] = {
                    'jobs': 0,
                    'sales': Decimal('0'),
                    'commission': Decimal('0'),
                }

            daily_totals[day_key]['jobs'] += 1
            daily_totals[day_key]['sales'] += service_price
            daily_totals[day_key]['commission'] += commission_amount

            month_total_sales += service_price
            month_total_commission += commission_amount

        staff_reports.append({
            'staff': staff,
            'work_items': work_items,
            'daily_totals': daily_totals,
            'month_jobs': completed_appointments.count(),
            'month_total_sales': month_total_sales,
            'month_total_commission': month_total_commission,
        })

    return render(request, 'staff_work_history.html', {
        'staff_reports': staff_reports,
        'selected_month': selected_month,
        'selected_year': selected_year,
    })

@login_required
def book_appointment(request):
    if request.method == 'POST':
        client_id = request.POST.get('client')
        service_id = request.POST.get('service')
        staff_id = request.POST.get('staff')
        appointment_date = request.POST.get('date')
        appointment_time = request.POST.get('time')
        payment_method = request.POST.get('payment_method') or 'Cash'

        Appointment.objects.create(
            client_id=client_id,
            service_id=service_id,
            staff_id=staff_id,
            date=appointment_date,
            time=appointment_time,
            payment_method=payment_method,
            status='Pending'  
        )

        return redirect('/appointments/')

    clients = Client.objects.all()
    services = Service.objects.all()
    staff = Staff.objects.all()

    return render(request, 'book_appointment.html', {
        'clients': clients,
        'services': services,
        'staff': staff,
    })

@login_required
def update_appointment_status(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status in ['Pending', 'Completed', 'Cancelled']:
            appointment.status = new_status
            appointment.save()

    return redirect('/appointments/')

def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Admin').exists()
    )

def is_staff(user):
    return user.is_authenticated and user.groups.filter(name='Staff').exists()

def is_admin_or_staff(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name='Admin').exists()
        or user.groups.filter(name='Staff').exists()
    )

@login_required
def appointments_list(request):
    appointments = Appointment.objects.select_related(
        'client',
        'staff',
        'service'
    ).order_by('-date', '-time')

    return render(request, 'appointments.html', {
        'appointments': appointments,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })

@login_required
def edit_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        appointment.client_id = request.POST.get('client')
        appointment.service_id = request.POST.get('service')
        appointment.staff_id = request.POST.get('staff')
        appointment.date = request.POST.get('date')
        appointment.time = request.POST.get('time')
        appointment.status = request.POST.get('status')
        appointment.payment_method = request.POST.get('payment_method') or 'Cash'
        appointment.save()

        return redirect('/appointments/')

    clients = Client.objects.all()
    services = Service.objects.all()
    staff = Staff.objects.all()

    return render(request, 'edit_appointment.html', {
        'appointment': appointment,
        'clients': clients,
        'services': services,
        'staff': staff,
    })


@login_required
def delete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.delete()
    return redirect('/appointments/')

def logout_view(request):
    logout(request)
    return redirect('/login/')

def public_staff_attendance(request):
    today = timezone.localdate()
    staff_list = Staff.objects.all().order_by('name')
    rows = []

    for staff_member in staff_list:
        attendance = StaffAttendance.objects.filter(
            staff=staff_member,
            date=today
        ).first()

        rows.append({
            'staff': staff_member,
            'attendance': attendance,
        })

    return render(request, 'public_staff_attendance.html', {
        'rows': rows,
        'today': today,
    })

def public_staff_check_in(request, staff_id):
    if request.method == 'POST':
        staff = get_object_or_404(Staff, id=staff_id)

        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        now_time = local_now.time()

        late_limit = time(8, 30)  # 8:30 AM Kenya time

        attendance, created = StaffAttendance.objects.get_or_create(
            staff=staff,
            date=today,
            defaults={
                'check_in': now_time,
                'is_late': now_time > late_limit,
            }
        )

        if created:
            if attendance.is_late:
                StaffPenalty.objects.get_or_create(
                    staff=staff,
                    attendance=attendance,
                    defaults={
                        'amount': 50,
                        'reason': 'Late arrival after 8:30 AM',
                    }
                )

                messages.warning(
                    request,
                    f"{staff.name} checked in late at {now_time.strftime('%I:%M %p')}."
                )
            else:
                messages.success(
                    request,
                    f"{staff.name} checked in on time at {now_time.strftime('%I:%M %p')}."
                )
        else:
            messages.info(request, f"{staff.name} already checked in today.")

    return redirect('/staff/public-attendance/')


def public_staff_check_out(request, attendance_id):
    if request.method == 'POST':
        attendance = get_object_or_404(StaffAttendance, id=attendance_id)

        if attendance.check_out:
            messages.info(request, f"{attendance.staff.name} already checked out.")
        else:
            attendance.check_out = timezone.localtime().time()
            attendance.save()
            messages.success(request, f"{attendance.staff.name} checked out successfully.")

    return redirect('/staff/public-attendance/')

@login_required
@user_passes_test(is_admin)
def payroll_report(request):
    today = date.today()

    selected_month = int(request.GET.get('month') or today.month)
    selected_year = int(request.GET.get('year') or today.year)

    # Payroll always ends on 27th of selected month
    period_end = date(selected_year, selected_month, 27)

    # Payroll starts on 28th of previous month
    if selected_month == 1:
        period_start = date(selected_year - 1, 12, 28)
    else:
        period_start = date(selected_year, selected_month - 1, 28)

    payroll_rows = []

    for staff_member in Staff.objects.all().order_by('name'):
        completed_appointments = Appointment.objects.filter(
            staff=staff_member,
            status='Completed',
            date__range=[period_start, period_end]
        ).select_related('service')

        total_sales = Decimal('0')
        total_earning = Decimal('0')

        for appointment in completed_appointments:
            service_price = Decimal(str(appointment.service.price or 0))
            commission_percent = Decimal(str(appointment.service.commission_percent or 0))
            commission_amount = Decimal(str(appointment.service.commission_amount or 0))

            if commission_amount > 0:
                staff_earning = commission_amount
            else:
                staff_earning = (service_price * commission_percent) / Decimal('100')

            total_sales += service_price
            total_earning += staff_earning

        total_penalties = StaffPenalty.objects.filter(
            staff=staff_member,
            date__range=[period_start, period_end]
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_penalties = Decimal(str(total_penalties))
        net_pay = total_earning - total_penalties

        payroll_rows.append({
            'staff': staff_member,
            'jobs': completed_appointments.count(),
            'total_sales': total_sales,
            'total_earning': total_earning,
            'total_penalties': total_penalties,
            'net_pay': net_pay,
        })

    months = [
        (1, 'January'),
        (2, 'February'),
        (3, 'March'),
        (4, 'April'),
        (5, 'May'),
        (6, 'June'),
        (7, 'July'),
        (8, 'August'),
        (9, 'September'),
        (10, 'October'),
        (11, 'November'),
        (12, 'December'),
    ]

    years = range(today.year - 2, today.year + 2)

    return render(request, 'payroll_report.html', {
        'payroll_rows': payroll_rows,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': months,
        'years': years,
        'period_start': period_start,
        'period_end': period_end,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })

@login_required
@user_passes_test(is_admin)
def expenses_list(request):
    today = date.today()

    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    expenses = Expense.objects.filter(
        expense_date__month=selected_month,
        expense_date__year=selected_year
    ).order_by('-expense_date', '-created_at')

    total_expenses = expenses.filter(expense_type='Expense').aggregate(
        total=Sum('amount')
    )['total'] or 0

    total_bills = expenses.filter(expense_type='Bill').aggregate(
        total=Sum('amount')
    )['total'] or 0

    unpaid_bills = expenses.filter(
        expense_type='Bill',
        status='Unpaid'
    ).aggregate(total=Sum('amount'))['total'] or 0

    paid_total = expenses.filter(status='Paid').aggregate(
        total=Sum('amount')
    )['total'] or 0

    return render(request, 'expenses.html', {
        'expenses': expenses,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'total_expenses': total_expenses,
        'total_bills': total_bills,
        'unpaid_bills': unpaid_bills,
        'paid_total': paid_total,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def add_expense(request):
    if request.method == 'POST':
        expense_type = request.POST.get('expense_type')
        title = request.POST.get('title')
        amount = Decimal(str(request.POST.get('amount') or 0))
        payment_method = request.POST.get('payment_method')
        status = request.POST.get('status')
        expense_date = request.POST.get('expense_date')
        due_date = request.POST.get('due_date') or None
        notes = request.POST.get('notes')

        Expense.objects.create(
            expense_type=expense_type,
            title=title,
            amount=amount,
            payment_method=payment_method,
            status=status,
            expense_date=expense_date,
            due_date=due_date,
            notes=notes,
        )

        messages.success(request, "Expense/Bill added successfully.")
        return redirect('/expenses/')

    return render(request, 'add_expense.html', {
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def mark_expense_paid(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    expense.status = 'Paid'
    expense.save()
    messages.success(request, "Bill marked as paid.")
    return redirect('/expenses/')


@login_required
@user_passes_test(is_admin)
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    expense.delete()
    messages.success(request, "Expense/Bill deleted.")
    return redirect('/expenses/')

@login_required
@user_passes_test(is_admin)
def invoice_list(request):
    invoices = Invoice.objects.select_related('client').all().order_by('-invoice_date', '-id')

    total_unpaid = Decimal('0')
    total_paid = Decimal('0')

    for invoice in invoices:
        total = Decimal(str(invoice.total_amount()))

        if invoice.status == 'Paid':
            total_paid += total
        elif invoice.status == 'Unpaid':
            total_unpaid += total

    return render(request, 'invoice_list.html', {
        'invoices': invoices,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def add_invoice(request):
    clients = Client.objects.all().order_by('name')

    if request.method == 'POST':
        client_id = request.POST.get('client')
        invoice_date = request.POST.get('invoice_date')
        due_date = request.POST.get('due_date') or None
        status = request.POST.get('status') or 'Unpaid'
        notes = request.POST.get('notes')

        descriptions = request.POST.getlist('description')
        quantities = request.POST.getlist('quantity')
        unit_prices = request.POST.getlist('unit_price')

        invoice = Invoice.objects.create(
            client_id=client_id,
            invoice_date=invoice_date,
            due_date=due_date,
            status=status,
            notes=notes,
        )

        for description, quantity, unit_price in zip(descriptions, quantities, unit_prices):
            if description.strip():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=description,
                    quantity=Decimal(str(quantity or 1)),
                    unit_price=Decimal(str(unit_price or 0)),
                )

        messages.success(request, "Invoice created successfully.")
        return redirect(f'/invoices/{invoice.id}/')

    return render(request, 'add_invoice.html', {
        'clients': clients,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    return render(request, 'invoice_detail.html', {
        'invoice': invoice,
        'items': invoice.items.all(),
        'total': invoice.total_amount(),
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def mark_invoice_paid(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice.status = 'Paid'
    invoice.save()
    messages.success(request, "Invoice marked as paid.")
    return redirect(f'/invoices/{invoice.id}/')


@login_required
@user_passes_test(is_admin)
def mark_invoice_unpaid(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice.status = 'Unpaid'
    invoice.save()
    messages.success(request, "Invoice marked as unpaid.")
    return redirect(f'/invoices/{invoice.id}/')


@login_required
@user_passes_test(is_admin)
def delete_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    invoice.delete()
    messages.success(request, "Invoice deleted.")
    return redirect('/invoices/')

@login_required
@user_passes_test(is_admin)
def departments_list(request):
    departments = Department.objects.all().order_by('name')

    return render(request, 'departments.html', {
        'departments': departments,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def add_department(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        if name:
            Department.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            messages.success(request, "Department added successfully.")

        return redirect('/departments/')

    return render(request, 'add_department.html', {
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })

@login_required
@user_passes_test(is_admin)
def edit_department(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        department.name = request.POST.get('name')
        department.description = request.POST.get('description')
        department.save()

        messages.success(request, "Department updated successfully.")
        return redirect('/departments/')

    return render(request, 'edit_department.html', {
        'department': department,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def delete_department(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    department.delete()

    messages.success(request, "Department deleted successfully.")
    return redirect('/departments/')

@login_required
@user_passes_test(is_admin_or_staff)
def services_list(request):
    services = Service.objects.select_related('department').all().order_by('name')

    return render(request, 'services.html', {
        'services': services,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def edit_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    staff_list = Staff.objects.all().order_by('name')
    departments = Department.objects.all().order_by('name')

    if request.method == 'POST':
        service.department_id = request.POST.get('department') or None
        service.name = request.POST.get('name')
        service.price = Decimal(str(request.POST.get('price') or 0))
        service.duration = int(request.POST.get('duration') or 0)
        service.commission_percent = Decimal(str(request.POST.get('commission_percent') or 0))
        service.commission_amount = Decimal(str(request.POST.get('commission_amount') or 0))

        if service.commission_amount == 0 and service.commission_percent > 0:
            service.commission_amount = (service.price * service.commission_percent) / Decimal('100')

        service.save()
        service.staff.set(request.POST.getlist('staff'))

        messages.success(request, "Service updated successfully.")
        return redirect('/services/')

    return render(request, 'edit_service.html', {
        'service': service,
        'staff_list': staff_list,
        'departments': departments,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })
