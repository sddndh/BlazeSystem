"""
config.py — نفس متغيرات البيئة الحالية، لا تغيير في Render.
"""
import os
import urllib.parse


class Config:
    # ── Discord (نفس الأسماء الحالية تماماً) ─────────────────────────────────
    BOT_TOKEN      = os.environ.get("BOT_TOKEN")
    CLIENT_ID      = os.environ.get("CLIENT_ID")
    CLIENT_SECRET  = os.environ.get("CLIENT_SECRET")
    DOMAIN         = os.environ.get("DOMAIN", "http://127.0.0.1:5000")

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL   = os.environ.get("DATABASE_URL")

    # ── Flask ─────────────────────────────────────────────────────────────────
    # ⚠️ مهم: في الكود القديم كانت os.urandom(24) تتجدد كل إعادة تشغيل
    # → هذا يُضيّع sessions المستخدمين. ضع قيمة ثابتة في Render.
    SECRET_KEY     = os.environ.get("FLASK_SECRET_KEY", "blaze-dev-key-change-in-prod")

    # ── Computed ──────────────────────────────────────────────────────────────
    REDIRECT_URI   = f"{DOMAIN}/callback"
    ENCODED_REDIRECT = urllib.parse.quote(REDIRECT_URI, safe='')
    OAUTH_URL      = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={ENCODED_REDIRECT}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
    )
