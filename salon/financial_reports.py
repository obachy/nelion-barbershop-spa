from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from .models import Appointment, Expense, QuickTaskCommission, QuickTaskSale


def is_admin_or_manager(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name='Admin').exists()
        or user.groups.filter(name='Manager').exists()
    )


@login_required
@user_passes_test(is_admin_or_manager)
def financial_report(request):
    today = timezone.localdate()

    selected_month = int(request.GET.get('month') or today.month)
    selected_year = int(request.GET.get('year') or today.year)

    # Financial period matches payroll/commission:
    # previous month 28th -> selected month 27th
    period_end = date(selected_year, selected_month, 27)

    if selected_month == 1:
        period_start = date(selected_year - 1, 12, 28)
    else:
        period_start = date(selected_year, selected_month - 1, 28)

    # -------------------------
    # SALES
    # -------------------------
    appointments = Appointment.objects.filter(
        status='Completed',
        approval_status='Approved',
        date__range=[period_start, period_end],
    ).select_related('service')

    appointment_sales = appointments.aggregate(
        total=Sum('service__price')
    )['total'] or Decimal('0')

    quick_tasks = QuickTaskSale.objects.filter(
        status='Completed',
        approval_status='Approved',
        created_at__date__range=[period_start, period_end],
    )

    quick_task_sales = quick_tasks.aggregate(
        total=Sum('sale_amount')
    )['total'] or Decimal('0')

    appointment_sales = Decimal(str(appointment_sales))
    quick_task_sales = Decimal(str(quick_task_sales))
    total_sales = appointment_sales + quick_task_sales

    # -------------------------
    # STAFF COMMISSION
    # -------------------------
    appointment_commission = Decimal('0')

    for appointment in appointments:
        service_price = Decimal(str(appointment.service.price or 0))
        commission_percent = Decimal(
            str(appointment.service.commission_percent or 0)
        )
        commission_amount = Decimal(
            str(appointment.service.commission_amount or 0)
        )

        if commission_amount > 0:
            earned_commission = commission_amount
        else:
            earned_commission = (
                service_price * commission_percent
            ) / Decimal('100')

        appointment_commission += earned_commission

    quick_task_commission = QuickTaskCommission.objects.filter(
        quick_task__status='Completed',
        quick_task__approval_status='Approved',
        quick_task__created_at__date__range=[period_start, period_end],
    ).aggregate(
        total=Sum('commission_amount')
    )['total'] or Decimal('0')

    quick_task_commission = Decimal(str(quick_task_commission))

    total_commission = (
        appointment_commission + quick_task_commission
    )

    # -------------------------
    # EXPENSES
    # Only paid expenses/bills reduce realised net profit.
    # -------------------------
    paid_expenses = Expense.objects.filter(
        status='Paid',
        expense_date__range=[period_start, period_end],
    )

    total_expenses = paid_expenses.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    total_expenses = Decimal(str(total_expenses))

    unpaid_bills = Expense.objects.filter(
        expense_type='Bill',
        status='Unpaid',
        expense_date__range=[period_start, period_end],
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    unpaid_bills = Decimal(str(unpaid_bills))

    # -------------------------
    # NET PROFIT
    # -------------------------
    net_profit = total_sales - total_commission - total_expenses

    months = [
        (1, 'January'), (2, 'February'), (3, 'March'),
        (4, 'April'), (5, 'May'), (6, 'June'),
        (7, 'July'), (8, 'August'), (9, 'September'),
        (10, 'October'), (11, 'November'), (12, 'December'),
    ]

    years = range(today.year - 2, today.year + 2)

    return render(request, 'financial_report.html', {
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': months,
        'years': years,
        'period_start': period_start,
        'period_end': period_end,

        'appointment_sales': appointment_sales,
        'quick_task_sales': quick_task_sales,
        'total_sales': total_sales,

        'appointment_commission': appointment_commission,
        'quick_task_commission': quick_task_commission,
        'total_commission': total_commission,

        'total_expenses': total_expenses,
        'unpaid_bills': unpaid_bills,
        'net_profit': net_profit,

        'is_admin': (
            request.user.is_superuser
            or request.user.groups.filter(name='Admin').exists()
        ),
        'is_manager': request.user.groups.filter(name='Manager').exists(),
        'is_staff': request.user.groups.filter(name='Staff').exists(),
    })
