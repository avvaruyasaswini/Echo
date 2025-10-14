import streamlit as st
import google.generativeai as genai
import json
from datetime import datetime, timezone
import html
from dotenv import load_dotenv
import os
from prompts import get_echo_prompt
from memory import (
    add_user, check_user, remember, recall, create_conversation, 
    get_conversations, get_messages, add_message, get_conversation_title, 
    update_conversation_title, delete_conversation, init_db, update_password,
    clear_conversation
)
from ui_components import show_sidebar
# load custom styles (UI only)
# load custom styles (UI only)
if os.path.exists("ui_styles.css"):
    st.markdown(f"<style>{open('ui_styles.css').read()}</style>", unsafe_allow_html=True)

# --- LOAD API KEY FROM .env FILE ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- INITIALIZE DATABASE & CONFIG ---
init_db()
st.set_page_config(page_title="Echo", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS ---
st.markdown("""
<style>
/* Your full custom CSS is here */
html, body, [class*="stApp"] {
    background: linear-gradient(180deg, #0f1724 0%, #071021 100%);
    color: #e6eef6;
}
/* Add other styles as needed */
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "user_id" not in st.session_state: st.session_state.user_id = None
if "username" not in st.session_state: st.session_state.username = None
if "private_mode" not in st.session_state: st.session_state.private_mode = False
if "active_public_convo_id" not in st.session_state: st.session_state.active_public_convo_id = None
if "active_private_convo_id" not in st.session_state: st.session_state.active_private_convo_id = None

# --- AUTHENTICATION / LOGIN PAGE ---
if not st.session_state.user_id:
    # Your full login/signup page code is here
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:        
        st.title("Echo - We Listen, We Don't Judge")
        st.subheader("Welcome! Please log in or create an account to continue.")
        tabs = st.tabs(["Login", "Register"])
        with tabs[0]:
            with st.form("login_form"):
                user = st.text_input("Username", key="login_user")
                pw = st.text_input("Password", type="password", key="login_pw")
                if st.form_submit_button("Log in"):
                    uid = check_user(user.strip(), pw)
                    if uid:
                        st.session_state.user_id = uid
                        st.session_state.username = user.strip()
                        st.rerun()
                    else:
                        st.error("Wrong username or password.")
        with tabs[1]:
            with st.form("register_form"):
                r_user = st.text_input("Pick a username", key="reg_user")
                r_pw = st.text_input("Pick a password", type="password", key="reg_pw")
                if st.form_submit_button("Create account"):
                    if not r_user or not r_pw:
                        st.warning("Please fill all fields.")
                    else:
                        if add_user(r_user.strip(), r_pw):
                            st.success("Account created. You can now log in.")
                        else:
                            st.error("Username already exists.")
else:
    # --- MAIN APP, SHOWN ONLY AFTER LOGIN ---

    # --- MODE AND SCOPE DETERMINATION (WITH UI BANNER) ---
    if st.session_state.private_mode:
        current_scope = "private"
        st.info("🔴 You are in Private Mode. These conversations are separate. Type 'exit' to return.")
    else:
        current_scope = "public"
    active_convo_id_key = f"active_{current_scope}_convo_id"
    
    # --- SIDEBAR ---
    show_sidebar(st.session_state.get(active_convo_id_key))
    
    # --- MAIN APP LOGIC ---
    conversations = get_conversations(st.session_state.user_id, current_scope)
    if not st.session_state.get(active_convo_id_key):
        if not conversations:
            st.session_state[active_convo_id_key] = create_conversation(st.session_state.user_id, "First Chat", current_scope)
        else:
            st.session_state[active_convo_id_key] = conversations[0][0]
        st.rerun()
    active_conversation_id = st.session_state[active_convo_id_key]

    # --- MAIN PAGE UI & CHAT DISPLAY ---
    st.title(get_conversation_title(active_conversation_id))
    st.markdown('<div class="app-subtext">Echo listens. Say anything — you’re safe here.</div>', unsafe_allow_html=True)

    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-pro-latest')
    else:
        st.error("API Key is not configured. Please check your .env file.")
        st.stop()

    current_messages = get_messages(active_conversation_id)
    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- BUG-FREE CHAT LOGIC ---
    
    # Check if it's the bot's turn to respond
    if current_messages and current_messages[-1]["role"] == "user":
        last_prompt = current_messages[-1]["content"]
        
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                try:
                    # The AI call is now safely inside the try block
                    user_strengths = recall(st.session_state.user_id, "public", "strengths") or []
                    user_facts = recall(st.session_state.user_id, current_scope, "facts") or []
                    context = ""
                    if user_strengths:
                        context += f"- User's known strengths: {', '.join(user_strengths)}\n"
                    if user_facts:
                        context += f"- Key facts the user has shared: {', '.join(user_facts)}\n"

                    smart_prompt = get_echo_prompt(last_prompt, context)
                    
                    response = model.generate_content(smart_prompt)
                    raw_text = response.text

                    # Robust JSON parser
                    start = raw_text.find('{')
                    end = raw_text.rfind('}') + 1
                    
                    if start != -1 and end != -1:
                        clean_json_str = raw_text[start:end]
                        json_response = json.loads(clean_json_str)
                        response_text = json_response["response"]
                        strengths = json_response.get("strengths", [])
                        facts = json_response.get("facts_learned", [])
                        
                        # --- Handle the response ---
                        if response_text == "INTERRUPT":
                            interrupt_message = "It sounds like your mind is spinning. Let's try a 30-second pause. I want you to look away from the screen and name one thing in the room that is blue. Take a deep breath."
                            add_message(active_conversation_id, "assistant", interrupt_message, "🤖")
                        else:
                            # --- MEMORY LOGIC ---
                            if strengths:
                                remember(st.session_state.user_id, current_scope, "strengths", strengths)
                            if facts:
                                remember(st.session_state.user_id, current_scope, "facts", facts)
                            
                            add_message(active_conversation_id, "assistant", response_text, "🤖")

                            # --- NEW: INTELLIGENT CHAT NAMING LOGIC ---
                            # Check if this is the very first exchange in a newly created chat
                            current_title = get_conversation_title(active_conversation_id)
                            if (current_title == "New Chat" or current_title.startswith("Chat #")) and len(get_messages(active_conversation_id)) == 2:
                                title_prompt = f"Summarize the following exchange in 3-5 words to be a chat title. Be concise and relevant. USER: '{last_prompt}' ASSISTANT: '{response_text}'"
                                title_response = model.generate_content(title_prompt).text
                                # Clean up the title (remove quotes, etc.) and update the database
                                new_title = title_response.strip().replace('"', '')
                                if new_title: # Ensure title is not empty
                                    update_conversation_title(active_conversation_id, new_title)

                    else: 
                        # Fallback if no JSON is found
                        add_message(active_conversation_id, "assistant", raw_text, "🤖")

                except Exception as e:
                    # This now handles errors from the AI call AND from parsing
                    error_message = "I'm having a little trouble connecting to my brain right now. Please try again in a moment."
                    add_message(active_conversation_id, "assistant", error_message, "🤖")
                    print(f"--- An error occurred during AI call or parsing ---")
                    print(f"Error: {e}")
                    print("--------------------------------------------------")
        st.rerun()

    # Handle the user's new input at the very end
    secret_keyword = recall(st.session_state.user_id, "public", "secret_keyword")
    if prompt := st.chat_input("Let's talk..."):
        if secret_keyword and prompt.strip().lower() == secret_keyword.lower():
            st.session_state.private_mode = True
            st.rerun()
        elif st.session_state.private_mode and prompt.strip().lower() == 'exit':
            st.session_state.private_mode = False
            st.rerun()
        else:
            add_message(active_conversation_id, "user", prompt, "👤")
            st.rerun()