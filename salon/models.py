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

class Service(models.Model):
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
