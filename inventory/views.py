import csv
import io
import os

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import (
    AssetForm,
    CellphoneSpecForm,
    CustomUserCreationForm,
    LaptopSpecForm,
    MonitorSpecForm,
    OtherSpecForm,
)
from .models import Asset, AuditLog, CellphoneSpec, LaptopSpec, MonitorSpec, OtherSpec

User = get_user_model()


# Role decorator handling role checks and superusers
def role_required(allowed_roles=[]):
    def decorator(view_func):
        def wrap(request, *args, **kwargs):
            if request.user.is_authenticated and (request.user.role in allowed_roles or request.user.is_superuser):
                return view_func(request, *args, **kwargs)
            return HttpResponse("Unauthorized Access", status=403)

        return wrap

    return decorator


@login_required
def user_logout(request):
    logout(request)
    return redirect("login")


@login_required
def asset_list(request):
    """
    Main Asset Inventory Dashboard with dynamic spec modal handling,
    timezone-aware timestamps, latest audit log tracking, scan file URLs,
    and TAG-based QR code generation.
    """
    # Validate both forms before creating any database records.
    if request.method == "POST" and "add_asset_submit" in request.POST:
        if not (request.user.is_superuser or request.user.role in ["ADMIN", "IT"]):
            return HttpResponse("Unauthorized Access", status=403)

        asset_form = AssetForm(request.POST)
        spec_form_classes = {
            "LAPTOP": LaptopSpecForm,
            "MONITOR": MonitorSpecForm,
            "CELLPHONE": CellphoneSpecForm,
            "OTHERS": OtherSpecForm,
        }
        spec_form_class = spec_form_classes.get(request.POST.get("asset_type"))
        spec_form = spec_form_class(request.POST) if spec_form_class else None

        asset_valid = asset_form.is_valid()
        spec_valid = spec_form.is_valid() if spec_form is not None else False

        if asset_valid and spec_valid:
            with transaction.atomic():
                asset = asset_form.save(commit=False)
                asset.created_by = request.user
                asset.updated_by = request.user
                # Asset.save() already generates the QR code.
                asset.save()

                spec = spec_form.save(commit=False)
                spec.asset = asset
                spec.save()

            messages.success(request, f"Asset '{asset.company_tag}' added successfully!")
            return redirect("asset_list")

        for form in (asset_form, spec_form):
            if form is None:
                continue
            for field_name, errors in form.errors.items():
                field = form.fields.get(field_name)
                label = (field.label or field_name) if field is not None else "Asset"
                for error in errors:
                    messages.error(request, f"{label}: {error}")

    query = request.GET.get("q", "")

    # Use select_related and prefetch_related to optimize query performance
    assets = (
        Asset.objects.all()
        .select_related("created_by", "updated_by")
        .prefetch_related("audit_logs__auditor")
        .order_by("-date_added")
    )

    if query:
        assets = assets.filter(
            Q(company_tag__icontains=query) | Q(serial_number__icontains=query) | Q(unit_name__icontains=query)
        )

    # Fetch unique assigned people for the accountability dropdown form
    unique_assignees = (
        Asset.objects.exclude(assigned_to__isnull=True)
        .exclude(assigned_to="")
        .values_list("assigned_to", flat=True)
        .distinct()
        .order_by("assigned_to")
    )

    # Build a dictionary mapping each assignee to their uploaded scan URL
    assignee_data = []
    for person in unique_assignees:
        asset_with_scan = (
            Asset.objects.filter(assigned_to=person, accountability_scan__isnull=False)
            .exclude(accountability_scan="")
            .first()
        )

        scan_url = asset_with_scan.accountability_scan.url if asset_with_scan else ""
        assignee_data.append({"name": person, "scan_url": scan_url})

    # Attach forms and latest audit log to each asset instance for template rendering
    for asset in assets:
        asset.form = AssetForm(instance=asset)
        asset.latest_audit = asset.audit_logs.all().order_by("-audit_date").first()

        if asset.asset_type == "LAPTOP" and hasattr(asset, "laptop_spec"):
            asset.spec_form = LaptopSpecForm(instance=asset.laptop_spec)
        elif asset.asset_type == "MONITOR" and hasattr(asset, "monitor_spec"):
            asset.spec_form = MonitorSpecForm(instance=asset.monitor_spec)
        elif asset.asset_type == "CELLPHONE" and hasattr(asset, "cellphone_spec"):
            asset.spec_form = CellphoneSpecForm(instance=asset.cellphone_spec)
        elif asset.asset_type == "OTHERS" and hasattr(asset, "other_spec"):
            asset.spec_form = OtherSpecForm(instance=asset.other_spec)

    # AJAX Live Search Support
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        data = []
        for asset in assets:
            qr_url = asset.qr_code.url if asset.qr_code else ""
            scan_url = asset.accountability_scan.url if asset.accountability_scan else ""

            created_user = (
                asset.created_by.get_full_name() or asset.created_by.username if asset.created_by else "System"
            )
            updated_user = (
                asset.updated_by.get_full_name() or asset.updated_by.username if asset.updated_by else "System"
            )

            # Format timezone-aware timestamps
            local_created = timezone.localtime(asset.date_added).strftime("%Y-%m-%d %H:%M") if asset.date_added else ""
            local_updated = (
                timezone.localtime(asset.date_updated).strftime("%Y-%m-%d %H:%M") if asset.date_updated else ""
            )

            # Latest audit information
            latest_log = asset.audit_logs.all().order_by("-audit_date").first()
            latest_remark = latest_log.remarks if latest_log else None
            latest_auditor = (
                (latest_log.auditor.get_full_name() or latest_log.auditor.username)
                if latest_log and latest_log.auditor
                else ""
            )
            latest_audit_date = (
                timezone.localtime(latest_log.audit_date).strftime("%Y-%m-%d %H:%M") if latest_log else ""
            )

            data.append(
                {
                    "id": asset.id,
                    "unit_name": asset.unit_name,
                    "company_tag": asset.company_tag,
                    "serial_number": asset.serial_number,
                    "status": asset.status,
                    "status_display": asset.get_status_display(),
                    "assigned_to": asset.assigned_to or "Unassigned",
                    "date_added": f"{created_user} ({local_created})",
                    "date_updated": f"{updated_user} ({local_updated})",
                    "qr_code_url": qr_url,
                    "accountability_scan_url": scan_url,
                    "latest_remark": latest_remark,
                    "latest_auditor": latest_auditor,
                    "latest_audit_date": latest_audit_date,
                }
            )
        return JsonResponse({"assets": data})

    return render(
        request,
        "asset_list.html",
        {
            "assets": assets,
            "query": query,
            "unique_assignees": unique_assignees,
            "assignee_data": assignee_data,
        },
    )


