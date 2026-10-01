from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from salon.views import RoleBasedLoginView, logout_view, quick_task_sale

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', RoleBasedLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('', include('salon.urls')),
    path('quick-task/', quick_task_sale, name='quick_task_sale'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
