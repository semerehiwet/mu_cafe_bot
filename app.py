import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import re
import io

# ==========================================
# 1. የዳታቤዝ ግንኙነት (eu-west-1 Session Pooler 5432 በመጠቀም)
# ==========================================
def get_db_connection():
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
# 2. የደህንነት መቆጣጠሪያ (አስተዳዳሪ መግቢያ)
# ==========================================
def check_password():
    """የይለፍ ቃል ትክክል ከሆነ True ይመልሳል፣ ካልሆነ ግን የመግቢያ ፎርም ያሳያል"""
    def password_entered():
        if st.session_state["password"] == "Mebrit@2026": # <--- የይለፍ ቃልህን እዚህ መቀየር ትችላለህ
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # የይለፍ ቃሉን ከሴሽን ለማጥፋት
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # ገና መግቢያው ከሆነ
        st.subheader("🔑 የአስተዳዳሪ መግቢያ")
        st.text_input("የይለፍ ቃል ያስገቡ", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # የይለፍ ቃል ከተሳሳተ
        st.subheader("🔑 የአስተዳዳሪ መግቢያ")
        st.text_input("የይለፍ ቃል ያስገቡ", type="password", on_change=password_entered, key="password")
        st.error("❌ የተሳሳተ የይለፍ ቃል! እባክዎ እንደገና ይሞክሩ።")
        return False
    else:
        # የይለፍ ቃል ትክክል ከሆነ
        return True

# የይለፍ ቃሉ ካልተረጋገጠ አፑን እዚህ ጋር ያቆመዋል
if not check_password():
    st.stop()

# ==========================================
# 3. QR ኮድ አንባቢ
# ==========================================
def parse_qr_data(qr_text):
    tx_id = "N/A"
    
    # የቴሌብር (Telebirr) QR ኮድ ከሆነ
    if "telebirr" in qr_text.lower() or "webapi.mytelebirr.et" in qr_text:
        tx_match = re.search(r'transactionId=([A-Za-z0-9]+)', qr_text)
        if tx_match:
            tx_id = tx_match.group(1)
        
    # የንግድ ባንክ (CBE) QR ኮድ ከሆነ
    elif "cbe" in qr_text.lower() or "combanketh" in qr_text.lower() or "cbebirr" in qr_text.lower():
        tx_match = re.search(r'v2-([A-Za-z0-9]+)', qr_text)
        if tx_match:
            tx_id = tx_match.group(1)
        else:
            tx_id = qr_text.split('/')[-1] if '/' in qr_text else qr_text
            
    # ሌላ
    else:
        tx_match = re.search(r'(?:TXN|Ref|ID|Transaction)[:=\s-]*([A-Za-z0-9]+)', qr_text, re.IGNORECASE)
        if tx_match:
            tx_id = tx_match.group(1)
        else:
            tx_id = f"QR-{qr_text[:12]}"
            
    return tx_id

# ==========================================
# 4. የዕጣ ቁጥር ማመንጫ (ከ 1 እስከ 2500)
# ==========================================
def get_allocated_tickets():
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
    allocated = []
    current = 1
    while len(allocated) < count and current <= 2500:
        if current not in used_tickets:
            allocated.append(current)
        current += 1
    return allocated

# ==========================================
# 5. የዌብሳይት ዲዛይን (UI)
# ==========================================
st.title("🏆 የስጦታ ዕጣ መቆጣጠሪያ ዌብሳይት")

# Logout ማድረጊያ በተን በቀኝ በኩል
if st.sidebar.button("🔒 መተግበሪያውን ዝጋ (Logout)"):
    st.session_state["password_correct"] = False
    st.rerun()

menu = st.tabs(["📤 አዲስ ደረሰኝ መመዝገቢያ", "📋 የተመዘገቡ ዕጣዎች ዝርዝር"])

with menu[0]:
    st.subheader("የባንክ ደረሰኝ ፎቶ እዚህ ያስገቡ")
    uploaded_file = st.file_uploader("Screenshot መርጠው ያስገቡ...", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="የተጫነው ደረሰኝ", width=300)
        
        detected_qr = decode(image)
        
        if detected_qr:
            qr_text = detected_qr[0].data.decode('utf-8')
            tx_id = parse_qr_data(qr_text)
            
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM customer_tickets WHERE transaction_id = %s", (tx_id,))
            existing_record = cursor.fetchone()
            cursor.close()
            conn.close()
            
            st.markdown("---")
            st.subheader("🔍 የደረሰኝ ማረጋገጫ ሊንክ")
            
            if qr_text.startswith("http"):
                st.link_button("🌐 ወደ ባንክ መረጃው ቀጥታ ለመሄድ እዚህ ይጫኑ", qr_text, use_container_width=True, type="primary")
                st.info(f"🔗 **የ QR Code ሙሉ ሊንክ፦** {qr_text}")
            else:
                st.warning("⚠️ በQR ኮዱ ውስጥ ምንም የድረ-ገጽ ሊንክ አልተገኘም!")
            
            st.markdown("---")
            
            # የተደገመ ደረሰኝ ምርመራ
            if existing_record:
                st.error(f"""
                🚨 **ይህ ደረሰኝ ቀደም ሲል ጥቅም ላይ ውሏል! (የተደገመ ደረሰኝ)**
                
                * **የተመዘገበበት ስም፦** {existing_record['customer_name']} 
                * **የተሰጠው የዕጣ ቁጥር፦** {existing_record['ticket_numbers']} 🎫
                * **ስልክ ቁጥር፦** {existing_record['customer_phone']}
                """)
                st.stop()
            else:
                st.success("✅ አዲስ ደረሰኝ! ከዚህ በፊት ጥቅም ላይ አልዋለም።")
            
            st.subheader("📝 የደረሰኝ መረጃዎች")
            edit_tx_id = st.text_input("የግብይት መለያ (Transaction ID)", value=tx_id)
            edit_amount = st.number_input("የተላከው ብር መጠን (Amount)", min_value=0.0, step=1.0)
            edit_sender = st.text_input("የላኪ ስም (Sender Name)", placeholder="የላኪውን ስም እዚህ ይጻፉ...")
            edit_receiver = st.text_input("የተቀባይ ስም (Receiver Name)", placeholder="የተቀባዩን ስም እዚህ ይጻፉ...")
            
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
            if st.button("አረጋግጥ እና መዝግብ (Accept & Save)"):
                if not c_name or not c_phone:
                    st.error("❌ እባክዎ የስም እና ስልክ መረጃዎችን ይሙሉ!")
                elif edit_amount <= 0:
                    st.error("❌ እባክዎ የተላከውን የብር መጠን ያስገቡ!")
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

# ==========================================
# 6. የተመዘገቡ ባለዕድሎች ዝርዝር እና የኤክሰል ማውረጃ
# ==========================================
with menu[1]:
    st.subheader("📋 የተመዘገቡ ባለዕድሎች ዝርዝር")
    search_query = st.text_input("በስም፣ በስልክ ቁጥር ወይም በዕጣ ቁጥር ይፈልጉ...")
    
    db_rows = []
    try:
        conn = get_db_connection()
        if search_query:
            query = """
                SELECT customer_name as ስም, customer_phone as ስልክ, ticket_numbers as "የዕጣ ቁጥሮች", amount as ብር, sender_name as ላኪ, receiver_name as ተቀባይ, transaction_id as "Ref ID", created_at as ቀን 
                FROM customer_tickets 
                WHERE customer_name ILIKE %s 
                   OR customer_phone ILIKE %s 
                   OR ticket_numbers LIKE %s 
                   OR ticket_numbers LIKE %s
                   OR ticket_numbers LIKE %s
                   OR ticket_numbers = %s
                ORDER BY id DESC
            """
            exact_match = search_query.strip()
            param_like_start = f"%,{exact_match}"
            param_like_end = f"{exact_match},%"
            param_like_middle = f"%,{exact_match},%"
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, (
                f"%{search_query}%", 
                f"%{search_query}%", 
                param_like_start, 
                param_like_end, 
                param_like_middle, 
                exact_match
            ))
            db_rows = cursor.fetchall()
            cursor.close()
        else:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT customer_name as ስም, customer_phone as ስልክ, ticket_numbers as "የዕጣ ቁጥሮች", amount as ብር, sender_name as ላኪ, receiver_name as ተቀባይ, transaction_id as "Ref ID", created_at as ቀን 
                FROM customer_tickets 
                ORDER BY id DESC
            """)
            db_rows = cursor.fetchall()
            cursor.close()
        conn.close()
        
        if db_rows:
            df_display = pd.DataFrame(db_rows)
            st.dataframe(df_display, use_container_width=True)
            
            # --------------------------------------------------
            # 🚀 የ Excel ማዘጋጃ (የመጀመሪያው መስመር የዕጣ ቁጥር 1 እንዲሆን)
            # --------------------------------------------------
            excel_rows = []
            for i in range(1, 2501):
                excel_rows.append({
                    "የዕጣ ቁጥር": i,
                    "የባለዕድሉ ስም": "",
                    "ስልክ ቁጥር": "",
                    "የተከፈለው ብር": "",
                    "የላኪ ስም": "",
                    "የተቀባይ ስም": "",
                    "Transaction ID": "",
                    "የተመዘገበበት ቀን": ""
                })
            
            df_template = pd.DataFrame(excel_rows)
            df_template.set_index("የዕጣ ቁጥር", inplace=True)
            
            for row in db_rows:
                tickets_list = [t.strip() for t in str(row["የዕጣ ቁጥሮች"]).split(",") if t.strip()]
                for ticket in tickets_list:
                    ticket_num = int(ticket)
                    if 1 <= ticket_num <= 2500:
                        df_template.at[ticket_num, "የባለዕድሉ ስም"] = row["ስም"]
                        df_template.at[ticket_num, "ስልክ ቁጥር"] = row["ስልክ"]
                        df_template.at[ticket_num, "የተከፈለው ብር"] = float(row["ብር"])
                        df_template.at[ticket_num, "የላኪ ስም"] = row["ላኪ"]
                        df_template.at[ticket_num, "የተቀባይ ስም"] = row["ተቀባይ"]
                        df_template.at[ticket_num, "Transaction ID"] = row["Ref ID"]
                        df_template.at[ticket_num, "የተመዘገበበት ቀን"] = str(row["ቀን"])
            
            df_final = df_template.reset_index()
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # header=False በማድረግ የርዕስ ቦታው እንዲጠፋና ዕጣ ቁጥር 1 ቀጥታ ረድፍ 1 ላይ እንዲጀምር ተደርጓል
                df_final.to_excel(writer, index=False, header=False, sheet_name='ዕጣዎች በዝርዝር')
            
            st.markdown("---")
            st.subheader("📥 የዕጣዎችን ዝርዝር በExcel አውርድ")
            st.download_button(
                label="📊 ሙሉ የዕጣዎች ዝርዝር Excel አውርድ",
                data=buffer.getvalue(),
                file_name="gift_lottery_tickets.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.info("ምንም መረጃ አልተገኘም!")
            
    except Exception as e:
        st.info(f"ስህተት ተፈጥሯል፦ {e}")
