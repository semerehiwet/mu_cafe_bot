from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "YOUR_BOT_TOKEN_HERE"

# Main menu
main_menu = [["🍽 የምግብ ፕሮግራም", "📍 የካፌ location"], ["❓ Help"]]

# Days menu
days_menu = [
    ["ሰኞ", "ማክሰኞ", "እሮብ"],
    ["ሐሙስ", "ዓርብ"],
    ["ቅዳሜ", "እሁድ"],
    ["🔙 Back"]
]

# Location menu
location_menu = [
    ["አሪድ", "ቢዝነስ"],
    ["ዓይደር", "ዲያስፖራ"],
    ["🔙 Back"]
]

# Food data
food_program = {
    "ሰኞ": "🍽 የሰኞ ፕሮግራም\nቁርስ: 2 ዳቦ + ሩዝ + ሻይ\nምሳ: ፓስታ + 2 ዳቦ\nእራት: እንጀራ + ስልስ + ሽሮ",
    "ማክሰኞ": "🍽 የማክሰኞ ፕሮግራም\nቁርስ: 2 ዳቦ + ፍርፍር + ሻይ\nምሳ: እንጀራ + ድንች\nእራት: እንጀራ + ድንች",
    "እሮብ": "🍽 የእሮብ ፕሮግራም\nቁርስ: 2 ዳቦ + ማኮሮኒ + ሻይ\nምሳ: እንጀራ + ድንች\nእራት: እንጀራ + ክክ",
    "ሐሙስ": "🍽 የሐሙስ ፕሮግራም\nቁርስ: 2 ዳቦ + ፍርፍር + ሻይ\nምሳ: እንጀራ + ሽሮ\nእራት: እንጀራ + ሽሮ",
    "ዓርብ": "🍽 የዓርብ ፕሮግራም\nቁርስ: 2 ዳቦ + ሻይ\nምሳ: እንጀራ + ድንች + ሽሮ\nእራት: እንጀራ + ሽሮ",
    "ቅዳሜ": "🍽 የቅዳሜ ፕሮግራም\nቁርስ: 2 ዳቦ + ሩዝ + ሻይ\nምሳ: እንጀራ + ክክ\nእራት: እንጀራ + ስልስ + ሽሮ",
    "እሁድ": "🍽 የእሁድ ፕሮግራም\nቁርስ: 2 ዳቦ + ፍርፍር + ሻይ\nምሳ: እንጀራ + ሽሮ + ስልስ\nእራት: እንጀራ + ክክ",
}

# Locations
locations = {
    "አሪድ": "📍 አሪድ: ከመግቢያ በር 500 ሜትር ወደ ሰሜን",
    "ቢዝነስ": "📍 ቢዝነስ: ከመግቢያ በር 300 ሜትር ወደ ምስራቅ",
    "ዓይደር": "📍 ዓይደር: ከመግቢያ በር 200 ሜትር ወደ ምዕራብ",
    "ዲያስፖራ": "📍 ዲያስፖራ: ከመግቢያ በር 400 ሜትር ወደ ደቡብ",
}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 እንኳን ወደ Cafe Bot በደህና መጡ!",
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

# Messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🍽 የምግብ ፕሮግራም":
        await update.message.reply_text("ቀን ይምረጡ:", reply_markup=ReplyKeyboardMarkup(days_menu, resize_keyboard=True))

    elif text in food_program:
        await update.message.reply_text(food_program[text])

    elif text == "📍 የካፌ location":
        await update.message.reply_text("Location ይምረጡ:", reply_markup=ReplyKeyboardMarkup(location_menu, resize_keyboard=True))

    elif text in locations:
        await update.message.reply_text(locations[text])

    elif text == "❓ Help":
        await update.message.reply_text("ምን ማድረግ ትፈልጋለህ?\n🍽 ምግብ ፕሮግራም ወይም 📍 location ይምረጡ")

    elif text == "🔙 Back":
        await update.message.reply_text("Main Menu", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))

# Run bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
