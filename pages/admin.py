import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import initialise_db, seed_knowledge, get_all_knowledge, add_knowledge, delete_knowledge

st.set_page_config(
    page_title="TrainBot Admin",
    page_icon="🔧",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500&family=IBM+Plex+Mono:wght@400&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0f0f0f;
    color: #e8e4dc;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding-top: 2.5rem !important;
    max-width: 680px !important;
}
.admin-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.8rem;
    font-weight: 600;
    color: #f0ede6;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}
.admin-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    color: rgba(255,255,255,0.25);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: rgba(255,255,255,0.3);
    margin-bottom: 0.6rem;
    margin-top: 1.8rem;
}
.entry-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.6rem;
}
.entry-keyword {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem;
    color: #f0ede6;
    font-weight: 500;
    margin-bottom: 0.25rem;
}
.entry-synonyms {
    font-size: 0.75rem;
    color: rgba(255,255,255,0.3);
    margin-bottom: 0.3rem;
}
.entry-answer {
    font-size: 0.82rem;
    color: rgba(255,255,255,0.6);
    line-height: 1.5;
    font-weight: 300;
}
.entry-date {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    color: rgba(255,255,255,0.15);
    margin-top: 0.4rem;
}
/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 6px !important;
    color: #f0ede6 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 300 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(255,255,255,0.3) !important;
    box-shadow: none !important;
}
.stTextInput label, .stTextArea label {
    color: rgba(255,255,255,0.45) !important;
    font-size: 0.78rem !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 400 !important;
}
/* Buttons */
.stButton > button {
    background: #f0ede6 !important;
    color: #0f0f0f !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    padding: 0.45rem 1.1rem !important;
}
.stButton > button:hover {
    background: #ffffff !important;
}
div[data-testid="column"]:last-child .stButton > button {
    background: transparent !important;
    color: rgba(255,255,255,0.25) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    font-size: 0.75rem !important;
    padding: 0.35rem 0.7rem !important;
}
div[data-testid="column"]:last-child .stButton > button:hover {
    color: #ff6b6b !important;
    border-color: rgba(255,100,100,0.3) !important;
}

/* ── NAV LAUNCHER ── */
.nav-launcher {
    position: fixed;
    top: 1rem;
    left: 1rem;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.4rem;
}
.nav-toggle {
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
}
.nav-toggle:hover {
    background: rgba(40, 44, 60, 0.95);
}
.nav-bubbles {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    overflow: hidden;
    max-height: 0;
    opacity: 0;
    transition: max-height 0.25s ease, opacity 0.2s ease;
}
.nav-bubbles.open {
    max-height: 120px;
    opacity: 1;
}
.nav-bubble {
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
}
.nav-bubble:hover {
    background: rgba(60, 65, 90, 0.95);
    color: #ffffff;
}
.nav-bubble.active {
    border-color: rgba(255,255,255,0.25);
    color: #ffffff;
}

</style>
""", unsafe_allow_html=True)






st.markdown('<div style="position:fixed;top:16px;right:20px;z-index:99999;display:flex;gap:10px;"><a href="/" style="font-family:monospace;font-size:0.65rem;letter-spacing:0.08em;text-transform:uppercase;color:rgba(255,255,255,0.35);text-decoration:none;padding:4px 10px;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:rgba(8,12,24,0.7);">Main</a><a href="/admin" style="font-family:monospace;font-size:0.65rem;letter-spacing:0.08em;text-transform:uppercase;color:rgba(255,255,255,0.35);text-decoration:none;padding:4px 10px;border-radius:6px;border:1px solid rgba(255,255,255,0.12);background:rgba(8,12,24,0.7);">Admin</a></div>', unsafe_allow_html=True)
# ── Init DB ────────────────────────────────────────────────────────────────────
initialise_db()
seed_knowledge()

# ── Password gate ──────────────────────────────────────────────────────────────
ADMIN_PASSWORD = "trainbot2026"

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

if not st.session_state.admin_authed:
    st.markdown('<div class="admin-title">TrainBot</div>', unsafe_allow_html=True)
    st.markdown('<div class="admin-sub">Admin — Knowledge Acquisition</div>', unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password", key="admin_pwd")
    if st.button("Login"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.admin_authed = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ── Admin UI ───────────────────────────────────────────────────────────────────
st.markdown('<div class="admin-title">TrainBot</div>', unsafe_allow_html=True)
st.markdown('<div class="admin-sub">Admin — Knowledge Acquisition</div>', unsafe_allow_html=True)

# ── Add new entry ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Add new knowledge entry</div>', unsafe_allow_html=True)

ka_keyword = st.text_input(
    "Keyword",
    placeholder="e.g. travelcard",
    help="The primary word that triggers this answer"
)
ka_synonyms = st.text_input(
    "Synonyms (comma-separated, optional)",
    placeholder="e.g. travel pass, london pass, zone card",
    help="Alternative phrases that should also trigger this answer"
)
ka_answer = st.text_area(
    "Answer",
    placeholder="e.g. A Travelcard gives unlimited travel across London's zones...",
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

# ── Current entries ────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Current knowledge base entries</div>', unsafe_allow_html=True)

entries = get_all_knowledge()
st.caption(f"{len(entries)} entries")

if not entries:
    st.info("No entries yet.")
else:
    for entry in entries:
        col_card, col_del = st.columns([11, 1])
        with col_card:
            st.markdown(f"""
            <div class="entry-card">
                <div class="entry-keyword">{entry['keyword']}</div>
                <div class="entry-synonyms">Synonyms: {entry['synonyms'] or 'none'}</div>
                <div class="entry-answer">{entry['answer']}</div>
                <div class="entry-date">Added {entry['created_at'][:10]}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            st.markdown("<div style='margin-top:0.6rem'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"del_{entry['id']}"):
                delete_knowledge(entry['id'])
                st.rerun()

# ── Logout ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Logout", key="logout"):
    st.session_state.admin_authed = False
    st.rerun()