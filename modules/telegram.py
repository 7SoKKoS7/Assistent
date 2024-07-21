import telebot
from config import telegram_api_key
from main import chat_with_gpt_multilang

bot = telebot.TeleBot(telegram_api_key)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! How can I assist you today?")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    response = chat_with_gpt_multilang(message.text)
    bot.reply_to(message, response)

def run_telegram_bot():
    bot.polling()
