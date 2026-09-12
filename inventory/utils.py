import io
import math
from PIL import Image, ImageDraw, ImageFont
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Asset
from .views import role_required

@login_required
@role_required(allowed_roles=['ADMIN', 'IT'])
def export_qr_grid_png(request):
    """
    Exports all asset QR codes into a single downloadable PNG grid image formatted as:
    <CompanyTag>   <CompanyTag>   <CompanyTag>   <CompanyTag>
      <QRCode>       <QRCode>       <QRCode>       <QRCode>
    """
    assets = Asset.objects.filter(qr_code__isnull=False).exclude(qr_code='')

    if not assets.exists():
        return HttpResponse("No assets with QR codes found to export.", status=404)

    # Grid & Item Layout Configurations
    COLUMNS = 4
    ROWS = math.ceil(assets.count() / COLUMNS)
    
    CARD_WIDTH = 240
    CARD_HEIGHT = 280
    PADDING = 20
    HEADER_MARGIN = 40  # Extra top margin for page title

    # Calculate overall Canvas Dimensions
    canvas_width = (COLUMNS * CARD_WIDTH) + ((COLUMNS + 1) * PADDING)
    canvas_height = (ROWS * CARD_HEIGHT) + ((ROWS + 1) * PADDING) + HEADER_MARGIN

    # Create white canvas
    canvas = Image.new('RGB', (canvas_width, canvas_height), color='white')
    draw = ImageDraw.Draw(canvas)

    # Load system font (falls back to PIL default if truetype isn't available)
    try:
        font_tag = ImageFont.truetype("arial.ttf", 16)
        font_header = ImageFont.truetype("arialbd.ttf", 20)
    except IOError:
        font_tag = ImageFont.load_default()
        font_header = ImageFont.load_default()

    # Draw Header Title
    draw.text((PADDING, 15), "COMPANY ASSET QR TAGS SHEET", fill="black", font=font_header)

    # Render each QR card onto the grid
    for index, asset in enumerate(assets):
        row = index // COLUMNS
        col = index % COLUMNS

        # Calculate bounding coordinates for this item card
        x_offset = PADDING + col * (CARD_WIDTH + PADDING)
        y_offset = HEADER_MARGIN + PADDING + row * (CARD_HEIGHT + PADDING)

        # 1. Draw CompanyTag Text Centered at Top of Card
        tag_text = str(asset.company_tag)
        bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
        text_width = bbox[2] - bbox[0]
        text_x = x_offset + (CARD_WIDTH - text_width) // 2
        text_y = y_offset + 10
        draw.text((text_x, text_y), tag_text, fill="black", font=font_tag)

        # 2. Load and Paste the Asset QR Code Image below CompanyTag
        try:
            asset_qr = Image.open(asset.qr_code.path).convert("RGB")
            asset_qr = asset_qr.resize((180, 180), Image.Resampling.LANCZOS)
            
            # Center QR image inside the item card
            qr_x = x_offset + (CARD_WIDTH - 180) // 2
            qr_y = y_offset + 45
            canvas.paste(asset_qr, (qr_x, qr_y))
        except Exception:
            # Handle missing file safely
            draw.text((x_offset + 20, y_offset + 100), "[QR Missing]", fill="red", font=font_tag)

        # Optional: Light border card outline around each tag box
        draw.rectangle(
            [x_offset, y_offset, x_offset + CARD_WIDTH, y_offset + CARD_HEIGHT],
            outline="#D3D3D3",
            width=1
        )

    # Stream generated Image buffer to HTTP Response
    buffer = io.BytesIO()
    canvas.save(buffer, format='PNG')
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Content-Disposition'] = 'attachment; filename="Company_Asset_QRCodes_Sheet.png"'
    return response
