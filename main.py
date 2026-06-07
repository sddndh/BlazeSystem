import discord
from discord.ext import commands
from flask import Flask, render_template, request, redirect, session
import requests
import threading
import os
import urllib.parse
import psycopg2 # مكتبة قاعدة البيانات السحابية

# ==========================================
# 1. إعدادات السحابة
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
DOMAIN = os.environ.get("DOMAIN", "http://127.0.0.1:5000")
DATABASE_URL = os.environ.get("DATABASE_URL") # رابط القاعدة الجديد

REDIRECT_URI = f"{DOMAIN}/callback"
encoded_redirect = urllib.parse.quote(REDIRECT_URI, safe='')
OAUTH_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={encoded_redirect}&response_type=code&scope=identify%20guilds"

# ==========================================
# 2. إعداد قاعدة البيانات السحابية (PostgreSQL)
# ==========================================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    if not DATABASE_URL: return
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                 guild_id TEXT PRIMARY KEY, 
                 welcome_msg TEXT)''')
    conn.commit()
    c.close()
    conn.close()

# ==========================================
# 3. محرك الموقع (Flask Dashboard)
# ==========================================
app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def home():
    return f'''
    <body style="background-color:#121212; color:white; text-align:center; padding-top:100px; font-family:sans-serif;">
        <h1>مرحباً بك في نظام Blaze</h1>
        <a href="{OAUTH_URL}" style="background-color:#ff5e00; padding:15px 30px; text-decoration:none; color:white; border-radius:5px; font-weight:bold; display:inline-block; margin-top:20px;">تسجيل الدخول بحساب Discord</a>
    </body>
    '''

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return "حدث خطأ في تسجيل الدخول."
    
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    
    if r.status_code != 200: return "فشل الربط مع ديسكورد."
    
    session['token'] = r.json()['access_token']
    return redirect('/dashboard')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'token' not in session: return redirect('/')
    
    h = {'Authorization': f"Bearer {session['token']}"}
    user_guilds = requests.get('https://discord.com/api/users/@me/guilds', headers=h).json()
    
    admin_guilds = [g for g in user_guilds if (int(g.get('permissions', 0)) & 0x8) == 0x8]
    if not admin_guilds: return "لا تملك صلاحيات إدارة في أي سيرفر."
    
    target_guild_id = str(admin_guilds[0]['id'])
    
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        new_msg = request.form.get('welcome_msg', 'حياك الله!')
        # طريقة التحديث والإدخال في PostgreSQL
        c.execute('''INSERT INTO settings (guild_id, welcome_msg) 
                     VALUES (%s, %s) 
                     ON CONFLICT (guild_id) 
                     DO UPDATE SET welcome_msg = EXCLUDED.welcome_msg''', 
                  (target_guild_id, new_msg))
        conn.commit()

    c.execute('SELECT welcome_msg FROM settings WHERE guild_id = %s', (target_guild_id,))
    row = c.fetchone()
    c.close()
    conn.close()
    
    current_msg = row[0] if row else "أهلاً بك في السيرفر، نتمنى لك وقتاً ممتعاً!"
    return render_template('dashboard.html', current_msg=current_msg)

def run_flask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ==========================================
# 4. محرك البوت (Discord.py)
# ==========================================
class BlazeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())

bot = BlazeBot()

@bot.event
async def on_ready():
    init_db() # إنشاء الجداول عند التشغيل
    print("-----------------------------------------")
    print(f"✅ البوت متصل كـ: {bot.user}")
    print(f"🌐 الموقع يعمل على: {DOMAIN}")
    print("-----------------------------------------")

@bot.event
async def on_member_join(member):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT welcome_msg FROM settings WHERE guild_id = %s', (str(member.guild.id),))
    row = c.fetchone()
    c.close()
    conn.close()
    
    welcome_msg = row[0] if row else "أهلاً بك في السيرفر، نتمنى لك وقتاً ممتعاً!"
    
    channel = member.guild.system_channel
    if channel:
        await channel.send(f"👋 {member.mention} | {welcome_msg}")

@bot.event
async def on_message(message):
    if message.author.bot or message.author.guild_permissions.administrator: return
    if "http" in message.content:
        await message.delete()
        await message.channel.send(f"🚫 ممنوع إرسال الروابط يا {message.author.mention}")

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.run(BOT_TOKEN)