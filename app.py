import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import re

# ==========================================
# 1. የዳታቤዝ ግንኙነት (eu-west-1 Session Pooler 5432 በመጠቀም)
# ==========================================
def get_db_connection():
    # ያንተ ትክክለኛ የይለፍ ቃል እና የSupabase መገናኛ አድራሻ (eu-west-1)
    connection_string = "postgresql://postgres.ocetuxtkfbrepihgddco:semo27537572@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
    return psycopg2.connect(connection_string)

# ሰንጠረዥ መፍጠሪያ
def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_tickets (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(100) UNIQUE NOT NULL,
            sender_name VARCHAR(100),
            receiver_name VARCHAR(100),
            amount DECIMAL(10, 2),
            customer_name VARCHAR(100) NOT NULL,
            customer_phone VARCHAR(20) NOT NULL,
            ticket_numbers TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"❌ የዳታቤዝ ሰንጠረዥ መፍጠር አልተቻለም፦ {e}")

init_db()

# ==========================================
# 2. QR ኮድ አንባቢ እና መረጃ መፍተኛ (የተሻሻለ)
# ==========================================
def parse_qr_data(qr_text):
    tx_id = "N/A"
    amount = 0.0
    sender = "ያልታወቀ ላኪ"
    receiver = "ያልታወቀ ተቀባይ"
    
    # 1. የቴሌብር (Telebirr) QR ኮድ ከሆነ
    if "telebirr" in qr_text.lower() or "webapi.mytelebirr.et" in qr_text:
        # Transaction ID መፈለግ
        tx_match = re.search(r'transactionId=([A-Za-z0-9]+)', qr_text)
        if tx_match:
            tx_id = tx_match.group(1)
            
        # የብር መጠን መፈለግ
        amt_match = re.search(r'amount=([0-9.]+)', qr_text)
        if amt_match:
            amount = float(amt_match.group(1))
            
        # የላኪ ስም (ካለ ለማውጣት መሞከር)
        sender_match = re.search(r'senderName=([^&]+)', qr_text)
        if sender_match:
            sender = sender_match.group(1).replace("%20", " ")
        else:
            sender = "Telebirr User (ላኪ)"
            
        # የተቀባይ ስም
        receiver_match = re.search(r'receiverName=([^&]+)', qr_text)
        if receiver_match:
            receiver = receiver_match.group(1).replace("%20", " ")
        else:
            receiver = "የቴሌብር ነጋዴ (Merchant)"
        
    # 2. የንግድ ባንክ (CBE Birr / CBE) QR ኮድ ከሆነ
    elif "cbe" in qr_text.lower() or "combanketh" in qr_text.lower() or "cbebirr" in qr_text.lower():
        # የግብይት ቁጥር መፈለግ (v2- ወይም CBE በያዘው መሠረት)
        tx_match = re.search(r'(?:v2-|TXN|Ref-)([A-Za-z0-9]+)', qr_text)
        if tx_match:
            tx_id = tx_match.group(1)
        else:
            # ሊንኩ ውስጥ በግልጽ ካልተገኘ አጠር ያለ መለያ መስጠት
            tx_id = qr_text.split('/')[-1][:15] if '/' in qr_text else "CBE-" + qr_text[:10]
            
        # የብር መጠን መፈለግ
        amt_match = re.search(r'(?:amount|amt|val)=([0-9.]+)', qr_text, re.IGNORECASE)
        if amt_match:
            amount = float(amt_match.group(1))
            
        # የላኪ ስም
        sender_match = re.search(r'(?:sender|from)=([^&]+)', qr_text, re.IGNORECASE)
        if sender_match:
            sender = sender_match.group(1).replace("%20", " ")
        else:
            sender = "CBE User (ላኪ)"
            
        # የተቀባይ ስም
        receiver_match = re.search(r'(?:receiver|to)=([^&]+)', qr_text, re.IGNORECASE)
        if receiver_match:
            receiver = receiver_match.group(1).replace("%20", " ")
        else:
            receiver = "የንግድ ባንክ አካውንት"
            
    # 3. ሌላ ማንኛውም የባንክ QR ኮድ ከሆነ
    else:
        # አጠቃላይ ጽሑፉን መፈተሽ
        tx_match = re.search(r'(?:TXN|Ref|ID|Transaction)[:=\s-]*([A-Za-z0-9]+)', qr_text, re.IGNORECASE)
        if tx_match:
            tx_id = tx_match.group(1)
        else:
            tx_id = f"QR-{qr_text[:12]}"
            
        amt_match = re.search(r'(?:amount|amt|ብር|ብር መጠን)[:=\s-]*([0-9.]+)', qr_text, re.IGNORECASE)
        if amt_match:
            amount = float(amt_match.group(1))
            
    return tx_id, amount, sender, receiver

