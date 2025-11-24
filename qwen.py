import streamlit as st
import mysql.connector
import pandas as pd
import requests


# ----------------------------------------------------
# LLM USING OLLAMA (Qwen 2.5 - 1.5B)
# ----------------------------------------------------
def call_llm(prompt):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": "gemma",
        "prompt": prompt,
        "stream": False
    }
    try:
        r = requests.post(url, json=data)
        json_resp = r.json()
        return json_resp.get("response", "").strip()
    except Exception as e:
        print("LLM Error:", e)
        return None


# ----------------------------------------------------
# DB CONNECTION
# ----------------------------------------------------
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        database="beta",
        user="mind",
        password="Mindroot@123",
        port="3306"
    )


# ----------------------------------------------------
# MEMORY (last 5 rounds)
# ----------------------------------------------------
if "memory" not in st.session_state:
    st.session_state.memory = []

def add_memory(user, mode, content):
    st.session_state.memory.append({
        "user": user,
        "mode": mode,
        "content": content
    })
    st.session_state.memory = st.session_state.memory[-5:]

def display_memory():
    text = ""
    for m in st.session_state.memory:
        text += f"\nUser: {m['user']}\nMode: {m['mode']}\nBot: {m['content']}\n"
    return text


# ----------------------------------------------------
# DB SCHEMA + RULES FOR AI
# ----------------------------------------------------
DATABASE_SCHEMA = """
Current Database Name: beta
customers(
    id(),
    name,
    push_token,
    unique_identifier,
    lifetime_points,
    current_points,
    tier,
    area_id,
    city_id,
    `language`(properties is en,ar),
    created_at,
    updated_at
)
areas(
    id,
    name,
    created_at,
    updated_at
)
city(
    id,
    name,
    created_at,
    updated_at
)
active_user_report(
    id,
    name,
    unique_identifier,
    created_at,
    updated_at
)
clients(
    id,
    name,
    email,
    email_verified_at,
    password,
    remember_token,
    created_at,
    updated_at
)
rewards(
    id,
    name,
    name_ar,
    description,
    description_ar,
    terms_conditions,
    terms_conditions_ar,
    tiers,
    points,
    per_user_redemption,
    per_user_monthly_redemption,
    start_date,
    end_date,
    `type`(properties is 1=>online, 2=>offline),
    image,
    unique_id,
    status (properties is 0=>inactive,1=>active),
    coupon_code (properties is 1=Single Code, 2=Multiple Code),
    csv_file,
    redeem_link,
    how_to_use,
    how_to_use_ar,
    sort_by,
    created_at,
    updated_at
)
reward_coupons(
    id,
    reward_id,
    code,
    no_of_uses,
    per_user_allotment,
    coupon_used,
    unique_id,
    status(properties is 0=>inactive,1=>active,2=>end),
    created_at,
    updated_at 
)
point_history(
    id,
    customer_id,
    points,
    type(properties is 1=>credit,2=>debit),
    resource_type(properties is resource_type - 1 = Topup points added | 2 = Referral points added | 3 = manual points added | 4 = Reward redemption points reduced | 5 = manual points reduced),
    reward_id,
    coupon_code,
    unique_id,
    reward_coupon_id,
    reward_name,
    reward_name_ar,
    refer_by,
    notes,
    created_at,
    updated_at,
    topup
)


Rules:
very strictly generate queries syntex on the bases of my sql version -> mysql  Ver 8.0.44-0ubuntu0.24.04.1 for Linux on x86_64 ((Ubuntu)
you have to generate sql queries according to schema . you also use database to understand and make queries for answering user queries .
"tell you that in that tables their are foreign key realtions as well .soo be careful while making joins " firstly understand the tables and information in it.
1. very important -> make sql queris for this version (mysql  Ver 8.0.44-0ubuntu0.24.04.1 for Linux on x86_64 ((Ubuntu))
2. understand the structure of the database from the schema above. and the information in it.
3. make sql queries faster and optimized it give right querie you also learn from previous mistakes and correct them.
4. Return ONLY raw SQL with NO backticks, NO markdown, NO explanations, NO formatting.
Do NOT wrap the SQL inside ```sql blocks```
Output only the SQL query.
5. You may output in two modes:
    MODE: SQL   → When user wants to search, insert, update, or delete.
    MODE: CHAT  → When user is greeting, asking general things.
5.1 For SQL mode:
    * Only output SQL (no explanation).
    * Never hallucinate columns.
    * Never alter table structure.
    * only SELECT query are allowed.
    * Use LOWER() for string matching.
5.2 For CHAT mode:
    * Talk naturally and be friendly.
    * You are "John", built by Shivam.
5.3 Always format output like:

MODE: SQL
<SQL QUERY>

or

MODE: CHAT
<chat reply>
6  Use the SQL standard for date arithmetic: DATE 'YYYY-MM-DD' - INTERVAL 'X UNIT'.
7. You firstly understand the structure of the database from the schema above.then you  underswtand what user wants from his query.
8. also take that queries in your memory which were previouly correct and similar to the current query and learn from them and give optimized and correct query.
"""


