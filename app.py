import streamlit as st
import psycopg2
import pandas as pd
import re
import random
from PIL import Image
from pyzbar.pyzbar import decode
import io

# ==========================================
# 1. የዳታቤዝ ግንኙነት (ከSecrets የሚነበብ)
# ==========================================
def get_db_connection():
    # በStreamlit Secrets ውስጥ የተቀመጠውን DATABASE_URL ይጠቀማል
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# ሰንጠረዡን መፍጠር (ከሌለ)
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lottery_tickets (
        id SERIAL PRIMARY KEY,
        transaction_id VARCHAR(100) UNIQUE, 
        bank_name VARCHAR(100),
        customer_name VARCHAR(100),
        customer_phone VARCHAR(20),
        ticket_numbers TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# መተግበሪያውን ስታስጀምር ዳታቤዙን አዘጋጅ
init_db()

st.set_page_config(page_title="የእጣ መቆጣጠሪያ", layout="centered")

# ==========================================
# 2. የQR ኮድ ማንበቢያ
# ==========================================
def parse_receipt_qr(qr_data):
    # ባንኮችን እና መለያ ቁጥራቸውን ለመለየት
    if "telebirr" in qr_data.lower() or "webapi.mytelebirr.et" in qr_data:
        match = re.search(r'transactionId=([A-Za-z0-9]+)', qr_data)
        return "Telebirr", (match.group(1) if match else f"TEL-{random.randint(1000, 9999)}")
    elif "cbe" in qr_data.lower() or "combanketh" in qr_data.lower():
        match = re.search(r'v2-([A-Za-z0-9]+)', qr_data)
        return "CBE", (match.group(1) if match else f"CBE-{random.randint(1000, 9999)}")
    return "ሌላ ባንክ", f"MANUAL-{random.randint(10000, 99999)}"

# ==========================================
# 3. የእጣ ማመንጫ (Sequential)
# ==========================================
def generate_sequential_tickets(count):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_numbers FROM lottery_tickets")
    all_data = cursor.fetchall()
    
    used_tickets = set()
    for row in all_data:
        if row[0]:
            for num in row[0].split(","):
                used_tickets.add(int(num.strip()))
    
    generated = []
    current_num = 1
    while len(generated) < count:
        if current_num not in used_tickets:
            generated.append(current_num)
        current_num += 1
    cursor.close()
    conn.close()
    return generated

# ==========================================
# 4. ዋናው ገጽ (UI)
# ==========================================
st.title("🏆 የዕጣ መቆጣጠሪያ ሲስተም")

menu = st.tabs(["📤 አዲስ ምዝገባ", "📋 ዝርዝር"])

with menu[0]:
    uploaded_file = st.file_uploader("ደረሰኝ ፎቶ (Screenshot)", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, width=200)
        
        # QR መፈተሽ
        detected = decode(image)
        bank_detected, tx_id = ("ያልታወቀ", "N/A")
        if detected:
            qr_data = detected[0].data.decode('utf-8')
            bank_detected, tx_id = parse_receipt_qr(qr_data)
            st.success(f"✅ {bank_detected} ደረሰኝ ተገኝቷል!")
        else:
            st.warning("⚠️ QR ኮድ አልተገኘም፣ መረጃውን በእጅ ይሙሉ")

        # መረጃ ማስገቢያ
        c_name = st.text_input("የባለዕድሉ ስም")
        c_phone = st.text_input("ስልክ ቁጥር (09/07...)")
        ticket_count = st.number_input("የሚሰጠው የእጣ ብዛት", min_value=1, value=1)
        tx_id_input = st.text_input("Ref ID", value=tx_id)

        if st.button("መዝግብ"):
            if not c_phone or len(c_phone) < 10:
                st.error("❌ ትክክለኛ ስልክ ቁጥር ያስገቡ")
            else:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    tickets = generate_sequential_tickets(ticket_count)
                    tickets_str = ",".join(map(str, tickets))
                    
                    cursor.execute("""
                        INSERT INTO lottery_tickets (transaction_id, bank_name, customer_name, customer_phone, ticket_numbers)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (tx_id_input, bank_detected, c_name, c_phone, tickets_str))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"🎉 ተመዝግቧል! የእጣ ቁጥሮች፦ {tickets_str}")
                except psycopg2.errors.UniqueViolation:
                    st.error("🚨 ይህ ደረሰኝ ቀድሞ ተመዝግቧል!")
                except Exception as e:
                    st.error(f"ስህተት፦ {e}")

with menu[1]:
    st.subheader("📋 የባለዕድሎች ዝርዝር")
    try:
        conn = get_db_connection()
        df = pd.read_sql("SELECT customer_name as ስም, customer_phone as ስልክ, ticket_numbers as እጣ, transaction_id as ID FROM lottery_tickets ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
    except:
        st.info("መረጃ ባዶ ነው።")
