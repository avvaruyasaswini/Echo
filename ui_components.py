import streamlit as st
import html
import json
from memory import (
    remember, recall, create_conversation, get_conversations,
    update_password, clear_conversation, delete_conversation
)

# ---------------------
# Helper utilities
# ---------------------
META_SCOPE = "meta"  # we store per-conversation metadata under this scope

def _get_meta(user_id, convo_id):
    """Return dict metadata for a convo (pinned, archived, title_override)."""
    raw = recall(user_id, META_SCOPE, f"convo_meta_{convo_id}")
    if not raw:
        return {"pinned": False, "archived": False, "title": None}
    try:
        return json.loads(raw)
    except Exception:
        return {"pinned": False, "archived": False, "title": None}

def _set_meta(user_id, convo_id, meta):
    """Persist metadata dict for a convo."""
    remember(user_id, META_SCOPE, f"convo_meta_{convo_id}", json.dumps(meta))

def pin_conversation(user_id, convo_id, pin=True):
    meta = _get_meta(user_id, convo_id)
    meta["pinned"] = bool(pin)
    _set_meta(user_id, convo_id, meta)

def archive_conversation(user_id, convo_id, archive=True):
    meta = _get_meta(user_id, convo_id)
    meta["archived"] = bool(archive)
    _set_meta(user_id, convo_id, meta)

def rename_conversation(user_id, convo_id, new_title):
    meta = _get_meta(user_id, convo_id)
    meta["title"] = new_title
    _set_meta(user_id, convo_id, meta)

def get_display_title(user_id, convo_id, original_title):
    meta = _get_meta(user_id, convo_id)
    return meta.get("title") or original_title

# ---------------------
# UI: Sidebar (Cleaned Up)
# ---------------------
# The helper functions at the top of the file remain the same...
# (_get_meta, _set_meta, etc.)

