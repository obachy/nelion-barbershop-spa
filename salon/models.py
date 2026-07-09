from django.db import models


# =========================
# CLIENT
# =========================

class Client(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name


# =========================
# STAFF
# =========================

class Staff(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    commission = models.IntegerField(default=0)

    def __str__(self):
        return self.name


# =========================
# SERVICE
# =========================
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Service(models.Model):

    department = models.ForeignKey(
    Department,
    on_delete=models.SET_NULL,
    blank=True,
    null=True,
    related_name='services'
    )
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes")

    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    staff = models.ManyToManyField(Staff, blank=True)

    def __str__(self):
        return self.name

# =========================
# APPOINTMENT
# =========================

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('M-Pesa', 'M-Pesa'),
        ('Bank', 'Bank'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')

    def __str__(self):
        return f"{self.client.name} - {self.service.name}"

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    def __str__(self):
        return f"{self.client} - {self.date}"


# =========================
# STAFF ATTENDANCE
# =========================

class StaffAttendance(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.DateField()
    check_in = models.TimeField()
    check_out = models.TimeField(blank=True, null=True)
    is_late = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.staff} - {self.date}"


# =========================
# STAFF PENALTY
# =========================

class StaffPenalty(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    attendance = models.ForeignKey(
        StaffAttendance,
        on_delete=models.CASCADE,
        related_name='penalties'
    )
    amount = models.IntegerField()
    reason = models.CharField(max_length=255)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff} - {self.amount}"
    
class Expense(models.Model):
    TYPE_CHOICES = [
        ('Expense', 'Expense'),
        ('Bill', 'Bill'),
    ]

    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('M-Pesa', 'M-Pesa'),
        ('Bank', 'Bank'),
        ('Other', 'Other'),
    ]

    expense_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Expense')
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Paid')
    expense_date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.expense_type} - {self.title} - {self.amount}"

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
        ('Cancelled', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    invoice_date = models.DateField()
    due_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_amount(self):
        return sum(item.total() for item in self.items.all())

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.invoice_number:
            self.invoice_number = f"INV-{self.id:05d}"
            super().save(update_fields=['invoice_number'])

    def __str__(self):
        return f"{self.invoice_number} - {self.client.name}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return self.description