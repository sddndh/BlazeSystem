"""
bot/cogs/leveling.py
نظام المستويات (XP) — يستخدم نفس get_db_connection (sync) مثل باقي المشروع.
"""
import math
import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from database import get_db_connection

XP_RANGE = (15, 25)
COOLDOWN_SECONDS = 60
NEON_ORANGE = 0xFF6B00


def level_from_xp(xp: int) -> int:
    return max(0, int(0.1 * math.sqrt(xp)))


def xp_for_level(level: int) -> int:
    return (level * 10) ** 2


def progress_bar(pct: float, width: int = 12) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def get_progress(xp: int) -> dict:
    lvl = level_from_xp(xp)
    cur = xp_for_level(lvl)
    nxt = xp_for_level(lvl + 1)
    needed = nxt - cur
    pct = (xp - cur) / needed * 100 if needed else 100
    return {"level": lvl, "progress_xp": xp - cur, "needed_xp": needed,
            "pct": round(pct, 1), "next_level_xp": nxt}


class LevelingCog(commands.Cog, name="Leveling"):
    def __init__(self, bot):
        self.bot = bot
        self._cooldowns: dict[str, datetime] = {}

    def _award_xp(self, user_id: str, guild_id: str, xp: int) -> tuple[int, int, int]:
        """يضيف XP ويُعيد (xp الجديد, المستوى القديم, المستوى الجديد)."""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """INSERT INTO user_levels (user_id, guild_id, xp, level, total_messages, last_activity)
               VALUES (%s, %s, %s, 0, 1, NOW())
               ON CONFLICT (user_id, guild_id) DO UPDATE
               SET xp = user_levels.xp + %s,
                   total_messages = user_levels.total_messages + 1,
                   last_activity = NOW()
               RETURNING xp, level""",
            (user_id, guild_id, xp, xp),
        )
        new_xp, old_level = c.fetchone()
        new_level = level_from_xp(new_xp)
        if new_level > old_level:
            c.execute(
                "UPDATE user_levels SET level = %s WHERE user_id = %s AND guild_id = %s",
                (new_level, user_id, guild_id),
            )
        conn.commit()
        c.close()
        conn.close()
        return new_xp, old_level, new_level

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        key = f"{message.guild.id}:{message.author.id}"
        now = datetime.now(timezone.utc)
        last = self._cooldowns.get(key)
        if last and (now - last).total_seconds() < COOLDOWN_SECONDS:
            return
        self._cooldowns[key] = now

        xp = random.randint(*XP_RANGE)
        new_xp, old_level, new_level = self._award_xp(
            str(message.author.id), str(message.guild.id), xp
        )

        if new_level > old_level:
            prog = get_progress(new_xp)
            embed = discord.Embed(
                title="🔥 LEVEL UP!",
                description=(f"{message.author.mention} وصل للمستوى **{new_level}**!\n"
                             f"`{progress_bar(prog['pct'])}` {prog['pct']}%"),
                color=NEON_ORANGE,
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            try:
                await message.channel.send(embed=embed, delete_after=30)
            except discord.Forbidden:
                pass

    @app_commands.command(name="rank", description="اعرض رتبتك ونقاطك")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """SELECT xp, level, total_messages,
                      RANK() OVER (PARTITION BY guild_id ORDER BY xp DESC) AS rank
               FROM user_levels WHERE user_id = %s AND guild_id = %s""",
            (str(target.id), str(interaction.guild_id)),
        )
        row = c.fetchone()
        c.close()
        conn.close()

        if not row:
            return await interaction.response.send_message(
                "❌ لا توجد بيانات. ابدأ بالدردشة!", ephemeral=True
            )

        xp, level, msgs, rank = row
        prog = get_progress(xp)
        embed = discord.Embed(title=f"📊 بطاقة {target.display_name}", color=NEON_ORANGE)
        embed.add_field(name="🏆 الترتيب", value=f"#{rank}", inline=True)
        embed.add_field(name="⚡ المستوى", value=str(level), inline=True)
        embed.add_field(name="✨ النقاط", value=f"{xp:,}", inline=True)
        embed.add_field(name="💬 الرسائل", value=f"{msgs:,}", inline=True)
        embed.add_field(
            name=f"التقدم للمستوى {level + 1}",
            value=f"`{progress_bar(prog['pct'])}` {prog['pct']}%\n{prog['progress_xp']:,} / {prog['needed_xp']:,}",
            inline=False,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="أفضل 10 أعضاء")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """SELECT user_id, xp, level FROM user_levels
               WHERE guild_id = %s ORDER BY xp DESC LIMIT 10""",
            (str(interaction.guild_id),),
        )
        rows = c.fetchall()
        c.close()
        conn.close()

        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        lines = []
        for i, (uid, xp, level) in enumerate(rows):
            try:
                user = await self.bot.fetch_user(int(uid))
                name = user.display_name
            except Exception:
                name = f"User {uid}"
            badge = medals.get(i, f"`#{i + 1}`")
            lines.append(f"{badge} **{name}** — Lv.{level} · {xp:,} XP")

        embed = discord.Embed(
            title=f"🏆 ترتيب {interaction.guild.name}",
            description="\n".join(lines) if lines else "لا توجد بيانات بعد!",
            color=NEON_ORANGE,
        )
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LevelingCog(bot))
