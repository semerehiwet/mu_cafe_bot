import os
import streamlit as nn
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# 1. የዳታቤዝ ግንኙነት (Database Connection)
def get_db_connection():
    # ያንተ ትክክለኛ የ Supabase ዳታቤዝ አድራሻ እና የይለፍ ቃል (Password)
    # የ @ ምልክት በ %40 ተተክቷል
    connection_string = "postgresql://postgres:%40semo27537572@db.ocetuxtkfbrepihgddco.supabase.co:5432/postgres?sslmode=require"
    return psycopg2.connect(connection_string)

# 2. የዳታቤዝ ሰንጠረዦችን መፍጠሪያ (Database Initialization)
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # የዕጣ ተጠቃሚዎች ሰንጠረዥ
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(50) NOT NULL,
            role VARCHAR(20) DEFAULT 'user'
        )
    ''')
    
    # የዕጣ ቁጥሮች ሰንጠረዥ
    cur.execute('''
        CREATE TABLE IF NOT EXISTS lottery_tickets (
            id SERIAL PRIMARY KEY,
            ticket_number INT UNIQUE NOT NULL,
            owner VARCHAR(50) DEFAULT NULL,
            purchased_at TIMESTAMP DEFAULT NULL,
            status VARCHAR(20) DEFAULT 'available'
        )
    ''')
    
    # የአሸናፊዎች ሰንጠረዥ
    cur.execute('''
        CREATE TABLE IF NOT EXISTS winners (
            id SERIAL PRIMARY KEY,
            ticket_number INT NOT NULL,
            winner_name VARCHAR(50) NOT NULL,
            draw_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # የመጀመሪያ አስተዳዳሪ (Admin) አካውንት መፍጠር
    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
        
    # የዕጣ ቁጥሮችን መሙላት (ከ 1 እስከ 100) - ገና ካልተፈጠሩ
    cur.execute("SELECT COUNT(*) FROM lottery_tickets")
    if cur.fetchone()[0] == 0:
        for i in range(1, 101):
            cur.execute("INSERT INTO lottery_tickets (ticket_number) VALUES (%s)", (i,))
            
    conn.commit()
    cur.close()
    conn.close()

# የዳታቤዝ ሰንጠረዦችን መጀመሪያ ላይ መፍጠር
try:
    init_db()
except Exception as e:
    nn.error(f"የዳታቤዝ ግንኙነት ስህተት አጋጥሟል፦ {e}")

# --- የ Streamlit UI መተግበሪያ ---
nn.set_page_config(page_title="የዕጣ መቆጣጠሪያ ሲስተም", page_icon="🎫", layout="centered")
nn.title("🎫 የስጦታ ዕጣ መቆጣጠሪያ ዌብሳይት")

# ሴሽን ስቴት (Session State) ማዘጋጀት
if 'logged_in' not in nn.session_state:
    nn.session_state.logged_in = False
    nn.session_state.username = ""
    nn.session_state.role = "user"

# 3. መግቢያ ገጽ (Login Section)
if not nn.session_state.logged_in:
    nn.subheader("መግቢያ ገጽ")
    username = nn.text_input("የመጠቃሚያ ስም (Username)")
    password = nn.text_input("የይለፍ ቃል (Password)", type="password")
    
    col1, col2 = nn.columns(2)
    with col1:
        if nn.button("ግባ (Login)"):
            try:
                conn = get_db_connection()
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
                user = cur.fetchone()
                cur.close()
                conn.close()
                
                if user:
                    nn.session_state.logged_in = True
                    nn.session_state.username = user['username']
                    nn.session_state.role = user['role']
                    nn.success(f"እንኳን በደህና መጡ {username}!")
                    nn.rerun()
                else:
                    nn.error("የተሳሳተ የተጠቃሚ ስም ወይም የይለፍ ቃል!")
            except Exception as e:
                nn.error(f"ስህተት፦ {e}")
                
    with col2:
        if nn.button("አዲስ አካውንት ፍጠር (Register)"):
            if username and password:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')", (username, password))
                    conn.commit()
                    cur.close()
                    conn.close()
                    nn.success("አካውንትዎ በተሳካ ሁኔታ ተፈጥሯል! አሁን መግባት ይችላሉ።")
                except psycopg2.IntegrityError:
                    nn.error("ይህ የተጠቃሚ ስም ቀደም ብሎ ተይዟል!")
                except Exception as e:
                    nn.error(f"ስህተት፦ {e}")
            else:
                nn.warning("እባክዎ የተጠቃሚ ስም እና የይለፍ ቃል ያስገቡ!")

# 4. ዋናው የዌብሳይት ገጽ (User and Admin Dashboard)
else:
    nn.sidebar.write(f"እንኳን ደህና መጡ፣ **{nn.session_state.username}** ({nn.session_state.role})")
    if nn.sidebar.button("ውጣ (Logout)"):
        nn.session_state.logged_in = False
        nn.session_state.username = ""
        nn.session_state.role = "user"
        nn.rerun()
        
    # --- የአስተዳዳሪ (Admin) ገጽ ---
    if nn.session_state.role == 'admin':
        nn.header("⚙️ የአስተዳዳሪ መቆጣጠሪያ ሰሌዳ")
        
        tab1, tab2, tab3 = nn.tabs(["የዕጣ ሁኔታ", "ዕጣ ማውጣት", "ሁሉንም ዳግም አስጀምር"])
        
        with tab1:
            nn.subheader("የዕጣ ቁጥሮች ሁኔታ")
            try:
                conn = get_db_connection()
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT status, COUNT(*) FROM lottery_tickets GROUP BY status")
                stats = cur.fetchall()
                for stat in stats:
                    nn.write(f"**{stat['status'].capitalize()}** tickets: {stat['count']}")
                cur.close()
                conn.close()
            except Exception as e:
                nn.error(e)
                
        with tab2:
            nn.subheader("🎁 አሸናፊ ዕጣ ማውጣት")
            if nn.button("ዕጣ አውጣ (Draw Winner)"):
                try:
                    conn = get_db_connection()
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    # ከተገዙት (sold) ቁጥሮች መካከል በዘፈቀደ አንድ አሸናፊ መምረጥ
                    cur.execute("SELECT * FROM lottery_tickets WHERE status = 'sold' ORDER BY RANDOM() LIMIT 1")
                    winner_ticket = cur.fetchone()
                    
                    if winner_ticket:
                        # አሸናፊውን መመዝገብ
                        cur.execute(
                            "INSERT INTO winners (ticket_number, winner_name) VALUES (%s, %s)",
                            (winner_ticket['ticket_number'], winner_ticket['owner'])
                        )
                        # የዕጣውን ሁኔታ ወደ አሸናፊ መቀየር
                        cur.execute(
                            "UPDATE lottery_tickets SET status = 'winner' WHERE ticket_number = %s",
                            (winner_ticket['ticket_number'],)
                        )
                        conn.commit()
                        nn.balloons()
                        nn.success(f"🎉 እንኳን ደስ አለዎት! አሸናፊው ቁጥር {winner_ticket['ticket_number']} ሲሆን ባለቤቱ {winner_ticket['owner']} ነው።")
                    else:
                        nn.warning("ምንም የተሸጠ የዕጣ ቁጥር የለም! መጀመሪያ ተጠቃሚዎች የዕጣ ቁጥር መግዛት አለባቸው።")
                    cur.close()
                    conn.close()
                except Exception as e:
                    nn.error(e)
                    
        with tab3:
            nn.subheader("⚠️ ሲስተሙን ሙሉ በሙሉ አጽዳ")
            if nn.button("ሁሉንም ዳግም አስጀምር (Reset All)"):
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE lottery_tickets SET status = 'available', owner = NULL, purchased_at = NULL")
                    cur.execute("DELETE FROM winners")
                    conn.commit()
                    cur.close()
                    conn.close()
                    nn.success("ሲስተሙ በተሳካ ሁኔታ ዳግም ተጀምሯል!")
                    nn.rerun()
                except Exception as e:
                    nn.error(e)

    # --- የተጠቃሚ (User) ገጽ ---
    else:
        nn.header("🎫 የዕጣ ቁጥር መግዣ")
        
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # የሚገኙ ቁጥሮችን ማምጣት
            cur.execute("SELECT ticket_number FROM lottery_tickets WHERE status = 'available' ORDER BY ticket_number")
            available_tickets = [row['ticket_number'] for row in cur.fetchall()]
            
            # ተጠቃሚው የገዛቸው ቁጥሮች
            cur.execute("SELECT ticket_number FROM lottery_tickets WHERE owner = %s", (nn.session_state.username,))
            my_tickets = [row['ticket_number'] for row in cur.fetchall()]
            
            # አሸናፊዎችን ማምጣት
            cur.execute("SELECT * FROM winners ORDER BY draw_date DESC")
            recent_winners = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # አሸናፊዎችን ማሳያ
            if recent_winners:
                nn.info("🔔 የቅርብ ጊዜ የዕጣ አሸናፊዎች ዝርዝር፦")
                for w in recent_winners:
                    nn.write(f"🎉 ቁጥር **{w['ticket_number']}** — አሸናፊ፦ **{w['winner_name']}** ({w['draw_date'].strftime('%Y-%m-%d %H:%M')})")
            
            nn.write("---")
            nn.write(f"🛍️ የገዟቸው የዕጣ ቁጥሮች ብዛት፦ **{len(my_tickets)}**")
            if my_tickets:
                nn.write(f"ያንተ ቁጥሮች፦ {', '.join(map(str, my_tickets))}")
                
            nn.write("---")
            if available_tickets:
                selected_ticket = nn.selectbox("ሊገዙት የሚፈልጉትን የዕጣ ቁጥር ይምረጡ፦", available_tickets)
                if nn.button("ዕጣ ቁጥሩን ግዛ (Buy Ticket)"):
                    try:
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE lottery_tickets SET status = 'sold', owner = %s, purchased_at = %s WHERE ticket_number = %s AND status = 'available'",
                            (nn.session_state.username, datetime.now(), selected_ticket)
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        nn.success(f"🎉 ቁጥር {selected_ticket} በተሳካ ሁኔታ ገዝተዋል!")
                        nn.rerun()
                    except Exception as e:
                        nn.error(f"መግዛት አልተቻለም፦ {e}")
            else:
                nn.warning("ሁሉም የዕጣ ቁጥሮች አልቀዋል!")
                
        except Exception as e:
            nn.error(f"የመረጃ ስህተት፦ {e}")