# ---------------------
# UI: Sidebar (BULLETPROOF VERSION)
# ---------------------
def show_sidebar(active_conversation_id):
    """
    A cleaner, refactored sidebar using st.popover for menus.
    - Added a "guard clause" to prevent crashing if the user is not logged in.
    """
    
    # --- !! NEW FIX STARTS HERE !! ---
    # First, safely get the user_id. If it doesn't exist, the user is not logged in.
    user_id = st.session_state.get("user_id")

    # If there's no user_id, don't try to render the rest of the sidebar.
    # We can show a simple message or just show nothing.
    if not user_id:
        st.sidebar.warning("Please log in to see your conversations.")
        return # Stop the function here
    
    # Safely get the username, providing a default if it's missing for some reason.
    username = st.session_state.get("username", "User")
    # --- !! NEW FIX ENDS HERE !! ---


    # ------- CSS --------
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"][aria-expanded="true"] { width: 340px; }
            .glass {
            }
            .sidebar-header { font-size:20px; font-weight:700; margin-bottom:10px; }
            .conversation-list { flex-grow:1; overflow-y:auto; margin-bottom:8px; padding-right:6px; }
            /* Remove the popover arrow completely */
            [data-testid="stPopover"] > button::after,
            [data-testid="stPopover"] > button svg {
                display: none !important;
            }
            [data-testid="stPopover"] > button { font-size: 1.2rem; }
            button[kind="primary"] {
            border-radius: 8px;
            background-color: #4a90e2;
            color: white;
            font-weight: 500;
        }
        button[kind="secondary"] {
            border-radius: 8px;
            background-color: transparent;
            color: #ccc;
            border: 1px solid #555;
        }
        button:hover {
            opacity: 0.85;
        }
        .conversation-list button {
        margin-bottom: 6px;
        text-align: left;
        padding: 6px 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -------- Container start --------
    st.sidebar.markdown('<div class="glass">', unsafe_allow_html=True)
    
    # Now we know 'username' exists, so this is safe.
    st.sidebar.markdown(f'<div class="sidebar-header">Welcome, {html.escape(username)}</div>', unsafe_allow_html=True)

    current_scope = "private" if st.session_state.get("private_mode") else "public"
    active_convo_key = f"active_{current_scope}_convo_id"

    # ------- New chat -------
    if st.sidebar.button("New Chat", use_container_width=True):
        count = len(get_conversations(user_id, current_scope)) + 1
        convo_id = create_conversation(user_id, f"Chat #{count}", current_scope)
        st.session_state[active_convo_key] = convo_id
        st.rerun()

    # ... THE REST OF THE FUNCTION IS EXACTLY THE SAME AS THE PREVIOUS "100% COMPLETE" ONE ...
    # (I've included it all below just in case)
    
    st.sidebar.subheader("Your Conversations")

    raw_convos = get_conversations(user_id, current_scope) or []
    pinned, unpinned, archived = [], [], []

    for convo_id, convo_title in raw_convos:
        meta = _get_meta(user_id, convo_id)
        display_title = get_display_title(user_id, convo_id, convo_title)
        convo_data = (convo_id, display_title, meta)
        
        if meta.get("archived"):
            archived.append(convo_data)
        elif meta.get("pinned"):
            pinned.append(convo_data)
        else:
            unpinned.append(convo_data)

    ordered = pinned + unpinned

    st.sidebar.markdown('<div class="conversation-list">', unsafe_allow_html=True)

    for convo_id, display_title, meta in ordered:
        is_active = (convo_id == active_conversation_id)
        
        col_main, col_dot = st.sidebar.columns([0.82, 0.18])

        with col_main:
            if st.button(
                display_title, key=f"select_{convo_id}",
                use_container_width=True, type="primary" if is_active else "secondary"
            ):
                st.session_state[active_convo_key] = convo_id
                st.rerun()

        with col_dot:
            with st.popover("⋮", use_container_width=True):
                new_title = st.text_input("Rename chat", value=display_title, key=f"rename_{convo_id}")
                if st.button("Save", key=f"save_rename_{convo_id}"):
                    rename_conversation(user_id, convo_id, new_title.strip())
                    st.rerun()
                
                st.divider()

                pin_text = "Unpin" if meta.get("pinned") else "Pin"
                if st.button(pin_text, key=f"pin_{convo_id}", use_container_width=True):
                    pin_conversation(user_id, convo_id, not meta.get("pinned"))
                    st.rerun()

                if st.button("Archive", key=f"archive_{convo_id}", use_container_width=True):
                    archive_conversation(user_id, convo_id, True)
                    if st.session_state.get(active_convo_key) == convo_id:
                        st.session_state[active_convo_key] = None
                    st.rerun()
                
                if st.button("Delete", type="primary", key=f"delete_{convo_id}", use_container_width=True):
                    delete_conversation(convo_id)
                    remember(user_id, META_SCOPE, f"convo_meta_{convo_id}", None)
                    if st.session_state.get(active_convo_key) == convo_id:
                        st.session_state[active_convo_key] = None
                    st.rerun()

    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    if archived:
        st.sidebar.divider()
        with st.sidebar.expander(f"Archived ({len(archived)})", expanded=False):
            for convo_id, display_title, meta in archived:
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    if st.button(display_title, key=f"select_arch_{convo_id}", use_container_width=True):
                        archive_conversation(user_id, convo_id, False)
                        st.session_state[active_convo_key] = convo_id
                        st.rerun()
                with col2:
                    with st.popover("...", key=f"pop_arch_{convo_id}", use_container_width=True):
                        if st.button("Restore", key=f"restore_arch_{convo_id}", use_container_width=True):
                            archive_conversation(user_id, convo_id, False)
                            st.rerun()
                        if st.button("Delete", type="primary", key=f"delete_arch_{convo_id}", use_container_width=True):
                            delete_conversation(convo_id)
                            remember(user_id, META_SCOPE, f"convo_meta_{convo_id}", None)
                            st.rerun()

    st.sidebar.divider()
    with st.sidebar.expander("Quick Relax Tools"):
        st.markdown("**Box Breathing:** Inhale 4s → Hold 4s → Exhale 4s → Hold 4s")
        st.markdown("**5-4-3-2-1:** 5 things you see → 4 touch → 3 hear → 2 smell → 1 taste")

    with st.sidebar.expander("Manage"):
        st.subheader("Private Mode Keyword")
        keyword = recall(user_id, "public", "secret_keyword")
        if not keyword:
            with st.form("set_keyword", clear_on_submit=True):
                new_kw = st.text_input("Set Keyword", type="password")
                if st.form_submit_button("Save") and new_kw:
                    remember(user_id, "public", "secret_keyword", new_kw.strip())
                    st.success("Keyword saved.")
                    st.rerun()
        else:
            st.success("Keyword already set.")
            if st.button("Reset Keyword"):
                remember(user_id, "public", "secret_keyword", None)
                st.rerun()

        st.subheader("Change Password")
        with st.form("change_pass", clear_on_submit=True):
            cur = st.text_input("Current Password", type="password")
            new = st.text_input("New Password", type="password")
            conf = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if not cur or not new or not conf:
                    st.warning("Fill all fields.")
                elif new != conf:
                    st.error("Passwords do not match.")
                elif update_password(user_id, cur, new):
                    st.success("Password updated.")
                else:
                    st.error("Incorrect current password.")

        st.subheader("Current Conversation")
        if st.button("Clear Chat History", use_container_width=True):
            if active_conversation_id:
                clear_conversation(active_conversation_id)
                st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("Log Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("</div>", unsafe_allow_html=True)