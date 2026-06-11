from PIL import Image, ImageDraw

_SIZE = 64
_MARGIN = 6


def _circle(color: str) -> Image.Image:
    img = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([_MARGIN, _MARGIN, _SIZE - _MARGIN, _SIZE - _MARGIN], fill=color)
    return img


ICONS: dict[str, Image.Image] = {
    "ready":      _circle("#4CAF50"),
    "recording":  _circle("#F44336"),
    "processing": _circle("#FFC107"),
    "error":      _circle("#9E9E9E"),
}
