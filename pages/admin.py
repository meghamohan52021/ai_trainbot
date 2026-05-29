import streamlit as st
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from knowledge.database import initialise_db, seed_knowledge, get_all_knowledge, add_knowledge, delete_knowledge

st.set_page_config(
    page_title="ChooChooAI Admin",
    page_icon="🚂",
    layout="centered",
    initial_sidebar_state="collapsed",
)

bg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "background.png")
if not os.path.exists(bg_path):
    bg_path = os.path.join(os.path.dirname(__file__), "background.png")
bg_b64 = ""
if os.path.exists(bg_path):
    with open(bg_path, "rb") as f:
        bg_b64 = base64.b64encode(f.read()).decode()

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
    padding-top: 3.2rem !important;
    padding-bottom: 3rem !important;
    max-width: 760px !important;
}}

.admin-hero {{
    padding: 0.2rem 0 0.45rem 0;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
.admin-panel {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}}
.admin-title {{
    font-family: 'Playfair Display', serif;
    font-size: 2.6rem;
    font-weight: 600;
    color: #1a1a1a;
    letter-spacing: -0.035em;
    line-height: 1.05;
    margin-bottom: 0.15rem;
}}
.admin-title span {{
    font-style: italic;
    color: #3d6b4f;
    font-weight: 400;
}}
.admin-sub {{
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.78rem;
    color: #6d756d;
    margin-bottom: 0.55rem;
}}
.section-label {{
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.62rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #a6aaa4;
    margin-bottom: 0.7rem;
    margin-top: 0.65rem;
    font-weight: 500;
}}
.entry-card {{
    background: rgba(210, 225, 210, 0.55);
    border: 1px solid rgba(140, 175, 140, 0.35);
    border-radius: 14px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.7rem;
}}
.entry-keyword {{
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.9rem;
    color: #1e3320;
    font-weight: 500;
    margin-bottom: 0.25rem;
}}
.entry-synonyms {{
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.75rem;
    color: #5a7a5a;
    margin-bottom: 0.35rem;
}}
.entry-answer {{
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.84rem;
    color: #263b28;
    line-height: 1.5;
    font-weight: 300;
}}
.entry-date {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    color: #8a968a;
    margin-top: 0.5rem;
}}

.stTextInput > div,
.stTextArea > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}}
.stTextInput [data-baseweb="input"],
.stTextArea [data-baseweb="textarea"] {{
    background: rgba(210, 225, 210, 0.55) !important;
    border: 1.5px solid rgba(120, 160, 120, 0.45) !important;
    border-radius: 999px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
    overflow: hidden !important;
}}
.stTextArea [data-baseweb="textarea"] {{
    border-radius: 16px !important;
}}
.stTextInput [data-baseweb="input"] input,
.stTextArea [data-baseweb="textarea"] textarea,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {{
    background: transparent !important;
    color: #1a1a1a !important;
    font-family: 'Instrument Sans', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 400 !important;
    border: none !important;
    box-shadow: none !important;
}}

.stTextInput [data-baseweb="input"] button,
.stTextInput [data-baseweb="input"] svg,
.stTextInput [data-baseweb="input"] [role="button"] {{
    background: transparent !important;
    color: #3d6b4f !important;
    fill: #3d6b4f !important;
    border: none !important;
    box-shadow: none !important;
}}
.stTextInput [data-baseweb="input"]:focus-within,
.stTextArea [data-baseweb="textarea"]:focus-within {{
    border-color: rgba(61, 107, 79, 0.7) !important;
    box-shadow: 0 0 12px rgba(61, 107, 79, 0.12) !important;
}}
.stTextInput label,
.stTextArea label {{
    color: #314734 !important;
    font-size: 0.78rem !important;
    font-family: 'Instrument Sans', sans-serif !important;
    font-weight: 500 !important;
}}
.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {{
    color: #9da69d !important;
}}

div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"],
.stTextInput div[data-baseweb="input"],
.stTextInput div[data-baseweb="base-input"],
.stTextArea div[data-baseweb="textarea"] {{
    background-color: rgba(232, 241, 226, 0.82) !important;
    background: rgba(232, 241, 226, 0.82) !important;
    border: 1.5px solid rgba(120, 160, 120, 0.55) !important;
    border-radius: 999px !important;
    color: #1e3320 !important;
    box-shadow: 0 2px 8px rgba(61, 107, 79, 0.06) !important;
}}
.stTextArea div[data-baseweb="textarea"] {{
    border-radius: 16px !important;
}}
div[data-baseweb="input"] *,
div[data-baseweb="base-input"] *,
div[data-baseweb="textarea"] * {{
    background-color: transparent !important;
    background: transparent !important;
    color: #1e3320 !important;
    font-family: 'Instrument Sans', sans-serif !important;
}}
input, textarea {{
    background-color: transparent !important;
    background: transparent !important;
    color: #1e3320 !important;
    -webkit-text-fill-color: #1e3320 !important;
}}
input::placeholder, textarea::placeholder {{
    color: #7a8a7a !important;
    -webkit-text-fill-color: #7a8a7a !important;
}}

button[aria-label*="password"],
button[title*="password"],
.stTextInput button {{
    background-color: rgba(232, 241, 226, 0.82) !important;
    color: #3d6b4f !important;
}}
.stTextInput svg {{
    fill: #3d6b4f !important;
    color: #3d6b4f !important;
}}

