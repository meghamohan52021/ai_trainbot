import streamlit as st
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(__file__))

from controller import ConversationController
from database import (
    initialise_db, seed_stations, seed_knowledge,
    create_session, close_session, log_message,

)

st.set_page_config(
    page_title="TrainBot",
    page_icon="🚂",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Background ─────────────────────────────────────────────────────────────────
bg_path = os.path.join(os.path.dirname(__file__), "background.png")
with open(bg_path, "rb") as f:
    bg_b64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500&family=IBM+Plex+Mono:wght@400&display=swap');

html {{
    background: url("data:image/png;base64,{bg_b64}") center center / cover fixed !important;
}}
body {{
    background: rgba(0,0,0,0.58) !important;
}}
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section[data-testid="stMain"],
.stApp {{
    background: transparent !important;
}}

#MainMenu, footer, header {{ visibility: hidden; }}

.block-container {{
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    max-width: 620px !important;
}}

/* ── Hide label, press enter hint, and grey wrapper on text input ── */
.stTextInput label {{
    display: none !important;
}}
.stTextInput > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}}
.stTextInput > div > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
small, .stTextInput + small {{
    display: none !important;
}}
/* Hide "Press Enter to apply" */
[data-testid="InputInstructions"] {{
    display: none !important;
}}
.stTextInput > div > div > div > small {{
    display: none !important;
}}

/* ── START SCREEN ── */
.start-screen {{
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 26vh;
    text-align: center;
}}
.start-title {{
    font-family: 'Playfair Display', serif;
    font-size: 3.4rem;
    font-weight: 600;
    color: #f0ede6;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 0.5rem;
}}
.start-sub {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: rgba(255,255,255,0.28);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}}

/* ── CHAT SCREEN HEADER ── */
.chat-header {{
    display: flex;
    align-items: baseline;
    padding: 2.2rem 0 0.9rem 0;
}}
.chat-brand-name {{
    font-family: 'Playfair Display', serif;
    font-size: 1.8rem;
    font-weight: 600;
    color: #f0ede6;
    letter-spacing: -0.025em;
}}
.chat-brand-tag {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    color: rgba(255,255,255,0.22);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-left: 0.65rem;
}}

/* ── CHAT CONTAINER ── */
.chat-container {{
    background: rgba(6, 10, 20, 0.72);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1.2rem;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    height: 52vh;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(255,255,255,0.07) transparent;
}}
.chat-spacer {{ flex: 1; }}

/* Bot message */
.msg-bot-wrap {{
    display: flex;
    gap: 0.55rem;
    align-items: flex-start;
}}
.bot-avatar {{
    width: 22px;
    height: 22px;
    background: rgba(255,255,255,0.08);
    border-radius: 50%;
    font-size: 8px;
    color: rgba(255,255,255,0.35);
    font-family: 'IBM Plex Mono', monospace;
    flex-shrink: 0;
    margin-top: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.msg-bot {{
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 2px 12px 12px 12px;
    padding: 0.6rem 0.85rem;
    font-size: 0.875rem;
    line-height: 1.65;
    color: #d8d4cc;
    max-width: 86%;
    white-space: pre-wrap;
    font-weight: 300;
    font-family: 'IBM Plex Sans', sans-serif;
}}

/* User message */
.msg-user-wrap {{
    display: flex;
    justify-content: flex-end;
}}
.msg-user {{
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.12);
    color: #f0ede6;
    border-radius: 12px 2px 12px 12px;
    padding: 0.52rem 0.85rem;
    font-size: 0.855rem;
    line-height: 1.55;
    max-width: 66%;
    font-weight: 300;
    font-family: 'IBM Plex Sans', sans-serif;
}}

/* ── RESET LINK ── */
.input-meta {{
    display: flex;
    justify-content: flex-end;
    padding: 0.4rem 0.2rem 0.25rem 0;
}}
.reset-label, .reset-label:visited {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.66rem;
    color: rgba(255,255,255,0.2) !important;
    text-decoration: underline !important;
    text-underline-offset: 3px;
    letter-spacing: 0.03em;
    cursor: pointer;
}}
.reset-label:hover {{
    color: rgba(255,255,255,0.5) !important;
}}

/* ── INPUT BOX ── */
.stTextInput > div > div > input {{
    background: rgba(6,10,20,0.72) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 24px !important;
    color: #f0ede6 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 300 !important;
    padding: 0.72rem 1.2rem !important;
    box-shadow: none !important;
    caret-color: #f0ede6 !important;
}}
.stTextInput > div > div > input:focus {{
    border-color: rgba(255,255,255,0.3) !important;
    box-shadow: none !important;
    outline: none !important;
}}
.stTextInput > div > div > input::placeholder {{
    color: rgba(255,255,255,0.2) !important;
}}

