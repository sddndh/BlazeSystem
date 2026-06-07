"""
bot/utils/welcome_image.py
مولّد بطاقات الترحيب — يدعم العربية والإنجليزية وعدة قوالب.

⚠️ النص العربي يحتاج معالجتين قبل الرسم:
   1. arabic_reshaper → وصل الحروف ببعضها
   2. python-bidi     → ضبط الاتجاه (يمين ← يسار)
   بدونهما تظهر الحروف مقطّعة ومعكوسة.

المكتبات المطلوبة (أضفها لـ requirements.txt):
   Pillow · arabic-reshaper · python-bidi · aiohttp
"""
from __future__ import annotations

import io
import os
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import arabic_reshaper
from bidi.algorithm import get_display


# ── الهوية البصرية ────────────────────────────────────────────────────────────
CARBON  = (13, 13, 13)
CARBON2 = (20, 20, 24)
ORANGE  = (255, 94, 0)
WHITE   = (240, 237, 232)
GRAY    = (150, 150, 150)
BORDER  = (42, 42, 42)

# مسار الخط — استخدم خطاً يدعم العربية (مثل Cairo أو Amiri).
# ضع ملف الخط في bot/assets/fonts/ ثم عدّل المسار.
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
FONT_BOLD    = os.path.join(FONT_DIR, "Cairo-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "Cairo-Regular.ttf")


def _ar(text: str) -> str:
    """يعالج النص العربي (تشكيل + اتجاه). آمن مع الإنجليزي أيضاً."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        # fallback آمن لو الخط مفقود
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size
        )


async def _fetch_avatar(url: str, size: int) -> Image.Image:
    """يحمّل صورة العضو ويقصّها دائرية."""
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url) as resp:
            data = await resp.read()

    avatar = Image.open(io.BytesIO(data)).convert("RGB").resize((size, size))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(avatar, (0, 0), mask)
    return out


# ── القوالب ───────────────────────────────────────────────────────────────────

async def generate_welcome_card(
    *,
    avatar_url: str,
    username: str,
    member_count: int,
    guild_name: str,
    title: str = "أهلاً بك",
    template: str = "carbon",
) -> io.BytesIO:
    """
    يُنشئ بطاقة ترحيب ويُعيدها كـ BytesIO جاهزة للإرسال في discord.File.

    template: "carbon" (افتراضي) | "minimal" | "glow"
    """
    W, H = 1000, 350
    img = Image.new("RGB", (W, H), CARBON)
    draw = ImageDraw.Draw(img)

    # خلفية: خطوط كربون قطرية
    for i in range(-H, W, 14):
        draw.line([(i, 0), (i + H, H)], fill=CARBON2, width=1)

    # توهج برتقالي خلف الأفاتار
    if template in ("carbon", "glow"):
        glow = Image.new("RGB", (W, H), CARBON)
        ImageDraw.Draw(glow).ellipse([60, 60, 340, 340], fill=(60, 24, 0))
        glow = glow.filter(ImageFilter.GaussianBlur(60))
        img = Image.blend(img, glow, 0.6)
        draw = ImageDraw.Draw(img)

    # إطار + شريط برتقالي
    draw.rectangle([0, 0, W - 1, H - 1], outline=BORDER, width=2)
    draw.rectangle([0, 0, 6, H], fill=ORANGE)

    # الأفاتار مع حلقة برتقالية
    AV = 200
    ax, ay = 75, 75
    avatar = await _fetch_avatar(avatar_url, AV)
    ring = Image.new("RGBA", (AV + 16, AV + 16), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([0, 0, AV + 15, AV + 15], outline=ORANGE, width=6)
    img.paste(ring, (ax - 8, ay - 8), ring)
    img.paste(avatar, (ax, ay), avatar)

    # النصوص
    f_title = _load_font(FONT_BOLD, 58)
    f_user  = _load_font(FONT_BOLD, 42)
    f_small = _load_font(FONT_REGULAR, 26)

    tx = 320
    draw.text((tx, 95),  _ar(title), font=f_title, fill=ORANGE)
    draw.text((tx, 165), username,   font=f_user,  fill=WHITE)
    draw.text(
        (tx, 225),
        _ar(f"العضو رقم {member_count}  •  {guild_name}"),
        font=f_small,
        fill=GRAY,
    )
    draw.line([(tx, 165), (tx + 260, 165)], fill=BORDER, width=2)

    # إخراج
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