# ----------------------------------------------------
# STREAMLIT UI
# ----------------------------------------------------
st.set_page_config(page_title="AI SQL Assistant", layout="centered")
st.title("🤖 AI Database Manager (SQL + Chat) —     GEMMA Edition")

with st.expander("Conversation Memory"):
    st.text(display_memory())

with st.expander("Database Schema"):
    st.code(DATABASE_SCHEMA, language="sql")

user_query = st.text_input("Ask anything:")


# ----------------------------------------------------
# PROCESS BUTTON
# ----------------------------------------------------
if st.button("Run"):
    with st.spinner("Thinking..."):

        # Create final prompt for Qwen
        full_prompt = f"""
{DATABASE_SCHEMA}

Conversation History:
{display_memory()}

User: "{user_query}"

Decide correct mode.
"""

        # Call gemma model
        raw = call_llm(full_prompt)

        if raw is None:
            st.error("⚠️ AI returned no content. Try again.")
            st.stop()


        # -----------------------------------------
        # PARSE MODE
        # -----------------------------------------
        if raw.startswith("MODE: SQL"):
            mode = "SQL"
            sql_query = raw.split("MODE: SQL")[-1].strip()

            st.subheader("Generated SQL")
            st.code(sql_query)

            # Execute SQL
            conn = connect_db()
            cur = conn.cursor()

            try:
                cur.execute(sql_query)

                if sql_query.lower().startswith("select"):
                    rows = cur.fetchall()
                    cols = [d[0] for d in cur.description]
                    df = pd.DataFrame(rows, columns=cols)
                    st.subheader("SQL Results")
                    st.dataframe(df)
                    result_display = rows
                else:
                    conn.commit()
                    st.success("✅ Query executed successfully")
                    result_display = "Success"

            except Exception as e:
                st.error(f"❌ SQL Error: {e}")
                add_memory(user_query, "SQL_ERROR", str(e))
                st.stop()

            cur.close()
            conn.close()

            # Store memory
            add_memory(user_query, "SQL", result_display)

           
            explain_prompt = f"""
You are John an expert ai database manager from Mind Root build by shivam . Explain everything about the result 

User: {user_query}
Result: {result_display}
"""

            explanation = call_llm(explain_prompt)

            st.subheader("AI Explanation")
            st.write(explanation)


        # -----------------------------------------
        # CHAT MODE
        # -----------------------------------------
        elif raw.startswith("MODE: CHAT"):
            chat_reply = raw.split("MODE: CHAT")[-1].strip()

            st.subheader("Chat Response")
            st.write(chat_reply)

            add_memory(user_query, "CHAT", chat_reply)

        else:
            st.error("⚠️ AI output unrecognized. Try again.")
