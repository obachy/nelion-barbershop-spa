from django.urls import path
from . import views
from .views import (
    public_staff_attendance,
    public_staff_check_in,
    public_staff_check_out,
    dashboard,
    book_appointment,
    update_appointment_status,
    clients_list,
    staff_list,
    services_list,
    appointments_list,
    edit_appointment,
    delete_appointment,
    add_client,
    add_staff,
    add_service,
    edit_service,
    delete_service,
    edit_client,
    client_booking,
    ajax_available_staff,
    staff_commission_report,
    staff_attendance_list,
    staff_check_in,
    staff_check_out,
    complete_appointment,
    walk_in_customer,
    staff_work_history,
    payroll_report,
    expenses_list,
    add_expense,
    mark_expense_paid,
    delete_expense,
    invoice_list,
    add_invoice,
    invoice_detail,
    mark_invoice_paid,
    mark_invoice_unpaid,
    delete_invoice,
    departments_list,
    add_department,
    edit_department,
    delete_department,
    system_users_list,
    create_system_user,
    delete_system_user,
    reset_system_user_password,
    edit_staff,
    delete_staff,

)

urlpatterns = [
    path('', dashboard, name='dashboard'),

    path('book-appointment/', book_appointment, name='book_appointment'),
    path('book/', client_booking, name='client_booking'),

    path('appointments/', appointments_list, name='appointments'),
    path('appointments/edit/<int:appointment_id>/', edit_appointment, name='edit_appointment'),
    path('appointments/delete/<int:appointment_id>/', delete_appointment, name='delete_appointment'),
    path('appointments/complete/<int:appointment_id>/', complete_appointment, name='complete_appointment'),
    path('update-status/<int:appointment_id>/', update_appointment_status, name='update_status'),

    path('clients/', clients_list, name='clients'),
    path('add-client/', add_client, name='add_client'),
    path('clients/edit/<int:client_id>/', edit_client, name='edit_client'),

    path('staff/', staff_list, name='staff'),
    path('add-staff/', add_staff, name='add_staff'),
    path('staff/commission/', staff_commission_report, name='staff_commission'),
    path('staff/attendance/', staff_attendance_list, name='staff_attendance'),
    path('staff/check-in/<int:staff_id>/', staff_check_in, name='staff_check_in'),
    path('staff/check-out/<int:attendance_id>/', staff_check_out, name='staff_check_out'),
    path('staff/work-history/', staff_work_history, name='staff_work_history'),

    path('services/', services_list, name='services'),
    path('add-service/', add_service, name='add_service'),
    path('services/edit/<int:service_id>/', edit_service, name='edit_service'),
    path('services/delete/<int:service_id>/', delete_service, name='delete_service'),

    path('ajax/available-staff/', ajax_available_staff, name='ajax_available_staff'),
    path('walk-in/', walk_in_customer, name='walk_in_customer'),
    path('staff/public-attendance/', public_staff_attendance, name='public_staff_attendance'),
    path('staff/public-check-in/<int:staff_id>/', public_staff_check_in, name='public_staff_check_in'),
    path('staff/public-check-out/<int:attendance_id>/', public_staff_check_out, name='public_staff_check_out'),
    path('staff/payroll/', payroll_report, name='payroll_report'),

    path('expenses/', expenses_list, name='expenses'),
    path('expenses/add/', add_expense, name='add_expense'),
    path('expenses/paid/<int:expense_id>/', mark_expense_paid, name='mark_expense_paid'),
    path('expenses/delete/<int:expense_id>/', delete_expense, name='delete_expense'),
    path('invoices/', invoice_list, name='invoice_list'),
    path('invoices/add/', add_invoice, name='add_invoice'),
    path('invoices/<int:invoice_id>/', invoice_detail, name='invoice_detail'),
    path('invoices/paid/<int:invoice_id>/', mark_invoice_paid, name='mark_invoice_paid'),
    path('invoices/unpaid/<int:invoice_id>/', mark_invoice_unpaid, name='mark_invoice_unpaid'),
    path('invoices/delete/<int:invoice_id>/', delete_invoice, name='delete_invoice'),
    path('departments/', departments_list, name='departments'),
    path('departments/add/', add_department, name='add_department'),
    path('departments/edit/<int:department_id>/', edit_department, name='edit_department'),
    path('departments/delete/<int:department_id>/', delete_department, name='delete_department'),
    path('staff/add/', add_staff, name='add_staff'),
    path('users/', system_users_list, name='system_users'),
    path('users/add/', create_system_user, name='create_system_user'),
    path('users/delete/<int:user_id>/', delete_system_user, name='delete_system_user'),
    path('users/reset-password/<int:user_id>/', reset_system_user_password, name='reset_system_user_password'),
    path('staff/edit/<int:staff_id>/', edit_staff, name='edit_staff'),
    path('staff/delete/<int:staff_id>/', delete_staff, name='delete_staff'),
    path(
        'approvals/',
        views.job_approvals,
        name='job_approvals'
    ),

    path(
        'approvals/appointment/<int:appointment_id>/approve/',
        views.approve_appointment,
        name='approve_appointment'
    ),

    path(
        'approvals/appointment/<int:appointment_id>/reject/',
        views.reject_appointment,
        name='reject_appointment'
    ),

    path(
        'approvals/quick-task/<int:task_id>/approve/',
        views.approve_quick_task,
        name='approve_quick_task'
    ),

    path(
        'approvals/quick-task/<int:task_id>/reject/',
        views.reject_quick_task,
        name='reject_quick_task'
    ),

    path(
        'work-history/appointment/<int:appointment_id>/edit/',
        views.edit_completed_appointment,
        name='edit_completed_appointment'
    ),

    path(
        'work-history/quick-task/<int:task_id>/edit/',
        views.edit_completed_quick_task,
        name='edit_completed_quick_task'
    ),
    path(
        'my-commission/',
        views.my_commission,
        name='my_commission'
    ),
    ]