# ==========================================
# 3. የዕጣ ቁጥር ማመንጫ (ከ 1 እስከ 2500)
# ==========================================
def get_allocated_tickets():
    """ቀድሞ የተያዙ የዕጣ ቁጥሮችን በሙሉ ይመልሳል"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticket_numbers FROM customer_tickets")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    used = set()
    for row in rows:
        for num in row[0].split(","):
            if num.strip():
                used.add(int(num.strip()))
    return used

def generate_auto_tickets(count, used_tickets):
    """ከ1 እስከ 2500 ባለው ውስጥ ያልተያዙ የዕጣ ቁጥሮችን በቅደም ተከተል ይሰጣል"""
    allocated = []
    current = 1
    while len(allocated) < count and current <= 2500:
        if current not in used_tickets:
            allocated.append(current)
        current += 1
    return allocated

# ==========================================
# 4. የዌብሳይት ዲዛይን (UI)
# ==========================================
st.set_page_config(page_title="የስጦታ ዕጣ መቆጣጠሪያ", layout="centered")
st.title("🏆 የስጦታ ዕጣ መቆጣጠሪያ ዌብሳይት")

menu = st.tabs(["📤 አዲስ ደረሰኝ መመዝገቢያ", "📋 የተመዘገቡ ዕጣዎች ዝርዝር"])

with menu[0]:
    st.subheader("የባንክ ደረሰኝ ፎቶ እዚህ ያስገቡ")
    uploaded_file = st.file_uploader("Screenshot መርጠው ያስገቡ...", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="የተጫነው ደረሰኝ", width=300)
        
        # QR ኮዱን ማንበብ
        detected_qr = decode(image)
        
        if detected_qr:
            qr_text = detected_qr[0].data.decode('utf-8')
            tx_id, amount, sender, receiver = parse_qr_data(qr_text)
            
            # በዳታቤዝ ውስጥ ደረሰኙ ቀድሞ መኖሩን ማረጋገጥ
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM customer_tickets WHERE transaction_id = %s", (tx_id,))
            existing_record = cursor.fetchone()
            cursor.close()
            conn.close()
            
            st.markdown("---")
            st.subheader("🔍 ከQR ኮድ የተገኙ ዝርዝር መረጃዎች")
            
            # የQR ኮዱን ትክክለኛ ሊንክ/ጽሑፍ እዚህ በግልጽ እናሳያለን
            st.info(f"🔗 **ትክክለኛ የ QR Code ሊንክ (Raw Data)፦** \n`{qr_text}`")
            
            # የደረሰኝ ድግግሞሽ ቼክ
            if existing_record:
                st.error(f"🚨 ይህ ደረሰኝ ቀደም ሲል ጥቅም ላይ ውሏል! (የተደገመ ደረሰኝ) \n\n* የተመዘገበበት ስም፦ {existing_record['customer_name']} \n* የዕጣ ቁጥሮች፦ {existing_record['ticket_numbers']}")
                st.stop() # አፑ እዚህ ላይ ይቆማል፣ እንዲመዘገብ አይፈቅድም
            else:
                st.success("✅ አዲስ ደረሰኝ! ከዚህ በፊት ጥቅም ላይ አልዋለም።")
            
            # መረጃውን በእጅ ማስተካከል እና ማየት እንዲቻል በሳጥን ማሳየት
            edit_tx_id = st.text_input("የግብይት መለያ (Transaction ID)", value=tx_id)
            edit_amount = st.number_input("የተላከው ብር መጠን", value=float(amount), min_value=0.0)
            edit_sender = st.text_input("የላኪ ስም (Sender Name)", value=sender)
            edit_receiver = st.text_input("የተቀባይ ስም (Receiver Name)", value=receiver)
            
            st.markdown("---")
            st.subheader("👤 የባለዕድሉ መረጃ")
            c_name = st.text_input("የባለዕድሉ ሙሉ ስም")
            c_phone = st.text_input("የባለዕድሉ ስልክ ቁጥር")
            
            st.markdown("---")
            st.subheader("🎫 የዕጣ አሰጣጥ ዘዴ")
            ticket_count = st.number_input("ስንት ትኬት ይፈቀድለታል?", min_value=1, value=1, step=1)
            
            allocation_mode = st.radio("የዕጣ ቁጥር መመደቢያ መንገድ፦", ["በራስ-ሰር (ከ1-2500 በቅደም ተከተል +1)", "በእጅ ለመምረጥ (በራስህ ቁጥር ለመስጠት)"])
            
            used_tickets = get_allocated_tickets()
            final_tickets = []
            
            if allocation_mode == "በራስ-ሰር (ከ1-2500 በቅደም ተከተል +1)":
                auto_gen = generate_auto_tickets(ticket_count, used_tickets)
                if len(auto_gen) < ticket_count:
                    st.warning("⚠️ በቂ ክፍት የዕጣ ቁጥር ከ 1 እስከ 2500 ውስጥ አልተገኘም!")
                else:
                    final_tickets = auto_gen
                    st.info(f"💡 የሚሰጡት የዕጣ ቁጥሮች፦ {', '.join(map(str, final_tickets))}")
            else:
                manual_input = st.text_input("የዕጣ ቁጥሮችን በኮማ (,) በመለየት ያስገቡ (ለምሳሌ፦ 5, 12, 105)፦")
                if manual_input:
                    try:
                        temp_tickets = [int(x.strip()) for x in manual_input.split(",") if x.strip()]
                        # ድግግሞሽ ቼክ
                        conflicts = [t for t in temp_tickets if t in used_tickets]
                        out_of_range = [t for t in temp_tickets if t < 1 or t > 2500]
                        
                        if conflicts:
                            st.error(f"❌ እነዚህ የዕጣ ቁጥሮች ቀድሞውኑ ተይዘዋል፦ {conflicts}")
                        elif out_of_range:
                            st.error(f"❌ እባክዎ ከ 1 እስከ 2500 ያሉ ቁጥሮችን ብቻ ያስገቡ!")
                        elif len(temp_tickets) != ticket_count:
                            st.warning(f"⚠️ የጻፍካቸው ቁጥሮች ብዛት ({len(temp_tickets)}) እና የፈቀድከው የትኬት ብዛት ({ticket_count}) አይዛመድም!")
                        else:
                            final_tickets = temp_tickets
                            st.success("✅ የመረጥካቸው ቁጥሮች በሙሉ ክፍት ናቸው!")
                    except ValueError:
                        st.error("❌ እባክዎ ቁጥሮችን ብቻ ያስገቡ!")
            
            st.markdown("---")
            # የመመዝገቢያ አዝራር
            if st.button("አረጋግጥ እና መዝግብ (Accept & Save)"):
                if not c_name or not c_phone:
                    st.error("❌ እባክዎ የስም እና ስልክ መረጃዎችን ይሙሉ!")
                elif not final_tickets:
                    st.error("❌ የሚሰጥ የዕጣ ቁጥር አልተመረጠም!")
                else:
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        tickets_str = ",".join(map(str, final_tickets))
                        
                        cursor.execute("""
                            INSERT INTO customer_tickets (transaction_id, sender_name, receiver_name, amount, customer_name, customer_phone, ticket_numbers)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (edit_tx_id, edit_sender, edit_receiver, edit_amount, c_name, c_phone, tickets_str))
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.balloons()
                        st.success(f"🎉 መረጃው በተሳካ ሁኔታ ተመዝግቧል! የተሰጡት የዕጣ ቁጥሮች፦ {tickets_str}")
                    except psycopg2.errors.UniqueViolation:
                        st.error("🚨 ይህ የግብይት መለያ (Transaction ID) ቀደም ሲል ተመዝግቧል!")
                    except Exception as e:
                        st.error(f"ስህተት አጋጥሟል፦ {e}")
        else:
            st.error("❌ በምስሉ ላይ ምንም የQR ኮድ ሊነበብ አልቻለም! እባክዎ ግልጽ የሆነ ፎቶ ይጫኑ።")

