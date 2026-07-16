import streamlit as st
import requests
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Wikimedia Retention",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- WIKIPEDIA-INSPIRED DARK THEME (forced — not left to the visitor's OS/browser setting) ---
WIKI_BLUE = "#3366cc"        # Wikipedia link blue
WIKI_BLUE_LIGHT = "#7aa7ff"  # brighter accent, readable on dark backgrounds
WIKI_BLUE_DARK = "#14428e"
WIKI_INK = "#202122"         # dark text — used only on light content cards
WIKI_GRAY = "#54595d"        # muted text — used only on light content cards
CARD_LIGHT = "#f7f9fc"       # light card surface for charts/metrics (contrast anchor)

BG_DEEP = "#0a1526"
BG_MID = "#13284a"
TEXT_LIGHT = "#eef3fc"
TEXT_MUTED = "#a9b9d8"

CUSTOM_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    }}

    /* Force one cohesive dark canvas regardless of the visitor's system theme */
    .stApp {{
        background: radial-gradient(circle at 10% -10%, {BG_MID} 0%, {BG_DEEP} 55%, #060d1a 100%) !important;
    }}
    .stApp, .stApp p, .stApp li, .stApp label {{
        color: {TEXT_LIGHT} !important;
    }}
    div[data-testid="stMarkdownContainer"] p {{
        color: {TEXT_MUTED} !important;
    }}

    /* Sidebar — same dark family, slightly richer, so the seam disappears */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(165deg, #0d1c33 0%, {WIKI_BLUE_DARK} 65%, {WIKI_BLUE} 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }}
    section[data-testid="stSidebar"] * {{
        color: #f5f8ff !important;
    }}
    section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {{
        color: #cdd9f2 !important;
    }}
    section[data-testid="stSidebar"] textarea {{
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 10px !important;
        color: #ffffff !important;
    }}
    section[data-testid="stSidebar"] textarea::placeholder {{
        color: rgba(255, 255, 255, 0.45) !important;
        font-style: italic;
    }}
    section[data-testid="stSidebar"] div[data-testid="stExpander"] {{
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.22);
        border-radius: 10px;
    }}
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
        border-radius: 8px !important;
    }}
    section[data-testid="stSidebar"] span[data-baseweb="tag"] {{
        background: {WIKI_BLUE} !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: linear-gradient(90deg, {WIKI_BLUE} 0%, {WIKI_BLUE_DARK} 100%);
        color: white !important;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.6em 1em;
        box-shadow: 0 4px 14px rgba(51, 102, 204, 0.35);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(51, 102, 204, 0.45);
        color: white !important;
    }}
    .stButton > button p {{
        color: white !important;
    }}

    /* Hero title — gradient text instead of an emoji icon */
    .hero-title {{
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -1px;
        line-height: 1.15;
        margin: 0.4rem 0 0.15rem 0;
        background: linear-gradient(90deg, {WIKI_BLUE_LIGHT} 0%, {WIKI_BLUE} 55%, #9b8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .hero-subtitle {{
        color: {TEXT_MUTED} !important;
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }}

    /* Metric cards — light surface for strong contrast against the dark canvas */
    div[data-testid="stMetric"] {{
        background: {CARD_LIGHT};
        border: 1px solid rgba(20, 66, 142, 0.12);
        border-radius: 14px;
        padding: 1rem 1.2rem;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
    }}
    div[data-testid="stMetricLabel"] p {{
        color: {WIKI_GRAY} !important;
        font-weight: 600;
    }}
    div[data-testid="stMetricValue"] {{
        color: {WIKI_BLUE_DARK} !important;
        font-weight: 800;
    }}

    /* Heatmap cards — same light-surface treatment, matches the chart's own colors */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {CARD_LIGHT};
        border-radius: 16px;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.3);
        padding: 0.25rem;
    }}

    hr {{
        border-color: rgba(255, 255, 255, 0.12);
    }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- CONSTANTS ---
EVENT_MAP = {'wlf': 'Folklore', 'wle': 'Earth', 'wlm': 'Monuments', 'wlb': 'Bangla'}
COUNTRY_MAP = {
    'bd': 'Bangladesh', 'in': 'India', 'de': 'Germany', 'it': 'Italy',
    'fr': 'France', 'us': 'United_States', 'ca': 'Canada', 'uk': 'United_Kingdom',
    'nl': 'Netherlands', 'pl': 'Poland', 'br': 'Brazil', 'mx': 'Mexico',
    'es': 'Spain', 'pt': 'Portugal', 'pk': 'Pakistan', 'np': 'Nepal',
    'ng': 'Nigeria', 'ke': 'Kenya', 'id': 'Indonesia',
    'ph': 'Philippines', 'my': 'Malaysia', 'tr': 'Turkey', 'eg': 'Egypt',
    'ua': 'Ukraine', 'ru': 'Russia', 'ch': 'Switzerland', 'se': 'Sweden',
    'no': 'Norway', 'fi': 'Finland', 'be': 'Belgium', 'at': 'Austria',
    'ar': 'Argentina', 'co': 'Colombia'
}

CODE_RE = re.compile(r'(wlf|wle|wlm|wlb)([a-z]{0,2})(\d{2})')

EXAMPLE_CODES = "wlfbd21 wlfbd22 wlfbd23 wlfin21 wlfin22 wlfin23"

# Wikipedia-blue gradient colormap for heatmaps
WIKI_CMAP = LinearSegmentedColormap.from_list(
    "wiki_blue", [CARD_LIGHT, "#bcd4f7", WIKI_BLUE, WIKI_BLUE_DARK, "#0b2b5c"]
)

# --- FUNCTIONS ---
@st.cache_data(show_spinner=False, ttl=3600)
def get_participants(code):
    try:
        code = re.sub(r'\s+', '', code).lower()
        event, cc, yr = CODE_RE.match(code).groups()
        cat = f"Images_from_Wiki_Loves_{EVENT_MAP[event]}_{2000 + int(yr)}"
        if cc:
            cat += f"_in_{COUNTRY_MAP.get(cc, '')}"

        response = requests.get(
            'https://ptools.toolforge.org/uploadersincat.php?category=' + cat, timeout=15
        )

        for uincattxt in response.content.decode("UTF-8").split('fieldset'):
            if '<legend>List</legend>' in uincattxt:
                break
        splt = list(uincattxt.split('>'))
        users = set()

        for s in splt:
            if "User:" in s and "href" not in s:
                users.add(s.replace("User:", "").replace("</a", ""))
        return users
    except Exception:
        return set()


def fetch_all_concurrently(codes):
    """Fetch participant sets for all codes in parallel for speed."""
    results = {}
    total = len(codes)
    progress = st.progress(0, text="Fetching data from Wikimedia Toolforge...")

    with ThreadPoolExecutor(max_workers=min(8, max(1, total))) as executor:
        future_to_code = {executor.submit(get_participants, code): code for code in codes}
        done = 0
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                results[code] = future.result()
            except Exception:
                results[code] = set()
            done += 1
            progress.progress(done / total, text=f"Fetched {done}/{total} events…")

    progress.empty()
    return results


def create_heatmap(events, country_name):
    sns.set_theme(style="white")

    event_codes = list(events.keys())
    size = len(event_codes)
    matrix = np.zeros((size, size))

    readable_labels = []
    for code in event_codes:
        event, cc, yr = CODE_RE.match(code).groups()
        readable_labels.append(f"{EVENT_MAP[event]} 20{yr}")

    for i, source in enumerate(event_codes):
        for j, target in enumerate(event_codes):
            source_users = events[source]
            if not source_users:
                matrix[i, j] = 0.0
            else:
                overlap = len(source_users & events[target])
                matrix[i, j] = (overlap / len(source_users)) * 100

    fig, ax = plt.subplots(figsize=(max(5, size * 1.2), max(4, size)))
    fig.patch.set_facecolor(CARD_LIGHT)
    ax.patch.set_facecolor(CARD_LIGHT)

    sns.heatmap(
        matrix, annot=True, fmt=".1f",
        xticklabels=readable_labels, yticklabels=readable_labels,
        cmap=WIKI_CMAP, linewidths=1, linecolor="#ffffff",
        cbar_kws={'label': 'Retention (%)'},
        vmin=0, vmax=100, ax=ax,
        annot_kws={"fontweight": "bold", "fontsize": 10}
    )

    ax.set_title(f"{country_name.replace('_', ' ')} Retention", pad=15, fontweight='bold',
                 fontsize=14, color=WIKI_INK)
    ax.set_ylabel("Source Event", fontweight='bold', color=WIKI_GRAY)
    ax.set_xlabel("Target Event", fontweight='bold', color=WIKI_GRAY)
    plt.xticks(rotation=45, ha='right', color=WIKI_GRAY)
    plt.yticks(rotation=0, color=WIKI_GRAY)
    plt.tight_layout()
    return fig


# --- CODE BUILDER (selector-assisted entry, appends into the manual box) ---
COUNTRY_OPTIONS = [''] + sorted(COUNTRY_MAP.keys(), key=lambda k: COUNTRY_MAP[k])


def _format_country(k):
    return "🌐 Global / No Country" if k == '' else COUNTRY_MAP[k].replace('_', ' ')


def add_codes_from_selectors():
    """Callback: builds codes from the selectors and merges them into the
    manual text box, run before the text_area widget re-renders."""
    sel_events = st.session_state.get("sel_events", [])
    sel_countries = st.session_state.get("sel_countries", [])
    yr_start, yr_end = st.session_state.get("yr_range", (2021, 2023))

    if not sel_events:
        st.session_state.builder_msg = "⚠️ Pick at least one event first."
        return

    countries = sel_countries if sel_countries else ['']
    new_codes = []
    for event in sel_events:
        for country in countries:
            for yr in range(yr_start, yr_end + 1):
                new_codes.append(f"{event}{country}{yr % 100:02d}")

    existing = st.session_state.get("code_input", "").split()
    merged = existing + [c for c in new_codes if c not in existing]
    st.session_state.code_input = " ".join(merged)
    st.session_state.builder_msg = f"✅ Added {len(new_codes)} code(s) — edit freely below."


def clear_code_input():
    st.session_state.code_input = ""
    st.session_state.builder_msg = ""


if "code_input" not in st.session_state:
    st.session_state.code_input = ""

# --- WEB APP INTERFACE ---

with st.sidebar:
    st.image("https://en.wikipedia.org/static/images/project-logos/enwiki.png", width=100)
    st.title("Configuration")
    st.markdown("Type codes manually, or use the builder below to add them for you.")

    user_input = st.text_area(
        "Event Codes (space-separated):",
        key="code_input",
        placeholder=EXAMPLE_CODES,
        height=110
    )

    with st.expander("🧩 Build codes from event / country / year"):
        st.multiselect(
            "Event(s)", options=list(EVENT_MAP.keys()),
            format_func=lambda k: EVENT_MAP[k], key="sel_events"
        )
        st.multiselect(
            "Countries (leave empty for global-only)", options=COUNTRY_OPTIONS,
            format_func=_format_country, key="sel_countries"
        )
        st.slider("Year range", 2010, 2026, (2021, 2023), key="yr_range")

        b_col1, b_col2 = st.columns(2)
        b_col1.button("➕ Add to input", on_click=add_codes_from_selectors, use_container_width=True)
        b_col2.button("🗑️ Clear", on_click=clear_code_input, use_container_width=True)

        if st.session_state.get("builder_msg"):
            st.caption(st.session_state.builder_msg)

    run_button = st.button("🚀 Generate Dashboard", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption("Powered by Wikimedia Toolforge & Streamlit")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="hero-title">Cross-Event Retention Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Analyze how many users return across different Wikimedia campaigns and regions.</div>',
    unsafe_allow_html=True
)

if run_button:
    raw_input = user_input.strip() or EXAMPLE_CODES
    codes = raw_input.split()
    valid = [c for c in (re.sub(r'\s+', '', cd).lower() for cd in codes) if CODE_RE.match(c)]

    if not valid:
        st.error("⚠️ No valid event codes found. Please check your formatting.")
        st.stop()

    participant_results = fetch_all_concurrently(valid)

    country_events = defaultdict(dict)
    for code in valid:
        event, cc, yr = CODE_RE.match(code).groups()
        participants = participant_results.get(code, set())
        if cc in COUNTRY_MAP and participants:
            country_events[cc][code] = participants

    valid_countries = {code: events for code, events in country_events.items() if len(events) >= 2}

    if not valid_countries:
        st.warning("⚠️ **Not enough data.** Heatmaps require at least two events in the same country to calculate overlap.")
    else:
        st.success("✅ Data fetched successfully!")
        st.markdown("---")

        total_events = sum(len(events) for events in valid_countries.values())
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Countries Analyzed", len(valid_countries))
        col_m2.metric("Total Events Included", total_events)
        col_m3.metric("Heatmaps Generated", len(valid_countries))

        st.markdown("<br>", unsafe_allow_html=True)

        cols = st.columns(2)
        for idx, (country_code, events) in enumerate(valid_countries.items()):
            country_name = COUNTRY_MAP[country_code]
            fig = create_heatmap(events, country_name)

            with cols[idx % 2]:
                with st.container(border=True):
                    st.pyplot(fig, use_container_width=True)