@login_required
@role_required(allowed_roles=["ADMIN", "IT"])
def edit_asset(request, pk):
    if request.method != "POST":
        return redirect("asset_list")

    spec_types = {
        "LAPTOP": (LaptopSpecForm, LaptopSpec),
        "MONITOR": (MonitorSpecForm, MonitorSpec),
        "CELLPHONE": (CellphoneSpecForm, CellphoneSpec),
        "OTHERS": (OtherSpecForm, OtherSpec),
    }

    with transaction.atomic():
        asset = get_object_or_404(
            Asset.objects.select_for_update(),
            pk=pk,
        )

        asset_form = AssetForm(request.POST, instance=asset)

        # Choose specifications using the submitted asset type.
        selected = spec_types.get(request.POST.get("asset_type"))
        spec_form = None
        selected_model = None

        if selected:
            spec_form_class, selected_model = selected
            existing_spec = selected_model.objects.filter(asset=asset).first()

            spec_form = spec_form_class(
                request.POST,
                instance=existing_spec,
            )

        asset_valid = asset_form.is_valid()
        spec_valid = spec_form.is_valid() if spec_form is not None else False

        if asset_valid and spec_valid:
            updated_asset = asset_form.save(commit=False)
            updated_asset.updated_by = request.user
            updated_asset.save()

            spec = spec_form.save(commit=False)
            spec.asset = updated_asset
            spec.save()

            # Remove specifications belonging to other asset types.
            for _, spec_model in spec_types.values():
                if spec_model is not selected_model:
                    spec_model.objects.filter(asset=updated_asset).delete()

            messages.success(
                request,
                f"Asset '{updated_asset.company_tag}' updated successfully!",
            )
        else:
            for form in (asset_form, spec_form):
                if form is None:
                    continue

                for field_name, errors in form.errors.items():
                    field = form.fields.get(field_name)
                    label = (field.label or field_name) if field is not None else "Asset"

                    for error in errors:
                        messages.error(
                            request,
                            f"{label}: {error}",
                        )

    return redirect("asset_list")


