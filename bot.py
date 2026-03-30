from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "YOUR_BOT_TOKEN_HERE"

# ===== MAIN MENU =====
main_menu = ReplyKeyboardMarkup(
    [
        ["📋 የምግብ ፕሮግራም"],
        ["📍 የካፌ Location"],
        ["ℹ️ Help"]
    ],
    resize_keyboard=True
)

# ===== DAYS MENU =====
days_menu = ReplyKeyboardMarkup(
    [
        ["ሰኞ", "ማክሰኞ", "እሮብ"],
        ["ሐሙስ", "ዓርብ", "ቅዳሜ"],
        ["እሁድ"]
    ],
    resize_keyboard=True
)

# ===== LOCATION MENU =====
location_menu = ReplyKeyboardMarkup(
    [
        ["አሪድ", "ቢዝነስ"],
        ["ዓይደር", "ዲያስፖራ"]
    ],
    resize_keyboard=True
)

# ===== FOOD DATA =====
food_menu = {
    "ሰኞ": "🍳 ቁርስ: ፍርፍር\n🍛 ምሳ: ሽሮ\n🍲 እራት: ዶሮ",
    "ማክሰኞ": "🍳 ቁርስ: እንቁላል\n🍛 ምሳ: ፓስታ\n🍲 እራት: ክክ",
    "እሮብ": "🍳 ቁርስ: ፍርፍር\n🍛 ምሳ: ሩዝ\n🍲 እራት: ስጋ",
    "ሐሙስ": "🍳 ቁርስ: እንቁላል\n🍛 ምሳ: ሽሮ\n🍲 እራት: ድንች",
    "ዓርብ": "🍳 ቁርስ: ፍርፍር\n🍛 ምሳ: ክክ\n🍲 እራት: ዓሣ",
    "ቅዳሜ": "🍳 ቁርስ: እንቁላል\n🍛 ምሳ: ሩዝ\n🍲 እራት: ዶሮ",
    "እሁድ": "🍳 ቁርስ: ፍርፍር\n🍛 ምሳ: ስጋ\n🍲 እራት: ክክ"
}

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 እንኳን ደህና መጡ!\n\nእባክዎ ከሚከተሉት ይምረጡ:",
        reply_markup=main_menu
    )

# ===== HANDLE MESSAGES =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # ምግብ ፕሮግራም
    if text == "📋 የምግብ ፕሮግራም":
        await update.message.reply_text("📅 ቀን ይምረጡ:", reply_markup=days_menu)

    # ቀኖች
    elif text in food_menu:
        await update.message.reply_text(f"📅 {text}\n{food_menu[text]}")

    # location
    elif text == "📍 የካፌ Location":
        await update.message.reply_text("📍 ቦታ ይምረጡ:", reply_markup=location_menu)

    elif text == "አሪድ":
        await update.message.reply_text("📍 አሪድ: ከመግቢያ በር 500 ሜትር ወደ ሰሜን")

    elif text == "ቢዝነስ":
        await update.message.reply_text("📍 ቢዝነስ: ከላይብረሪ አጠገብ")

    elif text == "ዓይደር":
        await update.message.reply_text("📍 ዓይደር: ከሆስፒታል በኩል")

    elif text == "ዲያስፖራ":
        await update.message.reply_text("📍 ዲያስፖራ: ከማዕከል ቅርብ")

    # help
    elif text == "ℹ️ Help":
        await update.message.reply_text(
            "ℹ️ ይህ bot የuniversity ምግብ ፕሮግራም ያሳያል።\n\n"
            "👉 ምግብ ለማየት → የምግብ ፕሮግራም\n"
            "👉 ቦታ ለማወቅ → Location"
        )

    else:
        await update.message.reply_text("❗ እባክዎ ከmenu ይምረጡ")

# ===== MAIN =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
