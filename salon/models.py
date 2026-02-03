from django.db import models
from datetime import time

class Client(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Staff(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    commission = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes")

    def __str__(self):
        return self.name


class Appointment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Completed', 'Completed'),
            ('Cancelled', 'Cancelled'),
        ],
        default='Pending'
    )

    def __str__(self):
        return f"{self.client} - {self.date} {self.time}"

class StaffAttendance(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.DateField()
    check_in = models.TimeField()
    check_out = models.TimeField(null=True, blank=True)

    is_late = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.staff.name} - {self.date}"

class StaffLeave(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.staff.name} Leave ({self.start_date} → {self.end_date})"

class StaffPenalty(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.DateField()
    reason = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.staff.name} - {self.amount}"
