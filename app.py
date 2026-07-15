import streamlit as st
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import re
import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================
# 1. የዳታቤዝ ግንኙነት እና Caching
# ==========================================
def get_db_connection():
    return psycopg2.connect("postgresql://postgres.ocetuxtkfbrepihgddco:semo27537572@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require")

@st.cache_data(ttl=600)
def get_allocated_tickets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_numbers FROM customer_tickets WHERE ticket_numbers != '' AND ticket_numbers IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    used = set()
    for row in rows:
        for num in row[0].split(","):
            if num.strip(): used.add(int(num.strip()))
    return used

# ==========================================
# 2. የደህንነት መቆጣጠሪያ
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

# ==========================================
# 3. ዋናው UI እና ተግባራት
# ==========================================
st.title("🏆 የስጦታ ዕጣ መቆጣጠሪያ")

if st.sidebar.button("🔒 መተግበሪያውን ዝጋ (Logout)"):
    st.session_state["password_correct"] = False
    st.rerun()

menu = st.tabs(["📤 አዲስ ደረሰኝ", "📋 ዝርዝር እና ፍለጋ", "⚙️ Reset"])

with menu[0]:
    uploaded_file = st.file_uploader("ደረሰኝ ፎቶ ይጫኑ...", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        image = Image.open(uploaded_file)
        decoded = decode(image)
        if decoded:
            qr_text = decoded[0].data.decode('utf-8')
            st.info(f"🔗 **የተገኘ ሊንክ:** {qr_text}")
            if qr_text.startswith("http"):
                st.link_button("🌐 የባንክ ማረጋገጫ ይክፈቱ", qr_text)
            
            amount = st.number_input("ብር", min_value=0.0, step=1.0)
            c_name = st.text_input("ስም")
            c_phone = st.text_input("ስልክ")
            
            if st.button("መዝግብ"):
                used = get_allocated_tickets()
                num_tickets = int(amount // 2500)
                tickets = []
                curr = 1
                while len(tickets) < num_tickets and curr <= 2500:
                    if curr not in used: tickets.append(curr)
                    curr += 1
                
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO customer_tickets (transaction_id, customer_name, customer_phone, ticket_numbers, amount) VALUES (%s, %s, %s, %s, %s)",
                           (qr_text[:50], c_name, c_phone, ",".join(map(str, tickets)), amount))
                conn.commit()
                conn.close()
                st.success(f"✅ ተመዝግቧል! የተሰጡ ቁጥሮች: {tickets}")
                st.cache_data.clear()
                st.rerun()

with menu[1]:
    st.subheader("🔍 ፍለጋ እና ዝርዝር")
    search = st.text_input("በስም፣ ስልክ ወይም የዕጣ ቁጥር ይፈልጉ...")
    
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM customer_tickets WHERE ticket_numbers != ''", conn)
    conn.close()
    
    if search:
        df = df[df['customer_name'].str.contains(search, case=False, na=False) | 
                df['customer_phone'].str.contains(search, na=False) | 
                df['ticket_numbers'].str.contains(search, na=False)]
    
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Excel አውርድ", csv, "report.csv", "text/csv")

with menu[2]:
    if st.button("⚠️ አዲሱን ዙር ጀምር (Reset)"):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE customer_tickets SET ticket_numbers = ''")
        conn.commit()
        conn.close()
        st.cache_data.clear()
        st.rerun()
