import streamlit as st
from pymongo import MongoClient
import pandas as pd
import google.generativeai as genai

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------
genai.configure(api_key="AIzaSyAGk2z-xBQJXUOpOMvAn7GavqYbL3uGsgw")

def call_llm_gemini(full_prompt):
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(full_prompt)
    return resp

# ----------------------------------------------------
# CONNECT TO MONGODB
# ----------------------------------------------------
def connect_mongo():
    client = MongoClient("mongodb://localhost:27017")   # no auth
    db = client["attendance_records"]  # your DB name
    return db


# ----------------------------------------------------
# SESSION MEMORY
# ----------------------------------------------------
if "memory" not in st.session_state:
    st.session_state.memory = []

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


def safe_text(resp):
    try:
        return resp.text.strip()
    except:
        return None


# ----------------------------------------------------
# MONGODB SCHEMA FOR LLM
# ----------------------------------------------------
MONGO_SCHEMA = """
You are an AI MongoDB Expert for the database "attendance_records".
You generate **only MongoDB queries**, no SQL.
You are an AI MongoDB Expert for the MongoDB database "loyalty".  
You strictly follow ALL the rules, relationships, and meanings listed below.
While generating SQL, you NEVER hallucinate any tables or columns.(IMPORTANT).
only generate SQL on the bases of MongoDB version v8.0.16 for Linux on x86_64


==========================
COLLECTION: sample
==========================

Fields:
{
  "$jsonSchema": {
    "bsonType": "object",
    "required": [
      "project_id",
      "user_id",
      "created_by_agent",
      "title",
      "description",
      "assigned_to",
      "status",
      "priority",
      "category",
      "start_date",
      "due_date",
      "estimated_hours",
      "actual_hours",
      "dependencies",
      "attachments",
      "location",
      "notes",
      "created_at",
      "updated_at"
    ],

    "properties": {
      "_id": { "bsonType": "objectId" },

      "project_id": { "bsonType": "string", "description": "Project reference ID" },
      "user_id": { "bsonType": "string", "description": "Assigned user ID" },
      "created_by_agent": { "bsonType": "string" },

      "title": { "bsonType": "string" },
      "description": { "bsonType": "string" },
      "assigned_to": { "bsonType": "string" },

      "status": { "bsonType": "string" },
      "priority": { "bsonType": "string" },
      "category": { "bsonType": "string" },

      "start_date": { "bsonType": "date" },
      "due_date": { "bsonType": "date" },
      "completed_at": { "bsonType": ["date", "null"] },

      "estimated_hours": { "bsonType": "int" },
      "actual_hours": { "bsonType": "int" },

      "dependencies": { "bsonType": "array" },
      "attachments": { "bsonType": "array" },

      "location": { "bsonType": "string" },
      "notes": { "bsonType": "string" },

      "created_at": { "bsonType": "date" },
      "updated_at": { "bsonType": "date" }
    }
  }
}

==========================
RULES
==========================

1. ONLY OUTPUT MONGODB JSON QUERIES.
   Example:
   MODE: MONGO
   db.attendance_records.find({ "status": "Completed" })

2. NEVER hallucinate fields.

3.It MUST be valid Python code that can be executed with eval().
  • Use PyMongo style.
  • All object keys MUST be in double quotes.
  • Always use db.attendance_records as the collection name (database is already selected in Python).
  • Do NOT wrap the query in extra {} or backticks.

4. NO insert, update, delete unless user asks.

5. write accurate query for mongodb version v8.0.16.

6. ALWAYS output in this format:
   
   MODE: MONGO
   <query>

  or

   MODE: CHAT
   <reply>
   
IMPORTANT:
Database name = attendance_records
Collection name = sample

Therefore:
• Correct query = db.sample.find({ ... })
• Correct aggregation = db.sample.aggregate([ ... ])
• NEVER use db.attendance_records.<query> because attendance_records is the DATABASE.

"""


# ----------------------------------------------------
# UI
# ----------------------------------------------------
st.set_page_config(page_title="AI MongoDB Manager", layout="centered")
st.title("🤖 MongoDB AI Database Manager")

with st.expander("Conversation Memory"):
    st.text(display_memory())

with st.expander("MongoDB Schema"):
    st.code(MONGO_SCHEMA, language="json")


user_query = st.text_input("Ask anything (MongoDB):")


# ----------------------------------------------------
# RUN
# ----------------------------------------------------
if st.button("Run"):
    with st.spinner("Thinking..."):

        full_prompt = f"""
{MONGO_SCHEMA}

Conversation History:
{display_memory()}

User: "{user_query}"

Decide correct MODE (MONGO or CHAT).
You are a MongoDB Specialist.
"""

        resp = call_llm_gemini(full_prompt)
        raw = safe_text(resp)

        if raw is None:
            st.error("Empty AI response.")
            st.stop()

        # ------------------------------
        # MONGO QUERY MODE
        # ------------------------------
        if raw.startswith("MODE: MONGO"):
            st.subheader("Generated MongoDB Query")
            mongo_query = raw.replace("MODE: MONGO", "").strip()
            st.code(mongo_query)

            try:
                db = connect_mongo()

                # Execute MongoDB query safely
                result = eval(mongo_query, {"db": db})
                st.write(result)

                # Convert cursor to DataFrame
                if isinstance(result, list):
                    df = pd.DataFrame(result)
                else:
                    df = pd.DataFrame(list(result))

                st.subheader("Results")
                st.dataframe(df)

                st.session_state.last_result = df
                st.session_state.last_query = mongo_query
                add_memory(user_query, "MONGO", mongo_query)

            except Exception as e:
                st.error(f"MongoDB Error: {e}")
                add_memory(user_query, "MONGO_ERROR", str(e))

        # ------------------------------
        # CHAT MODE
        # ------------------------------
        elif raw.startswith("MODE: CHAT"):
            reply = raw.replace("MODE: CHAT", "").strip()
            st.subheader("Chat Response")
            st.write(reply)
            add_memory(user_query, "CHAT", reply)

        else:
            st.error("Invalid AI Output format.")


# ----------------------------------------------------
# EXPLAIN RESULTS
# ----------------------------------------------------
if st.session_state.last_result is not None:
    if st.button("Explain Results"):
        with st.spinner("Explaining..."):

            explain_prompt = f"""
You are MongoDB Expert.
Explain the meaning of this query and result.

Query:
{st.session_state.last_query}

Result sample:
{st.session_state.last_result.head().to_string()}

Give a clear and simple explanation.
"""

            resp2 = call_llm_gemini(explain_prompt)
            explanation = safe_text(resp2) or "Could not generate explanation."

            st.subheader("AI Explanation")
            st.write(explanation)

            add_memory("Explain", "CHAT", explanation)
