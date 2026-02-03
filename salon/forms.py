from django import forms
from .models import Client, Staff, Service, Appointment, Client, StaffAttendance, StaffLeave, StaffPenalty


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['client', 'service', 'staff', 'date', 'time']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
           # 'status': forms.Select(attrs={'class': 'form-control'}),
        }


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'price', 'duration']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control'}),
        }
class ClientBookingForm(forms.Form):
    name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20)
    email = forms.EmailField(required=False)

    service = forms.ModelChoiceField(queryset=Service.objects.all())
    staff = forms.ModelChoiceField(queryset=Staff.objects.none())

class StaffAttendanceForm(forms.ModelForm):
    class Meta:
        model = StaffAttendance
        fields = '__all__'


class StaffLeaveForm(forms.ModelForm):
    class Meta:
        model = StaffLeave
        fields = '__all__'


class StaffPenaltyForm(forms.ModelForm):
    class Meta:
        model = StaffPenalty
        fields = '__all__'
   # staff = forms.ModelChoiceField(queryset=Staff.objects.all())
   # date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
   # time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
