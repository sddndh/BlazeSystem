"""
bot/cogs/phantom_pulse.py
الميزة التنافسية — محرك ذكاء المجتمع.
يستخدم نفس get_db_connection (sync) مثل باقي المشروع.

  • يتتبع نشاط الأعضاء يومياً
  • يحسب درجة صحة المجتمع (0–100)
  • يكتشف الأعضاء المعرّضين للمغادرة (churn)
  • أمر /phantom-report لعرض التقرير
"""
import json
from collections import defaultdict
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from database import get_db_connection

NEON_ORANGE = 0xFF6B00
SCHEDULE_HOURS = 24


def compute_health_score(m: dict) -> int:
    trend = max(0, min(100, 50 + m.get("trend_7d", 0) * 2))
    retention = m.get("retention_rate", 0) * 100
    churn = max(0, 100 - m.get("churn_ratio", 0) * 200)
    diversity = min(100, m.get("unique_active", 0) * 2)
    score = trend * 0.3 + retention * 0.35 + churn * 0.2 + diversity * 0.15
    return max(0, min(100, round(score)))


class PhantomPulseCog(commands.Cog, name="PhantomPulse"):
    def __init__(self, bot):
        self.bot = bot
        # guild_id -> {user_id: today_count}
        self._cache: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.daily_analysis.start()

    def cog_unload(self):
        self.daily_analysis.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        self._cache[str(message.guild.id)][str(message.author.id)] += 1

    @tasks.loop(hours=SCHEDULE_HOURS)
    async def daily_analysis(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            gid = str(guild.id)
            try:
                self._persist(gid)
                metrics = self._compute_metrics(gid)
                score = compute_health_score(metrics)
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(
                    """INSERT INTO phantom_health_scores (guild_id, score, metrics, recorded_at)
                       VALUES (%s, %s, %s, NOW())""",
                    (gid, score, json.dumps(metrics)),
                )
                conn.commit()
                c.close()
                conn.close()
                self._cache[gid].clear()
            except Exception as e:
                print(f"[PhantomPulse] خطأ في {gid}: {e}")

    @daily_analysis.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    def _persist(self, guild_id: str):
        conn = get_db_connection()
        c = conn.cursor()
        for uid, count in self._cache[guild_id].items():
            if count:
                c.execute(
                    """INSERT INTO member_activity_log (user_id, guild_id, message_count, logged_date)
                       VALUES (%s, %s, %s, CURRENT_DATE)
                       ON CONFLICT (user_id, guild_id, logged_date)
                       DO UPDATE SET message_count = member_activity_log.message_count + EXCLUDED.message_count""",
                    (uid, guild_id, count),
                )
        conn.commit()
        c.close()
        conn.close()

    def _compute_metrics(self, guild_id: str) -> dict:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """SELECT user_id, logged_date, message_count FROM member_activity_log
               WHERE guild_id = %s AND logged_date >= CURRENT_DATE - INTERVAL '14 days'""",
            (guild_id,),
        )
        rows = c.fetchall()
        c.close()
        conn.close()

        today = datetime.now(timezone.utc).date()
        w1 = sum(mc for _, d, mc in rows if (today - d).days <= 7)
        w2 = sum(mc for _, d, mc in rows if 7 < (today - d).days <= 14) or 1
        trend = ((w1 - w2) / max(w2, 1)) * 100

        u1 = {u for u, d, _ in rows if (today - d).days <= 7}
        u2 = {u for u, d, _ in rows if 7 < (today - d).days <= 14}
        churned = u2 - u1
        churn_ratio = len(churned) / max(len(u2), 1)
        retention = len(u1 & u2) / max(len(u2), 1)

        return {
            "trend_7d": round(trend, 1),
            "churn_ratio": round(churn_ratio, 3),
            "retention_rate": round(retention, 3),
            "unique_active": len(u1),
            "at_risk_users": list(churned)[:5],
        }

    @app_commands.command(name="phantom-report", description="تقرير صحة المجتمع")
    @app_commands.default_permissions(manage_guild=True)
    async def phantom_report(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gid = str(interaction.guild_id)
        metrics = self._compute_metrics(gid)
        score = compute_health_score(metrics)

        if score >= 75:
            color, label = 0x00FF88, "🟢 ممتاز"
        elif score >= 50:
            color, label = 0xFFAA00, "🟡 متوسط"
        else:
            color, label = 0xFF3333, "🔴 في خطر"

        embed = discord.Embed(
            title="🔮 تقرير Phantom Pulse",
            description=f"**درجة صحة المجتمع: {score}/100** — {label}",
            color=color,
        )
        embed.add_field(name="📊 اتجاه 7 أيام", value=f"{metrics['trend_7d']:+.1f}%", inline=True)
        embed.add_field(name="🔄 الاحتفاظ", value=f"{metrics['retention_rate'] * 100:.0f}%", inline=True)
        embed.add_field(name="👥 نشطون", value=str(metrics["unique_active"]), inline=True)

        if metrics["at_risk_users"]:
            risk = ", ".join(f"<@{u}>" for u in metrics["at_risk_users"])
            embed.add_field(
                name="⚠️ أعضاء معرّضون للمغادرة",
                value=f"قلّ نشاطهم — تواصل معهم:\n{risk}",
                inline=False,
            )
        embed.set_footer(text="Phantom Pulse™ · AuraBot")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(PhantomPulseCog(bot))
