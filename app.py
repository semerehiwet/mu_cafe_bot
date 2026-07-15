import streamlit as st
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import pandas as pd
from PIL import Image
from pyzbar.pyzbar import decode
import re
import io
import hmac

# ==========================================
# 1. የዳታቤዝ ግንኙነት (Connection Pool - eu-west-1 Session Pooler 5432 በመጠቀም)
# ==========================================
DB_CONNECTION_STRING = (
    "postgresql://postgres.ocetuxtkfbrepihgddco:semo27537572"
    "@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
)


@st.cache_resource(show_spinner=False)
def get_connection_pool():
    """
    አንድ ጊዜ ብቻ ተፈጥሮ (cached) ለመላው የአፑ ዕድሜ የሚያገለግል የግንኙነት ገንዳ (pool)።
    ይህ በየጥያቄው አዲስ TCP ግንኙነት ከመክፈት ይልቅ ግንኙነቶችን እንደገና ስለሚጠቀም ፍጥነትን ይጨምራል።
    """
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DB_CONNECTION_STRING,
    )


@contextmanager
def db_connection():
    """
    ከግንኙነት ገንዳው ውስጥ አንድ ግንኙነት ተውሶ፣ ስራው ሲያልቅ (ወይም ስህተት ቢፈጠር እንኳ) በራስ-ሰር
    ወደ ገንዳው የሚመልስ context manager። ግንኙነት ተከፍቶ የመቅረት እድልን ያስወግዳል።
    """
    conn_pool = get_connection_pool()
    conn = conn_pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn_pool.putconn(conn)


