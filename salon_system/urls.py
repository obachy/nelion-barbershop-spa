from django.contrib import admin
from django.urls import path, include
from salon.views import RoleBasedLoginView, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('', include('salon.urls')),
]