"""
bot/cogs/server_tools.py
نقل مباشر لمنطق on_message من main.py:
  1. الأوامر المخصصة
  2. حماية الروابط

⚠️ مهم: الاثنان في نفس الـ Cog لأن الكود الأصلي يوقف التنفيذ
   (return) عند وجود أمر مخصص، ولا يتحقق من الروابط بعدها.
   لو فصلناهم في Cog منفصل سيتحقق كلاهما في نفس الوقت.
"""
import discord
from discord.ext import commands
from database import get_db_connection


class ServerToolsCog(commands.Cog, name="ServerTools"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ─── نفس المنطق من main.py بالضبط ────────────────────────────────

        if message.author.bot:
            return
        if not message.guild:
            return

        conn = get_db_connection()
        c = conn.cursor()

        # 1️⃣ التحقق من الأوامر المخصصة أولاً
        c.execute(
            'SELECT response FROM custom_commands WHERE guild_id = %s AND command = %s',
            (str(message.guild.id), message.content)
        )
        row = c.fetchone()
        c.close()
        conn.close()

        if row:
            await message.channel.send(row[0])
            return  # ← توقف هنا، لا تتحقق من الروابط (نفس السلوك الأصلي)

        # 2️⃣ الحماية التلقائية من الروابط (فقط إذا لم يكن أمراً مخصصاً)
        if (
            not message.author.guild_permissions.administrator
            and "http" in message.content
        ):
            await message.delete()
            await message.channel.send(
                f"🚫 ممنوع إرسال الروابط يا {message.author.mention}"
            )


async def setup(bot):
    await bot.add_cog(ServerToolsCog(bot))