def init_db():
    """ሰንጠረዥ ከሌለ ይፈጥራል (አፑ ሲነሳ አንድ ጊዜ ብቻ የሚሰራ)።"""
    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
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
                    """
                )
            conn.commit()
    except Exception as e:
        st.error(f"❌ የዳታቤዝ ሰንጠረዥ መፍጠር አልተቻለም፦ {e}")


# @st.cache_resource ማለት ይህ ስራ አፑ በሚሰራበት ጊዜ ውስጥ አንድ ጊዜ ብቻ (ገጹ ዳግም ሲጫን አይደገምም) ይሰራል
@st.cache_resource(show_spinner=False)
def ensure_db_ready():
    init_db()
    return True


ensure_db_ready()

# ==========================================
# 2. የደህንነት መቆጣጠሪያ (አስተዳዳሪ መግቢያ)
# ==========================================
ADMIN_PASSWORD = "125536"  # <--- የይለፍ ቃልሽ እዚህ ተቀምጧል


def check_password():
    """የይለፍ ቃል ትክክል ከሆነ True ይመልሳል፣ ካልሆነ ግን የመግቢያ ፎርም ያሳያል"""

    def password_entered():
        # hmac.compare_digest timing-attack ን ለመከላከል ያገለግላል
        if hmac.compare_digest(st.session_state["password"], ADMIN_PASSWORD):
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
@st.cache_data(show_spinner=False)
def parse_qr_data(qr_text):
    """የQR ኮዱን ጽሁፍ ተንትኖ transaction id ያወጣል። ንፁህ (pure) ስሌት ስለሆነ cache ማድረግ ይቻላል።"""
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


@st.cache_data(show_spinner=False)
def decode_qr_from_bytes(image_bytes):
    """
    ከፎቶ bytes ውስጥ QR ኮድ ያነባል። ተመሳሳይ ፎቶ ዳግም ቢጫን (ለምሳሌ ገጹ rerun ሲያደርግ)
    QR ንባቡ ዳግም ስለማይሰራ ፈጣን ያደርገዋል።
    """
    image = Image.open(io.BytesIO(image_bytes))
    detected_qr = decode(image)
    qr_text = detected_qr[0].data.decode("utf-8") if detected_qr else None
    return qr_text, image


# ==========================================
# 4. የዕጣ ቁጥር ማመንጫ (ከ 1 እስከ 2500)
# ==========================================
@st.cache_data(ttl=10, show_spinner=False)
def get_allocated_tickets():
    """
    ጥቅም ላይ የዋሉ የዕጣ ቁጥሮችን ይመልሳል። አጭር (10 ሰከንድ) cache ስላለው በተደጋጋሚ
    ዳታቤዙ ላይ ጥያቄ ከመላክ ይታደጋል፤ አዲስ ደረሰኝ ሲመዘገብ/ዳግም ሲጀመር cache ይጸዳል።
    """
    with db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT ticket_numbers FROM customer_tickets "
                "WHERE ticket_numbers != '' AND ticket_numbers IS NOT NULL"
            )
            rows = cursor.fetchall()

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


def find_existing_transaction(tx_id):
    """
    ደረሰኙ ቀድሞ ተመዝግቦ እንደሆነ ያረጋግጣል። ትክክለኛነት (correctness) ወሳኝ ስለሆነ ይህ
    ተግባር ሆን ተብሎ cache አልተደረገም (ሁልጊዜ ትኩስ መረጃ ያመጣል)።
    """
    with db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM customer_tickets WHERE transaction_id = %s", (tx_id,))
            return cursor.fetchone()


def invalidate_ticket_caches():
    """አዲስ መረጃ ከተመዘገበ ወይም ዙር ዳግም ከተጀመረ በኋላ ያረጁ cache ዎችን ያጸዳል።"""
    get_allocated_tickets.clear()
    fetch_ticket_records.clear()


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
        image_bytes = uploaded_file.getvalue()

        try:
            qr_text, image = decode_qr_from_bytes(image_bytes)
        except Exception as e:
            st.error(f"❌ ፎቶውን ማንበብ አልተቻለም፦ {e}")
            qr_text, image = None, None

        if image is not None:
            st.image(image, caption="የተጫነው ደረሰኝ", width=300)

        if qr_text:
            tx_id = parse_qr_data(qr_text)

            try:
                existing_record = find_existing_transaction(tx_id)
            except Exception as e:
                st.error(f"❌ ደረሰኙን ማረጋገጥ አልተቻለም፦ {e}")
                st.stop()

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

            # --- እዚህ ጋር የትኬት ስሌት ተጨምሯል ---
            ticket_count = int(edit_amount // 2500)
            st.info(f"💡 የገባው ብር ለ **{ticket_count}** ትኬት ይበቃል (ለ 2500 ተከፍሎ)")
            # -----------------------------------

            edit_sender = st.text_input("የላኪ ስም (Sender Name)", placeholder="የላኪውን ስም እዚህ ይጻፉ...")
            edit_receiver = st.text_input("የተቀባይ ስም (Receiver Name)", placeholder="የተቀባዩን ስም እዚህ ይጻፉ...")

            st.markdown("---")
            st.subheader("👤 የባለዕድሉ መረጃ")
            c_name = st.text_input("የባለዕድሉ ሙሉ ስም (ግዴታ ነው)")
            c_phone = st.text_input("የባለዕድሉ ስልክ ቁጥር (ግዴታ ነው - ቢያንስ 10 አሃዝ)")

            st.markdown("---")
            st.subheader("🎫 የዕጣ አሰጣጥ ዘዴ")

            allocation_mode = st.radio(
                "የዕጣ ቁጥር መመደቢያ መንገድ፦",
                ["በራስ-ሰር (ከ1-2500 በቅደም ተከተል +1)", "በእጅ ለመምረጥ (በራስህ ቁጥር ለመስጠት)"],
            )

            try:
                used_tickets = get_allocated_tickets()
            except Exception as e:
                st.error(f"❌ የተያዙ ቁጥሮችን ማምጣት አልተቻለም፦ {e}")
                used_tickets = set()

            final_tickets = []

            if allocation_mode == "በራስ-ሰር (ከ1-2500 በቅደም ተከተል +1)":
                if ticket_count < 1:
                    st.warning("⚠️ ለዕጣ ለመሳተፍ ቢያንስ 2500 ብር መላክ አለብህ!")
                else:
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
                            st.error("❌ እባክዎ ከ 1 እስከ 2500 ያሉ ቁጥሮችን ብቻ ያስገቡ!")
                        elif len(temp_tickets) != ticket_count:
                            st.warning(
                                f"⚠️ የጻፍካቸው ቁጥሮች ብዛት ({len(temp_tickets)}) እና የፈቀድከው የትኬት ብዛት "
                                f"({ticket_count}) አይዛመድም!"
                            )
                        else:
                            final_tickets = temp_tickets
                            st.success("✅ የመረጥካቸው ቁጥሮች በሙሉ ክፍት ናቸው!")
                    except ValueError:
                        st.error("❌ እባክዎ ቁጥሮችን ብቻ ያስገቡ!")

            st.markdown("---")
            if st.button("አረጋግጥ እና መዝግብ (Accept & Save)"):
                phone_pattern = r'^\+?[0-9]{10,}$'
                clean_phone = c_phone.replace(" ", "").strip()

                if not c_name.strip():
                    st.error("❌ እባክዎ የባለዕድሉን ሙሉ ስም ያስገቡ!")
                elif not clean_phone:
                    st.error("❌ እባክዎ የባለዕድሉን ስልክ ቁጥር ያስገቡ!")
                elif not re.match(phone_pattern, clean_phone):
                    st.error("❌ ስህተት፦ የስልክ ቁጥሩ ቢያንስ 10 አሃዞች (ቁጥሮች) መሆን አለበት! (ምሳሌ፦ 0912345678 ወይም +251912345678)")
                elif edit_amount < 2500:
                    st.error("❌ ለዕጣ ለመሳተፍ ቢያንስ 2500 ብር መላክ አለብህ!")
                elif not final_tickets:
                    st.error("❌ የሚሰጥ የዕጣ ቁጥር አልተመረጠም!")
                else:
                    try:
                        tickets_str = ",".join(map(str, final_tickets))
                        with db_connection() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute(
                                    """
                                    INSERT INTO customer_tickets
                                        (transaction_id, sender_name, receiver_name, amount,
                                         customer_name, customer_phone, ticket_numbers)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    (
                                        edit_tx_id,
                                        edit_sender,
                                        edit_receiver,
                                        edit_amount,
                                        c_name.strip(),
                                        clean_phone,
                                        tickets_str,
                                    ),
                                )
                            conn.commit()

                        invalidate_ticket_caches()
                        st.balloons()
                        st.success(f"🎉 መረጃው በተሳካ ሁኔታ ተመዝግቧል! የተሰጡት የዕጣ ቁጥሮች፦ {tickets_str}")
                    except psycopg2.errors.UniqueViolation:
                        st.error("🚨 ይህ የግብይት መለያ (Transaction ID) ቀደም ሲል ተመዝግቧል!")
                    except Exception as e:
                        st.error(f"ስህተት አጋጥሟል፦ {e}")
        elif uploaded_file:
            st.error("❌ በምስሉ ላይ ምንም የQR ኮድ ሊነበብ አልቻለም! እባክዎ ግልጽ የሆነ ፎቶ ይጫኑ።")

