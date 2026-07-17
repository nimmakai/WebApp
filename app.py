import streamlit as st
import requests
import re
import numpy as np
import pandas as pd
import plotly.express as px
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

st.set_page_config(
    page_title="Wikimedia Campaigns",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

WIKI_BLUE = "#3366cc"
WIKI_BLUE_LIGHT = "#7aa7ff"
WIKI_BLUE_DARK = "#14428e"
WIKI_INK = "#202122"
WIKI_GRAY = "#54595d"
KORIKATH_LOGO_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/Project_Korikath_Logo.svg"
MW_API_URL = "https://commons.wikimedia.org/w/api.php"

BG_DEEP = "#0a1526"
BG_MID = "#13284a"
APP_BG = f"radial-gradient(circle at 10% -10%, {BG_MID} 0%, {BG_DEEP} 55%, #060d1a 100%)"
TEXT_MAIN = "#eef3fc"
TEXT_MUTED = "#a9b9d8"
CARD_BG = "rgba(255, 255, 255, 0.05)"
CARD_BORDER = "rgba(255, 255, 255, 0.12)"
SIDEBAR_BG = f"linear-gradient(165deg, #0d1c33 0%, {WIKI_BLUE_DARK} 65%, {WIKI_BLUE} 100%)"
SIDEBAR_TEXT = "#f5f8ff"
INPUT_BG = "rgba(255, 255, 255, 0.08)"
INSIGHT_BG = "rgba(122, 167, 255, 0.05)"

CUSTOM_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: {APP_BG} !important; }}
    .stApp, .stApp p, .stApp li, .stApp label {{ color: {TEXT_MAIN} !important; }}
    div[data-testid="stMarkdownContainer"] p {{ color: {TEXT_MUTED} !important; }}
    .stDeployButton, [data-testid="stHeaderActionElements"] {{ display: none !important; }}
    header[data-testid="stHeader"] {{ background: transparent !important; }}
    
    section[data-testid="stSidebar"] {{ background: {SIDEBAR_BG} !important; border-right: 1px solid {CARD_BORDER}; }}
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {{ color: {SIDEBAR_TEXT} !important; }}
    section[data-testid="stSidebar"] textarea, section[data-testid="stSidebar"] input {{ background: {INPUT_BG} !important; border: 1px solid {CARD_BORDER} !important; border-radius: 10px !important; color: {SIDEBAR_TEXT} !important; }}
    
    .stButton > button[kind="primary"] {{ background: linear-gradient(90deg, {WIKI_BLUE} 0%, {WIKI_BLUE_DARK} 100%); color: white !important; border: none; border-radius: 10px; font-weight: 600; padding: 0.6em 1em; box-shadow: 0 4px 14px rgba(51, 102, 204, 0.35); transition: transform 0.15s ease; }}
    .stButton > button[kind="primary"]:hover {{ transform: translateY(-1px); box-shadow: 0 6px 18px rgba(51, 102, 204, 0.45); }}
    
    .hero-title {{ font-size: 2.6rem; font-weight: 800; letter-spacing: -1px; margin: 1.5rem 0 0.15rem 0; background: linear-gradient(90deg, {WIKI_BLUE} 0%, {WIKI_BLUE_LIGHT} 50%, {WIKI_BLUE_DARK} 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .hero-subtitle {{ color: {TEXT_MUTED} !important; font-size: 1.05rem; margin-bottom: 2rem; }}
    
    .health-card {{ background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 20px; padding: 2rem; margin-top: 0.5rem; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1); }}
    .health-title {{ font-size: 1.4rem; font-weight: 800; color: {TEXT_MAIN}; margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid {CARD_BORDER}; padding-bottom: 1rem; }}
    .metric-label {{ font-size: 1.05rem; font-weight: 600; color: {TEXT_MAIN}; margin-bottom: 0.2rem; margin-top: 1rem; }}
    .metric-desc {{ font-size: 0.85rem; color: {TEXT_MUTED}; margin-bottom: 0.4rem; }}
    .stars {{ color: #ffc107; font-size: 1.3rem; letter-spacing: 3px; margin-bottom: 0.5rem; }}
    .overall-score {{ font-size: 2.8rem; font-weight: 800; color: {TEXT_MAIN}; margin-top: 0.5rem; }}
    .insight-box {{ border-left: 4px solid {WIKI_BLUE}; background: {INSIGHT_BG}; padding: 1.2rem 1.5rem; border-radius: 0 10px 10px 0; margin-bottom: 1.2rem; }}

    .fade-in-up {{ animation: fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both; }}
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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
REGION_COUNTRY_MAP = {
    "South Asia (SA)": ['bd', 'in', 'pk', 'np'],
    "Northern & Western Europe (NWE)": ['de', 'fr', 'uk', 'nl', 'be', 'ch', 'se', 'no', 'fi', 'at'],
    "Southern Europe & LatAm": ['it', 'es', 'pt', 'br', 'mx', 'ar', 'co'],
    "East, Southeast Asia, Pacific": ['id', 'ph', 'my'],
    "Africa & Middle East": ['ng', 'ke', 'eg', 'tr']
}

CODE_RE = re.compile(r'(wlf|wle|wlm|wlb)([a-z]{0,2})(\d{2,4})')

def normalize_year(yr_str):
    is_short = len(yr_str) <= 2
    full_year = 2000 + int(yr_str) if is_short else int(yr_str)
    return full_year, is_short

def get_category_name(code):
    match = CODE_RE.match(code)
    if not match:
        return None
    event, cc, yr = match.groups()
    full_year, _ = normalize_year(yr)
    cat = f"Images_from_Wiki_Loves_{EVENT_MAP[event]}_{full_year}"
    if cc and event != 'wlb':
        cat += f"_in_{COUNTRY_MAP.get(cc, '')}"
    return cat

@st.cache_data(show_spinner=False, ttl=1800)
def get_participants(code):
    cat = get_category_name(code)
    if not cat:
        return set()
    
    users = set()
    params = {
        "action": "query", "list": "categorymembers", "cmtitle": f"Category:{cat}",
        "cmtype": "file", "cmprop": "user", "cmlimit": "max", "format": "json"
    }
    
    try:
        while True:
            res = requests.get(MW_API_URL, params=params, timeout=15).json()
            members = res.get("query", {}).get("categorymembers", [])
            for m in members:
                if m.get("user"): users.add(m["user"])
            if "continue" in res:
                params.update(res["continue"])
            else:
                break
        return users
    except Exception:
        return set()

def fetch_all_concurrently(codes, progress_text="Fetching data..."):
    results = {}
    total = len(codes)
    if total == 0:
        return results
    progress = st.progress(0, text=progress_text)
    with ThreadPoolExecutor(max_workers=min(16, max(1, total))) as executor:
        future_to_code = {executor.submit(get_participants, code): code for code in codes}
        done = 0
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try: results[code] = future.result()
            except Exception: results[code] = set()
            done += 1
            progress.progress(done / total, text=f"{progress_text} ({done}/{total})")
    progress.empty()
    return results

@st.cache_data(show_spinner=False, ttl=3600)
def derive_regional_baselines(region_name, event_type, target_yr_int):
    if region_name not in REGION_COUNTRY_MAP:
        return {"retention_base": 12.0, "growth_base": 30.0}
    
    countries = REGION_COUNTRY_MAP[region_name]
    prev_yr = target_yr_int - 1
    prev_prev_yr = target_yr_int - 2
    yr1_fmt = str(prev_prev_yr)
    yr2_fmt = str(prev_yr)

    codes_to_fetch = [f"{event_type}{c}{yr}" for c in countries for yr in (yr1_fmt, yr2_fmt)]
    data = fetch_all_concurrently(codes_to_fetch, "Deriving dynamic regional baselines...")

    regional_retentions = []
    regional_growths = []

    for c in countries:
        c_base = data.get(f"{event_type}{c}{yr1_fmt}", set())
        c_target = data.get(f"{event_type}{c}{yr2_fmt}", set())
        if c_base and c_target:
            overlap = len(c_target & c_base)
            ret_rate = (overlap / len(c_base)) * 100
            growth_rate = (len(c_target - c_base) / len(c_target)) * 100
            regional_retentions.append(ret_rate)
            regional_growths.append(growth_rate)

    return {
        "retention_base": float(np.median(regional_retentions)) if regional_retentions else 15.0,
        "growth_base": float(np.median(regional_growths)) if regional_growths else 40.0
    }

def calculate_true_gini(array):
    array = np.array(array, dtype=np.float64)
    if array.size == 0: return 0.0
    array = np.sort(array)
    if np.amin(array) < 0: array -= np.amin(array)
    array += 0.0000001
    index = np.arange(1, array.shape[0] + 1)
    n = array.shape[0]
    return ((np.sum((2 * index - n - 1) * array)) / (n * np.sum(array)))

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_fast_proxy_metrics(code):
    cat = get_category_name(code)
    if not cat: return None, None, 0, 0

    params = {
        "action": "query", "list": "categorymembers", "cmtitle": f"Category:{cat}",
        "cmtype": "file", "cmlimit": "500", "cmprop": "title|user", "format": "json"
    }

    try:
        res = requests.get(MW_API_URL, params=params, timeout=10).json()
        data = res.get("query", {}).get("categorymembers", [])
    except Exception: return None, None, 0, 0

    if not data: return None, None, 0, 0

    user_counts = defaultdict(int)
    file_titles = []
    for item in data:
        user_counts[item.get("user", "Unknown")] += 1
        file_titles.append(item.get("title"))

    sample_size = len(file_titles)
    unique_contributors = len(user_counts)

    if unique_contributors <= 1:
        diversity_score = 0.0
    else:
        diversity_score = (1.0 - calculate_true_gini(list(user_counts.values()))) * 100.0

    sample_titles = random.sample(file_titles, min(sample_size, 50))
    titles_string = "|".join(sample_titles)

    usage_params = {
        "action": "query", "prop": "globalusage", "titles": titles_string,
        "gulimit": "500", "format": "json"
    }

    try:
        usage_res = requests.get(MW_API_URL, params=usage_params, timeout=10).json()
        pages = usage_res.get("query", {}).get("pages", {})
        used_files = sum(1 for page_info in pages.values() if page_info.get("globalusage", []))
        quality_raw = (used_files / len(sample_titles)) * 100.0 if sample_titles else None
    except Exception:
        quality_raw = None

    return quality_raw, diversity_score, sample_size, unique_contributors

def calculate_stars(score, max_score=100):
    normalized = min(max(score / max_score, 0), 1)
    stars = int(round(normalized * 5))
    return "★" * max(1, stars) + "☆" * (5 - max(1, stars))

def metric_block_html(label, raw_display, desc, score):
    stars_html = calculate_stars(score) if score is not None else '<span style="opacity:.5; font-size: 0.9rem;">— data unavailable —</span>'
    return (f'<div class="metric-label">{label} ({raw_display})</div>'
            f'<div class="metric-desc">{desc}</div>'
            f'<div class="stars">{stars_html}</div>')

with st.sidebar:
    st.markdown(f'<div style="text-align: center; margin-bottom: 20px;"><img src="{KORIKATH_LOGO_URL}" alt="Logo" style="width: 140px;"></div>', unsafe_allow_html=True)
    st.markdown("### Campaign Evaluator")
    
    target_event = st.text_input("🎯 Target Campaign Code", value="", placeholder="e.g., wlmbd2024").strip().lower()
    st.markdown("---")
    comp_mode = st.radio("Benchmark Against:", ["Previous Year", "Custom Event", "Regional Standard Only"], index=0)

    baseline_event = ""
    pure_regional_mode = False
    
    if comp_mode == "Custom Event":
        baseline_event = st.text_input("⚖️ Baseline Campaign Code", value="", placeholder="e.g., wlmbd2023").strip().lower()
    elif comp_mode == "Previous Year" and target_event:
        try:
            event, cc, yr = CODE_RE.match(target_event).groups()
            full_year, is_short = normalize_year(yr)
            prev_year = full_year - 1
            prev_str = f"{prev_year % 100:02d}" if is_short else str(prev_year)
            baseline_event = f"{event}{cc}{prev_str}"
            st.info(f"Auto-Baseline: **{baseline_event}**")
        except Exception:
            baseline_event = ""
    else:
        pure_regional_mode = True

    region = st.selectbox("🌍 Geographic Peer Group", list(REGION_COUNTRY_MAP.keys()))
    analyze_btn = st.button("🩺 Generate Evaluation Report", type="primary", use_container_width=True)

st.markdown('<div class="hero-title fade-in-up">Wikimedia Campaign Insights</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Provide a campaign code in the sidebar configuration to pull analytical reports via live MediaWiki statistical proxies.</div>', unsafe_allow_html=True)

if analyze_btn:
    if not target_event or (not pure_regional_mode and not baseline_event):
        st.error("⚠️ Please provide valid target and baseline event codes.")
        st.stop()
    if not CODE_RE.match(target_event):
        st.error(f"⚠️ **{target_event}** doesn't match a recognized event pattern (e.g. `wlmbd2024`).")
        st.stop()

    with st.status("Querying MediaWiki APIs for live metrics...", expanded=True) as status:
        status.write("🔎 Fetching native category member sets...")
        users_data = fetch_all_concurrently(
            [target_event] + ([baseline_event] if baseline_event else []),
            "Synchronizing primary target lists..."
        )
        target_users = users_data.get(target_event, set())
        base_users = users_data.get(baseline_event, set()) if baseline_event else set()

        if not target_users:
            status.update(label="❌ Analysis Failed", state="error")
            st.error(f"❌ Could not retrieve records for target category: **{target_event}**.")
            st.stop()

        region_vals = {"retention_base": None, "growth_base": None}
        if not pure_regional_mode:
            event_type, _, yr_str = CODE_RE.match(target_event).groups()
            target_yr_int, _ = normalize_year(yr_str)
            status.write(f"📊 Calculating dynamic medians across {region}...")
            region_vals = derive_regional_baselines(region, event_type, target_yr_int)

        metrics = {}
        if pure_regional_mode or len(base_users) == 0:
            metrics['Retention'] = {'raw': 'N/A', 'score': None}
            metrics['Growth'] = {'raw': 'N/A', 'score': None}
        else:
            overlap = len(target_users & base_users)
            ret_rate = (overlap / len(base_users)) * 100
            ret_score = (ret_rate / max(1, region_vals['retention_base'])) * 50
            metrics['Retention'] = {'raw': f"{ret_rate:.1f}%", 'score': min(100, ret_score)}

            new_users = len(target_users - base_users)
            growth_rate = (new_users / len(target_users)) * 100
            growth_score = (growth_rate / max(1, region_vals['growth_base'])) * 50
            metrics['Growth'] = {'raw': f"{growth_rate:.1f}%", 'score': min(100, growth_score)}

        status.write("🖼️ Extracting proxy image distribution and global metrics...")
        quality_raw, diversity_raw, sample_size, unique_contributors = fetch_fast_proxy_metrics(target_event)

        if quality_raw is not None:
            metrics['Quality'] = {'raw': f"{quality_raw:.1f}%", 'score': min(100.0, (quality_raw / 15.0) * 100)}
        else:
            metrics['Quality'] = {'raw': 'Unavailable', 'score': None}

        if diversity_raw is not None:
            metrics['Diversity'] = {'raw': f"{diversity_raw:.1f}", 'score': diversity_raw}
        else:
            metrics['Diversity'] = {'raw': 'Unavailable', 'score': None}

        WEIGHT_MAP = {'Retention': 0.50, 'Growth': 0.10, 'Quality': 0.25, 'Diversity': 0.15}
        scored = {k: metrics[k]['score'] for k in WEIGHT_MAP if metrics[k]['score'] is not None}
        available_weight = sum(WEIGHT_MAP[k] for k in scored)
        overall_raw = (sum(scored[k] * WEIGHT_MAP[k] for k in scored) / available_weight) if available_weight > 0 else 0
        metrics['Overall'] = round(overall_raw)

        status.update(label="✅ Performance Framework Constructed", state="complete", expanded=False)

    col1, col2 = st.columns([1, 1.2], gap="large")

    with col1:
        retention_desc = f"Retained users vs regional baseline ({region_vals.get('retention_base', 0):.1f}%)." if metrics['Retention']['score'] else "No baseline context."
        growth_desc = f"New registration tracking vs baseline ({region_vals.get('growth_base', 0):.1f}%)." if metrics['Growth']['score'] else "No baseline context."
        quality_desc = f"Proportion of a {sample_size}-file sample used globally across Wiki metrics."
        diversity_desc = f"Gini indexing calculation across {unique_contributors} distinct upload blocks."

        overall_score_html = f"{metrics['Overall']}<span style=\"font-size: 1.2rem; color: {TEXT_MUTED};\"> / 100</span>" if available_weight > 0 else "N/A"
        
        card_html = f"""<div class="health-card fade-in-up">
            <div class="health-title"><span>{target_event.upper()} Assessment Summary</span></div>
            {metric_block_html("User Retention", metrics['Retention']['raw'], retention_desc, metrics['Retention']['score'])}
            {metric_block_html("Fresh Contributor Growth", metrics['Growth']['raw'], growth_desc, metrics['Growth']['score'])}
            {metric_block_html("Media Production Utility", metrics['Quality']['raw'], quality_desc, metrics['Quality']['score'])}
            {metric_block_html("Contributor Diversity Index", metrics['Diversity']['raw'], diversity_desc, metrics['Diversity']['score'])}
            <hr style="border-color: {CARD_BORDER}; margin: 1.5rem 0;">
            <div class="metric-label">Unified Structural Health Score</div>
            <div class="overall-score">{overall_score_html}</div>
        </div>"""
        st.markdown(card_html, unsafe_allow_html=True)

    with col2:
        st.markdown("#### 📊 Metric Visual Matrix")
        score_rows = [(k, metrics[k]['score']) for k in WEIGHT_MAP if metrics[k]['score'] is not None]
        if score_rows:
            df_scores = pd.DataFrame(score_rows, columns=["Metric", "Score"])
            fig = px.bar(df_scores, x="Score", y="Metric", orientation="h", range_x=[0, 100], color="Score",
                         color_continuous_scale=["#e74c3c", "#f1c40f", "#2ecc71"], range_color=[0, 100], text="Score")
            fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color=TEXT_MAIN,
                              coloraxis_showscale=False, margin=dict(l=10, r=30, t=10, b=10), height=240, yaxis_title=None, xaxis_title=None)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        
        st.markdown("### 🧠 Diagnostic Insights")
        insights = []

        if metrics['Retention']['score'] is not None:
            raw_ret = float(metrics['Retention']['raw'].replace('%', ''))
            if (raw_ret - region_vals['retention_base']) > 5:
                insights.append(f"🚀 **Retention Strength:** The event outperformed its local regional baseline target benchmarks ({region_vals['retention_base']:.1f}%).")
            elif (raw_ret - region_vals['retention_base']) < -5:
                insights.append(f"📉 **Retention Variance:** The community experienced standard dropouts falling below regional profiles.")

        if quality_raw is not None and quality_raw > 15.0:
            insights.append(f"🛡️ **High Operational Value:** Over {quality_raw:.1f}% of images sampled have immediate utilization targets globally.")
        
        if unique_contributors <= 1:
            insights.append("🔒 **Monopoly Warning:** The active file batch originates entirely from a single contributor block.")
        elif diversity_raw is not None and float(metrics['Diversity']['raw']) < 40.0:
            insights.append("⚠️ **Production Concentration:** The pool presents asset volume skewing toward a minor subset of hyper-uploaders.")

        for ins in insights:
            st.markdown(f"<div class='insight-box fade-in-up'><p>{ins}</p></div>", unsafe_allow_html=True)
