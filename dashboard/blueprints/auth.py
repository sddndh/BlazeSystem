"""
dashboard/blueprints/auth.py
نقل مباشر لمسارات / و /callback من main.py — لا تغيير في المنطق.
"""
import requests
from flask import Blueprint, redirect, request, session
from config import Config

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def home():
    # ─── نفس صفحة الـ home من main.py ────────────────────────────────────
    return f'''
    <body style="background-color:#121212; color:white; text-align:center;
                 padding-top:100px; font-family:sans-serif;">
        <h1>مرحباً بك في نظام Blaze</h1>
        <a href="{Config.OAUTH_URL}"
           style="background-color:#ff5e00; padding:15px 30px; text-decoration:none;
                  color:white; border-radius:5px; font-weight:bold;
                  display:inline-block; margin-top:20px;">
            تسجيل الدخول بحساب Discord
        </a>
    </body>
    '''


@auth_bp.route('/callback')
def callback():
    # ─── نفس كود الـ callback من main.py ────────────────────────────────
    code = request.args.get('code')
    if not code:
        return "حدث خطأ."

    data = {
        'client_id':     Config.CLIENT_ID,
        'client_secret': Config.CLIENT_SECRET,
        'grant_type':    'authorization_code',
        'code':          code,
        'redirect_uri':  Config.REDIRECT_URI,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post(
        'https://discord.com/api/oauth2/token',
        data=data,
        headers=headers
    )

    if r.status_code != 200:
        return "فشل الربط."

    session['token'] = r.json()['access_token']
    return redirect('/dashboard')
