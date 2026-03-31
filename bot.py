from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "PUT_YOUR_TOKEN_HERE"

# MAIN MENU
main_menu = [["🍽 ምግብ", "📍 Location"], ["❓ Help"]]

# DAYS
days_menu = [
    ["ሰኞ", "ማክሰኞ", "እሮብ"],
    ["ሐሙስ", "ዓርብ"],
    ["ቅዳሜ", "እሁድ"],
    ["🔙 Back"]
]

# LOCATIONS
location_menu = [
    ["አሪድ", "ቢዝነስ"],
    ["ዓይደር", "ዲያስፖራ"],
    ["🔙 Back"]
]

# FOOD DATA
food = {
    "ሰኞ": "ቁርስ: 2 ዳቦ+ሩዝ+ሻይ\nምሳ: ፓስታ+2 ዳቦ\nእራት: እንጀራ+ስልስ+ሽሮ",
    "ማክሰኞ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ድንች\nእራት: እንጀራ+ድንች",
    "እሮብ": "ቁርስ: 2 ዳቦ+ማኮሮኒ+ሻይ\nምሳ: እንጀራ+ድንች\nእራት: እንጀራ+ክክ",
    "ሐሙስ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ሽሮ\nእራት: እንጀራ+ሽሮ",
    "ዓርብ": "ቁርስ: 2 ዳቦ+ሻይ\nምሳ: እንጀራ+ድንች+ሽሮ\nእራት: እንጀራ+ሽሮ",
    "ቅዳሜ": "ቁርስ: 2 ዳቦ+ሩዝ+ሻይ\nምሳ: እንጀራ+ክክ\nእራት: እንጀራ+ስልስ+ሽሮ",
    "እሁድ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ሽሮ+ስልስ\nእራት: እንጀራ+ክክ",
}

# LOCATIONS DATA
locations = {
    "አሪድ": "500m ወደ ሰሜን",
    "ቢዝነስ": "300m ወደ ምስራቅ",
    "ዓይደር": "200m ወደ ምዕራብ",
    "ዲያስፖራ": "400m ወደ ደቡብ",
}

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Menu ይምረጡ", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))

# HANDLE
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🍽 ምግብ":
        await update.message.reply_text("ቀን ይምረጡ", reply_markup=ReplyKeyboardMarkup(days_menu, resize_keyboard=True))

    elif text in food:
        await update.message.reply_text(food[text])

    elif text == "📍 Location":
        await update.message.reply_text("Location ይምረጡ", reply_markup=ReplyKeyboardMarkup(location_menu, resize_keyboard=True))

    elif text in locations:
        await update.message.reply_text(locations[text])

    elif text == "❓ Help":
        await update.message.reply_text("ምግብ ወይም location ይምረጡ")

    elif text == "🔙 Back":
        await update.message.reply_text("Menu", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))

# RUN
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot is running...")
app.run_polling()