.stTextArea div[data-baseweb="textarea"] {{
    background: rgba(232, 241, 226, 0.82) !important;
    border: 1.5px solid rgba(120, 160, 120, 0.55) !important;
    border-radius: 16px !important;
    box-shadow: 0 2px 8px rgba(61, 107, 79, 0.06) !important;
    overflow: hidden !important;
}}
.stTextArea div[data-baseweb="base-input"],
.stTextArea div[data-baseweb="textarea"] > div,
.stTextArea div[data-baseweb="textarea"] > div > div {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}}
.stTextArea textarea {{
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    color: #1e3320 !important;
    -webkit-text-fill-color: #1e3320 !important;
    resize: vertical !important;
}}
.stTextArea textarea:focus {{
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}}

.stButton > button {{
    background: #2d4f35 !important;
    color: #fdf8ec !important;
    border: 1px solid #1e3320 !important;
    border-radius: 999px !important;
    font-family: 'Instrument Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    padding: 0.48rem 1.15rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
}}
.stButton > button:hover {{
    background: #3d6b4f !important;
}}
div[data-testid="column"]:last-child .stButton > button {{
    background: rgba(253, 248, 236, 0.7) !important;
    color: #7d4b4b !important;
    border: 1px solid rgba(125, 75, 75, 0.24) !important;
    box-shadow: none !important;
    padding: 0.4rem 0.75rem !important;
}}
div[data-testid="column"]:last-child .stButton > button:hover {{
    color: #9a3f3f !important;
    border-color: rgba(154, 63, 63, 0.38) !important;
}}

.stCaptionContainer {{
    color: #7a8a7a !important;
    font-family: 'Instrument Sans', sans-serif !important;
}}
[data-testid="stAlert"] {{
    border-radius: 14px !important;
    font-family: 'Instrument Sans', sans-serif !important;
}}

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
    font-family: 'Instrument Sans', sans-serif;
    font-size: 0.72rem;
    color: #555;
    text-decoration: none;
    padding: 5px 12px;
    border-radius: 999px;
    border: 1px solid #ddd;
    background: rgba(255,255,255,0.78);
    transition: color 0.15s, border-color 0.15s, background 0.15s;
}}
.top-nav a:hover {{
    color: #1a1a1a;
    border-color: #aaa;
    background: #fff;
}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="top-nav"><a href="/">Main</a><a href="/admin">Admin</a></div>', unsafe_allow_html=True)

initialise_db()
seed_knowledge()

ADMIN_PASSWORD = "trainbot2026"

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if not st.session_state.admin_authed:
    st.markdown("""
    <div class="admin-hero">
        <div class="admin-title">ChooChoo<span>AI</span>.</div>
        <div class="admin-sub">Admin knowledge base</div>
    </div>
    """, unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password", key="admin_pwd")
    if st.button("Login"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_authed = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

st.markdown("""
<div class="admin-hero">
    <div class="admin-title">ChooChoo<span>AI</span>.</div>
    <div class="admin-sub">Admin knowledge base</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-label">Add knowledge entry</div>', unsafe_allow_html=True)

ka_keyword = st.text_input(
    "Keyword",
    placeholder="Example: travelcard",
    help="The primary word that triggers this answer"
)
ka_synonyms = st.text_input(
    "Synonyms",
    placeholder="Example: travel pass, london pass, zone card",
    help="Alternative phrases that should also trigger this answer"
)
ka_answer = st.text_area(
    "Answer",
    placeholder="Example: A Travelcard gives unlimited travel across London zones.",
    height=120,
    help="The full answer the chatbot will return"
)

if st.button("Add to knowledge base"):
    if ka_keyword.strip() and ka_answer.strip():
        success = add_knowledge(ka_keyword, ka_synonyms, ka_answer)
        if success:
            st.success(f"Added: '{ka_keyword.strip()}'")
            st.rerun()
        else:
            st.warning(f"'{ka_keyword.strip()}' already exists. Choose a different keyword.")
    else:
        st.error("Keyword and answer are both required.")

st.markdown('<div class="section-label">Current knowledge base entries</div>', unsafe_allow_html=True)

entries = get_all_knowledge()
st.caption(f"{len(entries)} entries")

if not entries:
    st.info("No entries yet.")
else:
    for entry in entries:
        col_card, col_del = st.columns([11, 1])
        with col_card:
            keyword = str(entry['keyword']).replace("<", "&lt;").replace(">", "&gt;")
            synonyms = str(entry['synonyms'] or 'none').replace("<", "&lt;").replace(">", "&gt;")
            answer = str(entry['answer']).replace("<", "&lt;").replace(">", "&gt;")
            created = str(entry['created_at'][:10])
            st.markdown(f"""
            <div class="entry-card">
                <div class="entry-keyword">{keyword}</div>
                <div class="entry-synonyms">Synonyms: {synonyms}</div>
                <div class="entry-answer">{answer}</div>
                <div class="entry-date">Added {created}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            st.markdown("<div style='margin-top:0.6rem'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"del_{entry['id']}"):
                delete_knowledge(entry['id'])
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
if st.button("Logout", key="logout"):
    st.session_state.admin_authed = False
    st.rerun()