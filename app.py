import streamlit as st
from PIL import Image
import pandas as pd
import time
import plotly.express as px
from datetime import datetime, timedelta, timezone 
import numpy as np
import io
import requests
import base64  

GITHUB_USER = "duckola"
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", None)

# Page Config
st.set_page_config(
    page_title="Adolfo | Autobiography & Portfolio",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded",
)

ACCENT_COLORS = {
    "Violet": "#7c3aed",
    "Blue": "#2563eb",
    "Teal": "#0d9488",
    "Pink": "#db2777",
    "Gold": "#d97706",
}

def inject_css(accent: str) -> None:
    st.markdown(
        f"""
        <style>
          :root {{
            --accent: {accent};
          }}
          .accent-text {{ color: var(--accent); }}
          .accent-bg {{ background: linear-gradient(90deg, var(--accent), #111827); border-radius: 12px; padding: 1px; }}
          .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 16px; }}
          .pill {{ display:inline-block; padding: 4px 10px; border-radius: 999px; background: rgba(124,58,237,0.08); border: 1px solid rgba(255,255,255,0.08); margin-right: 6px; margin-bottom: 6px; }}
          .muted {{ color: #9ca3af; }}
          .hero-title {{ font-size: 40px; font-weight: 800; margin: 0; }}
          .hero-sub {{ font-size: 18px; color: #9ca3af; margin-top: 8px; }}
          .footer {{ color:#9ca3af; font-size: 13px; text-align: center; margin-top: 24px; }}
          .stButton>button {{ border-radius:10px; border:1px solid #1f2937; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# Utilities
@st.cache_data(show_spinner=False)
def load_local_image(path: str, fallback_url: str = "") -> Image.Image | None:
    try:
        return Image.open(path)
    except Exception:
        if fallback_url:
            try:
                return Image.open(fallback_url)
            except Exception:
                return None
        return None

def make_resume_bytes(name: str = "Adolfo") -> bytes:
    content = f"""{name} — Resume\n\nSummary\n- Passionate about software, data and delightful user experiences.\n\nExperience\n- Student Developer — Projects in Streamlit, Python, and Web.\n\nSkills\n- Python, Streamlit, Plotly, Pandas, SQL, HTML/CSS/JS\n\nLinks\n- GitHub: https://github.com/\n- LinkedIn: https://www.linkedin.com/\n"""
    return content.encode("utf-8")

def load_file_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner="Fetching GitHub data...")
def get_github_monthly_commits(username, months=6):
    """Fetch monthly commit counts from a user's public GitHub repos."""
    
    headers = {}
    if "GITHUB_TOKEN" in st.secrets and st.secrets["GITHUB_TOKEN"]:
        headers["Authorization"] = f"token {st.secrets['GITHUB_TOKEN']}"
        print("ℹ️ Using GitHub token for API requests.")
    else:
        print("ℹ️ GITHUB_TOKEN secret not found or empty. Proceeding unauthenticated (may hit rate limits).")

    try:
        # Get user repos
        repos_url = f"https://api.github.com/users/{username}/repos"
        repos_response = requests.get(repos_url, headers=headers)
        repos_response.raise_for_status()
        repos = repos_response.json()

        # Prepare date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=months * 30)

        monthly_counts = {}

        # Iterate over repos
        for repo in repos:
            repo_name = repo["name"]
            commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
            params = {"since": start_date.isoformat(), "until": end_date.isoformat()}
            
            commits_response = requests.get(commits_url, params=params, headers=headers)
            
            if commits_response.status_code == 200:
                commits = commits_response.json()
                for commit in commits:
                    commit_date = commit["commit"]["author"]["date"]
                    month_str = commit_date[:7]  # e.g. "2025-11"
                    monthly_counts[month_str] = monthly_counts.get(month_str, 0) + 1

        # Build DataFrame
        if not monthly_counts:
            print("ℹ️ No commits found for user.")
            return None  

        df = pd.DataFrame(list(monthly_counts.items()), columns=["Month", "Commits"])
        df["Month"] = pd.to_datetime(df["Month"])
        df = df.sort_values("Month")
        return df

    except Exception as e:
        if "403" in str(e):
            print("❌ GitHub fetch error: 403 Forbidden. Likely rate-limited. Add a GITHUB_TOKEN to st.secrets.")
        else:
            print(f"❌ GitHub fetch error: {e}")
        return None  


