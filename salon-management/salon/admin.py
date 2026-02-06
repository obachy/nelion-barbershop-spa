from django.contrib import admin
from .models import Client, Staff, Service, Appointment

admin.site.register(Client)
admin.site.register(Staff)
admin.site.register(Service)
admin.site.register(Appointment)

# Register your models here.