# ==========================================
# 6. የተመዘገቡ ባለዕድሎች ዝርዝር እና የኤክሰል ማውረጃ
# ==========================================
@st.cache_data(ttl=15, show_spinner=False)
def fetch_ticket_records(search_query):
    """
    የደንበኞችን ዝርዝር ከዳታቤዙ ያመጣል። search_query ራሱ የ cache ቁልፍ አካል ስለሆነ፣
    የተለያዩ ፍለጋዎች ተለያይተው cache ይደረጋሉ፤ 15 ሰከንድ ውስጥ ተመሳሳይ ፍለጋ ቢደገም
    ዳታቤዙ ላይ ዳግም አይጠየቅም።
    """
    with db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if search_query:
                query = """
                    SELECT customer_name as ስም, customer_phone as ስልክ,
                           ticket_numbers as "የዕጣ ቁጥሮች", amount as ብር,
                           sender_name as ላኪ, receiver_name as ተቀባይ,
                           transaction_id as "Ref ID", created_at as ቀን
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
                cursor.execute(
                    query,
                    (
                        f"%{search_query}%",
                        f"%{search_query}%",
                        f"%,{exact_match}",
                        f"{exact_match},%",
                        f"%,{exact_match},%",
                        exact_match,
                    ),
                )
            else:
                cursor.execute(
                    """
                    SELECT customer_name as ስም, customer_phone as ስልክ,
                           ticket_numbers as "የዕጣ ቁጥሮች", amount as ብር,
                           sender_name as ላኪ, receiver_name as ተቀባይ,
                           transaction_id as "Ref ID", created_at as ቀን
                    FROM customer_tickets
                    WHERE ticket_numbers != '' AND ticket_numbers IS NOT NULL
                    """
                )
            return cursor.fetchall()


@st.cache_data(ttl=15, show_spinner=False)
def build_full_tickets_csv(db_rows_tuple):
    """
    ከ 1 እስከ 2500 ያለውን ሙሉ የዕጣ ሰንጠረዥ ገንብቶ CSV ያመነጫል። ግቤቱ tuple ስለሆነ
    (hashable) cache ማድረግ ይቻላል፤ መረጃው ካልተቀየረ CSV ዳግም አይገነባም።
    """
    tickets_data = []
    for i in range(1, 2501):
        tickets_data.append(
            {
                "የዕጣ ቁጥር": i,
                "የባለዕድሉ ስም": "",
                "ስልክ ቁጥር": "",
                "የተከፈለው ብር": "",
                "የላኪ ስም": "",
                "የተቀባይ ስም": "",
                "Transaction ID": "",
                "የተመዘገበበት ቀን": "",
            }
        )

    for row in db_rows_tuple:
        row = dict(row)
        if row["የዕጣ ቁጥሮች"]:
            tickets_list = [t.strip() for t in str(row["የዕጣ ቁጥሮች"]).split(",") if t.strip()]
            for ticket in tickets_list:
                try:
                    ticket_num = int(ticket)
                    if 1 <= ticket_num <= 2500:
                        idx = ticket_num - 1
                        tickets_data[idx]["የባለዕድሉ ስም"] = row["ስም"]
                        tickets_data[idx]["ስልክ ቁጥር"] = str(row["ስልክ"]).strip()
                        tickets_data[idx]["የተከፈለው ብር"] = float(row["ብር"])
                        tickets_data[idx]["የላኪ ስም"] = row["ላኪ"] if row["ላኪ"] else ""
                        tickets_data[idx]["የተቀባይ ስም"] = row["ተቀባይ"] if row["ተቀባይ"] else ""
                        tickets_data[idx]["Transaction ID"] = row["Ref ID"]
                        tickets_data[idx]["የተመዘገበበት ቀን"] = str(row["ቀን"])
                except ValueError:
                    pass

    df_final = pd.DataFrame(tickets_data)
    return df_final.to_csv(index=False, header=True, encoding="utf-8-sig")


with menu[1]:
    st.subheader("📋 የተመዘገቡ ባለዕድሎች ዝርዝር")

    search_query = st.text_input("በስም፣ በስልክ ቁጥር ወይም በዕጣ ቁጥር ይፈልጉ...")
    sort_by = st.selectbox(
        "📋 መረጃዎችን መደርደሪያ (Sort By)፦",
        [
            "በጊዜ ዝርዝር (ከአዲስ ወደ አሮጌ)",
            "በጊዜ ዝርዝር (ከአሮጌ ወደ አዲስ)",
            "በያዘው የዕጣ ቁጥር (ከትንሽ ወደ ትልቅ)",
        ],
    )

    try:
        db_rows = fetch_ticket_records(search_query)
    except Exception as e:
        st.error(f"ስህተት ተፈጥሯል፦ {e}")
        db_rows = []

    if db_rows:
        df_display = pd.DataFrame(db_rows)

        if sort_by == "በጊዜ ዝርዝር (ከአዲስ ወደ አሮጌ)":
            df_display['ቀን'] = pd.to_datetime(df_display['ቀን'])
            df_display = df_display.sort_values(by='ቀን', ascending=False)

        elif sort_by == "በጊዜ ዝርዝር (ከአሮጌ ወደ አዲስ)":
            df_display['ቀን'] = pd.to_datetime(df_display['ቀን'])
            df_display = df_display.sort_values(by='ቀን', ascending=True)

        elif sort_by == "በያዘው የዕጣ ቁጥር (ከትንሽ ወደ ትልቅ)":
            def get_first_ticket_num(ticket_str):
                try:
                    nums = [int(x.strip()) for x in str(ticket_str).split(",") if x.strip()]
                    return min(nums) if nums else 99999
                except Exception:
                    return 99999

            df_display['temp_sort_key'] = df_display['የዕጣ ቁጥሮች'].apply(get_first_ticket_num)
            df_display = df_display.sort_values(by='temp_sort_key', ascending=True)
            df_display = df_display.drop(columns=['temp_sort_key'])

        st.dataframe(df_display, use_container_width=True)

        try:
            # db_rows ወደ tuple of tuples (hashable) ተቀይሮ cache-friendly ይደረጋል
            hashable_rows = tuple(tuple(row.items()) for row in db_rows)
            csv_data = build_full_tickets_csv(hashable_rows)

            st.markdown("---")
            st.subheader("📥 የዕጣዎችን ዝርዝር በExcel አውርድ")
            st.download_button(
                label="📊 ሙሉ የዕጣዎች ዝርዝር Excel አውርድ",
                data=csv_data,
                file_name="lottery_tickets.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"❌ CSV ማመንጨት አልተቻለም፦ {e}")
    else:
        st.info("በዚህ ዙር የተመዘገበ ምንም አዲስ መረጃ የለም!")

# ==========================================
# 7. ⚙️ አዲሱ ዙር ማስጀመሪያ (Reset Round) ታብ ክፍል
# ==========================================
with menu[2]:
    st.subheader("🔄 ለ2ኛ ዙር ዕጣ ቁጥሮችን በሙሉ ነጻ ማድረጊያ")
    st.info("""
    💡 **ይህ ተግባር የሚከተሉትን ያከናውናል፦**
    1. ከ 1 እስከ 2500 ያሉትን የዕጣ ቁጥሮች በሙሉ ነጻ ያደርጋል (ስም እና ስልክ እንደ አዲስ እንዲመዘገብ ያደርጋል)።
    2. የድሮ ደረሰኞች በድጋሚ እንዳይመዘገቡ ይቆለፋሉ።
    """)

    confirm_reset = st.checkbox("አዎ፣ የዕጣ ቁጥሮቹን ብቻ ነጻ አድርጌ አዲስ ዙር ለመጀመር እስማማለሁ።")

    if confirm_reset:
        reset_password = st.text_input(
            f"ለማረጋገጥ የአስተዳዳሪውን የይለፍ ቃል ({ADMIN_PASSWORD}) እዚህ ያስገቡ፦", type="password"
        )

        if st.button("🚀 አዲሱን ዙር በይፋ ጀምር (Reset Tickets Only)", type="primary"):
            if hmac.compare_digest(reset_password, ADMIN_PASSWORD):
                try:
                    with db_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("UPDATE customer_tickets SET ticket_numbers = ''")
                        conn.commit()

                    invalidate_ticket_caches()
                    st.balloons()
                    st.success("🎉 የዕጣ ቁጥሮች በሙሉ በተሳካ ሁኔታ ነጻ ተደርገዋል! 2ኛው ዙር አሁን በይፋ ተጀምሯል።")
                    st.rerun()
                except Exception as e:
                    st.error(f"ስህተት አጋጥሟል፦ {e}")
            else:
                st.error("❌ የተሳሳተ የይለፍ ቃል! ዳግም ማስጀመር አልተቻለም።")
