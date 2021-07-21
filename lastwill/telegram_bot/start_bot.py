from lastwill.settings import bot_token
from lastwill.telegram_bot.bot import Bot

bot = Bot(bot_token)
bot.start()
