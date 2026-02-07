from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.db.models import Sum
from datetime import date
from .models import Client, Staff, Service, Appointment
from .forms import (
    AppointmentForm,
    ClientForm,
    StaffForm,
    ServiceForm,
    ClientBookingForm,

)

# -------------------
# ROLE HELPERS
# -------------------
def is_admin(user):
    return user.groups.filter(name='Admin').exists()

def is_staff(user):
    return user.groups.filter(name='Staff').exists()

<<<<<<< HEAD
=======
def is_admin_or_staff(user):
    return is_admin(user) or is_staff(user)

>>>>>>> 3c72d3d (Describe change)
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
@user_passes_test(is_admin_or_staff)
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
        'is_admin': request.user.groups.filter(name='Admin').exists(),
        'is_staff': request.user.groups.filter(name='Staff').exists(),
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
    else:
        form = ClientForm(instance=client)

    return render(request, 'add_form.html', {
        'form': form,
        'title': 'Edit Client'
    })

from .forms import ClientBookingForm
from .models import Appointment, Client
<<<<<<< HEAD

def client_booking(request):
    # 1️⃣ Get date & time from request (GET for AJAX, POST for submit)
=======
def client_booking(request):
>>>>>>> 3c72d3d (Describe change)
    selected_date = request.GET.get('date') or request.POST.get('date')
    selected_time = request.GET.get('time') or request.POST.get('time')

    available_staff = Staff.objects.all()

<<<<<<< HEAD
    # 3️⃣ If date & time selected → exclude booked staff
=======
>>>>>>> 3c72d3d (Describe change)
    if selected_date and selected_time:
        booked_staff_ids = Appointment.objects.filter(
            date=selected_date,
            time=selected_time
        ).values_list('staff_id', flat=True)

        available_staff = Staff.objects.exclude(id__in=booked_staff_ids)

<<<<<<< HEAD
    # 4️⃣ Create form FIRST (important)
=======
>>>>>>> 3c72d3d (Describe change)
    form = ClientBookingForm(request.POST or None)

    # 5️⃣ Inject dynamic staff queryset (CRITICAL)
    form.fields['staff'].queryset = available_staff

<<<<<<< HEAD
    # 6️⃣ Handle POST (booking)
=======
>>>>>>> 3c72d3d (Describe change)
    if request.method == 'POST' and form.is_valid():
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
            date=form.cleaned_data['date'],
            time=form.cleaned_data['time'],
            status='Pending'
        )

<<<<<<< HEAD
        return redirect('/appointments/')  # or booking success page
=======
        return render(request, 'booking_success.html')
>>>>>>> 3c72d3d (Describe change)

    return render(request, 'client_booking.html', {
        'form': form
    })
    else:
        form = ClientBookingForm()
        form.fields['staff'].queryset = available_staff

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
