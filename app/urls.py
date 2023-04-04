from django.contrib import admin
from django.urls import path
from main import views
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('connect/data', views.data),
    path('connect/install', views.install),
    path('connect/uninstall', views.uninstall),
    path('pdf/generate', views.generate_pdf),
    path('pdf/settings', views.load_settings),
    path('pdf/settings2', views.load_settings),
    path('health', views.health)
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
