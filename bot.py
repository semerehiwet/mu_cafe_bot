from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TOKEN = "8146345458:AAFNkn0CwekS4aluEkYIzO8M5pni6tIAPJE"

def start(update: Update, context: CallbackContext):
    keyboard = [["🍽 የምግብ ፕሮግራም", "📍 ካፌ Location"],
                ["ℹ️ Help"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("እንኳን ወደ MU Cafe Bot በደህና መጡ!", reply_markup=reply_markup)

updater = Updater(TOKEN)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))

updater.start_polling()
updater.idle()