def load_file_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

@st.cache_data(show_spinner=False)
def display_pdf(file_path):
    """Displays a PDF in the app."""
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        # Set a reasonable height and 100% width
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500" type="application/pdf" style="border:none; border-radius: 8px;"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Certificate file not found: {file_path}. Make sure it's in the same folder as your app.")
    except Exception as e:
        st.error(f"Error displaying PDF: {e}")

# GitHub Data Fetch + Streak Logic
def get_repo_count(user: str, use_token=True) -> int:
    """Return total number of non-fork repos, authenticated if possible."""
    headers = {"Accept": "application/vnd.github+json"}
    if use_token and "GITHUB_TOKEN" in st.secrets:
        headers["Authorization"] = f"token {st.secrets['GITHUB_TOKEN']}"
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{user}/repos"
        params = {"type": "owner", "per_page": 100, "page": page}
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return len([r for r in repos if not r.get("fork")])

def get_repos_created_this_year(user: str) -> int:
    """Count how many repos were created in the current year."""
    year = datetime.now().year
    headers = {}
    if "GITHUB_TOKEN" in st.secrets:
        headers["Authorization"] = f"token {st.secrets['GITHUB_TOKEN']}"
    url = f"https://api.github.com/users/{user}/repos?type=owner&per_page=100"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return 0
    repos = resp.json()
    return sum(1 for r in repos if r["created_at"].startswith(str(year)))

def get_weekly_streak_increase(dates):
    """Roughly estimate weekly streak improvement."""
    today = datetime.now().date()
    one_week_ago = today - timedelta(days=7)
    recent_days = [d for d in dates if d >= str(one_week_ago)]
    return len(recent_days)


def github_request(url, params=None):
    """Handle GitHub API requests with or without authentication."""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=3600, show_spinner="Fetching GitHub activity...")
def get_daily_commit_dates(user: str, months=6):
    """Return list of commit dates (YYYY-MM-DD) within the given months."""
    repos_url = f"https://api.github.com/users/{user}/repos"
    repos = github_request(repos_url, {"type": "owner"})
    since = datetime.now(timezone.utc) - timedelta(days=months * 30)
    dates = set()

    for repo in repos:
        commits_url = f"https://api.github.com/repos/{user}/{repo['name']}/commits"
        params = {"since": since.isoformat()}
        try:
            commits = github_request(commits_url, params)
        except Exception:
            continue
        for c in commits:
            date_str = c["commit"]["author"]["date"]
            dates.add(date_str[:10])
    return sorted(dates)


def compute_streak(dates):
    """Compute current commit streak (days in a row with commits)."""
    today = datetime.now().date()
    streak = 0
    day = today
    while str(day) in dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


# Session state: visit count
if "visits" not in st.session_state:
    st.session_state["visits"] = 0
st.session_state["visits"] += 1

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["Home", "Autobiography", "Portfolio", "Achievements & Extras", "Contact"],
    key="main_nav",
)
st.sidebar.markdown("---")

# Sidebar profile
profile_img = load_local_image(
    "FormalPicture - Adolfo.jpg",
    fallback_url="https://i.imgur.com/5cOaVTD.png",
)
if profile_img is not None:
    st.sidebar.image(profile_img, caption="Adolfo", use_container_width=True)

accent_choice = st.sidebar.selectbox("Accent color", list(ACCENT_COLORS.keys()), index=0)
inject_css(ACCENT_COLORS[accent_choice])

st.sidebar.markdown("**Quick Links**")
col_a, col_b = st.sidebar.columns(2)
with col_a:
    st.link_button("GitHub", "https://github.com/duckola")
with col_b:
    st.link_button("LinkedIn", "https://www.linkedin.com/in/lee-jasmin-adolfo-113618373/")

resume_pdf = load_file_bytes("resume_adolfo.pdf")
if resume_pdf:
    st.sidebar.download_button(
        label="Download Resume (PDF)",
        data=resume_pdf,
        file_name="Lee_Jasmin_Adolfo_Resume.pdf",
        mime="application/pdf",
    )
else:
    st.sidebar.download_button(
        label="Download Resume (TXT)",
        data=make_resume_bytes("Lee Jasmin R. Adolfo"),
        file_name="Lee_Jasmin_Adolfo_Resume.txt",
        mime="text/plain",
    )

