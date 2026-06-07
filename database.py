"""
database.py — نفس دوال get_db_connection و init_db من main.py الحالي.
"""
import psycopg2
from config import Config


def get_db_connection():
    """نفس الدالة الموجودة حالياً في main.py."""
    return psycopg2.connect(Config.DATABASE_URL)


def init_db():
    """
    تهيئة الجداول — نفس الكود الحالي بالضبط.
    تشتغل مرة واحدة عند بدء البوت.
    """
    if not Config.DATABASE_URL:
        return

    conn = get_db_connection()
    c = conn.cursor()

    # جدول الترحيب (موجود حالياً)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            guild_id    TEXT PRIMARY KEY,
            welcome_msg TEXT
        )
    """)

    # أعمدة قوالب صور الترحيب (تُضاف بأمان للجدول الموجود)
    c.execute("ALTER TABLE settings ADD COLUMN IF NOT EXISTS image_enabled  BOOLEAN DEFAULT FALSE")
    c.execute("ALTER TABLE settings ADD COLUMN IF NOT EXISTS image_title    TEXT    DEFAULT 'أهلاً بك'")
    c.execute("ALTER TABLE settings ADD COLUMN IF NOT EXISTS image_template TEXT    DEFAULT 'carbon'")

    # جدول الأوامر المخصصة (موجود حالياً)
    c.execute("""
        CREATE TABLE IF NOT EXISTS custom_commands (
            guild_id TEXT,
            command  TEXT,
            response TEXT,
            PRIMARY KEY (guild_id, command)
        )
    """)

    # ── جداول الميزات الجديدة (تُضاف بأمان لأن IF NOT EXISTS) ──────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_levels (
            user_id        TEXT NOT NULL,
            guild_id       TEXT NOT NULL,
            xp             INTEGER NOT NULL DEFAULT 0,
            level          INTEGER NOT NULL DEFAULT 0,
            total_messages INTEGER NOT NULL DEFAULT 0,
            last_activity  TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, guild_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS member_activity_log (
            user_id       TEXT NOT NULL,
            guild_id      TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            logged_date   DATE NOT NULL,
            PRIMARY KEY (user_id, guild_id, logged_date)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS phantom_health_scores (
            id          BIGSERIAL PRIMARY KEY,
            guild_id    TEXT NOT NULL,
            score       INTEGER NOT NULL,
            metrics     TEXT NOT NULL DEFAULT '{}',
            recorded_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    conn.commit()
    c.close()
    conn.close()
    print("✅ قاعدة البيانات جاهزة")
