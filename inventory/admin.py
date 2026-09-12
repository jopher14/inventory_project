from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Asset, LaptopSpec, MonitorSpec, CellphoneSpec, OtherSpec, AuditLog

# Customizing User Admin to show Roles
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Role Configuration', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Configuration', {'fields': ('role',)}),
    )

admin.site.register(User, CustomUserAdmin)

# Inline models for quick Spec management inside Asset Admin
class LaptopSpecInline(admin.StackedInline):
    model = LaptopSpec

class MonitorSpecInline(admin.StackedInline):
    model = MonitorSpec

class CellphoneSpecInline(admin.StackedInline):
    model = CellphoneSpec

class OtherSpecInline(admin.StackedInline):
    model = OtherSpec

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('company_tag', 'unit_name', 'asset_type', 'status', 'assigned_to', 'date_added')
    search_fields = ('company_tag', 'serial_number', 'unit_name')
    list_filter = ('asset_type', 'status')
    inlines = [LaptopSpecInline, MonitorSpecInline, CellphoneSpecInline, OtherSpecInline]

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('asset', 'auditor', 'audit_date', 'remarks')
    search_fields = ('asset__company_tag', 'auditor__username')
