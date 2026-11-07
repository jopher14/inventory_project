import io
import math

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from PIL import Image, ImageDraw, ImageFont

from .models import Asset
from .views import role_required


@login_required
@role_required(allowed_roles=["ADMIN", "IT"])
@require_POST
def export_qr_grid_png(request):
    """Export the saved QR images for selected assets as a single PNG."""
    selected_ids = set()
    for value in request.POST.getlist("asset_ids"):
        if not (value.isascii() and value.isdecimal() and len(value) <= 19):
            continue

        asset_id = int(value)
        if 0 < asset_id <= 2**63 - 1:
            selected_ids.add(asset_id)

    if not selected_ids:
        messages.warning(request, "Select at least one QR code to export.")
        return redirect("asset_list")

    assets = list(Asset.objects.filter(pk__in=selected_ids, qr_code__isnull=False).exclude(qr_code="").order_by("pk"))

    if not assets:
        messages.warning(request, "The selected assets have no QR codes to export.")
        return redirect("asset_list")

    columns = 4
    rows = math.ceil(len(assets) / columns)
    card_width = 240
    card_height = 280
    padding = 20
    header_margin = 40
    qr_size = 180

    canvas_width = columns * card_width + (columns + 1) * padding
    canvas_height = rows * card_height + (rows + 1) * padding + header_margin

    canvas = Image.new("RGB", (canvas_width, canvas_height), color="white")
    draw = ImageDraw.Draw(canvas)

    try:
        font_tag = ImageFont.truetype("arial.ttf", 16)
        font_header = ImageFont.truetype("arialbd.ttf", 20)
    except OSError:
        font_tag = ImageFont.load_default()
        font_header = ImageFont.load_default()

    draw.text(
        (padding, 15),
        "COMPANY ASSET QR TAGS SHEET",
        fill="black",
        font=font_header,
    )

    for index, asset in enumerate(assets):
        row, column = divmod(index, columns)
        x_offset = padding + column * (card_width + padding)
        y_offset = header_margin + padding + row * (card_height + padding)

        tag = asset.company_tag
        left, _, right, _ = draw.textbbox((0, 0), tag, font=font_tag)
        text_x = x_offset + (card_width - (right - left)) // 2
        draw.text((text_x, y_offset + 10), tag, fill="black", font=font_tag)

        try:
            with asset.qr_code.open("rb") as qr_file, Image.open(qr_file) as image:
                qr_image = image.convert("RGB").resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        except OSError:
            draw.text(
                (x_offset + 20, y_offset + 100),
                "[QR Missing]",
                fill="red",
                font=font_tag,
            )
        else:
            qr_x = x_offset + (card_width - qr_size) // 2
            canvas.paste(qr_image, (qr_x, y_offset + 45))

        draw.rectangle(
            [x_offset, y_offset, x_offset + card_width, y_offset + card_height],
            outline="#D3D3D3",
            width=1,
        )

    with io.BytesIO() as buffer:
        canvas.save(buffer, format="PNG")
        response = HttpResponse(buffer.getvalue(), content_type="image/png")

    response["Content-Disposition"] = 'attachment; filename="Company_Asset_QRCodes_Sheet.png"'
    return response