@login_required
@role_required(allowed_roles=["ADMIN", "IT"])
def delete_asset(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == "POST":
        tag = asset.company_tag
        asset.delete()
        messages.warning(request, f"Asset '{tag}' has been deleted.")
    return redirect("asset_list")


@login_required
@role_required(allowed_roles=["ADMIN"])
def create_user(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(request, f"User account '{new_user.username}' created successfully!")
        else:
            messages.error(request, "Failed to create user.")
    return redirect("asset_list")


@login_required
@role_required(allowed_roles=["ADMIN", "AUDIT"])
def audit_scan(request):
    asset = None
    scanned_tag = ""

    if request.method == "POST":
        scanned_input = request.POST.get("company_tag", "").strip()
        remarks = request.POST.get("remarks", "").strip()

        # Parse new QR format: "<CompanyTag> | <SerialNumber> | <UnitName>"
        tag_to_search = scanned_input
        if " | " in scanned_input:
            tag_to_search = scanned_input.split(" | ")[0].strip()

        scanned_tag = tag_to_search

        # 1. Search for asset
        try:
            asset = Asset.objects.get(company_tag=tag_to_search)
        except Asset.DoesNotExist:
            messages.error(request, f"No asset found matching Company Tag: '{tag_to_search}'")
            return render(request, "inventory/audit_scan.html", {"scanned_tag": scanned_tag})

        # 2. Save audit log if remarks were submitted
        if "submit_audit" in request.POST:
            if remarks:
                AuditLog.objects.create(asset=asset, auditor=request.user, remarks=remarks)
                messages.success(request, f"Audit successfully logged for asset '{asset.company_tag}'!")
                return redirect("audit_scan")
            else:
                messages.error(request, "Please enter remarks before submitting the audit.")

    return render(request, "inventory/audit_scan.html", {"asset": asset, "scanned_tag": scanned_tag})


# --------------------------------------------------
# 1. CSV EXPORT
# --------------------------------------------------
@login_required
@role_required(allowed_roles=["ADMIN", "AUDIT"])
def export_csv(request):
    current_time = timezone.localtime(timezone.now())
    filename_timestamp = current_time.strftime("%Y-%m-%d_%H%M")
    display_timestamp = current_time.strftime("%Y-%m-%d %H:%M")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="inventory_audit_report_{filename_timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Company Tag",
            "Unit Name",
            "Serial Number",
            "Status",
            "Assigned To",
            "Created By",
            "Date Added",
            "Updated By",
            "Date Updated",
            "Latest Audit Remarks",
        ]
    )

    assets = Asset.objects.all().select_related("created_by", "updated_by").order_by("-date_added")

    for asset in assets:
        created_user = asset.created_by.get_full_name() or asset.created_by.username if asset.created_by else "System"
        updated_user = asset.updated_by.get_full_name() or asset.updated_by.username if asset.updated_by else "System"

        local_date_added = timezone.localtime(asset.date_added).strftime("%Y-%m-%d %H:%M") if asset.date_added else ""
        local_date_updated = (
            timezone.localtime(asset.date_updated).strftime("%Y-%m-%d %H:%M") if asset.date_updated else ""
        )

        latest_audit = asset.audit_logs.order_by("-audit_date").first()
        latest_remark = latest_audit.remarks if latest_audit else "No Remarks"

        writer.writerow(
            [
                asset.company_tag,
                asset.unit_name,
                asset.serial_number,
                asset.get_status_display(),
                asset.assigned_to or "Unassigned",
                created_user,
                local_date_added,
                updated_user,
                local_date_updated,
                latest_remark,
            ]
        )

    writer.writerow([])
    writer.writerow(["Audited By Signature:", request.user.get_full_name() or request.user.username])
    writer.writerow(["Date:", display_timestamp])
    writer.writerow(["Assisted By Signature:", "___________________"])
    writer.writerow(["Date:", "___________________"])

    return response


