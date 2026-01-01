import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
import google.generativeai as genai

# --- CONFIGURATION ---
DATA_FILE = "fitness_data.json"
st.set_page_config(page_title="Fitness Coach", page_icon="💪")

# --- AUTHENTICATION & API SETUP ---
# 1. Password Protection
def check_password():
    if st.session_state.get("password_correct", False): return True
    st.header("🔒 Login Required")
    pwd = st.text_input("Enter Password", type="password")
    if st.button("Log In"):
        if pwd == "password1":
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("❌ Incorrect Password")
    return False

if not check_password(): st.stop()

# 2. Setup AI (Gemini)
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Google API Key missing in Secrets!")

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

ROUTINE = {
    "Monday": {"Focus": "UPPER BODY A", "Exercises": ["Chest Press", "Seated Row", "Shoulder Press", "Lat Pulldown", "Plank"]},
    "Tuesday": {"Focus": "LOWER BODY", "Exercises": ["Leg Press", "Goblet Squat", "Leg Curls", "Lunges", "Calf Raises"]},
    "Wednesday": {"Focus": "ARMS & ABS", "Exercises": ["Tricep Pushdown", "Bicep Curls", "Overhead Tri Ext", "Hammer Curls", "Russian Twists"]},
    "Thursday": {"Focus": "UPPER BODY B", "Exercises": ["Pec Fly", "Rear Delt Fly", "Assisted Pull-Up", "Lateral Raises", "Face Pulls"]},
    "Friday": {"Focus": "FULL BODY GAUNTLET", "Exercises": ["Chest Press", "Leg Press", "Seated Row", "Shoulder Press", "Bicep Curls"]}
}

data = load_data()

# --- SIDEBAR ---
st.sidebar.title("🔥 My Fitness App")
page = st.sidebar.radio("Go to", ["Coach Mode", "📸 AI Calorie Scanner", "Log Weight", "Manual Nutrition", "Progress Graphs"])

# --- PAGE: AI SCANNER ---
if page == "📸 AI Calorie Scanner":
    st.title("📸 Snap & Track")
    st.write("Take a photo of your meal. AI will estimate calories & protein.")
    
    # Camera Input (Works on phones!)
    img_file = st.camera_input("Take a picture")
    
    if img_file:
        st.image(img_file, caption="Your Meal")
        
        if st.button("🤖 Analyze Meal"):
            with st.spinner("AI is analyzing your food..."):
                try:
                    # Send image to Gemini
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # Prepare image data
                    image_parts = [{"mime_type": img_file.type, "data": img_file.getvalue()}]
                    
                    prompt = """
                    You are a nutritionist. Analyze this food image.
                    Estimate the total Calories and Protein (grams).
                    Return ONLY a JSON response like this:
                    {"food_name": "Grilled Chicken & Rice", "calories": 550, "protein": 45}
                    Do not add markdown formatting.
                    """
                    
                    response = model.generate_content([prompt, image_parts[0]])
                    result_text = response.text.strip().replace("```json", "").replace("```", "")
                    ai_data = json.loads(result_text)
                    
                    # Show Result
                    st.success(f"Identified: {ai_data['food_name']}")
                    col1, col2 = st.columns(2)
                    col1.metric("Calories", ai_data['calories'])
                    col2.metric("Protein", f"{ai_data['protein']}g")
                    
                    # Save Button
                    if st.button("Add to Daily Log"):
                        entry = {
                            "date": datetime.now().strftime("%Y-%m-%d"), 
                            "calories": ai_data['calories'], 
                            "protein": ai_data['protein']
                        }
                        data["calories"].append(entry)
                        save_data(data)
                        st.success("Logged successfully!")
                        
                except Exception as e:
                    st.error(f"AI Error: {e}")

# --- PAGE: WORKOUT COACH ---
elif page == "Coach Mode":
    day = datetime.now().strftime("%A")
    st.header(f"Today: {day}")
    if day not in ROUTINE:
        st.info("Rest Day.")
    else:
        plan = ROUTINE[day]
        st.subheader(plan['Focus'])
        with st.form("workout_form"):
            results = {}
            for ex in plan['Exercises']:
                current_pr = data["prs"].get(ex, 0)
                label = f"{ex} (PR: {current_pr} lbs)" if current_pr > 0 else f"{ex} (New)"
                if ex in ["Plank", "Russian Twists"]:
                    results[ex] = st.text_input(label)
                else:
                    results[ex] = st.number_input(label, step=2.5)
            
            if st.form_submit_button("Save Workout"):
                log = {"date": datetime.now().strftime("%Y-%m-%d"), "day": day, "exercises": {}}
                for ex, val in results.items():
                    log["exercises"][ex] = val
                    if isinstance(val, float) and val > data["prs"].get(ex, 0):
                        data["prs"][ex] = val
                data["history"].append(log)
                save_data(data)
                st.success("Saved!")

# --- PAGE: LOG WEIGHT ---
elif page == "Log Weight":
    st.header("Log Weight")
    w = st.number_input("Weight (lbs)", value=230.0, step=0.1)
    if st.button("Save Weight"):
        data["body_weight"].append({"date": datetime.now().strftime("%Y-%m-%d"), "weight": w})
        save_data(data)
        st.success("Saved!")

# --- PAGE: MANUAL NUTRITION ---
elif page == "Manual Nutrition":
    st.header("Manual Log")
    with st.form("food"):
        c = st.number_input("Calories", step=50)
        p = st.number_input("Protein", step=5)
        if st.form_submit_button("Save"):
            data["calories"].append({"date": datetime.now().strftime("%Y-%m-%d"), "calories": c, "protein": p})
            save_data(data)
            st.success("Saved!")

# --- PAGE: GRAPHS ---
elif page == "Progress Graphs":
    st.header("Progress")
    tab1, tab2 = st.tabs(["Weight", "Calories"])
    with tab1:
        if data["body_weight"]: st.line_chart(pd.DataFrame(data["body_weight"]), x="date", y="weight")
    with tab2:
        if data["calories"]: st.bar_chart(pd.DataFrame(data["calories"]), x="date", y="calories")
