from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
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
    QuickTaskSale,
    QuickTaskCommission,

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
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Admin').exists()
    )


def is_staff(user):
    return user.is_authenticated and user.groups.filter(name='Staff').exists()


def is_manager(user):
    return user.is_authenticated and user.groups.filter(name='Manager').exists()


def is_admin_or_staff(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name='Admin').exists()
        or user.groups.filter(name='Manager').exists()
        or user.groups.filter(name='Staff').exists()
    )


def is_admin_manager_or_staff(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name='Admin').exists()
        or user.groups.filter(name='Manager').exists()
        or user.groups.filter(name='Staff').exists()
    )


def is_admin_or_manager(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name='Admin').exists()
        or user.groups.filter(name='Manager').exists()
    )


def get_staff_profile_for_user(user):
    if not user.is_authenticated:
        return None

    staff_profile = Staff.objects.filter(user=user).first()

    if staff_profile:
        return staff_profile

    staff_profile = Staff.objects.filter(phone=user.username).first()

    if staff_profile:
        staff_profile.user = user
        staff_profile.save()
        return staff_profile

    return None

# ======================
# LOGIN
# ======================

class RoleBasedLoginView(LoginView):
    template_name = 'login.html'

    def get_success_url(self):
        return reverse_lazy('dashboard')

# ======================
# DASHBOARD
# ======================

@login_required
def dashboard(request):
    today = timezone.localdate()

    # Today sales, including appointments + quick tasks
    appointment_sales_today = Appointment.objects.filter(
        status='Completed',
        date=today
    ).aggregate(total=Sum('service__price'))['total'] or 0

    quick_task_sales_today = QuickTaskSale.objects.filter(
        status='Completed',
        created_at__date=today
    ).aggregate(total=Sum('sale_amount'))['total'] or 0

    todays_revenue = Decimal(str(appointment_sales_today)) + Decimal(str(quick_task_sales_today))

    # Income per day this month
    daily_labels = []
    daily_sales = []

    for day in range(1, today.day + 1):
        current_date = today.replace(day=day)

        appointment_total = Appointment.objects.filter(
            status='Completed',
            date=current_date
        ).aggregate(total=Sum('service__price'))['total'] or 0

        quick_task_total = QuickTaskSale.objects.filter(
            status='Completed',
            created_at__date=current_date
        ).aggregate(total=Sum('sale_amount'))['total'] or 0

        total_income = Decimal(str(appointment_total)) + Decimal(str(quick_task_total))

        daily_labels.append(current_date.strftime('%d %b'))
        daily_sales.append(float(total_income))

    # Monthly income
    monthly_labels = []
    monthly_sales = []

    for month in range(1, 13):
        appointment_total = Appointment.objects.filter(
            status='Completed',
            date__month=month,
            date__year=today.year
        ).aggregate(total=Sum('service__price'))['total'] or 0

        quick_task_total = QuickTaskSale.objects.filter(
            status='Completed',
            created_at__month=month,
            created_at__year=today.year
        ).aggregate(total=Sum('sale_amount'))['total'] or 0

        total_month_income = Decimal(str(appointment_total)) + Decimal(str(quick_task_total))

        monthly_labels.append(str(month))
        monthly_sales.append(float(total_month_income))

    # Staff performance this month
    staff_labels = []
    staff_jobs = []

    if is_admin(request.user) or is_manager(request.user):
        performance_staff_list = Staff.objects.all().order_by('name')
    else:
        staff_profile = get_staff_profile_for_user(request.user)

        if staff_profile:
            performance_staff_list = Staff.objects.filter(id=staff_profile.id)
        else:
            performance_staff_list = Staff.objects.none()

    for staff_member in performance_staff_list:
        appointment_jobs = Appointment.objects.filter(
            staff=staff_member,
            status='Completed',
            date__month=today.month,
            date__year=today.year
        ).count()

        quick_task_jobs = QuickTaskCommission.objects.filter(
            staff=staff_member,
            quick_task__status='Completed',
            quick_task__created_at__date__month=today.month,
            quick_task__created_at__date__year=today.year
        ).count()

        total_jobs = appointment_jobs + quick_task_jobs

        staff_labels.append(staff_member.name)
        staff_jobs.append(total_jobs)

    # Attendance this month
    attendance_labels = []
    attendance_days = []

    for staff_member in performance_staff_list:
        days_present = StaffAttendance.objects.filter(
            staff=staff_member,
            date__month=today.month,
            date__year=today.year,
            check_in__isnull=False
        ).count()

        attendance_labels.append(staff_member.name)
        attendance_days.append(days_present)

    # Staff commission this month, including appointments + quick tasks
    staff_commission_total = Decimal('0')
    commission_labels = []
    commission_totals = []

    month_start = today.replace(day=1)

    if is_admin(request.user) or is_manager(request.user):
        commission_staff_list = Staff.objects.all().order_by('name')
    else:
        staff_profile = get_staff_profile_for_user(request.user)

        if staff_profile:
            commission_staff_list = Staff.objects.filter(id=staff_profile.id)
        else:
            commission_staff_list = Staff.objects.none()
            messages.error(request, "Your login account is not linked to a staff profile.")

    for staff_member in commission_staff_list:
        total_commission = Decimal('0')

        completed_appointments = Appointment.objects.filter(
            staff=staff_member,
            status='Completed',
            date__range=[month_start, today]
        ).select_related('service')

        for appointment in completed_appointments:
            service_price = Decimal(str(appointment.service.price or 0))
            commission_percent = Decimal(str(appointment.service.commission_percent or 0))
            commission_amount = Decimal(str(appointment.service.commission_amount or 0))

            if commission_amount > 0:
                earned_commission = commission_amount
            else:
                earned_commission = (service_price * commission_percent) / Decimal('100')

            total_commission += earned_commission

        quick_task_commission = QuickTaskCommission.objects.filter(
            staff=staff_member,
            quick_task__status='Completed',
            quick_task__created_at__date__range=[month_start, today]
        ).aggregate(total=Sum('commission_amount'))['total'] or 0

        total_commission += Decimal(str(quick_task_commission))

        commission_labels.append(staff_member.name)
        commission_totals.append(float(total_commission))

        if not is_admin(request.user):
            staff_commission_total = total_commission

    # Invoice totals
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

        'paid_invoice_total': paid_invoice_total,
        'unpaid_invoice_total': unpaid_invoice_total,
        'staff_commission_total': staff_commission_total,

        'is_admin': is_admin(request.user),
        'is_manager': is_manager(request.user),
        'is_staff': is_staff(request.user),
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
@user_passes_test(is_admin_manager_or_staff)
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
@user_passes_test(is_admin_manager_or_staff)
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

    return render(request, 'staff.html', {
        'staff': staff,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })

