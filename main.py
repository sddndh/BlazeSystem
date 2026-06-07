import discord
from discord.ext import commands
from flask import Flask, render_template, request, redirect, session
import requests
import threading
import os
import urllib.parse
import psycopg2

# ==========================================
# 1. إعدادات السحابة
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
DOMAIN = os.environ.get("DOMAIN", "http://127.0.0.1:5000")
DATABASE_URL = os.environ.get("DATABASE_URL")

REDIRECT_URI = f"{DOMAIN}/callback"
encoded_redirect = urllib.parse.quote(REDIRECT_URI, safe='')
OAUTH_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={encoded_redirect}&response_type=code&scope=identify%20guilds"

# ==========================================
# 2. إعداد قاعدة البيانات
# ==========================================
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    if not DATABASE_URL: return
    conn = get_db_connection()
    c = conn.cursor()
    # جدول الترحيب
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                 guild_id TEXT PRIMARY KEY, 
                 welcome_msg TEXT)''')
    # جدول الأوامر المخصصة الجديد
    c.execute('''CREATE TABLE IF NOT EXISTS custom_commands (
                 guild_id TEXT, 
                 command TEXT, 
                 response TEXT,
                 PRIMARY KEY (guild_id, command))''')
    conn.commit()
    c.close()
    conn.close()

# ==========================================
# 3. محرك الموقع
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
    if not code: return "حدث خطأ."
    
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    
    if r.status_code != 200: return "فشل الربط."
    
    session['token'] = r.json()['access_token']
    return redirect('/dashboard')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'token' not in session: return redirect('/')
    
    h = {'Authorization': f"Bearer {session['token']}"}
    user_guilds = requests.get('https://discord.com/api/users/@me/guilds', headers=h).json()
    admin_guilds = [g for g in user_guilds if (int(g.get('permissions', 0)) & 0x8) == 0x8]
    if not admin_guilds: return "لا تملك صلاحيات إدارة."
    
    target_guild_id = str(admin_guilds[0]['id'])
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')
        
        # حفظ الترحيب
        if action == 'save_welcome':
            new_msg = request.form.get('welcome_msg', 'حياك الله!')
            c.execute('''INSERT INTO settings (guild_id, welcome_msg) VALUES (%s, %s) 
                         ON CONFLICT (guild_id) DO UPDATE SET welcome_msg = EXCLUDED.welcome_msg''', 
                      (target_guild_id, new_msg))
                      
        # إضافة أمر جديد
        elif action == 'add_command':
            cmd = request.form.get('command', '').strip()
            resp = request.form.get('response', '').strip()
            if cmd and resp:
                if not cmd.startswith('!'): cmd = '!' + cmd # إضافة علامة التعجب تلقائياً
                c.execute('''INSERT INTO custom_commands (guild_id, command, response) VALUES (%s, %s, %s) 
                             ON CONFLICT (guild_id, command) DO UPDATE SET response = EXCLUDED.response''', 
                          (target_guild_id, cmd, resp))
                          
        # حذف أمر
        elif action == 'delete_command':
            cmd = request.form.get('command')
            c.execute('DELETE FROM custom_commands WHERE guild_id = %s AND command = %s', (target_guild_id, cmd))
            
        conn.commit()

    # جلب البيانات لعرضها في الموقع
    c.execute('SELECT welcome_msg FROM settings WHERE guild_id = %s', (target_guild_id,))
    row = c.fetchone()
    current_msg = row[0] if row else "أهلاً بك!"
    
    c.execute('SELECT command, response FROM custom_commands WHERE guild_id = %s', (target_guild_id,))
    commands_list = c.fetchall()
    
    c.close()
    conn.close()
    
    return render_template('dashboard.html', current_msg=current_msg, commands=commands_list)

def run_flask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ==========================================
# 4. محرك البوت
# ==========================================
class BlazeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())

bot = BlazeBot()

@bot.event
async def on_ready():
    init_db()
    print("✅ البوت متصل ومستعد!")

@bot.event
async def on_member_join(member):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT welcome_msg FROM settings WHERE guild_id = %s', (str(member.guild.id),))
    row = c.fetchone()
    c.close()
    conn.close()
    if row and member.guild.system_channel:
        await member.guild.system_channel.send(f"👋 {member.mention} | {row[0]}")

@bot.event
async def on_message(message):
    if message.author.bot: return

    # التحقق من الأوامر المخصصة
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT response FROM custom_commands WHERE guild_id = %s AND command = %s', (str(message.guild.id), message.content))
    row = c.fetchone()
    c.close()
    conn.close()

    if row:
        await message.channel.send(row[0])
        return # إذا كان أمراً مخصصاً، يتوقف هنا ولا يكمل باقي الأكواد

    # الحماية التلقائية
    if not message.author.guild_permissions.administrator and "http" in message.content:
        await message.delete()
        await message.channel.send(f"🚫 ممنوع إرسال الروابط يا {message.author.mention}")

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot.run(BOT_TOKEN)