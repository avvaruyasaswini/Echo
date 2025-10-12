import streamlit as st
from datetime import datetime, timezone
import html
from dotenv import load_dotenv
import os
from prompts import get_echo_prompt
from memory import (
    add_user,
    check_user,
    remember,
    recall,
    create_conversation,
    get_conversations,
    get_messages,
    add_message,
    get_conversation_title,
    update_conversation_title,
    delete_conversation,
    init_db
)
import requests
from echo_api import generate_response

load_dotenv()
API_KEY = os.getenv("ECHO_API_KEY")
init_db()
st.set_page_config(page_title="Echo", layout="wide", initial_sidebar_state="expanded")
# -----------------------
# CSS
# -----------------------
st.markdown("""
<style>
/* Main container for scrolling messages */
.chat-container {
    height: 100vh
    overflow-y: auto;
    padding: 20px;
    padding-bottom: 120px; /* IMPORTANT: Adds space at the bottom */
}

/* NEW - Responsive */
.fixed-input {
    position: fixed;
    bottom: 0;
    left: var(--sidebar-width);
    right: 0;
    transition: left 0.3s ease;
}
@media (max-width: 768px) {
    .fixed-input {
        left: 0 !important;
    }
}
/* Adjust left position when sidebar is collapsed (optional but good practice) */
body[data-sidebar-state="collapsed"] .fixed-input {
    left: 0;
}
/* Send button inside fixed input */
.fixed-input button {
    width: 100%;
    margin-top: 6px;
    background: rgba(0,200,255,0.9);
    color: black;
    font-weight: bold;
    border-radius: 10px;
    border: none;
}

/* Adjust left if sidebar collapsed */
body[data-sidebar-state="collapsed"] .fixed-input {
    left: 0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Input area (bottom half of right_col) */
.input-area {
    padding: 10px 0 0 0;
    height: 90px; /* same as text_area height */
    background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
    border-top: 1px solid rgba(255,255,255,0.06);
    border-radius: 0 0 14px 14px;
}

/* Textarea inside the input area */
.input-area textarea {
    width: 100% !important;
    height: 70px !important;
    background-color: rgba(255,255,255,0.05) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
    padding: 8px;
}

/* Send button */
.input-area button {
    width: 100%;
    background: rgba(0, 200, 255, 0.9);
    color: black;
    font-weight: bold;
    border: none;
    margin-top: 4px;
    border-radius: 10px;
}

:root {
    --glass-bg: rgba(255,255,255,0.03);
    --glass-border: rgba(255,255,255,0.06);
    --accent: rgba(0, 200, 255, 0.9);
}
html, body, [class*="stApp"] {
    background: linear-gradient(180deg, #0f1724 0%, #071021 100%);
    color: #e6eef6;
}
.glass {
    background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
    border-radius: 14px;
}
.center-card {
    max-width:900px;
    margin: 14px auto;
}
.bubble {
    display: inline-block;
    padding: 12px 14px;
    margin: 8px 0;
    border-radius: 14px;
    max-width: 72%;
    line-height: 1.25;
    box-shadow: 0 4px 12px rgba(2,6,23,0.6);
}
.user-bubble {
    background: linear-gradient(90deg, #34C759, #30B158);
    color: white;
    border-radius: 18px 18px 4px 18px;
    float: right;
    text-align: right;
}
.assistant-bubble {
    background: #E5E5EA;
    color: black;
    border-radius: 18px 18px 18px 4px;
    float: left;
    text-align: left;
}
.meta {
    font-size: 11px;
    color: #9fb0c9;
    margin-top: 6px;
}
.clearfix { clear: both; }
.echoing-bubble {
    display: inline-block;
    opacity: 0.7;
    animation: blink 1.5s infinite;
}
@keyframes blink {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.8; }
}
div[data-testid="stTextArea"] textarea {
    background-color: rgba(255, 255, 255, 0.05) !important;
    color: white !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 10px !important;
}
div[data-testid="stFormSubmitButton"] button {
    width: 100%;
    background: var(--accent);
    color: black;
    font-weight: bold;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# -----------------------
# Helpers
# -----------------------
def ensure_default_convo(user_id, scope="public"):
    convs = get_conversations(user_id, scope)
    if not convs:
        title = "New Chat"
        new_id = create_conversation(user_id, title, scope)
        return new_id
    return convs[0][0]

def render_messages(conversation_id):
    messages = get_messages(conversation_id)
    for m in messages:
        ts_utc = datetime.strptime(m.get("timestamp"), "%Y-%m-%d %H:%M:%S")
        ts_local = ts_utc.replace(tzinfo=timezone.utc).astimezone(tz=None)
        ts_str = ts_local.strftime("%I:%M %p")

        if m["role"] == "user":
            st.markdown(f'<div class="bubble user-bubble">{html.escape(m["content"])}</div><div class="clearfix"></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="meta" style="text-align:right;">You • {ts_str}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bubble assistant-bubble">{html.escape(m["content"])}</div><div class="clearfix"></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="meta" style="text-align:left;">Echo • {ts_str}</div>', unsafe_allow_html=True)

# -----------------------
# Session state
# -----------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "private_mode" not in st.session_state:
    st.session_state.private_mode = False
if "message_to_process" not in st.session_state:
    st.session_state.message_to_process = None

from ui_components import show_sidebar

# -----------------------
# Logged-in / auth UI
# -----------------------
if not st.session_state.user_id:
    # login / register UI
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.markdown('<div class="glass center-card">', unsafe_allow_html=True)
        st.markdown("<h2>Welcome to <strong>Echo</strong></h2>", unsafe_allow_html=True)
        st.markdown("<p style='margin:0 0 14px 0; color:#9fb0c9;'>Dark mode enabled. Secure private chats. Salted passwords. No nonsense.</p>", unsafe_allow_html=True)
        tabs = st.tabs(["Login", "Register", "Quick Demo"])
        # Login tab
        with tabs[0]:
            with st.form("login_form"):
                user = st.text_input("Username", placeholder="your-username", key="login_user")
                pw = st.text_input("Password", type="password", key="login_pw")
                submitted = st.form_submit_button("Log in")
                if submitted:
                    uid = check_user(user.strip(), pw)
                    if uid:
                        st.session_state.user_id = uid
                        st.session_state.username = user.strip()
                        pub_active = ensure_default_convo(uid, "public")
                        priv_active = ensure_default_convo(uid, "private")
                        st.session_state["active_public_convo_id"] = pub_active
                        st.session_state["active_private_convo_id"] = priv_active
                        st.rerun()
                    else:
                        st.error("Wrong username or password.")
        # Register tab
        with tabs[1]:
            with st.form("register_form"):
                r_user = st.text_input("Pick a username", key="reg_user")
                r_pw = st.text_input("Pick a password", type="password", key="reg_pw")
                r_pw2 = st.text_input("Confirm password", type="password", key="reg_pw2")
                do_register = st.form_submit_button("Create account")
                if do_register:
                    if not r_user or not r_pw or not r_pw2:
                        st.warning("Fill all fields.")
                    elif r_pw != r_pw2:
                        st.error("Passwords don't match.")
                    else:
                        ok = add_user(r_user.strip(), r_pw)
                        if ok:
                            st.success("Account created. Log in now.")
                        else:
                            st.error("Username already exists.")
        # Demo tab
        with tabs[2]:
            st.info("Quick Demo (temporary user, no password).")
            if st.button("Start Demo Account"):
                demo_username = f"demo_{int(datetime.now(timezone.utc).timestamp())}"
                try:
                    add_user(demo_username, "demopw123")
                    uid = check_user(demo_username, "demopw123")
                    st.session_state.user_id = uid
                    st.session_state.username = demo_username
                    pub_active = ensure_default_convo(uid, "public")
                    priv_active = ensure_default_convo(uid, "private")
                    st.session_state["active_public_convo_id"] = pub_active
                    st.session_state["active_private_convo_id"] = priv_active
                    st.rerun()
                except Exception:
                    st.error("DB issue with demo user.")
        st.markdown("</div>", unsafe_allow_html=True)
else:
    # Logged-in chat UI
    active_scope = "private" if st.session_state.get("private_mode") else "public"
    active_key = f"active_{active_scope}_convo_id"
    if active_key not in st.session_state or not st.session_state.get(active_key):
        st.session_state[active_key] = ensure_default_convo(st.session_state.user_id, active_scope)
    active_convo = st.session_state.get(active_key)
    show_sidebar(active_convo)
    
    # --- START OF CORRECTED LAYOUT ---

    # Header
    st.markdown(f"<h3 style='margin:0'>{get_conversation_title(active_convo)}</h3>", unsafe_allow_html=True)
    st.markdown("<div style='color:#9fb0c9; margin-bottom:10px;'>Modern chat • Dark glass • C3 interface</div>", unsafe_allow_html=True)

    # Chat messages container (this is the scrollable part)
    st.markdown('<div class="chat-container" id="chat-container">', unsafe_allow_html=True)
    render_messages(active_convo)
    if st.session_state.message_to_process:
        st.markdown('<div class="bubble assistant-bubble echoing-bubble">echoing…</div><div class="clearfix"></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True) # CLOSE chat-container
    st.markdown("""
        <script>
        setTimeout(function() {
            var chatContainer = parent.document.querySelector('[data-testid="stVerticalBlock"] .chat-container');
            if (chatContainer) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }, 100);
        </script>
        """, unsafe_allow_html=True)
    # Fixed input area (now outside the chat container)
    st.markdown('<div class="fixed-input">', unsafe_allow_html=True)
    with st.form("msg_form_unique", clear_on_submit=True):
        user_msg = st.text_area(
            "Message",
            placeholder="Type your message...",
            key="user_msg_text_unique",
            height=70,
            label_visibility="collapsed"
        )
        send = st.form_submit_button("Send")
    st.markdown('</div>', unsafe_allow_html=True) # CLOSE fixed-input

    # --- END OF CORRECTED LAYOUT ---

    # Logic (remains the same)
    # ------------------- MESSAGE PROCESSING -------------------
    if send and user_msg.strip():
        # Save user message to session state
        st.session_state.message_to_process = user_msg.strip()

    # Process the message if there’s one pending
    if st.session_state.message_to_process:
        user_msg = st.session_state.message_to_process
        st.session_state.message_to_process = None

        # 1️⃣ Add user message to chat
        add_message(active_convo, "user", user_msg, "user")

        # 2️⃣ Prepare context from last 10 messages
        messages = get_messages(active_convo)
        context_text = " ".join([m["content"] for m in messages[-10:]])

        # 3️⃣ Build the prompt
        prompt_text = get_echo_prompt(user_msg, context_text)

        # 4️⃣ Call Echo API
        raw_json = generate_response(prompt_text)
        st.text(f"DEBUG: {raw_json}")  # <-- debug raw output

        # 5️⃣ Parse JSON safely
        import json
        try:
            data = json.loads(raw_json)
            reply = data.get("response", raw_json)  # fallback to raw text
        except json.JSONDecodeError:
            reply = raw_json  # fallback to raw text if JSON fails

        # 6️⃣ Add Echo's reply to chat
        add_message(active_convo, "assistant", reply, "assistant")

        # 7️⃣ Trigger a single rerun to refresh the chat UI
        st.rerun()

    # ------------------- AUTO-SCROLL -------------------
    st.markdown("""
    <script>
    const chatContainer = document.getElementById("chat-container");
    if (chatContainer) { chatContainer.scrollTop = chatContainer.scrollHeight; }
    </script>
    """, unsafe_allow_html=True)


    # Auto-scroll (target the correct container)
    st.markdown("""
    <script>
    const chatContainer = document.getElementById("chat-container");
    if (chatContainer) { chatContainer.scrollTop = chatContainer.scrollHeight; }
    </script>
    """, unsafe_allow_html=True)