import streamlit as st
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import google.generativeai as genai
from github import Github, GithubException

# --- CONFIGURATION ---
DATA_FILE = "fitness_data.json"
st.set_page_config(page_title="Fitness Coach", page_icon="💪")

# --- AUTHENTICATION ---
def check_password():
    if st.session_state.get("password_correct", False): return True
    st.header("🔒 Login Required")
    pwd = st.text_input("Enter Password", type="password")
    if st.button("Log In"):
        if pwd == "gym2025": # CHANGE THIS
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("❌ Incorrect Password")
    return False

if not check_password(): st.stop()

# --- SETUP API KEYS ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except: pass

# --- BACKUP FUNCTION ---
def backup_to_github(data):
    token = st.secrets.get("GITHUB_TOKEN")
    repo_name = st.secrets.get("GITHUB_REPO")
    
    if not token or not repo_name:
        st.error("❌ GitHub keys missing in Secrets!")
        return

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        json_str = json.dumps(data, indent=4)
        
        # Try to get existing file to update it
        try:
            contents = repo.get_contents(DATA_FILE)
            repo.update_file(contents.path, "Auto-backup from Streamlit", json_str, contents.sha)
            st.success("✅ Backup successfully pushed to GitHub!")
        except:
            # File doesn't exist yet, create it
            repo.create_file(DATA_FILE, "Initial backup from Streamlit", json_str)
            st.success("✅ New backup file created on GitHub!")
            
    except Exception as e:
        st.error(f"⚠️ Backup Failed: {e}")

