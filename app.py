import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import cv2
import random
import re
from pyzbar.pyzbar import decode
from PIL import Image
from datetime import datetime

# ==========================================
# የደህንነት ማረጋገጫ (Password Login)
# ==========================================
def check_password():
    """ተጠቃሚው ትክክለኛ ፓስወርድ ማስገባቱን ያረጋግጣል"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown("<h2 style='text-align: center;'>🔐 እባክዎ መጀመሪያ ይግቡ</h2>", unsafe_allow_html=True)
        password = st.text_input("የይለፍ ቃል (Password) ያስገቡ፦", type="password")
        if st.button("ግባ"):
            # የይለፍ ቃሉን እዚህ ጋር መቀየር ትችላለህ (ለምሳሌ 'የአንተ_ምስጢር')
            if password == "1234": 
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ የተሳሳተ የይለፍ ቃል!")
        return False
    return True

if check_password():
    # ==========================================
    # ዳታቤዝ ማዋቀር
    # ==========================================
    DB_FILE = "lottery_database.db"
    MAX_TICKETS = 5000

    st.set_page_config(page_title="የእጣ መቆጣጠሪያ", layout="centered")

    def get_db_connection():
        conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=30)
        return conn

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE,
        bank_name TEXT,
        sender_name TEXT,
        receiver_name TEXT,
        amount REAL,
        status TEXT,
        ticket_numbers TEXT,
        customer_name TEXT,
        customer_phone TEXT,
        created_at TEXT
    )
    """)
    conn.commit()

    # ==========================================
    # የQR ኮድ ማንበቢያ
    # ==========================================
    def parse_receipt_qr(qr_data):
        bank_name = "Unknown Bank"
        tx_id = f"MANUAL-{random.randint(100000, 999999)}"
        if "telebirr" in qr_data.lower() or "webapi.mytelebirr.et" in qr_data:
            bank_name = "Telebirr"
            match = re.search(r'transactionId=([A-Za-z0-9]+)', qr_data)
            if match:
                tx_id = match.group(1)
        elif "cbe" in qr_data.lower() or "combanketh" in qr_data.lower():
            bank_name = "CBE"
            match = re.search(r'v2-([A-Za-z0-9]+)', qr_data)
            if match:
                tx_id = match.group(1)
        return bank_name, tx_id

    def advanced_qr_reader(pil_image):
        try:
            detected_qrs = decode(pil_image)
            if detected_qrs:
                return detected_qrs[0].data.decode('utf-8')
        except:
            pass
        return None

    def generate_sequential_tickets(count):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticket_numbers FROM transactions WHERE status = 'APPROVED'")
        used_tickets = set()
        for row in cursor.fetchall():
            if row[0]:
                for num in row[0].split(","):
                    try:
                        used_tickets.add(int(num.strip()))
                    except:
                        pass
        generated = []
        current_num = 1
        while len(generated) < count:
            if current_num not in used_tickets:
                generated.append(current_num)
            current_num += 1
            if current_num > MAX_TICKETS:
                break
        return generated

    def is_valid_phone(phone_str):
        phone_clean = re.sub(r'\s+', '', phone_str)
        return bool(re.match(r'^(09|07)\d{8}$', phone_clean))

    # ==========================================
    # በሞባይል ስክሪን የተስተካከለ UI
    # ==========================================
    st.title("🏆 የዕጣ መቆጣጠሪያ")
    
    menu = st.tabs(["📤 አዲስ መመዝገቢያ", "📋 ባለዕድሎች", "🔍 ፈልግ"])

    # 1. መመዝገቢያ ገጽ
    with menu[0]:
        uploaded_file = st.file_uploader("የደረሰኝ ፎቶ ይጫኑ", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, width=250)
            qr_data = advanced_qr_reader(image)
            
            bank_detected = "ያልታወቀ ባንክ"
            detected_tx_id = f"MANUAL-{random.randint(100000, 999999)}"
            
            if qr_data:
                bank_detected, detected_tx_id = parse_receipt_qr(qr_data)
                st.success(f"✅ QR ተገኝቷል! {bank_detected}")
            
            bank_name = st.text_input("ባንክ", value=bank_detected)
            tx_id = st.text_input("Ref ID", value=detected_tx_id)
            sender = st.text_input("ላኪ (Sender)")
            receiver = st.text_input("ተቀባይ (Receiver)")
            amount = st.number_input("የብር መጠን", min_value=1.0)
            
            st.markdown("---")
            c_name = st.text_input("የባለዕድሉ ስም")
            c_phone = st.text_input("ስልክ ቁጥር (10 አሃዝ)")
            ticket_count = st.number_input("የትኬት ብዛት", min_value=1, value=1)
            
            ticket_mode = st.radio("የእጣ ቁጥር አሰጣጥ", ["በራስ-ሰር ጀነሬት (+1)", "እኔ ልጻፍ"])
            custom_tickets = ""
            if ticket_mode == "እኔ ልጻፍ":
                custom_tickets = st.text_input("የእጣ ቁጥሮቹን በኮማ በመለየት ያስገቡ")
                
            if st.button("አረጋግጥና መዝግብ"):
                if not is_valid_phone(c_phone):
                    st.error("❌ ስልክ ቁጥሩ ግድ 10 አሃዝ መሆን አለበት (በ09 ወይም 07 የሚጀምር)!")
                elif not c_name:
                    st.error("❌ እባክዎ ስም ያስገቡ!")
                else:
                    final_tickets_str = ""
                    if ticket_mode == "በራስ-ሰር ጀነሬት (+1)":
                        generated_nums = generate_sequential_tickets(ticket_count)
                        final_tickets_str = ",".join(map(str, generated_nums))
                    else:
                        final_tickets_str = custom_tickets
                        
                    if final_tickets_str:
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("""
                            INSERT INTO transactions 
                            (transaction_id, bank_name, sender_name, receiver_name, amount, status, ticket_numbers, customer_name, customer_phone, created_at)
                            VALUES (?, ?, ?, ?, ?, 'APPROVED', ?, ?, ?, ?)
                        """, (tx_id, bank_name, sender, receiver, amount, final_tickets_str, c_name, c_phone, current_time))
                        conn.commit()
                        st.success(f"🎉 በተሳካ ሁኔታ ተመዝግቧል! የእጣ ቁጥር፦ {final_tickets_str}")
                        st.balloons()

    # 2. የተመዘገቡት ዝርዝር
    with menu[1]:
        st.subheader("📋 የባለዕድሎች ዝርዝር")
        df = pd.read_sql_query("SELECT customer_name as 'ስም', ticket_numbers as 'እጣ', customer_phone as 'ስልክ' FROM transactions WHERE status = 'APPROVED'", conn)
        if df.empty:
            st.info("ምንም የተመዘገበ ባለዕድል የለም።")
        else:
            st.dataframe(df, use_container_width=True)

    # 3. ፈልግ
    with menu[2]:
        st.subheader("🔍 ፈጣን መፈለጊያ")
        search_query = st.text_input("ስልክ፣ ስም ወይም እጣ ቁጥር ያስገቡ...")
        if search_query:
            cursor.execute("SELECT customer_name, customer_phone, ticket_numbers, bank_name, amount FROM transactions WHERE customer_name LIKE ? OR customer_phone LIKE ? OR ticket_numbers LIKE ?", (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
            results = cursor.fetchall()
            if results:
                for r in results:
                    st.info(f"👤 ስም፦ {r[0]} | 📞 ስልክ፦ {r[1]} | 🎫 እጣ፦ {r[2]} | 🏦 ባንክ፦ {r[3]} ({r[4]} ETB)")
            else:
                st.error("ምንም አልተገኘም!")
