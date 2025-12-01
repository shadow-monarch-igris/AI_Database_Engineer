import streamlit as st
import mysql.connector
import pandas as pd
import google.generativeai as genai
from openai import OpenAI

# open ai key 
# client = OpenAI(api_key="YOUR_OPENAI_KEY_HERE")

# gemini key 
genai.configure(api_key="AIzaSyAGk2z-xBQJXUOpOMvAn7GavqYbL3uGsgw")

# Model call functions

def call_llm_gemini(full_prompt):
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(full_prompt)
    return resp

# def call_llm_gpt(full_prompt):
#     response = client.chat.completions.create(
#         model="gpt-4.1-mini",   # change to gpt-4.1 or gpt-5.1 if you want
#         messages=[
#             {"role": "system", "content": "You are an AI SQL Expert."},
#             {"role": "user", "content": full_prompt}
#         ],
#         temperature=0
#     )

#     return response.choices[0].message.content

# connect to DB
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        database="loyalty",
        user="root",
        password="Shivam@0209",
        port="3306"
    )


# last 10 rounds memory

if "memory" not in st.session_state:
    st.session_state.memory = []

# Store last SQL result + query for explanation
if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_query" not in st.session_state:
    st.session_state.last_query = None

def add_memory(user, mode, content):
    st.session_state.memory.append({
        "user": user,
        "mode": mode,
        "content": content
    })
    st.session_state.memory = st.session_state.memory[-10:]

def display_memory():
    text = ""
    for m in st.session_state.memory:
        text += f"\nUser: {m['user']}\nMode: {m['mode']}\nBot: {m['content']}\n"
    return text

# Text extract from resposnse
def safe_text(resp):
    try:
        if resp and resp.candidates and resp.candidates[0].content:
            return resp.text.strip()
        return None
    except:
        return None
    
# DB SCHEMA + RULES FOR AI

DATABASE_SCHEMA = """
You are an AI SQL Expert for the MySQL database "loyalty".  
You strictly follow ALL the rules, relationships, and meanings listed below.
While generating SQL, you NEVER hallucinate any tables or columns.(IMPORTANT).
only generate SQL on the bases of MySQL Ver 8.0.44-0ubuntu0.24.04.1 for Linux on x86_64

====================================================
DATABASE STRUCTURE + COLUMN MEANINGS (FULL DOCUMENTATION)
====================================================

------------------------------------------
TABLE: areas
------------------------------------------
id                → Primary key
name              → Area name
created_at
updated_at

------------------------------------------
TABLE: city
------------------------------------------
id                → Primary key
name              → City name
created_at
updated_at

------------------------------------------
TABLE: customers
------------------------------------------
id
name
push_token
unique_identifier → A long unique number
lifetime_points   → Total points earned ever
current_points    → Points currently available
tier              → FK → tiers.id
area_id           → FK → areas.id
city_id           → FK → city.id
language          → 'en' or 'ar'
created_at
updated_at

------------------------------------------
TABLE: tiers
------------------------------------------
id
name              → Tier name (Ex: Bronze, Silver, Gold)
points            → Points required for tier
status            → 1 = active, 2 = inactive
created_at
updated_at

------------------------------------------
TABLE: point_history
------------------------------------------
id
customer_id        → FK → customers.id
points             → Positive or negative points
type               → 1 = credit, 2 = debit
resource_type      → 1 = Topup added
                     2 = Referral added
                     3 = Manual points added
                     4 = Reward redemption (points reduced)
                     5 = Manual points reduced
reward_id          → FK → rewards.id
coupon_code
unique_id
reward_coupon_id   → FK → reward_coupons.id
reward_name
reward_name_ar
refer_by           → FK → customers.id (referrer)
notes
topup
created_at
updated_at

------------------------------------------
TABLE: reward_coupons
------------------------------------------
id
reward_id         → FK → rewards.id
code
no_of_use
per_user_allotment
coupon_used
unique_id
status            → 0 = inactive, 1 = active, 2 = ended
created_at
updated_at

------------------------------------------
TABLE: rewards
------------------------------------------
id
name
name_ar
description
description_ar
terms_conditions
terms_conditions_ar
tiers             → Comma-separated tier IDs
points            → Points needed for redemption
per_user_redemption
per_user_monthly_redemption
start_date
end_date
type              → 1 = online, 2 = offline
image
unique_id
status            → 0 = inactive, 1 = active
coupon_code       → 1 = Single Code, 2 = Multiple Code
csv_file
redeem_link
how_to_use
how_to_use_ar
sort_by
created_at
updated_at

------------------------------------------
TABLE: users
------------------------------------------
id
name
email (unique)
role              → 1 = admin, 2 = user
status            → 1 = active, 2 = inactive
created_at
updated_at

------------------------------------------
TABLE: settings
------------------------------------------
id
topup_points     → Money-to-points conversion
referral_points
firebase_key
sms_token
sms_token_expiry
created_at
updated_at


====================================================
FOREIGN KEY RELATIONSHIPS (INFERRED)
====================================================
customers.area_id → areas.id  
customers.city_id → city.id  
customers.tier → tiers.id  

point_history.customer_id → customers.id  
point_history.reward_id → rewards.id  
point_history.reward_coupon_id → reward_coupons.id  
point_history.refer_by → customers.id  

reward_coupons.reward_id → rewards.id  


====================================================
GLOBAL SQL RULES
====================================================

1. While generating SQL, do not halucinate any tables or columns.

2. ONLY SELECT QUERIES ARE ALLOWED  
   ❌ No DELETE  
   ❌ No UPDATE  
   ❌ No INSERT  
   ❌ No ALTER  
   Only SELECT queries.

3. SQL must be valid for:
   MySQL Ver 8.0.44-0ubuntu0.24.04.1 for Linux on x86_64

4. ALWAYS use LOWER() for string matching:
   LOWER(column_name) = LOWER('text')

5. NEVER hallucinate columns or tables. 

6. JOIN only using valid FK paths listed above.

7. NO markdown, NO backticks, NO explanation.
   Output ONLY raw SQL.

8. Always format output like:

    MODE: SQL
    <SQL QUERY>  

    or

    MODE: CHAT
    <chat reply> 

9. Mode rules:
   • MODE: SQL → When user asks to search, check, fetch, filter, count, view data.  
   • MODE: CHAT → Greetings, general questions, normal conversation.  
   You are “John”, built by Shivam.

10. Learn from all previously correct queries and keep improving accuracy.

11. NEVER modify table structure or create new fields.

12. Date arithmetic must use MySQL format:
    DATE '2024-01-10' - INTERVAL 5 DAY


====================================================
PRIORITY LOGIC (MOST IMPORTANT)
====================================================
Before generating SQL:
1. do not hallucinate user intent
2. Understand user intent  
3. Identify required table(s)  
4. Apply correct FK joins  
5. Use optimized filters & indexes  
6. Produce final, perfect, raw SQL


====================================================
FINAL BEHAVIOR SUMMARY
====================================================
do not halucination any tables or columns.
You are a MySQL-8.0.44 SQL specialist.
You never produce unsafe or invalid SQL.
You always return the most accurate, optimized SELECT query.

====================================================
DATABASE EXTRA RULES
====================================================
Active customer = any customer with at least one row in point_history. Always join customers.id = point_history.customer_id when user asks about “active customer”. Never consider a customer active without point_history activity.
"""

