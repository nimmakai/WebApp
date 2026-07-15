import streamlit as st
import requests
import re
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Wikimedia Retention", 
    page_icon="🌍", 
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# --- FUNCTIONS ---
@st.cache_data(show_spinner=False)
def get_participants(code):
    try:
        code = re.sub(r'\s+', '', code).lower()
        event, cc, yr = re.match(r'(wlf|wle|wlm|wlb)([a-z]{0,2})(\d{2})', code).groups()
        cat = f"Images_from_Wiki_Loves_{EVENT_MAP[event]}_{2000 + int(yr)}"
        if cc: cat += f"_in_{COUNTRY_MAP.get(cc, '')}"
        
        response = requests.get('https://ptools.toolforge.org/uploadersincat.php?category='+cat, timeout=15)
        
        for uincattxt in response.content.decode("UTF-8").split('fieldset'):
            if '<legend>List</legend>' in uincattxt: break
        splt = list(uincattxt.split('>'))
        users = set()

        for s in splt:
            if "User:" in s and "href" not in s:
                users.add(s.replace("User:","").replace("</a",""))
        return users
    except Exception:
        return set()

def create_heatmap(events, country_name):
    # Modernize the plot aesthetics
    sns.set_theme(style="white")
    
    event_codes = list(events.keys())
    size = len(event_codes)
    matrix = np.zeros((size, size))
    
    # --- Convert codes (wlfbd21) to readable names (Folklore 2021) ---
    readable_labels = []
    for code in event_codes:
        event, cc, yr = re.match(r'(wlf|wle|wlm|wlb)([a-z]{0,2})(\d{2})', code).groups()
        readable_labels.append(f"{EVENT_MAP[event]} 20{yr}")
    # ------------------------------------------------------------------
    
    for i, source in enumerate(event_codes):
        for j, target in enumerate(event_codes):
            source_users = events[source]
            if not source_users:
                matrix[i, j] = 0.0
            else:
                overlap = len(source_users & events[target])
                retention = (overlap / len(source_users)) * 100
                matrix[i, j] = retention
                
    fig, ax = plt.subplots(figsize=(max(5, size * 1.2), max(4, size)))
    
    # Draw the heatmap using our new readable labels
    sns.heatmap(
        matrix, annot=True, fmt=".1f", 
        xticklabels=readable_labels, yticklabels=readable_labels, 
        cmap="mako_r", linewidths=.5, cbar_kws={'label': 'Retention (%)'},
        vmin=0, vmax=100, ax=ax
    )
    
    plt.title(f"{country_name} Retention", pad=15, fontweight='bold', fontsize=14, color="#333333")
    plt.ylabel("Source Event", fontweight='bold', color="#555555")
    plt.xlabel("Target Event", fontweight='bold', color="#555555")
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    return fig

# --- WEB APP INTERFACE ---

# 1. Sidebar Configuration
with st.sidebar:
    # Swapped to a static Wikipedia asset URL that allows hotlinking
    st.image("https://en.wikipedia.org/static/images/project-logos/enwiki.png", width=100)
    st.title("Configuration")
    st.markdown("Enter your event codes below to scrape Wikimedia and generate retention heatmaps.")
    
    default_codes = "wlfbd21 wlfbd22 wlfbd23 wlfin21 wlfin22 wlfin23"
    user_input = st.text_area("Event Codes (space-separated):", value=default_codes, height=120)
    
    run_button = st.button("🚀 Generate Dashboard", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.caption("Powered by Wikimedia Toolforge & Streamlit")

# 2. Main Page Header
# Added a line break so Safari doesn't tuck the title under the top bar
st.markdown("<br>", unsafe_allow_html=True)
st.title("🌍 Cross-Event Retention Dashboard")
st.markdown("Analyze how many users return across different Wikimedia campaigns and regions.")

# 3. Execution Logic
if run_button:
    codes = user_input.split()
    valid = [c for c in (re.sub(r'\s+', '', cd).lower() for cd in codes) 
             if re.match(r'(wlf|wle|wlm|wlb)([a-z]{0,2})(\d{2})', c)]
    
    if not valid:
        st.error("⚠️ No valid event codes found. Please check your formatting.")
        st.stop()

    country_events = defaultdict(dict)
    
    with st.spinner("Fetching data from Wikimedia Toolforge..."):
        for code in valid:
            event, cc, yr = re.match(r'(wlf|wle|wlm|wlb)([a-z]{0,2})(\d{2})', code).groups()
            participants = get_participants(code)
            if cc in COUNTRY_MAP and participants:
                country_events[cc][code] = participants

    valid_countries = {code: events for code, events in country_events.items() if len(events) >= 2}

    if not valid_countries:
        st.warning("⚠️ **Not enough data.** Heatmaps require at least two events in the same country to calculate overlap.")
    else:
        st.success("✅ Data fetched successfully!")
        st.markdown("---")
        
        # 4. Display Dashboard Metrics
        total_events = sum(len(events) for events in valid_countries.values())
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Countries Analyzed", len(valid_countries))
        col_m2.metric("Total Events Included", total_events)
        col_m3.metric("Heatmaps Generated", len(valid_countries))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 5. Display Heatmaps in a clean grid (2 columns)
        cols = st.columns(2)
        
        for idx, (country_code, events) in enumerate(valid_countries.items()):
            country_name = COUNTRY_MAP[country_code]
            fig = create_heatmap(events, country_name)
            
            with cols[idx % 2]:
                st.pyplot(fig)