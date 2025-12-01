import streamlit as st
from pymongo import MongoClient
from bson import ObjectId, SON
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
    client = MongoClient("mongodb://localhost:27017")
    db = client["attendance_records"]          # YOUR DATABASE
    return db


# ----------------------------------------------------
# CLEAN MONGODB DOCUMENTS BEFORE DATAFRAME
# ----------------------------------------------------
def clean_docs(docs):
    cleaned = []

    for d in docs:
        clean_doc = {}
        for k, v in d.items():

            if isinstance(v, ObjectId):
                clean_doc[k] = str(v)

            elif isinstance(v, dict) or isinstance(v, list):
                clean_doc[k] = str(v)

            else:
                clean_doc[k] = v

        cleaned.append(clean_doc)

    return cleaned


# ----------------------------------------------------
# SESSION
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
# MONGO SCHEMA FOR AI
# ----------------------------------------------------
MONGO_SCHEMA = """
You are an AI MongoDB Expert.

DATABASE = attendance_records
COLLECTION = sample

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


Always generate PyMongo syntax:

    db.sample.find({ ... })

or

    db.sample.aggregate([ ... ])

RULES:
1. Keys MUST be in double quotes → "$match"
2. SORT must be list style:
       .sort([("category", 1)])
3. Must be valid Python code for eval()
4. NO JavaScript-style code
6. Always format output like:

    MODE: MONGO
    <MONGO QUERY>                                 
    or
    MODE: CHAT
    <chat reply>

====================================================
PRIORITY LOGIC (MOST IMPORTANT)
====================================================
Before generating MONGO query:
1. do not hallucinate user intent
2. Understand user intent  
3. Identify required table(s)  
4. Apply correct FK joins  
5. Use optimized filters & indexes  
6. Produce final, perfect, raw MONGO query
"""

#              GUI
st.set_page_config(page_title="AI MongoDB Manager", layout="centered")
st.title("🤖 AI Database manager (queries+chat)-v-MONGODB")

with st.expander("Conversation Memory"):
    st.text(display_memory())

with st.expander("MongoDB Schema"):
    st.code(MONGO_SCHEMA)


user_query = st.text_input("Ask anything (MongoDB):")


# ----------------------------------------------------
# RUN
# ------------------------------------------------mgupta@mind-roots.com----
if st.button("Run"):
    with st.spinner("Thinking..."):

        full_prompt = f"""
{MONGO_SCHEMA}

Previous conversation:
{display_memory()}

User: "{user_query}"
"""

        resp = call_llm_gemini(full_prompt)
        raw = safe_text(resp)
        st.write(raw)

        if raw is None:
            st.error("⚠ Empty AI response.")
            st.stop()

        if raw.upper().strip().startswith("MODE: MONGO"):
            raw = raw.replace("```", "").replace("json", "").replace("python", "").strip()
            mongo_query = raw.replace("MODE: MONGO", "").strip()
            st.subheader("Generated Query:")
            st.code(mongo_query)

            try:
                db = connect_mongo()

                safe_context = {"db": db}
                result = eval(mongo_query, safe_context)
                st.write(result)
                docs = list(result)
                st.write(docs)
                docs = clean_docs(docs)

                df = pd.DataFrame(docs)
                
                st.subheader("Results")
                st.dataframe(df)

                st.session_state.last_result = df
                st.session_state.last_query = mongo_query
                add_memory(user_query, "MONGO", mongo_query)

            except Exception as e:
                st.error(f"MongoDB Error: {e}")
                add_memory(user_query, "MONGO_ERROR", str(e))

        elif raw.upper().strip().startswith("MODE: CHAT"):
            reply = raw.replace("MODE: CHAT", "").strip()
            st.subheader("Chat Response")
            st.write(reply)
            add_memory(user_query, "CHAT", reply)

        else:
            st.error("Invalid AI output format.")


# ----------------------------------------------------
# EXPLAIN RESULTS
# ----------------------------------------------------
if st.session_state.last_result is not None:
    if st.button("Explain Results"):
        with st.spinner("Explaining..."):

            explain_prompt = f"""
Explain the meaning of this MongoDB query and its result.

Query:
{st.session_state.last_query}

Sample Result:
{st.session_state.last_result.head().to_string()}
"""

            resp2 = call_llm_gemini(explain_prompt)
            explanation = safe_text(resp2) or "Could not explain."

            st.subheader("AI Explanation")
            st.write(explanation)

            add_memory("Explain", "CHAT", explanation)
