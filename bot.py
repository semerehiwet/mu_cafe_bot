from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8146345458:AAFNkn0CwekS4aluEkYIzO8M5pni6tIAPJE"

# ===== MENUS =====
main_menu = [["🍽 የምግብ ፕሮግራም", "📍 የካፌ location"], ["❓ Help"]]

days_menu = [
    ["ሰኞ", "ማክሰኞ", "እሮብ"],
    ["ሐሙስ", "ዓርብ"],
    ["ቅዳሜ", "እሁድ"],
    ["🔙 Back"]
]

location_menu = [
    ["አሪድ", "ቢዝነስ"],
    ["ዓይደር", "ዲያስፖራ"],
    ["🔙 Back"]
]

# ===== FOOD PROGRAM =====
food_program = {
    "ሰኞ": "🍽 የሰኞ\nቁርስ: 2 ዳቦ + ሩዝ + ሻይ\nምሳ: ፓስታ + 2 ዳቦ\nእራት: እንጀራ + ስልስ + ሽሮ",
    "ማክሰኞ": "🍽 የማክሰኞ\nቁርስ: 2 ዳቦ + ፍርፍር + ሻይ\nምሳ: እንጀራ + ድንች\nእራት: እንጀራ + ድንች",
    "እሮብ": "🍽 የእሮብ\nቁርስ: 2 ዳቦ + ማኮሮኒ + ሻይ\nምሳ: እንጀራ + ድንች\nእራት: እንጀራ + ክክ",
    "ሐሙስ": "🍽 የሐሙስ\nቁርስ: 2 ዳቦ + ፍርፍር + ሻይ\nምሳ: እንጀራ + ሽሮ\nእራት: እንጀራ + ሽሮ",
    "ዓርብ": "🍽 የዓርብ\nቁርስ: 2 ዳቦ + ሻይ\nምሳ: እንጀራ + ድንች + ሽሮ\nእራት: እንጀራ + ሽሮ",
    "ቅዳሜ": "🍽 የቅዳሜ\nቁርስ: 2 ዳቦ + ሩዝ + ሻይ\nምሳ: እንጀራ + ክክ\nእራት: እንጀራ + ስልስ + ሽሮ",
    "እሁድ": "🍽 የእሁድ\nቁርስ: 2 ዳቦ + ፍርፍር + ሻይ\nምሳ: እንጀራ + ሽሮ + ስልስ\nእራት: እንጀራ + ክክ",
}

# ===== LOCATIONS =====
locations = {
    "አሪድ": "📍 አሪድ: 500m ወደ ሰሜን",
    "ቢዝነስ": "📍 ቢዝነስ: 300m ወደ ምስራቅ",
    "ዓይደር": "📍 ዓይደር: 200m ወደ ምዕራብ",
    "ዲያስፖራ": "📍 ዲያስፖራ: 400m ወደ ደቡብ",
}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 እንኳን ደህና መጡ!",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🍽 የምግብ ፕሮግራም":
        await update.message.reply_text("ቀን ይምረጡ", reply_markup=ReplyKeyboardMarkup(days_menu, resize_keyboard=True))

    elif text in food_program:
        await update.message.reply_text(food_program[text])

    elif text == "📍 የካፌ location":
        await update.message.reply_text("Location ይምረጡ", reply_markup=ReplyKeyboardMarkup(location_menu, resize_keyboard=True))

    elif text in locations:
        await update.message.reply_text(locations[text])

    elif text == "❓ Help":
        await update.message.reply_text("🍽 ምግብ ወይም 📍 location ይምረጡ")

    elif text == "🔙 Back":
        await update.message.reply_text("Main Menu", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))

# ===== RUN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