# --- DATA HANDLING ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            for key in ["history", "prs", "body_weight", "calories"]:
                if key not in data: data[key] = [] if key != "prs" else {}
            return data
    return {"history": [], "prs": {}, "body_weight": [], "calories": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def calculate_streak(data):
    dates = set([e["date"] for e in data["history"] + data["calories"]])
    sorted_dates = sorted(list(dates), reverse=True)
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if not sorted_dates or (sorted_dates[0] != today and sorted_dates[0] != yesterday):
        return 0
        
    streak = 0
    check_date = datetime.now()
    if sorted_dates[0] == yesterday: check_date -= timedelta(days=1)
    
    for _ in range(len(sorted_dates)):
        if check_date.strftime("%Y-%m-%d") in sorted_dates:
            streak += 1
            check_date -= timedelta(days=1)
        else: break
    return streak

# --- APP START ---
data = load_data()
streak = calculate_streak(data)

ROUTINE = {
    "Monday": {"Focus": "UPPER BODY A", "Exercises": ["Chest Press", "Seated Row", "Shoulder Press", "Lat Pulldown", "Plank"]},
    "Tuesday": {"Focus": "LOWER BODY", "Exercises": ["Leg Press", "Goblet Squat", "Leg Curls", "Lunges", "Calf Raises"]},
    "Wednesday": {"Focus": "ARMS & ABS", "Exercises": ["Tricep Pushdown", "Bicep Curls", "Overhead Tri Ext", "Hammer Curls", "Russian Twists"]},
    "Thursday": {"Focus": "UPPER BODY B", "Exercises": ["Pec Fly", "Rear Delt Fly", "Assisted Pull-Up", "Lateral Raises", "Face Pulls"]},
    "Friday": {"Focus": "FULL BODY GAUNTLET", "Exercises": ["Chest Press", "Leg Press", "Seated Row", "Shoulder Press", "Bicep Curls"]}
}

st.sidebar.title("🔥 Fitness Coach")
st.sidebar.metric("Current Streak", f"{streak} Days")
page = st.sidebar.radio("Go to", ["Coach Mode", "📸 AI Calorie Scanner", "Log Weight", "Manual Nutrition", "Progress Graphs", "⚙️ Tools & Backup"])

if page == "📸 AI Calorie Scanner":
    st.title("📸 Snap & Track")
    img_file = st.camera_input("Take a picture")
    if img_file:
        st.image(img_file, caption="Your Meal")
        if st.button("🤖 Analyze Meal"):
            with st.spinner("Analyzing..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    image_parts = [{"mime_type": img_file.type, "data": img_file.getvalue()}]
                    prompt = "Analyze this food image. Estimate total Calories and Protein (g). Return ONLY JSON: {\"food_name\": \"...\", \"calories\": 0, \"protein\": 0}"
                    response = model.generate_content([prompt, image_parts[0]])
                    text = response.text.strip().replace("```json", "").replace("```", "")
                    ai_data = json.loads(text)
                    st.success(f"Identified: {ai_data['food_name']}")
                    col1, col2 = st.columns(2)
                    col1.metric("Calories", ai_data['calories'])
                    col2.metric("Protein", f"{ai_data['protein']}g")
                    if st.button("Add to Log"):
                        data["calories"].append({"date": datetime.now().strftime("%Y-%m-%d"), "calories": ai_data['calories'], "protein": ai_data['protein']})
                        save_data(data)
                        st.success("Logged!")
                except Exception as e: st.error(f"Error: {e}")

elif page == "Coach Mode":
    day = datetime.now().strftime("%A")
    st.header(f"Today: {day}")
    if day not in ROUTINE: st.info("Rest Day.")
    else:
        plan = ROUTINE[day]
        st.subheader(plan['Focus'])
        with st.form("workout_form"):
            results = {}
            for ex in plan['Exercises']:
                current_pr = data["prs"].get(ex, 0)
                label = f"{ex} (PR: {current_pr} lbs)" if current_pr > 0 else f"{ex} (New)"
                if ex in ["Plank", "Russian Twists"]: results[ex] = st.text_input(label)
                else: results[ex] = st.number_input(label, step=2.5)
            if st.form_submit_button("Save Workout"):
                log = {"date": datetime.now().strftime("%Y-%m-%d"), "day": day, "exercises": {}}
                for ex, val in results.items():
                    log["exercises"][ex] = val
                    if isinstance(val, float) and val > data["prs"].get(ex, 0): data["prs"][ex] = val
                data["history"].append(log)
                save_data(data)
                st.success("Saved!")
                st.rerun()

elif page == "Log Weight":
    st.header("Log Weight")
    w = st.number_input("Weight (lbs)", value=230.0, step=0.1)
    if st.button("Save Weight"):
        data["body_weight"].append({"date": datetime.now().strftime("%Y-%m-%d"), "weight": w})
        save_data(data)
        st.success("Saved!")

elif page == "Manual Nutrition":
    st.header("Manual Log")
    with st.form("food"):
        c = st.number_input("Calories", step=50)
        p = st.number_input("Protein", step=5)
        if st.form_submit_button("Save"):
            data["calories"].append({"date": datetime.now().strftime("%Y-%m-%d"), "calories": c, "protein": p})
            save_data(data)
            st.success("Saved!")

elif page == "Progress Graphs":
    st.header("Progress")
    tab1, tab2 = st.tabs(["Weight", "Calories"])
    with tab1:
        if data["body_weight"]: st.line_chart(pd.DataFrame(data["body_weight"]), x="date", y="weight")
    with tab2:
        if data["calories"]: st.bar_chart(pd.DataFrame(data["calories"]), x="date", y="calories")

elif page == "⚙️ Tools & Backup":
    st.title("⚙️ Tools")
    
    st.subheader("☁️ Cloud Backup")
    if "GITHUB_TOKEN" in st.secrets:
        if st.button("Sync Data to GitHub Now"):
            with st.spinner("Backing up..."):
                backup_to_github(data)
    else:
        st.warning("Add GITHUB_TOKEN to secrets to enable cloud backup.")

    st.divider()
    
    st.subheader("🏋️ 1-Rep Max Calculator")
    col1, col2 = st.columns(2)
    weight = col1.number_input("Weight", value=100)
    reps = col2.number_input("Reps", value=10)
    if weight > 0 and reps > 0:
        one_rm = weight * (1 + reps/30)
        st.metric("Estimated 1-Rep Max", f"{int(one_rm)} lbs")
