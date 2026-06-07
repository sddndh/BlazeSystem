"""
bot/core.py — كلاس BlazeBot مع تحميل تلقائي للـ Cogs.
نفس اسم البوت الحالي (BlazeBot) محفوظ.
"""
import os
import discord
from discord.ext import commands
from config import Config
from database import init_db


class BlazeBot(commands.Bot):
    def __init__(self):
        # نفس الإعدادات الحالية تماماً
        super().__init__(
            command_prefix='!',
            intents=discord.Intents.all()
        )

    async def setup_hook(self):
        """يُحمِّل كل ملف .py في مجلد cogs/ تلقائياً."""
        cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
        for filename in sorted(os.listdir(cogs_dir)):
            if filename.endswith('.py') and not filename.startswith('_'):
                module = f'bot.cogs.{filename[:-3]}'
                try:
                    await self.load_extension(module)
                    print(f'  ✅ Cog محمّل: {filename[:-3]}')
                except Exception as e:
                    print(f'  ❌ فشل تحميل {filename[:-3]}: {e}')

        # مزامنة أوامر السلاش (للـ /rank و /leaderboard و /phantom-report)
        try:
            synced = await self.tree.sync()
            print(f'  ✅ تمت مزامنة {len(synced)} أمر سلاش')
        except Exception as e:
            print(f'  ⚠️ تعذّرت مزامنة أوامر السلاش: {e}')

    async def on_ready(self):
        init_db()   # نفس استدعاء init_db من on_ready الحالي
        print(f'✅ البوت متصل ومستعد! [{self.user}]')


def run_bot():
    bot = BlazeBot()
    bot.run(Config.BOT_TOKEN)
