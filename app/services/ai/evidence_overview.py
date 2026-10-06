"""Render one source image with every located device marked for review."""

import base64
import io
from PIL import Image, ImageDraw, ImageFont


def render_evidence_overview(image_path, devices):
    """Return a data URL and legend; unlocated items remain explicitly unmarked."""
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    width, height = image.size
    draw = ImageDraw.Draw(image)
    legend = []
    for device in devices:
        box = getattr(device, "box_2d", None)
        if not box or len(box) != 4:
            continue
        ymin, xmin, ymax, xmax = box
        if not (0 <= xmin < xmax <= 1000 and 0 <= ymin < ymax <= 1000):
            continue
        rectangle = (round(xmin * width / 1000), round(ymin * height / 1000),
                     round(xmax * width / 1000), round(ymax * height / 1000))
        number = len(legend) + 1
        draw.rectangle(rectangle, outline="#d91c32", width=max(2, width // 500))
        x, y = rectangle[:2]
        label = str(number)
        label_width = 8 + 8 * len(label)
        draw.rectangle((x, max(0, y - 18), x + label_width, y), fill="#d91c32")
        draw.text((x + 4, max(0, y - 17)), label, fill="white", font=ImageFont.load_default())
        legend.append({"number": number, "tag": getattr(device, "tag", "") or "",
                       "name": getattr(device, "name", "") or "", "box_2d": list(box)})
    if not legend:
        return None
    image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return {"image": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode(),
            "legend": legend, "marked_count": len(legend), "total_count": len(devices)}
