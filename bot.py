from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8146345458:AAFNkn0CwekS4aluEkYIzO8M5pni6tIAPJE"

main_menu = [["🍽 ምግብ", "📍 Location"], ["❓ Help"]]

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

food = {
    "ሰኞ": "ቁርስ: 2 ዳቦ+ሩዝ+ሻይ\nምሳ: ፓስታ+2 ዳቦ\nእራት: እንጀራ+ስልስ+ሽሮ",
    "ማክሰኞ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ድንች\nእራት: እንጀራ+ድንች",
    "እሮብ": "ቁርስ: 2 ዳቦ+ማኮሮኒ+ሻይ\nምሳ: እንጀራ+ድንች\nእራት: እንጀራ+ክክ",
    "ሐሙስ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ሽሮ\nእራት: እንጀራ+ሽሮ",
    "ዓርብ": "ቁርስ: 2 ዳቦ+ሻይ\nምሳ: እንጀራ+ድንች+ሽሮ\nእራት: እንጀራ+ሽሮ",
    "ቅዳሜ": "ቁርስ: 2 ዳቦ+ሩዝ+ሻይ\nምሳ: እንጀራ+ክክ\nእራት: እንጀራ+ስልስ+ሽሮ",
    "እሁድ": "ቁርስ: 2 ዳቦ+ፍርፍር+ሻይ\nምሳ: እንጀራ+ሽሮ+ስልስ\nእራት: እንጀራ+ክክ",
}

locations = {
    "አሪድ": "ከ መግብያ በር 500m ወደ ሰሜን",
    "ቢዝነስ": "ከ መግብያ በር (homeland hotel)750m ወደ ምዕራብ",
    "ዓይደር": "ከ መግብያ በር (ላዕለዋይ በሪ)750 ወደ ምዕራብ",
    "ዲያስፖራ": "400m ወደ ደቡብ",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Menu", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))

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
        await update.message.reply_text("እርዳታ: ምግብ ወይም location ይምረጡ")

    elif text == "🔙 Back":
        await update.message.reply_text("Menu", reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True))

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()