# ----------------------------------------------------
# BEGIN UI
# ----------------------------------------------------
st.set_page_config(page_title="AI SQL Assistant", layout="centered")
st.title("🤖 AI Database manager (sql+chat)")

with st.expander("Conversation Memory"):
    st.text(display_memory())

with st.expander("Database Schema"):
    st.code(DATABASE_SCHEMA, language="sql")

user_query = st.text_input("Ask anything:")

# ----------------------------------------------------
# PROCESS QUERY
# ----------------------------------------------------
if st.button("Run"):
    with st.spinner("Thinking..."):

        full_prompt = f"""
{DATABASE_SCHEMA}

Conversation History:
{display_memory()}

User: "{user_query}"

Decide your mode correctly either sql or chat. don't halucinate
You are smart ai database manager named "SQL Expert" built by MRT . you have access to database "loyalty" . you can perform only select queries to fetch information from it. 
you can also give explanation about the result of sql query. you can also chatting with the user in friendly manner.
"""

        resp = call_llm_gemini(full_prompt)
        raw = safe_text(resp)

        if raw is None:
            st.error("⚠️ Empty AI response.")
            st.stop()

        # ---------------------------
        # SQL MODE
        # ---------------------------
        if raw.startswith("MODE: SQL"):
            st.subheader("Generated SQL")
            sql_query = raw.replace("MODE: SQL", "").strip()
            st.code(sql_query)

            try:
                conn = connect_db()
                cur = conn.cursor()
                cur.execute(sql_query)

                if sql_query.lower().startswith("select"):
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]
                    df = pd.DataFrame(rows, columns=cols)

                    st.subheader("SQL Results")
                    st.dataframe(df)

                    # Store result for global explain button
                    st.session_state.last_result = rows
                    st.session_state.last_query = sql_query

                    add_memory(user_query, "SQL", rows)

                else:
                    conn.commit()
                    st.success("Query executed successfully.")
                    st.session_state.last_result = None
                    st.session_state.last_query = None

                cur.close()
                conn.close()

            except Exception as e:
                st.error(f"❌ SQL Error: {e}")
                add_memory(user_query, "SQL_ERROR", str(e))

 
        # CHAT MODE
        elif raw.startswith("MODE: CHAT"):
            chat_reply = raw.replace("MODE: CHAT", "").strip()
            st.subheader("Chat Response")
            st.write(chat_reply)
            add_memory(user_query, "CHAT", chat_reply)

        else:
            st.error("⚠️ Invalid AI format.")

# explain fuction 

if st.session_state.last_result and st.session_state.last_query:
    if st.button("Explain Result"):
        with st.spinner("Explaining..."):
            
            explain_prompt = f"""
You are "SQL Expert" for  AI DB Manager.
Explain this SQL result clearly.
How you generated it, what it means, any insights.

Query: {st.session_state.last_query}
Result: {st.session_state.last_result}
"""

            resp2 = call_llm_gemini(explain_prompt)
            explanation = safe_text(resp2) or "Could not generate explanation."

            st.subheader("AI Explanation")
            st.write(explanation)

            add_memory("Explain Result", "CHAT", explanation)
