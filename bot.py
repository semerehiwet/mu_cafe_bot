import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("8146345458:AAFNkn0CwekS4aluEkYIzO8M5pni6tIAPJE")

# ===== MENU =====
main_menu = [["🍽 የምግብ ፕሮግራም", "📍 የካፌ location"], ["ℹ️ Help"]]
days_menu = [["ሰኞ", "ማክሰኞ"], ["እሮብ", "ሐሙስ"], ["አርብ", "ቅዳሜ"], ["እሁድ"]]
location_menu = [["አሪድ", "ቢዝነስ"], ["ዓይደር", "ዲያስፖራ"]]

# ===== FOOD DATA =====
menu = {
    "ሰኞ": "ቁርስ: 2 ዳቦ+ሩዝ+ሻይ\nምሳ: ፓስታ+2 ዳቦ\nእራት: እንጀራ+ስልስ+ሽሮ",
    "ማክሰኞ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ድንች\nእራት: እንጀራ+ድንች",
    "እሮብ": "ቁርስ: 2 ዳቦ+ማኮሮኒ+ሻይ\nምሳ: እንጀራ+ድንች\nእራት: እንጀራ+ክክ",
    "ሐሙስ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ሽሮ\nእራት: እንጀራ+ሽሮ",
    "አርብ": "ቁርስ: 2 ዳቦ+ሻይ\nምሳ: እንጀራ+ድንች+ሽሮ\nእራት: እንጀራ+ሽሮ",
    "ቅዳሜ": "ቁርስ: 2 ዳቦ+ሩዝ+ሻይ\nምሳ: እንጀራ+ክክ\nእራት: እንጀራ+ስልስ+ሽሮ",
    "እሁድ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ሽሮ+ስልስ\nእራት: እንጀራ+ክክ"
}

# ===== LOCATION DATA =====
locations = {
    "አሪድ": "ከመግቢያ በር 500 ሜትር ወደ ሰሜን",
    "ቢዝነስ": "በካምፓስ መሀከል",
    "ዓይደር": "ከ library በኋላ",
    "ዲያስፖራ": "ከ main gate በግራ"
}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "እንኳን ወደ ካፌ Bot በደህና መጡ!",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

# ===== MESSAGE HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🍽 የምግብ ፕሮግራም":
        await update.message.reply_text(
            "ቀን ምረጥ:",
            reply_markup=ReplyKeyboardMarkup(days_menu, resize_keyboard=True)
        )

    elif text in menu:
        await update.message.reply_text(menu[text])

    elif text == "📍 የካፌ location":
        await update.message.reply_text(
            "ቦታ ምረጥ:",
            reply_markup=ReplyKeyboardMarkup(location_menu, resize_keyboard=True)
        )

    elif text in locations:
        await update.message.reply_text(locations[text])

    elif text == "ℹ️ Help":
        await update.message.reply_text("ምን ማድረግ ትፈልጋለህ?")

    else:
        await update.message.reply_text("እባክህ menu ውስጥ ያለውን ተጠቀም")

# ===== MAIN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()