/* ── SEND BUTTON ── */
.stButton > button {{
    width: 44px !important;
    height: 44px !important;
    min-width: 44px !important;
    border-radius: 50% !important;
    background: #f0ede6 !important;
    color: #0a0e1a !important;
    border: none !important;
    font-size: 1.1rem !important;
    padding: 0 !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-top: 1px !important;
}}
.stButton > button:hover {{
    background: #ffffff !important;
}}

/* Hide column gaps */
[data-testid="column"] {{
    padding-left: 0.25rem !important;
    padding-right: 0.25rem !important;
}}

/* ── NAV LAUNCHER ── */
.nav-launcher {{
    position: fixed;
    top: 1rem;
    left: 1rem;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.4rem;
}}
.nav-toggle {{
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: rgba(20, 24, 40, 0.85);
    border: 1px solid rgba(255,255,255,0.12);
    backdrop-filter: blur(10px);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    color: #f0ede6;
    transition: background 0.15s;
    flex-shrink: 0;
}}
.nav-toggle:hover {{
    background: rgba(40, 44, 60, 0.95);
}}
.nav-bubbles {{
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    overflow: hidden;
    max-height: 0;
    opacity: 0;
    transition: max-height 0.25s ease, opacity 0.2s ease;
}}
.nav-bubbles.open {{
    max-height: 120px;
    opacity: 1;
}}
.nav-bubble {{
    display: block;
    padding: 0.4rem 0.85rem;
    border-radius: 10px;
    background: rgba(20, 24, 40, 0.88);
    border: 1px solid rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.75rem;
    font-weight: 400;
    color: #f0ede6;
    text-decoration: none !important;
    white-space: nowrap;
    transition: background 0.15s;
}}
.nav-bubble:hover {{
    background: rgba(60, 65, 90, 0.95);
    color: #ffffff;
}}
.nav-bubble.active {{
    border-color: rgba(255,255,255,0.25);
    color: #ffffff;
}}


div[data-testid="stVerticalBlock"] > div:last-child .stButton > button {{
    width: 34px !important;
    height: 34px !important;
    min-width: 34px !important;
    border-radius: 9px !important;
    background: transparent !important;
    border: 1.5px solid rgba(255,255,255,0.7) !important;
    color: #f0ede6 !important;
    font-size: 14px !important;
    padding: 0 !important;
    backdrop-filter: blur(12px) !important;
}}
div[data-testid="stVerticalBlock"] > div:last-child .stButton > button:hover {{
    background: rgba(255,255,255,0.08) !important;
    border-color: #ffffff !important;
}}
div[data-testid="stVerticalBlock"] > div:last-child a {{
    font-size: 0.75rem !important;
    color: rgba(255,255,255,0.75) !important;
    padding: 5px 12px !important;
    border-radius: 8px !important;
    background: rgba(10,14,26,0.85) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    backdrop-filter: blur(12px) !important;
    text-decoration: none !important;
    display: block !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}}
div[data-testid="stVerticalBlock"] > div:last-child a:hover {{
    background: rgba(40,45,65,0.95) !important;
    color: #ffffff !important;
}}

[data-testid="stButton"]:has(button[aria-label="nav_toggle"]) button,
div:has(> [data-testid="stButton"] button[title="⊹"]) button {{
    width: 34px !important;
    height: 34px !important;
    min-width: 34px !important;
    border-radius: 9px !important;
    background: transparent !important;
    border: 1.5px solid rgba(255,255,255,0.7) !important;
    color: #f0ede6 !important;
    font-size: 13px !important;
    padding: 0 !important;
    position: fixed !important;
    top: 14px !important;
    left: 14px !important;
    z-index: 9999 !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
}}

/* ── Sidebar styling ── */

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] span {{
    color: rgba(255,255,255,0.75) !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}}

