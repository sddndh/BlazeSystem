"""
main.py — نقطة الإطلاق.
نفس أسلوب threading.Thread الحالي — يعمل على Render بدون تغيير.
"""
import logging
import os
import threading

from app import create_app
from bot.core import run_bot


def run_flask():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    port = int(os.environ.get("PORT", 5000))
    create_app().run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()   # البوت يشتغل في الـ main thread (نفس الأسلوب الحالي)
