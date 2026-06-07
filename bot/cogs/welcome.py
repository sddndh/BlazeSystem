"""
bot/cogs/welcome.py
نظام الترحيب — الآن يرسل بطاقة صورة بدلاً من نص فقط.
يقرأ إعدادات القالب من جدول settings (مع توافق كامل مع القديم).
"""
import discord
from discord.ext import commands

from database import get_db_connection
from bot.utils.welcome_image import generate_welcome_card


class WelcomeCog(commands.Cog, name="Welcome"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # جلب الإعدادات
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """SELECT welcome_msg, image_enabled, image_title, image_template
               FROM settings WHERE guild_id = %s""",
            (str(member.guild.id),),
        )
        row = c.fetchone()
        c.close()
        conn.close()

        if not row:
            return

        welcome_msg   = row[0] or "أهلاً بك!"
        image_enabled = row[1] if len(row) > 1 else False
        image_title   = row[2] if len(row) > 2 and row[2] else "أهلاً بك"
        template      = row[3] if len(row) > 3 and row[3] else "carbon"

        channel = member.guild.system_channel
        if not channel:
            return

        # ── الوضع الجديد: بطاقة صورة ──────────────────────────────────────
        if image_enabled:
            try:
                buf = await generate_welcome_card(
                    avatar_url=member.display_avatar.with_size(256).url,
                    username=member.display_name,
                    member_count=member.guild.member_count,
                    guild_name=member.guild.name,
                    title=image_title,
                    template=template,
                )
                file = discord.File(buf, filename="welcome.png")
                await channel.send(
                    content=f"👋 {member.mention} | {welcome_msg}",
                    file=file,
                )
                return
            except Exception as e:
                print(f"[Welcome] فشل توليد البطاقة، الرجوع للنص: {e}")

        # ── الوضع القديم: نص فقط (fallback آمن) ──────────────────────────
        await channel.send(f"👋 {member.mention} | {welcome_msg}")


async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
