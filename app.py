Import streamlit as st
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
        if st.session_state["password"] == "125536": # <--- የይለፍ ቃልሽ እዚህ ተቀምጧል
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # የይለፍ ቃሉን ከሴሽን ለማጥፋት
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.subheader("🔑 የአስተዳዳሪ መግቢያ")
        st.text_input("የይለፍ ቃል ያስገቡ", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.subheader("🔑 የአስተዳዳሪ መግቢያ")
        st.text_input("የይለፍ ቃል ያስገቡ", type="password", on_change=password_entered, key="password")
        st.error("❌ የተሳሳተ የይለፍ ቃል! እባክዎ እንደገና ይሞክሩ።")
        return False
    else:
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

# Logout ማድረጊያ በተን በስተግራ በኩል
if st.sidebar.button("🔒 መተግበሪያውን ዝጋ (Logout)"):
    st.session_state["password_correct"] = False
    st.rerun()

# ሦስት ክፍሎች (Tabs)
menu = st.tabs(["📤 አዲስ ደረሰኝ መመዝገቢያ", "📋 የተመዘገቡ ዕጣዎች ዝርዝር", "⚙️ የዕጣ ቁጥሮች ዳግም ማስጀመሪያ (Reset)"])

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
            
            # ደረሰኝ በ 1ኛው ዙር ጥቅም ላይ ውሎ ከነበረ እዚህ ጋር ይይዘዋል!
            if existing_record:
                st.error(f"""
                🚨 **ይህ ደረሰኝ በቀደመው ዙር ጥቅም ላይ ውሏል!**
                * በመሆኑም ይህንን ደረሰኝ ለሁለተኛ ዙር መጠቀም አይቻልም።
                
                * **የቀደመው ዙር የተመዘገበበት ስም፦** {existing_record['customer_name']} 
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
            c_name = st.text_input("የባለዕድሉ ሙሉ ስም (ግዴታ ነው)")
            c_phone = st.text_input("የባለዕድሉ ስልክ ቁጥር (ግዴታ ነው - ቢያንስ 10 አሃዝ)")
            
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
                # ስልክ ቁጥሩን ቼክ ማድረጊያ Regex (ከተፈለገ በ '+' ሊጀምር ይችላል፣ በመቀጠል ቢያንስ 10 አሃዞች መኖር አለበት)
                phone_pattern = r'^\+?[0-9]{10,}$'
                clean_phone = c_phone.replace(" ", "").strip()
                
                if not c_name.strip():
                    st.error("❌ እባክዎ የባለዕድሉን ሙሉ ስም ያስገቡ!")
                elif not clean_phone:
                    st.error("❌ እባክዎ የባለዕድሉን ስልክ ቁጥር ያስገቡ!")
                elif not re.match(phone_pattern, clean_phone):
                    st.error("❌ ስህተት፦ የስልክ ቁጥሩ ቢያንስ 10 አሃዞች (ቁጥሮች) መሆን አለበት! (ምሳሌ፦ 0912345678 ወይም +251912345678)")
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
                        """, (edit_tx_id, edit_sender, edit_receiver, edit_amount, c_name.strip(), clean_phone, tickets_str))
                        
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
    
    # የፍለጋ ሳጥን
    search_query = st.text_input("በስም፣ በስልክ ቁጥር ወይም በዕጣ ቁጥር ይፈልጉ...")
    
    # 🔄 አዲሱ የመደርደሪያ ምርጫ (Sort Options)
    sort_by = st.selectbox(
        "📋 መረጃዎችን መደርደሪያ (Sort By)፦",
        [
            "በጊዜ ዝርዝር (ከአዲስ ወደ አሮጌ)", 
            "በጊዜ ዝርዝር (ከአሮጌ ወደ አዲስ)", 
            "በያዘው የዕጣ ቁጥር (ከትንሽ ወደ ትልቅ)"
        ]
    )
    
    db_rows = []
    try:
        conn = get_db_connection()
        # ለወቅታዊው ዙር የሚታዩት የዕጣ ቁጥር ያላቸው (ያልተሰረዙት) ብቻ ናቸው
        if search_query:
            query = """
                SELECT customer_name as ስም, customer_phone as ስልክ, ticket_numbers as "የዕጣ ቁጥሮች", amount as ብር, sender_name as ላኪ, receiver_name as ተቀባይ, transaction_id as "Ref ID", created_at as ቀን 
                FROM customer_tickets 
                WHERE ticket_numbers != '' AND ticket_numbers IS NOT NULL AND (
                   customer_name ILIKE %s 
                   OR customer_phone ILIKE %s 
                   OR ticket_numbers LIKE %s 
                   OR ticket_numbers LIKE %s
                   OR ticket_numbers LIKE %s
                   OR ticket_numbers = %s
                )
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
                WHERE ticket_numbers != '' AND ticket_numbers IS NOT NULL
            """)
            db_rows = cursor.fetchall()
            cursor.close()
        conn.close()
        
        if db_rows:
            df_display = pd.DataFrame(db_rows)
            
            # --- 🚀 ለመደርደሪያው (Sorting) የተሰራ ሎጂክ ---
            if sort_by == "በጊዜ ዝርዝር (ከአዲስ ወደ አሮጌ)":
                df_display['ቀን'] = pd.to_datetime(df_display['ቀን'])
                df_display = df_display.sort_values(by='ቀን', ascending=False)
                
            elif sort_by == "በጊዜ ዝርዝር (ከአሮጌ ወደ አዲስ)":
                df_display['ቀን'] = pd.to_datetime(df_display['ቀን'])
                df_display = df_display.sort_values(by='ቀን', ascending=True)
                
            elif sort_by == "በያዘው የዕጣ ቁጥር (ከትንሽ ወደ ትልቅ)":
                # ከዕጣ ቁጥሮቹ ውስጥ የመጀመሪያውን ትንሹን ቁጥር ወስዶ ለመደርደር
                def get_first_ticket_num(ticket_str):
                    try:
                        nums = [int(x.strip()) for x in str(ticket_str).split(",") if x.strip()]
                        return min(nums) if nums else 99999
                    except:
                        return 99999
                
                df_display['temp_sort_key'] = df_display['የዕጣ ቁጥሮች'].apply(get_first_ticket_num)
                df_display = df_display.sort_values(by='temp_sort_key', ascending=True)
                df_display = df_display.drop(columns=['temp_sort_key'])
            
            # ሰንጠረዡን በዌብሳይቱ ላይ ማሳያ
            st.dataframe(df_display, use_container_width=True)
            
            # --------------------------------------------------
            # 🚀 የ Excel ማዘጋጃ (በአዲሱ ዙር መሠረት)
            # --------------------------------------------------
            tickets_data = []
            for i in range(1, 2501):
                tickets_data.append({
                    "የዕጣ ቁጥር": i,
                    "የባለዕድሉ ስም": "",
                    "ስልክ ቁጥር": "",   
                    "የተከፈለው ብር": "",   
                    "የላኪ ስም": "",
                    "የተቀባይ ስም": "",
                    "Transaction ID": "",
                    "የተመዘገበበት ቀን": ""
                })
            
            for row in db_rows:
                if row["የዕጣ ቁጥሮች"]:
                    tickets_list = [t.strip() for t in str(row["የዕጣ ቁጥሮች"]).split(",") if t.strip()]
                    for ticket in tickets_list:
                        try:
                            ticket_num = int(ticket)
                            if 1 <= ticket_num <= 2500:
                                idx = ticket_num - 1
                                tickets_data[idx]["የባለዕድሉ ስም"] = row["ስም"]
                                
                                phone_str = str(row["ስልክ"]).strip()
                                if phone_str.isdigit():
                                    tickets_data[idx]["ስልክ ቁጥር"] = int(phone_str)
                                else:
                                    tickets_data[idx]["ስልክ ቁጥር"] = phone_str
                                
                                tickets_data[idx]["የተከፈለው ብር"] = float(row["ብር"])
                                tickets_data[idx]["የላኪ ስም"] = row["ላኪ"] if row["ላኪ"] else ""
                                tickets_data[idx]["የተቀባይ ስም"] = row["ተቀባይ"] if row["ተቀባይ"] else ""
                                tickets_data[idx]["Transaction ID"] = row["Ref ID"]
                                tickets_data[idx]["የተመዘገበበት ቀን"] = str(row["ቀን"])
                        except ValueError:
                            pass
            
            df_final = pd.DataFrame(tickets_data)
            csv_data = df_final.to_csv(index=False, header=False, encoding='utf-8-sig')
            
            st.markdown("---")
            st.subheader("📥 የዕጣዎችን ዝርዝር በExcel አውርድ")
            st.download_button(
                label="📊 የ2ኛ ዙር ሙሉ የዕጣዎች ዝርዝር Excel አውርድ",
                data=csv_data,
                file_name="round_2_lottery_tickets.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("በዚህ ዙር የተመዘገበ ምንም አዲስ መረጃ የለም!")
            
    except Exception as e:
        st.error(f"ስህተት ተፈጥሯል፦ {e}")

# ==========================================
# 7. ⚙️ አዲሱ ዙር ማስጀመሪያ (Reset Round) ታብ ክፍል
# ==========================================
with menu[2]:
    st.subheader("🔄 ለ2ኛ ዙር ዕጣ ቁጥሮችን በሙሉ ነጻ ማድረጊያ")
    st.info("""
    💡 **ይህ ተግባር የሚከተሉትን ያከናውናል፦**
    1. ከ 1 እስከ 2500 ያሉትን የዕጣ ቁጥሮች በሙሉ ነጻ ያደርጋል (ስም እና ስልክ እንደ አዲስ እንዲመዘገብ ያደርጋል)።
    2. **ነገር ግን በመጀመሪያው ዙር ጥቅም ላይ የዋሉትን Screenshots (Transaction IDs) በዳታቤዙ ውስጥ ያስቀምጣል።** 
    3. በዚህም ምክንያት በመጀመሪያው ዙር ያሸነፉበትን ወይም የተጠቀሙበትን ደረሰኝ በ2ኛው ዙር ላይ ደግመው ለመጠቀም ቢሞክሩ ሲስተሙ አይቀበላቸውም።
    """)
    
    # ድንገት በስህተት እንዳይነካ ተጨማሪ ማረጋገጫ
    confirm_reset = st.checkbox("አዎ፣ የዕጣ ቁጥሮቹን ብቻ ነጻ አድርጌ አዲስ ዙር ለመጀመር እስማማለሁ።")
    
    if confirm_reset:
        reset_password = st.text_input("ለማረጋገጥ የአስተዳዳሪውን የይለፍ ቃል (125536) እዚህ ያስገቡ፦", type="password")
        
        if st.button("🚀 አዲሱን ዙር በይፋ ጀምር (Reset Tickets Only)", type="primary"):
            if reset_password == "125536":
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # የዕጣ ቁጥሮቹን ብቻ ባዶ ማድረግ (በዚህም ምክንያት የድሮ ባለዕድሎች መረጃ ለጊዜው ይደበቃል፤ አዲስ ዙር ይጀምራል)
                    cursor.execute("UPDATE customer_tickets SET ticket_numbers = ''")
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    st.balloons()
                    st.success("🎉 የዕጣ ቁጥሮች በሙሉ በተሳካ ሁኔታ ነጻ ተደርገዋል! 2ኛው ዙር አሁን በይፋ ተጀምሯል። አሮጌ ደረሰኞች ግን እንዳይደገሙ ተቆልፈው ቀርተዋል።")
                    st.rerun()
                except Exception as e:
                    st.error(f"ስህተት አጋጥሟል፦ {e}")
            else:
                st.error("❌ የተሳሳተ የይለፍ ቃል! ዳግም ማስጀመር አልተቻለም።")

