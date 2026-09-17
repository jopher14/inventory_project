from django.contrib.auth import views as auth_views
from django.urls import path

from . import utils, views
from .forms import CustomAuthenticationForm

urlpatterns = [
    # Authentication Routes
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html", authentication_form=CustomAuthenticationForm
        ),
        name="login",
    ),
    path("logout/", views.user_logout, name="logout"),
    # Core Inventory & Modal Action Routes
    path("", views.asset_list, name="asset_list"),
    path("users/create/", views.create_user, name="create_user"),
    path("asset/<int:pk>/edit/", views.edit_asset, name="edit_asset"),
    path("asset/<int:pk>/delete/", views.delete_asset, name="delete_asset"),
    # Audit & Reporting Routes
    path("audit/scan/", views.audit_scan, name="audit_scan"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
    path("export/qr-grid/", utils.export_qr_grid_png, name="export_qr_grid_png"),
    path("users/", views.user_list, name="user_list"),
    path("asset/accountability/pdf/", views.generate_accountability_pdf, name="generate_accountability_pdf"),
    path(
        "asset/<int:pk>/accountability/upload/",
        views.upload_accountability_scan,
        name="upload_accountability_scan",
    ),
]
