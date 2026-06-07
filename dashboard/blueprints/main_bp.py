"""
dashboard/blueprints/main_bp.py
نقل مباشر لمسار /dashboard من main.py — نفس المنطق تماماً.
"""
import requests
from flask import Blueprint, redirect, render_template, request, session
from database import get_db_connection

main_bp = Blueprint('main', __name__)


@main_bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # ─── نفس كود /dashboard من main.py بالضبط ────────────────────────────

    if 'token' not in session:
        return redirect('/')

    h = {'Authorization': f"Bearer {session['token']}"}
    user_guilds = requests.get(
        'https://discord.com/api/users/@me/guilds', headers=h
    ).json()

    # تحقق من صلاحية الرد (أحياناً Discord يُرجع error dict)
    if not isinstance(user_guilds, list):
        return redirect('/')

    admin_guilds = [
        g for g in user_guilds
        if (int(g.get('permissions', 0)) & 0x8) == 0x8
    ]
    if not admin_guilds:
        return "لا تملك صلاحيات إدارة."

    target_guild_id = str(admin_guilds[0]['id'])

    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        action = request.form.get('action')

        # حفظ الترحيب (+ إعدادات الصورة الجديدة)
        if action == 'save_welcome':
            new_msg       = request.form.get('welcome_msg', 'حياك الله!')
            image_enabled = request.form.get('image_enabled') == '1'
            image_title   = request.form.get('image_title', 'أهلاً بك').strip() or 'أهلاً بك'
            image_template= request.form.get('image_template', 'carbon')
            c.execute(
                """INSERT INTO settings (guild_id, welcome_msg, image_enabled, image_title, image_template)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (guild_id) DO UPDATE SET
                       welcome_msg    = EXCLUDED.welcome_msg,
                       image_enabled  = EXCLUDED.image_enabled,
                       image_title    = EXCLUDED.image_title,
                       image_template = EXCLUDED.image_template""",
                (target_guild_id, new_msg, image_enabled, image_title, image_template)
            )

        # إضافة أمر
        elif action == 'add_command':
            cmd  = request.form.get('command', '').strip()
            resp = request.form.get('response', '').strip()
            if cmd and resp:
                if not cmd.startswith('!'):
                    cmd = '!' + cmd
                c.execute(
                    """INSERT INTO custom_commands (guild_id, command, response) VALUES (%s, %s, %s)
                       ON CONFLICT (guild_id, command) DO UPDATE SET response = EXCLUDED.response""",
                    (target_guild_id, cmd, resp)
                )

        # حذف أمر
        elif action == 'delete_command':
            cmd = request.form.get('command')
            c.execute(
                'DELETE FROM custom_commands WHERE guild_id = %s AND command = %s',
                (target_guild_id, cmd)
            )

        conn.commit()

    # جلب البيانات للعرض
    c.execute(
        """SELECT welcome_msg, image_enabled, image_title, image_template
           FROM settings WHERE guild_id = %s""",
        (target_guild_id,)
    )
    row = c.fetchone()
    if row:
        current_msg    = row[0] or "أهلاً بك!"
        image_enabled  = row[1]
        image_title    = row[2]
        image_template = row[3]
    else:
        current_msg, image_enabled, image_title, image_template = "أهلاً بك!", False, "أهلاً بك", "carbon"

    c.execute(
        'SELECT command, response FROM custom_commands WHERE guild_id = %s',
        (target_guild_id,)
    )
    commands_list = c.fetchall()

    c.close()
    conn.close()

    return render_template(
        'dashboard.html',
        current_msg=current_msg,
        image_enabled=image_enabled,
        image_title=image_title,
        image_template=image_template,
        commands=commands_list
    )
