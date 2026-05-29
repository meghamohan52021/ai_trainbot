import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(__file__))

from core.controller import ConversationController
from knowledge.database import (
    initialise_db, seed_stations, seed_knowledge,
    create_session, close_session, log_message,
)

st.set_page_config(
    page_title="ChooChooAI",
    page_icon="🚂",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Background image ───────────────────────────────────────────────────────────
bg_path = os.path.join(os.path.dirname(__file__), "background.png")
with open(bg_path, "rb") as f:
    bg_b64 = base64.b64encode(f.read()).decode()

# ── Train image ────────────────────────────────────────────────────────────────
train_b64 = ""
for train_filename in ("choochoo_train.png", "railguide_train.png"):
    train_path = os.path.join(os.path.dirname(__file__), train_filename)
    if os.path.exists(train_path):
        with open(train_path, "rb") as f:
            train_b64 = base64.b64encode(f.read()).decode()
        break

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400;1,600&family=Instrument+Sans:wght@300;400;500&family=IBM+Plex+Mono:wght@400&display=swap');

html {{ background: #fdf8ec !important; }}
body {{ background: #fdf8ec !important; }}

[data-testid="stApp"],
[data-testid="stAppViewContainer"],
section[data-testid="stMain"],
.stApp {{
    background: url("data:image/png;base64,{bg_b64}") center center / cover fixed no-repeat !important;
}}

[data-testid="stHeader"] {{ background: transparent !important; }}
#MainMenu, footer, header {{ visibility: hidden; }}

.block-container {{
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    max-width: 680px !important;
}}

.stTextInput label {{ display: none !important; }}
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
small, .stTextInput + small {{ display: none !important; }}
[data-testid="InputInstructions"] {{ display: none !important; }}

.start-screen {{
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 18vh;
    text-align: center;
}}
.start-title {{
    font-family: 'Playfair Display', serif;
    font-size: 3.6rem;
    font-weight: 600;
    color: #1a1a1a;
    letter-spacing: -0.03em;
    line-height: 1.05;
    margin-bottom: 0;
}}
.start-title-italic {{
    font-family: 'Playfair Display', serif;
    font-size: 3.6rem;
    font-weight: 400;
    font-style: italic;
    color: #3d6b4f;
    letter-spacing: -0.03em;
    line-height: 1.05;
    margin-bottom: 0.8rem;
    display: block;
}}
.start-sub {{
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.95rem;
    color: #5a5a5a;
    font-weight: 400;
    line-height: 1.5;
    margin-bottom: 2.2rem;
}}
.chips-row {{
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 1rem;
}}
.chip {{
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.78rem;
    color: #1a1a1a !important;
    background: rgba(210, 225, 210, 0.5) !important;
    border: 1px solid rgba(120, 160, 120, 0.45) !important;
    border-radius: 999px;
    padding: 0.38rem 0.9rem;
    cursor: pointer;
    font-weight: 500;
    text-decoration: none;
}}
.chip:hover {{
    background: rgba(210, 225, 210, 0.8) !important;
    border-color: rgba(120, 160, 120, 0.7) !important;
}}

.chat-header {{
    display: flex;
    align-items: baseline;
    padding: 2.2rem 0 0.9rem 0;
}}
.chat-brand-name {{
    font-family: 'Playfair Display', serif;
    font-size: 1.8rem;
    font-weight: 600;
    color: #1a1a1a;
    letter-spacing: -0.025em;
}}
.chat-brand-name span {{
    font-style: italic;
    color: #3d6b4f;
    font-weight: 400;
}}
.chat-brand-tag {{
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.7rem;
    color: #999;
    margin-left: 0.65rem;
}}

.chat-container {{
    background: transparent;
    border: none;
    border-radius: 14px;
    padding: 1.2rem;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    height: 52vh;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(100,140,100,0.2) transparent;
}}
.chat-spacer {{ flex: 1; }}

.msg-bot-wrap {{
    display: flex;
    gap: 0.55rem;
    align-items: flex-start;
}}
.bot-avatar {{
    width: 22px;
    height: 22px;
    background: #3d6b4f;
    border-radius: 50%;
    font-size: 8px;
    color: #fff;
    font-family: 'IBM Plex Mono', monospace;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.msg-bot {{
    background: rgba(210, 225, 210, 0.75);
    border: 1px solid rgba(140, 175, 140, 0.4);
    border-radius: 2px 12px 12px 12px;
    padding: 0.6rem 0.85rem;
    font-size: 0.875rem;
    line-height: 1.65;
    color: #1e3320;
    max-width: 86%;
    white-space: pre-wrap;
    font-family: 'Instrument Sans', sans-serif;
}}
.msg-bot a {{
    color: #3d6b4f;
    text-decoration: underline;
    text-underline-offset: 2px;
}}

.msg-user-wrap {{
    display: flex;
    justify-content: flex-end;
}}
.msg-user {{
    background: #2d4f35;
    border: 1px solid #1e3320;
    color: #e8f0e8;
    border-radius: 12px 2px 12px 12px;
    padding: 0.52rem 0.85rem;
    font-size: 0.855rem;
    line-height: 1.55;
    max-width: 66%;
    font-family: 'Instrument Sans', sans-serif;
}}

/* All Streamlit buttons get the black circle — covers both send buttons */
.stButton > button {{
    width: 44px !important;
    height: 44px !important;
    min-width: 44px !important;
    border-radius: 50% !important;
    background: #1a1a1a !important;
    color: #f0ede6 !important;
    border: none !important;
    font-size: 1.1rem !important;
    padding: 0 !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-top: 1px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18) !important;
}}
.stButton > button:hover {{ background: #333 !important; }}

.stTextInput > div > div > input {{
    background: rgba(210, 225, 210, 0.55) !important;
    border: 1.5px solid rgba(120, 160, 120, 0.5) !important;
    border-radius: 999px !important;
    color: #1a1a1a !important;
    font-family: 'Instrument Sans', sans-serif !important;
    font-size: 0.92rem !important;
    padding: 0.72rem 1.4rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
    caret-color: #1a1a1a !important;
}}
.stTextInput > div > div > input:focus {{
    border-color: rgba(100, 140, 100, 0.8) !important;
    box-shadow: 0 0 12px rgba(100, 140, 100, 0.18) !important;
    outline: none !important;
}}
.stTextInput > div > div > input::placeholder {{ color: #aaa !important; }}

[data-testid="column"] {{
    padding-left: 0.25rem !important;
    padding-right: 0.25rem !important;
}}

div[data-testid="stHorizontalBlock"] {{
    max-width: 520px !important;
    margin: 0 auto !important;
}}

.loop-track-wrap {{ margin-bottom: 1rem; margin-top: 0.2rem; }}
.loop-track {{ position: relative; width: 100%; height: 56px; overflow: hidden; }}
.loop-rail {{ position: absolute; left: 0; right: 0; top: 34px; height: 2px; background: rgba(140, 175, 140, 0.32); }}
.loop-sleepers {{ position: absolute; left: 0; right: 0; top: 30px; display: flex; justify-content: space-between; padding: 0 6px; }}
.loop-sleeper {{ width: 2px; height: 8px; background: rgba(140, 175, 140, 0.22); border-radius: 1px; }}
.loop-train {{ position: absolute; top: 4px; width: 82px; height: 48px; left: -41px; animation: train-loop 12s linear infinite; z-index: 3; }}
.loop-train img {{ width: 100%; height: auto; display: block; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.08)); }}

.smoke {{ position: absolute; border-radius: 50%; background: rgba(160, 165, 155, 0.45); opacity: 0; pointer-events: none; }}
.smoke.s1 {{ width: 8px; height: 8px; top: 2px; left: 52px; animation: puff1 2.2s ease-out infinite; }}
.smoke.s2 {{ width: 10px; height: 10px; top: 0px; left: 59px; animation: puff2 2.2s ease-out infinite 0.45s; }}
.smoke.s3 {{ width: 12px; height: 12px; top: -6px; left: 66px; animation: puff3 2.2s ease-out infinite 0.9s; }}

@keyframes puff1 {{ 0% {{ transform: translate(0,0) scale(0.4); opacity:0; }} 20% {{ opacity:0.45; }} 100% {{ transform: translate(-10px,-16px) scale(1.4); opacity:0; }} }}
@keyframes puff2 {{ 0% {{ transform: translate(0,0) scale(0.4); opacity:0; }} 20% {{ opacity:0.38; }} 100% {{ transform: translate(-14px,-22px) scale(1.6); opacity:0; }} }}
@keyframes puff3 {{ 0% {{ transform: translate(0,0) scale(0.4); opacity:0; }} 20% {{ opacity:0.28; }} 100% {{ transform: translate(-18px,-28px) scale(1.8); opacity:0; }} }}
@keyframes train-loop {{ 0% {{ left: -41px; }} 100% {{ left: calc(100% - 41px); }} }}

.thinking-wrap {{ display: flex; align-items: center; gap: 0.6rem; padding: 0.4rem 0 0.6rem 0.5rem; }}
.thinking-track {{ position: relative; width: 120px; height: 18px; }}
.thinking-rail {{ position: absolute; top: 50%; left: 0; right: 0; height: 1.5px; background: rgba(140,175,140,0.3); transform: translateY(-50%); }}
.thinking-train-small {{ position: absolute; top: 50%; width: 28px; height: auto; transform: translateY(-58%); animation: thinking-chug 1.6s linear infinite; }}
.thinking-train-small img {{ width: 100%; height: auto; display: block; }}
.train-fallback {{ font-size: 22px; line-height: 1; }}
@keyframes thinking-chug {{ 0% {{ left: -18px; opacity:0; }} 8% {{ opacity:1; }} 92% {{ opacity:1; }} 100% {{ left: 122px; opacity:0; }} }}
.thinking-label {{ font-family: 'Instrument Sans', sans-serif; font-size: 0.7rem; color: #7a9a7a; font-weight: 300; font-style: italic; }}

.top-nav {{ position: fixed; top: 16px; right: 20px; z-index: 99999; display: flex; gap: 10px; align-items: center; }}
.top-nav a {{ font-family: 'Instrument Sans', sans-serif; font-size: 0.72rem; color: #555; text-decoration: none; padding: 5px 12px; border-radius: 999px; border: 1px solid #ddd; background: #fff; }}
.top-nav a:hover {{ color: #1a1a1a; border-color: #aaa; }}

/* ── Mobile responsive ─────────────────────────────────────────────────────── */
@media (max-width: 768px) {{
    #rg-panel {{ display: none !important; }}

    .block-container {{
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }}

    .start-title {{ font-size: 2.4rem !important; }}
    .start-title-italic {{ font-size: 2.4rem !important; }}
    .start-sub {{ font-size: 0.85rem !important; }}
    .start-screen {{ padding-top: 10vh !important; }}

    .chat-container {{ height: 58vh !important; }}

    .msg-bot {{ max-width: 95% !important; font-size: 0.82rem !important; }}
    .msg-user {{ max-width: 82% !important; font-size: 0.82rem !important; }}

    .chips-row {{ gap: 0.35rem !important; padding: 0 0.5rem !important; }}
    .chip {{ font-size: 0.72rem !important; padding: 0.32rem 0.75rem !important; }}

    .loop-track-wrap {{ margin-bottom: 0.4rem !important; }}

    .top-nav {{ top: 8px !important; right: 8px !important; }}
    .top-nav a {{ font-size: 0.65rem !important; padding: 4px 8px !important; }}

    .chat-brand-name {{ font-size: 1.4rem !important; }}

    .stTextInput > div > div > input {{
        font-size: 0.85rem !important;
        padding: 0.6rem 1rem !important;
    }}

    div[data-testid="stHorizontalBlock"] {{
        max-width: 100% !important;
    }}
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
if "waiting" not in st.session_state:
    st.session_state.waiting = False

# ── Reset handler ──────────────────────────────────────────────────────────────
if st.session_state.do_reset:
    close_session(st.session_state.session_id, task_completed=None)
    st.session_state.controller = ConversationController()
    st.session_state.session_id = create_session()
    st.session_state.messages = []
    st.session_state.turn = 0
    st.session_state.input_key += 1
    st.session_state.waiting = False
    st.session_state.do_reset = False
    st.rerun()

# ── Reset via query param ──────────────────────────────────────────────────────
params = st.query_params
if params.get("reset") == "1":
    st.query_params.clear()
    st.session_state.do_reset = True
    st.rerun()

has_messages = len(st.session_state.messages) > 0
task = st.session_state.controller.state.current_task

# ── START SCREEN ───────────────────────────────────────────────────────────────
if not has_messages:
    components.html("""
    <script>
    (function() {
        var old = window.parent.document.getElementById('rg-panel');
        if (old) old.remove();
    })();
    </script>
    """, height=0)

    st.markdown("""
    <div class="start-screen">
        <div class="start-title">ChooChooAI.</div>
        <div class="start-title-italic">Travel smarter.</div>
        <div class="start-sub">Find tickets, check delays, predict arrivals<br>and get answers across the UK rail network.</div>
    </div>
    """, unsafe_allow_html=True)

    col_input, col_send = st.columns([8, 1])
    with col_input:
        user_input = st.text_input(
            "msg",
            placeholder="Tell me about your journey...",
            key=f"start_input_{st.session_state.input_key}"
        )
    with col_send:
        send = st.button("↑", key="start_send")

    st.markdown("""
    <div class="chips-row">
        <a class="chip" href="?chip=I+want+to+go+to+Edinburgh+on+Friday">Edinburgh on Friday</a>
        <a class="chip" href="?chip=I+want+to+travel+from+Manchester+to+London+as+a+return">Manchester return</a>
        <a class="chip" href="?chip=Can+you+explain+what+Delay+Repay+is">Delay Repay help</a>
    </div>
    """, unsafe_allow_html=True)

    if params.get("chip"):
        chip_text = params.get("chip")
        st.query_params.clear()
        greeting = st.session_state.controller.prompts.greeting()
        st.session_state.messages.append({"role": "bot", "text": greeting})
        log_message(st.session_state.session_id, 0, "bot", greeting)
        st.session_state.turn += 1
        st.session_state.messages.append({"role": "user", "text": chip_text})
        log_message(st.session_state.session_id, st.session_state.turn, "user", chip_text)
        response = st.session_state.controller.handle_user_input(chip_text)
        st.session_state.turn += 1
        st.session_state.messages.append({"role": "bot", "text": response})
        log_message(st.session_state.session_id, st.session_state.turn, "bot", response)
        st.session_state.input_key += 1
        st.rerun()

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
    components.html("""
    <script>
    (function() {
        var old = window.parent.document.getElementById('rg-panel');
        if (old) old.remove();

        var panel = window.parent.document.createElement('div');
        panel.id = 'rg-panel';
        panel.style.cssText = 'position:fixed;top:0;left:0;width:240px;height:100vh;padding:2rem 1.1rem 2rem 1.3rem;overflow-y:auto;z-index:9998;scrollbar-width:none;font-family:Instrument Sans,sans-serif;background:#fdf8ec!important;border-right:1px solid rgba(61,107,79,0.10);box-shadow:8px 0 24px rgba(61,107,79,0.04);';
        panel.innerHTML = `
            <div style="font-family:Playfair Display,serif;font-size:1rem;font-weight:600;color:#1e3320;margin-bottom:0.15rem;">ChooChooAI</div>
            <div style="font-size:0.6rem;color:#bbb;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:1.2rem;">Quick Reference</div>

            <div style="font-size:0.58rem;font-weight:500;color:#bbb;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.45rem;">Compensation</div>
            <div class="rgcard"><div class="rgt">Delay Repay</div><div class="rgd">Claim for delays of 15+ mins. Most operators pay 25 to 100% of your fare back.</div></div>
            <div class="rgcard"><div class="rgt">Cancelled Train</div><div class="rgd">Full refund if cancelled and you choose not to travel.</div></div>

            <hr style="border:none;border-top:1px solid rgba(140,175,140,0.2);margin:0.9rem 0;">

            <div style="font-size:0.58rem;font-weight:500;color:#bbb;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.45rem;">Tickets &amp; Passes</div>
            <div class="rgcard"><div class="rgt">Railcards</div><div class="rgd">Save one third on most fares with 16 to 25, Senior, Two Together and more.</div></div>
            <div class="rgcard"><div class="rgt">Advance vs Anytime</div><div class="rgd">Advance is cheapest but train specific. Anytime is flexible but pricier.</div></div>
            <div class="rgcard"><div class="rgt">Split Ticketing</div><div class="rgd">Two tickets for one journey can be significantly cheaper.</div></div>

            <hr style="border:none;border-top:1px solid rgba(140,175,140,0.2);margin:0.9rem 0;">

            <div style="font-size:0.58rem;font-weight:500;color:#bbb;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.45rem;">Know Your Rights</div>
            <div class="rgcard"><div class="rgt">National Rail Conditions</div><div class="rgd">Your full rights as a passenger under UK rail law.</div></div>
        `;

        var style = window.parent.document.createElement('style');
        style.textContent = '.rgcard{background:rgba(210,225,210,0.28);border:1px solid rgba(140,175,140,0.28);border-radius:10px;padding:0.7rem 0.85rem;margin-bottom:0.5rem;} .rgt{font-size:0.78rem;font-weight:500;color:#1e3320;margin-bottom:0.18rem;font-family:Instrument Sans,sans-serif;} .rgd{font-size:0.68rem;color:#5a7a5a;line-height:1.45;font-weight:300;font-family:Instrument Sans,sans-serif;}';
        panel.appendChild(style);
        window.parent.document.body.appendChild(panel);
    })();
    </script>
    """, height=0)

    st.markdown("""
    <div class="chat-header">
        <span class="chat-brand-name">Choo<span>ChooAI</span></span>
        <span class="chat-brand-tag">Train Travel Assistant</span>
    </div>
    """, unsafe_allow_html=True)

    sleepers_html = '<div class="loop-sleeper"></div>' * 22
    train_img_html = (
        f'<img src="data:image/png;base64,{train_b64}" alt="ChooChooAI train">'
        if train_b64
        else '<span class="train-fallback">🚂</span>'
    )

    st.markdown(f"""
<div class="loop-track-wrap">
<div class="loop-track">
<div class="loop-rail"></div>
<div class="loop-sleepers">{sleepers_html}</div>
<div class="loop-train">
<span class="smoke s1"></span>
<span class="smoke s2"></span>
<span class="smoke s3"></span>
{train_img_html}
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # ── Messages ──────────────────────────────────────────────────────────────
    messages_html = '<div class="chat-spacer"></div>'
    for msg in st.session_state.messages:
        if msg["role"] == "bot":
            text = msg["text"]
            messages_html += f'''
            <div class="msg-bot-wrap">
                <div class="bot-avatar">cc</div>
                <div class="msg-bot">{text}</div>
            </div>'''
        else:
            text = msg["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            messages_html += f'''
            <div class="msg-user-wrap">
                <div class="msg-user">{text}</div>
            </div>'''

    if st.session_state.waiting:
        messages_html += f'''
        <div class="thinking-wrap">
            <div class="thinking-track">
                <div class="thinking-rail"></div>
                <div class="thinking-train-small">{train_img_html}</div>
            </div>
            <div class="thinking-label">finding your options...</div>
        </div>'''

    st.markdown(f'''
<div class="chat-container" id="chat-box">{messages_html}</div>
<script>
  var c = document.getElementById("chat-box");
  if (c) c.scrollTop = c.scrollHeight;
</script>
''', unsafe_allow_html=True)

    # ── Input row with reset as HTML link on the left ─────────────────────────
    col_reset, col_input, col_send = st.columns([1, 9, 1])
    with col_reset:
        st.markdown('''
        <div style="padding-top:0.6rem;text-align:right;">
            <a href="?reset=1" style="font-family:'Instrument Sans',sans-serif;font-size:0.66rem;
            color:#bbb;text-decoration:underline;text-underline-offset:3px;
            letter-spacing:0.03em;">reset</a>
        </div>
        ''', unsafe_allow_html=True)
    with col_input:
        user_input = st.text_input(
            "msg",
            placeholder="Continue the conversation...",
            key=f"chat_input_{st.session_state.input_key}"
        )
    with col_send:
        send = st.button("↑", key="chat_send")

    if send and user_input.strip():
        text = user_input.strip()
        st.session_state.turn += 1
        st.session_state.messages.append({"role": "user", "text": text})
        log_message(st.session_state.session_id, st.session_state.turn, "user", text)
        st.session_state.waiting = True
        st.session_state.input_key += 1
        st.rerun()

    if st.session_state.waiting:
        last = st.session_state.messages[-1]
        if last["role"] == "user":
            response = st.session_state.controller.handle_user_input(last["text"])
            st.session_state.turn += 1
            st.session_state.messages.append({"role": "bot", "text": response})
            log_message(st.session_state.session_id, st.session_state.turn, "bot", response)
            st.session_state.waiting = False

            if "journey details are complete" in response or "delay details are complete" in response:
                completed_task = st.session_state.controller.state.current_task or task
                close_session(st.session_state.session_id, task_completed=completed_task)

            st.rerun()