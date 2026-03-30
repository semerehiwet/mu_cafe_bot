from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import datetime

TOKEN = "8146345458:AAFNkn0CwekS4aluEkYIzO8M5pni6tIAPJE"

# የሳምንት ምግብ program
menu = {
    "Monday": "🍚 ሩዝ + ዶሮ",
    "Tuesday": "🍝 ፓስታ",
    "Wednesday": "🍛 ሽሮ",
    "Thursday": "🥔 ድንች + ስጋ",
    "Friday": "🍲 ክክ",
    "Saturday": "🍚 ሩዝ + አትክልት",
    "Sunday": "🍗 ዶሮ"
}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 እንኳን ደህና መጡ!\n\n"
        "Commands:\n"
        "/today - ዛሬ ምን ምግብ ነው\n"
        "/menu - ሙሉ ሳምንት\n"
        "/help - መረጃ"
    )

# /today
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today_day = datetime.datetime.now().strftime("%A")
    food = menu.get(today_day, "No data")

    await update.message.reply_text(
        f"📅 ዛሬ ({today_day})\n🍽 ምግብ: {food}"
    )

# /menu
async def full_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📋 የሳምንት ምግብ ፕሮግራም:\n\n"

    for day, food in menu.items():
        text += f"{day} → {food}\n"

    await update.message.reply_text(text)

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ ይህ bot በ university የምግብ ፕሮግራም ያሳያል።\n"
        "Use /today ወይም /menu"
    )

# main
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("today", today))
app.add_handler(CommandHandler("menu", full_menu))
app.add_handler(CommandHandler("help", help_command))

app.run_polling()
