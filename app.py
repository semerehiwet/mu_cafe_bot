import streamlit as st
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import re
import io
import psycopg2

# ==========================================
# 1. የዳታቤዝ ግንኙነት (አስተማማኝ ግንኙነት)
# ==========================================
def get_db_connection():
    # በተደጋጋሚ መከፈት/መዘጋትን ለመቀነስ የስትሪምሊት connection መጠቀም ይቻላል
    # ግን እንደነበረው እንዲቀጥል በዚህ መልክ አድርጌዋለሁ
    connection_string = "postgresql://postgres.ocetuxtkfbrepihgddco:semo27537572@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
    return psycopg2.connect(connection_string)

# ==========================================
# 2. የ Caching ተግባራት (ለፍጥነት)
# ==========================================
@st.cache_data(ttl=600)
def get_allocated_tickets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_numbers FROM customer_tickets WHERE ticket_numbers != '' AND ticket_numbers IS NOT NULL")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    used = set()
    for row in rows:
        for num in row[0].split(","):
            if num.strip():
                used.add(int(num.strip()))
    return used

# ==========================================
# 3. የደህንነት እና ሌሎች ተግባራት
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "125536":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.subheader("🔑 የአስተዳዳሪ መግቢያ")
        st.text_input("የይለፍ ቃል ያስገቡ", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.error("❌ የተሳሳተ የይለፍ ቃል!")
        st.text_input("የይለፍ ቃል ያስገቡ", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password():
    st.stop()

def parse_qr_data(qr_text):
    if "telebirr" in qr_text.lower() or "webapi.mytelebirr.et" in qr_text:
        tx_match = re.search(r'transactionId=([A-Za-z0-9]+)', qr_text)
        return tx_match.group(1) if tx_match else "QR-Telebirr"
    elif "cbe" in qr_text.lower() or "combanketh" in qr_text.lower():
        tx_match = re.search(r'v2-([A-Za-z0-9]+)', qr_text)
        return tx_match.group(1) if tx_match else qr_text.split('/')[-1]
    else:
        tx_match = re.search(r'(?:TXN|Ref|ID|Transaction)[:=\s-]*([A-Za-z0-9]+)', qr_text, re.IGNORECASE)
        return tx_match.group(1) if tx_match else f"QR-{qr_text[:12]}"

def generate_auto_tickets(count, used_tickets):
    allocated = []
    current = 1
    while len(allocated) < count and current <= 2500:
        if current not in used_tickets: allocated.append(current)
        current += 1
    return allocated

# ==========================================
# 4. ዋናው UI (ምንም አልተቀየረም)
# ==========================================
st.title("🏆 የስጦታ ዕጣ መቆጣጠሪያ ዌብሳይት")

if st.sidebar.button("🔒 መተግበሪያውን ዝጋ (Logout)"):
    st.session_state["password_correct"] = False
    st.rerun()

menu = st.tabs(["📤 አዲስ ደረሰኝ መመዝገቢያ", "📋 የተመዘገቡ ዕጣዎች ዝርዝር", "⚙️ የዕጣ ቁጥሮች ዳግም ማስጀመሪያ (Reset)"])

with menu[0]:
    uploaded_file = st.file_uploader("Screenshot መርጠው ያስገቡ...", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        image = Image.open(uploaded_file)
        detected_qr = decode(image)
        if detected_qr:
            tx_id = parse_qr_data(detected_qr[0].data.decode('utf-8'))
            # መረጃን ለመፈተሽ
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM customer_tickets WHERE transaction_id = %s", (tx_id,))
            exists = cursor.fetchone()
            cursor.close()
            conn.close()

            if exists:
                st.error("🚨 ይህ ደረሰኝ አስቀድሞ ተመዝግቧል!")
            else:
                edit_amount = st.number_input("የተላከው ብር መጠን", min_value=0.0, step=1.0)
                c_name = st.text_input("የባለዕድሉ ሙሉ ስም")
                c_phone = st.text_input("የባለዕድሉ ስልክ")
                
                if st.button("አረጋግጥ እና መዝግብ"):
                    used = get_allocated_tickets()
                    tickets = generate_auto_tickets(int(edit_amount // 2500), used)
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO customer_tickets (transaction_id, customer_name, customer_phone, ticket_numbers, amount) VALUES (%s, %s, %s, %s, %s)",
                                   (tx_id, c_name, c_phone, ",".join(map(str, tickets)), edit_amount))
                    conn.commit()
                    conn.close()
                    
                    st.success("✅ ተመዝግቧል!")
                    st.cache_data.clear() # Cache-ውን አድስ
                    st.rerun()

with menu[1]:
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM customer_tickets WHERE ticket_numbers != ''", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)
    
with menu[2]:
    if st.button("🚀 አዲሱን ዙር በይፋ ጀምር"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE customer_tickets SET ticket_numbers = ''")
        conn.commit()
        conn.close()
        st.cache_data.clear() # Cache-ውን አጽዳ
        st.rerun()