with menu[1]:
    st.subheader("📋 የተመዘገቡ ባለዕድሎች ዝርዝር")
    
    search_query = st.text_input("በስም ወይም በስልክ ይፈልጉ...")
    
    try:
        conn = get_db_connection()
        if search_query:
            query = """
                SELECT customer_name as ስም, customer_phone as ስልክ, ticket_numbers as "የዕጣ ቁጥሮች", amount as ብር, sender_name as ላኪ, receiver_name as ተቀባይ, transaction_id as "Ref ID", created_at as ቀን 
                FROM customer_tickets 
                WHERE customer_name ILIKE %s OR customer_phone ILIKE %s 
                ORDER BY id DESC
            """
            df = pd.read_sql(query, conn, params=(f"%{search_query}%", f"%{search_query}%"))
        else:
            df = pd.read_sql("""
                SELECT customer_name as ስም, customer_phone as ስልክ, ticket_numbers as "የዕጣ ቁጥሮች", amount as ብር, sender_name as ላኪ, receiver_name as ተቀባይ, transaction_id as "Ref ID", created_at as ቀን 
                FROM customer_tickets 
                ORDER BY id DESC
            """, conn)
        conn.close()
        
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.info("ምንም መረጃ የለም ወይም ስህተት ተፈጥሯል!")