/* ── Top-right nav ── */
.top-nav {{
    position: fixed;
    top: 16px;
    right: 20px;
    z-index: 99999;
    display: flex;
    gap: 10px;
    align-items: center;
}}
.top-nav a {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.35);
    text-decoration: none;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.12);
    background: rgba(8,12,24,0.7);
    backdrop-filter: blur(8px);
    transition: color 0.15s, border-color 0.15s;
}}
.top-nav a:hover {{
    color: rgba(255,255,255,0.8);
    border-color: rgba(255,255,255,0.3);
}}
</style>
""", unsafe_allow_html=True)








st.markdown('<div class="top-nav"><a href="/">Main</a><a href="/admin">Admin</a></div>', unsafe_allow_html=True)
# ── Init ───────────────────────────────────────────────────────────────────────
initialise_db()
seed_stations()
seed_knowledge()

if "controller" not in st.session_state:
    st.session_state.controller = ConversationController()
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.turn = 0
    st.session_state.session_id = create_session()
if "input_key" not in st.session_state:
    st.session_state.input_key = 0
if "do_reset" not in st.session_state:
    st.session_state.do_reset = False

# ── Reset handler ──────────────────────────────────────────────────────────────
if st.session_state.do_reset:
    close_session(st.session_state.session_id, task_completed=None)
    st.session_state.controller = ConversationController()
    st.session_state.session_id = create_session()
    st.session_state.messages = []
    st.session_state.turn = 0
    st.session_state.input_key += 1
    st.session_state.do_reset = False
    st.rerun()

has_messages = len(st.session_state.messages) > 0
task = st.session_state.controller.state.current_task


# ── START SCREEN ───────────────────────────────────────────────────────────────
if not has_messages:
    st.markdown("""
    <div class="start-screen">
        <div class="start-title">TrainBot</div>
        <div class="start-sub">Ask me about tickets, delays or fares</div>
    </div>
    """, unsafe_allow_html=True)

    col_input, col_send = st.columns([11, 1])
    with col_input:
        user_input = st.text_input(
            "msg",
            placeholder="Tell me about your journey in your own words...",
            key=f"input_{st.session_state.input_key}"
        )
    with col_send:
        send = st.button("↑")

    if send and user_input.strip():
        text = user_input.strip()
        greeting = st.session_state.controller.prompts.greeting()
        st.session_state.messages.append({"role": "bot", "text": greeting})
        log_message(st.session_state.session_id, 0, "bot", greeting)

        st.session_state.turn += 1
        st.session_state.messages.append({"role": "user", "text": text})
        log_message(st.session_state.session_id, st.session_state.turn, "user", text)

        response = st.session_state.controller.handle_user_input(text)
        st.session_state.turn += 1
        st.session_state.messages.append({"role": "bot", "text": response})
        log_message(st.session_state.session_id, st.session_state.turn, "bot", response)

        st.session_state.input_key += 1
        st.rerun()


# ── CHAT SCREEN ────────────────────────────────────────────────────────────────
else:
    st.markdown("""
    <div class="chat-header">
        <span class="chat-brand-name">TrainBot</span>
        <span class="chat-brand-tag">UK Rail Assistant</span>
    </div>
    """, unsafe_allow_html=True)

    # Messages
    messages_html = '<div class="chat-spacer"></div>'
    for msg in st.session_state.messages:
        text = msg["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if msg["role"] == "bot":
            messages_html += f'''
            <div class="msg-bot-wrap">
                <div class="bot-avatar">tb</div>
                <div class="msg-bot">{text}</div>
            </div>'''
        else:
            messages_html += f'''
            <div class="msg-user-wrap">
                <div class="msg-user">{text}</div>
            </div>'''

    st.markdown(f'''
<div class="chat-container" id="chat-box">{messages_html}</div>
<script>
  var c = document.getElementById("chat-box");
  if (c) c.scrollTop = c.scrollHeight;
</script>
''', unsafe_allow_html=True)

    # Reset link - clicking sets a query param, JS handles it
    st.markdown('''
    <div class="input-meta">
        <a class="reset-label" href="?reset=1">reset</a>
    </div>
    ''', unsafe_allow_html=True)

    # Detect reset via query param
    params = st.query_params
    if params.get("reset") == "1":
        st.query_params.clear()
        st.session_state.do_reset = True
        st.rerun()

    # Input row
    col_input, col_send = st.columns([11, 1])
    with col_input:
        user_input = st.text_input(
            "msg",
            placeholder="Continue the conversation...",
            key=f"input_{st.session_state.input_key}"
        )
    with col_send:
        send = st.button("↑")

    # Send
    if send and user_input.strip():
        text = user_input.strip()
        st.session_state.turn += 1
        st.session_state.messages.append({"role": "user", "text": text})
        log_message(st.session_state.session_id, st.session_state.turn, "user", text)

        response = st.session_state.controller.handle_user_input(text)
        st.session_state.turn += 1
        st.session_state.messages.append({"role": "bot", "text": response})
        log_message(st.session_state.session_id, st.session_state.turn, "bot", response)

        if "journey details are complete" in response or "delay details are complete" in response:
            completed_task = st.session_state.controller.state.current_task or task
            close_session(st.session_state.session_id, task_completed=completed_task)

        st.session_state.input_key += 1
        st.rerun()