# --------------------------------------------------
# 2. PDF EXPORT
# --------------------------------------------------
@login_required
@role_required(allowed_roles=["ADMIN", "AUDIT"])
def export_pdf(request):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#2C3E50"),
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#7F8C8D"),
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#2C3E50"),
    )
    header_cell_style = ParagraphStyle(
        "TableHeaderCell",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    current_time = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M")

    elements.append(Paragraph("Company Asset Inventory Audit Report", title_style))
    elements.append(
        Paragraph(
            f"Generated on: {current_time} | Auditor: {request.user.get_full_name() or request.user.username}",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        Paragraph("Tag", header_cell_style),
        Paragraph("Unit Name", header_cell_style),
        Paragraph("Serial No.", header_cell_style),
        Paragraph("Status", header_cell_style),
        Paragraph("Assigned To", header_cell_style),
        Paragraph("Created By", header_cell_style),
        Paragraph("Updated By", header_cell_style),
        Paragraph("Latest Audit Remarks", header_cell_style),
    ]

    table_data = [headers]
    assets = Asset.objects.all().select_related("created_by", "updated_by").order_by("-date_added")

    for asset in assets:
        created_user = asset.created_by.get_full_name() or asset.created_by.username if asset.created_by else "System"
        updated_user = asset.updated_by.get_full_name() or asset.updated_by.username if asset.updated_by else "System"
        latest_audit = asset.audit_logs.order_by("-audit_date").first()
        latest_remark = latest_audit.remarks if latest_audit else "No Remarks"

        table_data.append(
            [
                Paragraph(asset.company_tag, cell_style),
                Paragraph(asset.unit_name, cell_style),
                Paragraph(asset.serial_number, cell_style),
                Paragraph(asset.get_status_display(), cell_style),
                Paragraph(asset.assigned_to or "Unassigned", cell_style),
                Paragraph(created_user, cell_style),
                Paragraph(updated_user, cell_style),
                Paragraph(latest_remark, cell_style),
            ]
        )

    col_widths = [70, 90, 90, 75, 90, 85, 85, 135]
    asset_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    asset_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#212529")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
            ]
        )
    )

    elements.append(asset_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Signature Block
    sig_cell_style = ParagraphStyle("SigCell", parent=styles["Normal"], fontSize=9, leading=12)
    sig_data = [
        [
            Paragraph(
                "<b>Audited By:</b> " + (request.user.get_full_name() or request.user.username),
                sig_cell_style,
            ),
            Paragraph("<b>Assisted By:</b> ___________________________", sig_cell_style),
        ],
        [
            Paragraph("<b>Signature:</b> ___________________________", sig_cell_style),
            Paragraph("<b>Signature:</b> ___________________________", sig_cell_style),
        ],
        [
            Paragraph("<b>Date:</b> " + current_time.split(" ")[0], sig_cell_style),
            Paragraph("<b>Date:</b> ___________________________", sig_cell_style),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[360, 360])
    sig_table.setStyle(TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)

    filename_timestamp = current_time.replace(" ", "_").replace(":", "")
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="inventory_audit_report_{filename_timestamp}.pdf"'

    return response


@login_required
@role_required(allowed_roles=["ADMIN"])
def user_list(request):
    """
    Displays all registered system accounts and handles user account creation, status toggling, and editing.
    """
    # 1. Handle POST submission for creating a new user account
    if request.method == "POST" and "create_user_submit" in request.POST:
        user_creation_form = CustomUserCreationForm(request.POST)
        if user_creation_form.is_valid():
            new_user = user_creation_form.save()
            messages.success(request, f"User account '{new_user.username}' created successfully!")
            return redirect("user_list")
        else:
            messages.error(request, "Failed to create user account. Please check the form errors.")
    else:
        user_creation_form = CustomUserCreationForm()

    # 2. Handle POST submission for toggling user active/inactive status
    if request.method == "POST" and "toggle_status_id" in request.POST:
        target_user = get_object_or_404(User, id=request.POST.get("toggle_status_id"))
        if target_user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            target_user.is_active = not target_user.is_active
            target_user.save()
            status_str = "activated" if target_user.is_active else "deactivated"
            messages.success(request, f"User account '{target_user.username}' has been {status_str}.")
        return redirect("user_list")

    # 3. Handle POST submission for editing a user account
    if request.method == "POST" and "edit_user_id" in request.POST:
        user_id = request.POST.get("edit_user_id")
        target_user = get_object_or_404(User, id=user_id)

        target_user.username = request.POST.get("username")
        target_user.first_name = request.POST.get("first_name", "")
        target_user.last_name = request.POST.get("last_name", "")
        target_user.email = request.POST.get("email", "")
        target_user.role = request.POST.get("role")

        new_password = request.POST.get("new_password")
        if new_password:
            target_user.set_password(new_password)

        target_user.save()
        messages.success(request, f"User account '{target_user.username}' updated successfully!")
        return redirect("user_list")

    users = User.objects.all().order_by("-date_joined")
    return render(
        request,
        "inventory/user_list.html",
        {"users": users, "user_creation_form": user_creation_form},
    )


# 1. GENERATE ACCOUNTABILITY PDF FOR MULTIPLE ASSETS BY ASSIGNEE
@login_required
@role_required(allowed_roles=["ADMIN", "IT"])
@require_POST
def generate_accountability_pdf(request):
    assignee = request.POST.get("assigned_to", "Unassigned")

    # Query database directly for assets assigned to this person
    # Change 'YourAssetModel', 'assigned_to', 'unit_name', and 'serial_number' to match your actual model fields
    assets_queryset = Asset.objects.filter(assigned_to=assignee)

    assets_list = []
    for asset in assets_queryset:
        assets_list.append(
            {"unitName": getattr(asset, "unit_name", str(asset)), "serialNumber": getattr(asset, "serial_number", "")}
        )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    # Title & Header
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, leading=20, alignment=1)
    elements.append(Paragraph("IT ASSET ACCOUNTABILITY FORM", title_style))
    elements.append(Spacer(1, 0.25 * inch))

    # Form Info Body
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    header_content = f"""
    This document serves as formal confirmation of the issuance and receipt of company IT hardware.<br/><br/>
    <b>Assignee / Employee:</b> {assignee}<br/>
    <b>Date Issued:</b> {timezone.now().strftime("%Y-%m-%d")}<br/>
    """
    elements.append(Paragraph(header_content, body_style))
    elements.append(Spacer(1, 0.15 * inch))

    # Assets Table Header and Rows
    table_data = [
        [
            Paragraph("<b>#</b>", body_style),
            Paragraph("<b>Unit Name</b>", body_style),
            Paragraph("<b>Serial Number</b>", body_style),
        ]
    ]

    for index, item in enumerate(assets_list, start=1):
        table_data.append(
            [
                Paragraph(str(index), body_style),
                Paragraph(item.get("unitName", ""), body_style),
                Paragraph(item.get("serialNumber", ""), body_style),
            ]
        )

    # Build ReportLab Table
    asset_table = Table(table_data, colWidths=[40, 250, 250])
    asset_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ]
        )
    )

    elements.append(asset_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Terms & Conditions Paragraph
    terms = (
        "By signing below, the employee acknowledges receipt of the asset(s) listed above in good working "
        "condition and agrees to follow company asset security and usage policies."
    )
    elements.append(Paragraph(terms, body_style))
    elements.append(Spacer(1, 0.4 * inch))

    # Signature Block Table
    sig_data = [
        [
            Paragraph(
                f"<b>Issued By (IT Dept):</b> {request.user.get_full_name() or request.user.username}",
                body_style,
            ),
            Paragraph(f"<b>Received By:</b> {assignee}", body_style),
        ],
        [
            Paragraph("Signature: _______________________", body_style),
            Paragraph("Signature: _______________________", body_style),
        ],
        [
            Paragraph(f"Date: {timezone.now().strftime('%Y-%m-%d')}", body_style),
            Paragraph("Date: _______________________", body_style),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)

    clean_assignee = "".join(c for c in assignee if c.isalnum() or c in (" ", "_")).rstrip().replace(" ", "_")
    filename = f"Accountability_Form_{clean_assignee}.pdf"

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# 2. UPLOAD SCANNED ACCOUNTABILITY PDF
@login_required
@role_required(allowed_roles=["ADMIN", "IT"])
def upload_accountability_scan(request, assignee):
    # Fetch all assets belonging to this assignee
    assets = Asset.objects.filter(assigned_to=assignee)
    if not assets.exists():
        return JsonResponse({"status": "error", "message": "No assets found for this assignee."}, status=404)

    if request.method == "POST" and request.FILES.get("accountability_scan"):
        uploaded_file = request.FILES["accountability_scan"]

        # Clean up existing scan file from storage if it exists on the first asset
        existing_asset = assets.first()
        if existing_asset and existing_asset.accountability_scan:
            if os.path.isfile(existing_asset.accountability_scan.path):
                os.remove(existing_asset.accountability_scan.path)

        # Format filename cleanly based strictly on the assignee's name
        file_extension = os.path.splitext(uploaded_file.name)[1]
        safe_name = assignee.replace(" ", "_")
        uploaded_file.name = f"Accountability_Form_{safe_name}{file_extension}"

        scan_url = None
        for asset in assets:
            asset.accountability_scan = uploaded_file
            asset.save()  # Saves to database permanently
            if not scan_url:
                scan_url = asset.accountability_scan.url

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "success", "message": "Scan uploaded successfully!", "scan_url": scan_url})

    return JsonResponse({"status": "error", "message": "Invalid request."}, status=400)