st.sidebar.markdown("---")
st.sidebar.caption("👋 Created with ❤ using Streamlit • Visits: " + str(st.session_state["visits"]))

# ============================================================
st.markdown(
    """
    <div class="accent-bg" style="margin-bottom: 24px;">
      <div class="card" style="padding:24px;">
        <div class="hero-title">🌟 Adolfo — Autobiography & Portfolio</div>
        <div class="hero-sub">Exploring code, design and data; building thoughtful, human-centered products.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# Pages
# ============================================================

if page == "Home":
    # --- GitHub stats ---
    repo_count = get_repo_count("duckola")
    repos_this_year = get_repos_created_this_year("duckola")
    commit_dates = get_daily_commit_dates("duckola", months=6)
    streak_days = compute_streak(commit_dates)
    increase_this_week = get_weekly_streak_increase(commit_dates)
    prev_year_count = repo_count - repos_this_year


    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.image(
            profile_img if profile_img is not None else "https://i.imgur.com/5cOaVTD.png",
            caption="Hello there!",
            width=230,
        )
    with col2:
        st.metric("Projects", repo_count, f"+{repos_this_year} this year")
        st.metric("Learning Streak", f"{streak_days} days", f"+{increase_this_week} this week")
        st.metric("Coffee", "∞ cups")
    with col3:
        st.write(
            """
            ## Hi, I'm **Lee Jasmin R. Adolfo** 👋
            I love building with Python and Streamlit — from data visualizations to sleek web apps.
            This site shares my story, selected projects, and ways to connect.
            """
        )
        st.success("Explore the sections with the sidebar!")

    st.markdown("### Highlights")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='card'><b>Focus</b><br/><span class='muted'>Data apps, UI polish, Game Development, Web Development</span></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='card'><b>Values</b><br/><span class='muted'>Clarity, empathy, rigor, creativity, passion</span></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='card'><b>Now Learning</b><br/><span class='muted'>LLM tooling, Plotly, Game Development, Web Development</span></div>", unsafe_allow_html=True)

    st.markdown("### Recent Activity")
    df = get_github_monthly_commits("duckola", months=5)
    
    if df is not None and not df.empty:
        chart = px.bar(df, x="Month", y="Commits", title="Monthly commits (GitHub public activity)")
        c_left, c_right = st.columns([2, 1])
        with c_left:
            st.plotly_chart(chart, use_container_width=True)
        with c_right:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent PushEvent commits found (or rate-limited). Try again later or add a GitHub token in st.secrets as GITHUB_TOKEN for higher limits.")

    # Map
    st.markdown("### 🌏 Places I Love")

    # --- Try to get user's live location ---
    try:
        response = requests.get("https://ipinfo.io/json", timeout=5) 
        data = response.json()
        loc_str = data["loc"]  # example: "10.3157,123.8854"
        lat, lon = map(float, loc_str.split(","))
        current_city = data.get("city", "Unknown")
        current_country = data.get("country", "Unknown")
        current_label = f"{current_city}, {current_country} (Current Location)"
    except Exception:
        lat, lon = 10.2790, 123.8615  # fallback (Cebu)
        current_label = "Cebu, Philippines (Home)"

    # --- Favorite places + current location ---
    locations = pd.DataFrame(
        {
            "lat": [35.6762, 46.8182, 48.8566, 54.5260, lat],
            "lon": [139.6503, 8.2275, 2.3522, 15.2551, lon],
            "label": ["Tokyo, Japan", "Switzerland", "France", "Europe", current_label],
        }
    )

    st.map(locations, zoom=2)
    st.write("📍 Currently showing:", current_label)
elif page == "Autobiography":
    # --- HEADER ---
    st.markdown("<h1 style='text-align: center;'>📖 My Story</h1>", unsafe_allow_html=True)
    st.markdown("<hr style='border: 1px solid #ddd; margin-top: -10px;'>", unsafe_allow_html=True)

    # --- MAIN LAYOUT ---
    col1, col2 = st.columns([1, 2], gap="large")

    # LEFT COLUMN - PROFILE INFO 
    with col1:
        st.image(
            profile_img if profile_img is not None else "https://i.imgur.com/5cOaVTD.png",
            width=240,
            caption="Lee Jasmin R. Adolfo"
        )

        st.markdown("""
        <div style="font-size: 16px; line-height: 1.8; margin-top: 15px;">
            <b>📍 Address:</b> Greenbelt Dr., Quiot Pardo, Cebu City, Cebu<br>
            <b>📧 Email:</b> <a href="mailto:leejasminadolfo@gmail.com">leejasminadolfo@gmail.com</a><br>
            <b>📱 Mobile:</b> +63 991 998 0930<br>
            <b>💬 Pronouns:</b> she/her
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br><b>🌏 Languages</b>", unsafe_allow_html=True)
        st.markdown("""
        <div style="margin-top: 5px; font-size: 16px; line-height: 1.8;">
            🇵🇭 Cebuano — Native<br>
            🇵🇭 Filipino — Fluent<br>
            🇬🇧 English — Fluent
        </div>
        """, unsafe_allow_html=True)

    # RIGHT COLUMN 
    with col2:
        st.subheader("Hello! 👋")
        st.write("""
        I'm Lee Jasmin, a Computer Science student at the **Cebu Institute of Technology – University** with a deep passion for bringing ideas to life through code and design.

        My journey started in high school with the basics of HTML and CSS, which sparked an immediate curiosity. I was fascinated by how a few lines of text could build a visible, interactive world. This curiosity pushed me to explore programming more deeply.

        My first real-world test came during my IT immersion at **SARWASSCO** (San Remigio Water Sanitation Service Cooperative). It was an invaluable experience where I wasn't just learning theory; I was providing technical support, assisting with system maintenance, and organizing customer data in Excel. It taught me the importance of reliable systems and paying close attention to detail.

        Today, I'm building on that foundation by diving into a diverse range of technologies, from backend languages like **Python, Java, and PHP** to design tools like **Figma and Canva**. I thrive on the challenge of figuring things out, whether it's designing a user interface, developing a web app, or providing virtual assistance.

        As a **fast learner who is team-oriented and adaptable**, my goal is to find an opportunity where I can contribute to meaningful projects, continue to grow my skills, and help deliver high-quality, professional results.
        """)

        st.markdown("---")
        st.subheader("🎓 Education")
        st.markdown("""
        **Cebu Institute of Technology – University** *Bachelor of Science in Computer Science* 🗓️ *Expected Graduation: June 2027*
        """)


elif page == "Portfolio":
    st.header("🗂️ My Portfolio")
    st.markdown("Here is a selection of my featured projects. Click any title to visit the GitHub repository.")
 
    projects = [
        {
            "name": "🌸 Bloom",
            "desc": "An exercise progress tracker that plans your workout routine with AI.",
            "tech": "Python, Streamlit, OpenAI API",
            "url": "https://github.com/duckola/bloom"
        },
        {
            "name": "🥗 NutriLens",
            "desc": "JavaFX desktop app for food image analysis and nutrition tracking using FDC and LogMeal APIs, with Gemini AI integration.",
            "tech": "JavaFX, API Integration, FDC API, LogMeal, Gemini",
            "url": "https://github.com/duckola/NutriLens_Capstone"
        },
        {
            "name": "⭐ Trials of Survival: Beyond the Sky",
            "desc": "A story-driven RPG inspired by *The Little Prince* combining narrative and gameplay design.",
            "tech": "Game Development, C#, Unity",
            "url": "https://github.com/duckola/TheLittlePrince"
        },
        {
            "name": "🍔 FoodDo",
            "desc": "Food retail system with ordering, tracking, and inventory management features.",
            "tech": "PHP, MySQL, Bootstrap",
            "url": "https://github.com/duckola/FoodDo"
        },
        {
            "name": "Kiimo-o (Ongoing)",
            "tech": "Mobile Development, Geolocation, Database",
            "desc": "A social media app with a twist: see nearby users' posts, notes, videos, or selfies.",
            "url": "https://github.com/duckola/KiiMo-o"
        },
        {
            "name": "WeatherWise (Ongoing)",
            "tech": "Python, Streamlit, Weather API",
            "desc": "Tells you what to expect from the weather and helps you decide on a course of action based on your needs.",
            "url": ""
        },
        {
            "name": "Ad Blocker Extension",
            "tech": "JavaScript, HTML/CSS (Browser Extension)",
            "desc": "A personal project to build a custom ad-blocking browser extension.",
            "url": ""
        },
        {
            "name": "Portfolio Website",
            "tech": "Streamlit, Plotly",
            "desc": "Dynamic, data-driven portfolio (this site!).",
            "url": "https://github.com/duckola/portfolio"
        },
    ]

    cols = st.columns(2)
    for i, p in enumerate(projects):
        with cols[i % 2]:
            if p.get("url"):
                title = f"<a href='{p['url']}' target='_blank' style='color:#FFFFFF; font-size:1.15em;'><b>{p['name']} 🔗</b></a>"
            else:
                title = f"<b style='font-size:1.15em;'>{p['name']}</b>"

            card_html = f"""
            <div class='card'>
                {title}<br/>
                <span class='muted'>{p['desc']}</span><br/>
                <i>{p['tech']}</i>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🎨 Design Works")
    st.image(
        ["poster1.png", "poster2.png"],
        width=300,
        caption=["Poster 1", "Poster 2"]
    )




elif page == "Contact":
    st.header("📬 Contact Me")
    with st.form("contact_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Your Name")
            email = st.text_input("Your Email")
            reason = st.selectbox("Reason", ["Say hi", "Collab", "Hire", "Other"]) 
        with c2:
            company = st.text_input("Company / School")
            availability = st.date_input("Preferred date", value=datetime.now())
            urgency = st.slider("Urgency", 1, 5, 3)

        message = st.text_area("Your Message", height=120)
        upload = st.file_uploader("Attach a file (optional)", type=["pdf", "png", "jpg", "zip"]) 
        camera = st.camera_input("Snap a picture (optional)")

        submitted = st.form_submit_button("Send Message")
        if submitted:
            st.success(f"✅ Thank you {name or 'there'}! Your message has been received.")
            if upload is not None:
                st.info(f"Attached: {upload.name} — {upload.size} bytes")

    st.markdown("---")
    st.markdown("📧 **Email:** leejasminadolfo@gmail.com")
    st.markdown("🔗 [LinkedIn](https://www.linkedin.com/in/lee-jasmin-adolfo-113618373/) | [GitHub](https://github.com/duckola)")

elif page == "Achievements & Extras":
    st.header("🌟 Achievements & Extras")
    st.markdown("A mix of my academic milestones, certificates, hackathons, and a little fun corner about me!")

    tabs = st.tabs([
        "🏅 Certificates",
        "💡 Hackathons Joined",
        "🏛️ Organizations",
        "🎓 Academic Achievements",
        "🎵 Fun Zone",
    ])

    #Certificates
    with tabs[0]:
        st.subheader("🏅 Certificates")
        st.markdown("Click on any certificate to view the file.")
        
        certs = [
            {
                "title": "Introduction to Python",
                "issuer": "Sololearn",
                "year": "Issued: Aug 2025",
                "file": "python_certificate.jpg" 
            },
            {
                "title": "Java Object-Oriented Programming",
                "issuer": "CodeChum & CITU",
                "year": "Issued: May 2025",
                "file": "java_certificate.pdf" 
            },
            {
                "title": "Graphic Design Essentials",
                "issuer": "Canva Design School",
                "year": "Issued: Sep 2024",
                "file": "canva_certificate.pdf"
            },
            {
                "title": "Youth Hackathon 2025 (Certificate of Participation)",
                "issuer": "UNESCO",
                "year": "Issued: Oct 2025",
                "file": "unesco_certificate.pdf" 
            }
        ]

        for c in certs:
            expander_title = f"**{c['title']}** — *{c['issuer']} ({c['year']})*"
            
            with st.expander(expander_title):
                if c['file']:
                    # Check file type
                    if c['file'].endswith(".pdf"):
                        display_pdf(c['file']) 
                    elif c['file'].endswith((".jpg", ".png", ".jpeg")):
                        st.image(c['file'], use_container_width=True)
                    else:
                        st.info(f"Cannot display this file type: {c['file']}")
                else:
                    # Fallback for certs without a file
                    st.info("No certificate file available to display for this entry.")

    # Hackathons Joined
    with tabs[1]:
        st.subheader("💡 Hackathons & Competitions")
        
        hackathons = [
            {
                "name": "CEB-i Hacks", 
                "desc": "A 6-week idea challenge to spark student-led innovation, focusing on AI-powered solutions to improve travel and tourism in Cebu."
            },
            {
                "name": "UNESCO Youth Hackathon 2025", 
                "desc": "A flagship initiative of UNESCO’s Global Media and Information Literacy (MIL) Week, empowering youth to build MIL solutions to tackle digital challenges."
            },
        ]
        
        for h in hackathons:
            st.markdown(f"<div class='card'><b>{h['name']}</b><br/><span class='muted'>{h['desc']}</span></div>", unsafe_allow_html=True)            

    # Organizations
    with tabs[2]:
        st.subheader("🏛️ Organizations Joined")
        
        orgs = [
            {
                "name": "Computer Students' Society",
                "role": "Committee on Documentation (2025-2026)"
            },
            {
                "name": "Robotics Society of CIT-U",
                "role": "Member (2024)"
            },
            {
                "name": "Computer Student's Society",
                "role": "Committee on Volunteers, Member (2023-2024)"
            },
        ]
        
        for o in orgs:
            st.markdown(f"<div class='card'><b>{o['name']}</b><br/><span class='muted'>{o['role']}</span></div>", unsafe_allow_html=True)
    
    
    # Academic Achievements
    with tabs[3]:
        st.subheader("🎓 Academic Achievements")
        
        timeline = [
            {
                "year": "2025", 
                "achievement": "Top 25 Hackathon finalist, Ceb-i Hacks Cebu"
            },
            {
                "year": "2024", 
                "achievement": "Parangal Awardee (Academic Achiever, 1st Year College)"
            },
            {
                "year": "Senior High (2021-2023)", 
                "achievement": "With High Honors"
            },
            {
                "year": "Junior High(2017-2021)", 
                "achievement": "With High Honors"
            },
            {
                "year": "Elementary", 
                "achievement": "With Highest Honors"
            },
            {
                "year": "2014", 
                "achievement": "Division Level Top 4 ReadAThon Competition"
            },

        ]
        
        for t in timeline:
            st.markdown(f"<div class='card'><b>{t['year']}</b><br/><span class='muted'>{t['achievement']}</span></div>", unsafe_allow_html=True)

    # Fun Zone
    with tabs[4]:
        st.subheader("🎵 Fun Zone — The Human Behind the Code 💖")
        st.markdown("""
        - 🧁 **Likes:** Photography, listening to japanese rock music, pancakes
        - 🎮 **Hobbies:** Playing Genshin Impact, badminton, and designing UIs  
        - 🎧 **Favorite Artist:** The Academic
        - 🎬 **Favorite Series:** The 100 
        - 💭 **Fun Fact:** I find frogs cute
        """)
         
        st.markdown("---")
        st.markdown("### Media & Sample Work")
        
        tab1, tab2 = st.tabs(["Self Introduction", "Sample Website"])

        with tab1:
            st.write("**Self Introduction Video**")
            st.markdown(
            """
            <div style="position: relative; width: 100%; height: 0; padding-top: 56.25%;
            padding-bottom: 0; box-shadow: 0 2px 8px 0 rgba(63,69,81,0.16); margin-top: 1.6em; margin-bottom: 0.9em; overflow: hidden;
            border-radius: 8px; will-change: transform;">
            <iframe loading="lazy" style="position: absolute; width: 100%; height: 100%; top: 0; left: 0; border: none; padding: 0; margin: 0;"
                src="https.canva.com/design/DAGb4IWuNfY/RFIRzxT8_Cz2gQPjUvL7bA/watch?embed" allowfullscreen="allowfullscreen" allow="fullscreen">
            </iframe>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with tab2:
            st.write("**Sample Website (Canva)**")
            st.markdown(
            """
            <div style="position: relative; width: 100%; height: 0; padding-top: 62.5000%;
            padding-bottom: 0; box-shadow: 0 2px 8px 0 rgba(63,69,81,0.16); margin-top: 1.6em; margin-bottom: 0.9em; overflow: hidden;
            border-radius: 8px; will-change: transform;">
            <iframe loading="lazy" style="position: absolute; width: 100%; height: 100%; top: 0; left: 0; border: none; padding: 0;margin: 0;"
                src="https://www.canva.com/design/DAGU7EQCzjs/_uWx62KLsG-rcCe_gPw8ng/watch?embed" allowfullscreen="allowfullscreen" allow="fullscreen">
            </iframe>
            </div>
            <a href="https.../watch?..." target="_blank" rel="noopener">
            </a>
            """,
            unsafe_allow_html=True,
        )
# ============================================================
# Footer
# ============================================================
st.markdown("<div class='footer'>© " + str(datetime.now().year) + " Adolfo — Built with Streamlit</div>", unsafe_allow_html=True)