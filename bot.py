from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8146345458:AAFNkn0CwekS4aluEkYIzO8M5pni6tIAPJE"

# Main Menu
main_menu = [["🍽 የምግብ ፕሮግራም", "📍 የካፌ Location"],
             ["❓ Help"]]

# Days Menu
days_menu = [["ሰኞ", "ማክሰኞ", "እሮብ"],
             ["ሐሙስ", "ዓርብ", "ቅዳሜ"],
             ["እሁድ", "🔙 Back"]]

# Location Menu
location_menu = [["አሪድ", "ቢዝነስ"],
                 ["ዓይደር", "ዲያስፖራ"],
                 ["🔙 Back"]]

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 እንኳን ወደ Cafe Bot በደህና መጡ!",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Food program
    if text == "🍽 የምግብ ፕሮግራም":
        await update.message.reply_text(
            "ቀን ይምረጡ:",
            reply_markup=ReplyKeyboardMarkup(days_menu, resize_keyboard=True)
        )

    elif text in ["ሰኞ","ማክሰኞ","እሮብ","ሐሙስ","ዓርብ","ቅዳሜ","እሁድ"]:
        await update.message.reply_text(
            f"📅 {text} ፕሮግራም\n\n"
            f"🍳 ቁርስ: እንጀራ + ሽሮ\n"
            f"🍛 ምሳ: ሩዝ + ዶሮ\n"
            f"🍲 እራት: ፓስታ",
            reply_markup=ReplyKeyboardMarkup(days_menu, resize_keyboard=True)
        )

    # Location
    elif text == "📍 የካፌ Location":
        await update.message.reply_text(
            "ካፌ ይምረጡ:",
            reply_markup=ReplyKeyboardMarkup(location_menu, resize_keyboard=True)
        )

    elif text == "አሪድ":
        await update.message.reply_text("📍 ከመግቢያ 500m ወደ ሰሜን")

    elif text == "ቢዝነስ":
        await update.message.reply_text("📍 ከLibrary አጠገብ")

    elif text == "ዓይደር":
        await update.message.reply_text("📍 ከHospital በቀርብ")

    elif text == "ዲያስፖራ":
        await update.message.reply_text("📍 ከMain gate በቀርብ")

    # Help
    elif text == "❓ Help":
        await update.message.reply_text(
            "ℹ️ እባክህ ከmenu ላይ ምርጫ ያድርጉ:\n"
            "🍽 የምግብ ፕሮግራም\n"
            "📍 Location\n"
            "❓ Help"
        )

    # Back
    elif text == "🔙 Back":
        await update.message.reply_text(
            "🏠 Main Menu",
            reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        )

# Run bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