@login_required
@user_passes_test(is_admin)
def add_staff(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not name or not phone or not password:
            messages.error(request, "Name, phone and password are required.")
            return redirect('/staff/add/')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('/staff/add/')

        username = phone.replace(" ", "")

        if User.objects.filter(username=username).exists():
            messages.error(request, "A user with this phone number already exists.")
            return redirect('/staff/add/')

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=name
        )

        staff_group, created = Group.objects.get_or_create(name='Staff')
        user.groups.add(staff_group)
        user.is_staff = False
        user.is_superuser = False
        user.save()

        Staff.objects.create(
            user=user,
            name=name,
            phone=phone
        )

        messages.success(
            request,
            f"Staff created successfully. Username: {username}"
        )
        return redirect('/staff/')

    return render(request, 'add_staff.html', {
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })

@login_required
@user_passes_test(is_admin)
def edit_staff(request, staff_id):
    staff_member = get_object_or_404(Staff, id=staff_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not name or not phone:
            messages.error(request, "Name and phone are required.")
            return redirect(f'/staff/edit/{staff_member.id}/')

        staff_member.name = name
        staff_member.phone = phone
        staff_member.save()

        if staff_member.user:
            staff_member.user.first_name = name
            staff_member.user.username = phone.replace(" ", "")
            staff_member.user.save()

        messages.success(request, "Staff updated successfully.")
        return redirect('/staff/')

    return render(request, 'edit_staff.html', {
        'staff_member': staff_member,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def delete_staff(request, staff_id):
    staff_member = get_object_or_404(Staff, id=staff_id)

    linked_user = staff_member.user

    staff_member.delete()

    if linked_user and linked_user != request.user:
        linked_user.delete()

    messages.success(request, "Staff deleted successfully.")
    return redirect('/staff/')

# ======================
# SERVICES
# ======================

@login_required
@user_passes_test(is_admin_manager_or_staff)
def services_list(request):
    services = Service.objects.all().order_by('name')
    return render(request, 'services.html', {'services': services})

@login_required
@user_passes_test(is_admin_manager_or_staff)
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
@user_passes_test(is_admin_or_manager)
def staff_attendance_list(request):
    local_now = timezone.localtime(timezone.now())
    today = local_now.date()

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

    return render(request, 'staff_attendance.html', {
        'rows': rows,
        'today': today,
        'is_admin': is_admin(request.user),
        'is_manager': is_manager(request.user),
        'is_staff': is_staff(request.user),
    })

@login_required
@user_passes_test(is_admin_or_manager)
def staff_check_in(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)

    local_now = timezone.localtime(timezone.now())
    today = local_now.date()
    now_time = local_now.time()

    late_limit = time(8, 30)

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
            messages.warning(request, f"{staff.name} checked in late.")
        else:
            messages.success(request, f"{staff.name} checked in on time.")
    else:
        messages.info(request, f"{staff.name} already checked in today.")

    return redirect('/staff/attendance/')
   
@login_required
@user_passes_test(is_admin_or_manager)
def staff_check_out(request, attendance_id):
    attendance = get_object_or_404(StaffAttendance, id=attendance_id)

    if attendance.check_out:
        messages.info(request, f"{attendance.staff.name} already checked out.")
    else:
        attendance.check_out = timezone.localtime(timezone.now()).time()
        attendance.save()
        messages.success(request, f"{attendance.staff.name} checked out successfully.")

    return redirect('/staff/attendance/')

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
    today = timezone.localdate()

    selected_month = int(request.GET.get('month') or today.month)
    selected_year = int(request.GET.get('year') or today.year)

    commission_rows = []

    for staff_member in Staff.objects.all().order_by('name'):
        completed_appointments = Appointment.objects.filter(
            staff=staff_member,
            status='Completed',
            date__month=selected_month,
            date__year=selected_year
        ).select_related('service')

        appointment_commission_total = Decimal('0')

        for appointment in completed_appointments:
            service_price = Decimal(str(appointment.service.price or 0))
            commission_percent = Decimal(str(appointment.service.commission_percent or 0))
            commission_amount = Decimal(str(appointment.service.commission_amount or 0))

            if commission_amount > 0:
                earned_commission = commission_amount
            else:
                earned_commission = (service_price * commission_percent) / Decimal('100')

            appointment_commission_total += earned_commission

        quick_task_commission_total = QuickTaskCommission.objects.filter(
            staff=staff_member,
            quick_task__status='Completed',
            quick_task__created_at__month=selected_month,
            quick_task__created_at__year=selected_year
        ).aggregate(total=Sum('commission_amount'))['total'] or 0

        quick_task_commission_total = Decimal(str(quick_task_commission_total))

        quick_task_jobs = QuickTaskCommission.objects.filter(
            staff=staff_member,
            quick_task__status='Completed',
            quick_task__created_at__month=selected_month,
            quick_task__created_at__year=selected_year
        ).count()

        total_commission = appointment_commission_total + quick_task_commission_total

        commission_rows.append({
            'staff': staff_member,
            'appointment_jobs': completed_appointments.count(),
            'quick_task_jobs': quick_task_jobs,
            'total_jobs': completed_appointments.count() + quick_task_jobs,
            'appointment_commission_total': appointment_commission_total,
            'quick_task_commission_total': quick_task_commission_total,
            'total_commission': total_commission,
        })

    months = [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December'),
    ]

    years = range(today.year - 2, today.year + 2)

    return render(request, 'staff_commission.html', {
        'commission_rows': commission_rows,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': months,
        'years': years,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
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
    today = timezone.localdate()

    selected_month = int(request.GET.get('month') or today.month)
    selected_year = int(request.GET.get('year') or today.year)
    staff_id = request.GET.get('staff')

    work_rows = []

    # Completed appointment work
    appointments = Appointment.objects.filter(
        status='Completed',
        date__month=selected_month,
        date__year=selected_year
    ).select_related('client', 'service', 'staff').order_by('-date', '-time')

    if staff_id:
        appointments = appointments.filter(staff_id=staff_id)

    for appointment in appointments:
        service_price = Decimal(str(appointment.service.price or 0))
        commission_percent = Decimal(str(appointment.service.commission_percent or 0))
        commission_amount = Decimal(str(appointment.service.commission_amount or 0))

        if commission_amount > 0:
            earned_commission = commission_amount
        else:
            earned_commission = (service_price * commission_percent) / Decimal('100')

        client_phone = ''
        if appointment.client:
            client_phone = getattr(appointment.client, 'phone', '') or ''

        work_rows.append({
            'date': appointment.date,
            'time': appointment.time,
            'staff': appointment.staff,
            'client_name': appointment.client.name if appointment.client else 'Walk-in',
            'client_phone': client_phone,
            'work_type': 'Appointment',
            'task_name': appointment.service.name,
            'sale_amount': service_price,
            'commission': earned_commission,
        })

    # Quick task work
    quick_commissions = QuickTaskCommission.objects.filter(
        quick_task__status='Completed',
        quick_task__created_at__month=selected_month,
        quick_task__created_at__year=selected_year
    ).select_related('staff', 'quick_task').order_by('-quick_task__created_at')

    if staff_id:
        quick_commissions = quick_commissions.filter(staff_id=staff_id)

    for item in quick_commissions:
        local_created = timezone.localtime(item.quick_task.created_at)

        work_rows.append({
            'date': local_created.date(),
            'time': local_created.time(),
            'staff': item.staff,
            'client_name': item.quick_task.client_name or 'Walk-in',
            'client_phone': item.quick_task.client_phone or '',
            'work_type': 'Quick Task',
            'task_name': item.quick_task.task_name,
            'sale_amount': item.quick_task.sale_amount,
            'commission': item.commission_amount,
        })

    work_rows = sorted(
        work_rows,
        key=lambda row: (row['date'], row['time']),
        reverse=True
    )

    staff_list = Staff.objects.all().order_by('name')

    months = [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December'),
    ]

    years = range(today.year - 2, today.year + 2)

    return render(request, 'staff_work_history.html', {
        'work_rows': work_rows,
        'staff_list': staff_list,
        'selected_staff': staff_id,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': months,
        'years': years,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
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

    # Payroll period: previous month 28th to selected month 27th
    period_end = date(selected_year, selected_month, 27)

    if selected_month == 1:
        period_start = date(selected_year - 1, 12, 28)
    else:
        period_start = date(selected_year, selected_month - 1, 28)

    payroll_rows = []

    for staff_member in Staff.objects.all().order_by('name'):
        # Appointment work
        completed_appointments = Appointment.objects.filter(
            staff=staff_member,
            status='Completed',
            date__range=[period_start, period_end]
        ).select_related('service')

        appointment_jobs = completed_appointments.count()
        appointment_sales_total = Decimal('0')
        appointment_commission_total = Decimal('0')

        for appointment in completed_appointments:
            service_price = Decimal(str(appointment.service.price or 0))
            commission_percent = Decimal(str(appointment.service.commission_percent or 0))
            commission_amount = Decimal(str(appointment.service.commission_amount or 0))

            if commission_amount > 0:
                earned_commission = commission_amount
            else:
                earned_commission = (service_price * commission_percent) / Decimal('100')

            appointment_sales_total += service_price
            appointment_commission_total += earned_commission

        # Quick task work
        quick_task_commissions = QuickTaskCommission.objects.filter(
            staff=staff_member,
            quick_task__status='Completed',
            quick_task__created_at__date__range=[period_start, period_end]
        ).select_related('quick_task')

        quick_task_jobs = quick_task_commissions.count()

        quick_task_commission_total = quick_task_commissions.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0

        quick_task_sales_total = Decimal('0')

        for item in quick_task_commissions:
            quick_task_sales_total += Decimal(str(item.quick_task.sale_amount or 0))

        quick_task_commission_total = Decimal(str(quick_task_commission_total))

        total_jobs = appointment_jobs + quick_task_jobs
        total_sales = appointment_sales_total + quick_task_sales_total
        total_earning = appointment_commission_total + quick_task_commission_total

        total_penalties = StaffPenalty.objects.filter(
            staff=staff_member,
            date__range=[period_start, period_end]
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_penalties = Decimal(str(total_penalties))
        net_pay = total_earning - total_penalties

        payroll_rows.append({
            'staff': staff_member,

            'jobs': total_jobs,
            'appointment_jobs': appointment_jobs,
            'quick_task_jobs': quick_task_jobs,

            'appointment_sales_total': appointment_sales_total,
            'quick_task_sales_total': quick_task_sales_total,
            'total_sales': total_sales,

            'appointment_commission_total': appointment_commission_total,
            'quick_task_commission_total': quick_task_commission_total,
            'total_earning': total_earning,

            'total_penalties': total_penalties,
            'net_pay': net_pay,
        })

    months = [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December'),
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
@user_passes_test(is_admin_manager_or_staff)
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
@user_passes_test(is_admin_manager_or_staff)
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
@user_passes_test(is_admin_or_manager)
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
@user_passes_test(is_admin_manager_or_staff)
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
@user_passes_test(is_admin_manager_or_staff)
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
@user_passes_test(is_admin_manager_or_staff)
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

@login_required
@user_passes_test(is_admin)
def system_users_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'system_users.html', {
        'users': users,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def create_system_user(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        role = request.POST.get('role', '').strip()

        if not username or not password or not role:
            messages.error(request, "Please fill all required fields.")
            return redirect('/users/add/')

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('/users/add/')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('/users/add/')

        user = User.objects.create_user(username=username, password=password)

        admin_group, _ = Group.objects.get_or_create(name='Admin')
        manager_group, _ = Group.objects.get_or_create(name='Manager')
        staff_group, _ = Group.objects.get_or_create(name='Staff')

        if role == 'Admin':
            user.groups.add(admin_group)
            user.is_staff = True
            user.is_superuser = False

        elif role == 'Manager':
            user.groups.add(manager_group)
            user.is_staff = False
            user.is_superuser = False

        elif role == 'Staff':
            user.groups.add(staff_group)
            user.is_staff = False
            user.is_superuser = False

            existing_staff = Staff.objects.filter(phone=username).first()

            if existing_staff:
                existing_staff.user = user
                existing_staff.save()
            else:
                Staff.objects.create(
                    user=user,
                    name=username,
                    phone=username
                )

        user.is_active = True
        user.save()

        messages.success(request, "User created successfully.")
        return redirect('/users/')

    return render(request, 'create_system_user.html', {
        'is_admin': is_admin(request.user),
        'is_manager': is_manager(request.user),
        'is_staff': is_staff(request.user),
    })


@login_required
@user_passes_test(is_admin)
def delete_system_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('/users/')

    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('/users/')


@login_required
@user_passes_test(is_admin)
def reset_system_user_password(request, user_id):
    system_user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect(f'/users/reset-password/{system_user.id}/')

        system_user.set_password(password)
        system_user.save()

        messages.success(request, "Password reset successfully.")
        return redirect('/users/')

    return render(request, 'reset_system_user_password.html', {
        'system_user': system_user,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })

@login_required
@user_passes_test(is_admin_manager_or_staff)
def quick_task_sale(request):
    staff_list = Staff.objects.all().order_by('name')

    if request.method == 'POST':
        task_name = request.POST.get('task_name', '').strip()
        client_name = request.POST.get('client_name', '').strip()
        client_phone = request.POST.get('client_phone', '').strip()
        sale_amount = Decimal(str(request.POST.get('sale_amount') or 0))
        selected_staff_ids = request.POST.getlist('staff_ids')

        if not task_name:
            messages.error(request, "Task name is required.")
            return redirect('/quick-task/')

        if sale_amount <= 0:
            messages.error(request, "Sale amount must be greater than zero.")
            return redirect('/quick-task/')

        if not selected_staff_ids:
            messages.error(request, "Please select at least one staff member.")
            return redirect('/quick-task/')

        # Save client automatically if name or phone is provided
        if client_name or client_phone:
            if client_phone:
                client, created = Client.objects.get_or_create(
                    phone=client_phone,
                    defaults={
                        'name': client_name if client_name else client_phone
                    }
                )

                if not created and client_name and client.name != client_name:
                    client.name = client_name
                    client.save()
            else:
                Client.objects.get_or_create(
                    name=client_name,
                    defaults={
                        'phone': ''
                    }
                )

        quick_task = QuickTaskSale.objects.create(
            task_name=task_name,
            client_name=client_name if client_name else None,
            client_phone=client_phone if client_phone else None,
            sale_amount=sale_amount,
            status='Completed',
            created_by=request.user,
        )

        for staff_id in selected_staff_ids:
            staff_member = Staff.objects.filter(id=staff_id).first()

            if staff_member:
                commission_type = request.POST.get(f'commission_type_{staff_id}', 'amount')
                commission_value = Decimal(str(request.POST.get(f'commission_{staff_id}') or 0))

                if commission_type == 'percent':
                    commission_amount = (sale_amount * commission_value) / Decimal('100')
                else:
                    commission_amount = commission_value

                QuickTaskCommission.objects.create(
                    quick_task=quick_task,
                    staff=staff_member,
                    commission_amount=commission_amount
                )

        messages.success(request, "Quick task sale completed successfully.")
        return redirect('/')

    recent_tasks = QuickTaskSale.objects.all().order_by('-created_at')[:10]

    return render(request, 'quick_task_sale.html', {
        'staff_list': staff_list,
        'recent_tasks': recent_tasks,
        'is_admin': is_admin(request.user),
        'is_staff': is_staff(request.user),
    })