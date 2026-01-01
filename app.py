import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd

# --- PASSWORD PROTECTION ---
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # 1. If password is already correct, return True
    if st.session_state.get("password_correct", False):
        return True

    # 2. Show input for password
    st.header("🔒 Login Required")
    pwd = st.text_input("Enter Password", type="password")
    
    if st.button("Log In"):
        # REPLACE "gym2025" WITH YOUR DESIRED PASSWORD
        if pwd == "Tinted1!":
            st.session_state["password_correct"] = True
            st.rerun()  # Reloads the app to show the content
        else:
            st.error("❌ Incorrect Password")
            
    return False

# Stop the app here if password is wrong
if not check_password():
    st.stop()

# --- YOUR APP STARTS HERE ---
# (Paste the rest of your original code below this line)
import json
import os
# ... etc ...

# --- CONFIGURATION ---
DATA_FILE = "fitness_data.json"
st.set_page_config(page_title="Fitness Coach", page_icon="💪")

# --- DATA HANDLING ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Ensure keys exist
            for key in ["history", "prs", "body_weight", "calories"]:
                if key not in data: data[key] = [] if key != "prs" else {}
            return data
    return {"history": [], "prs": {}, "body_weight": [], "calories": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- ROUTINE DEFINITION ---
ROUTINE = {
    "Monday": {"Focus": "UPPER BODY A (Push/Pull)", "Exercises": ["Chest Press", "Seated Row", "Shoulder Press", "Lat Pulldown", "Plank"]},
    "Tuesday": {"Focus": "LOWER BODY (Legs)", "Exercises": ["Leg Press", "Goblet Squat", "Leg Curls", "Lunges", "Calf Raises"]},
    "Wednesday": {"Focus": "ARMS & ABS", "Exercises": ["Tricep Pushdown", "Bicep Curls", "Overhead Tri Ext", "Hammer Curls", "Russian Twists"]},
    "Thursday": {"Focus": "UPPER BODY B (Isolation)", "Exercises": ["Pec Fly", "Rear Delt Fly", "Assisted Pull-Up", "Lateral Raises", "Face Pulls"]},
    "Friday": {"Focus": "FULL BODY GAUNTLET", "Exercises": ["Chest Press", "Leg Press", "Seated Row", "Shoulder Press", "Bicep Curls"]}
}

data = load_data()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("🔥 My Fitness App")
page = st.sidebar.radio("Go to", ["Coach Mode (Workout)", "Log Weight", "Nutrition Tracker", "Progress Graphs"])

# --- PAGE 1: WORKOUT COACH ---
if page == "Coach Mode (Workout)":
    day = datetime.now().strftime("%A")
    st.title(f"Today is {day}")
    
    if day not in ROUTINE:
        st.info("Today is a Rest Day. Go for a walk or recover! 🧘")
    else:
        plan = ROUTINE[day]
        st.header(f"Focus: {plan['Focus']}")
        
        with st.form("workout_form"):
            results = {}
            for exercise in plan['Exercises']:
                st.subheader(exercise)
                
                # Coach Logic
                current_pr = data["prs"].get(exercise, 0)
                if current_pr > 0:
                    target = int(current_pr * 1.05)
                    st.caption(f"🏆 Current PR: {current_pr} lbs | 🎯 **Coach Goal: {target} lbs**")
                else:
                    st.caption("🆕 New Exercise! Start moderate.")
                
                # Input
                if exercise in ["Plank", "Russian Twists"]:
                    val = st.text_input(f"Log {exercise} (Time/Reps)", key=exercise)
                    results[exercise] = val
                else:
                    val = st.number_input(f"Weight Lifted (lbs)", min_value=0.0, step=2.5, key=exercise)
                    results[exercise] = val
            
            submitted = st.form_submit_button("✅ Finish Workout")
            
            if submitted:
                # Save Logic
                log_entry = {"date": datetime.now().strftime("%Y-%m-%d"), "day": day, "exercises": {}}
                new_prs = []
                
                for ex, val in results.items():
                    log_entry["exercises"][ex] = val
                    # Check PR (only if it's a number/weight)
                    if isinstance(val, float) and val > data["prs"].get(ex, 0):
                        data["prs"][ex] = val
                        new_prs.append(f"{ex} ({val} lbs)")
                
                data["history"].append(log_entry)
                save_data(data)
                
                st.success("Workout Saved!")
                if new_prs:
                    st.balloons()
                    st.write(f"🎉 **NEW PRs SET:** {', '.join(new_prs)}")

# --- PAGE 2: LOG WEIGHT ---
elif page == "Log Weight":
    st.title("⚖️ Body Weight Tracker")
    with st.form("weight_form"):
        w = st.number_input("Current Weight (lbs)", min_value=100.0, value=230.0)
        submit = st.form_submit_button("Log Weight")
        
        if submit:
            data["body_weight"].append({"date": datetime.now().strftime("%Y-%m-%d"), "weight": w})
            save_data(data)
            st.success("Weight Logged!")

# --- PAGE 3: NUTRITION ---
elif page == "Nutrition Tracker":
    st.title("🥗 Nutrition Log")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Calorie Goal", "2300")
    with col2:
        st.metric("Protein Goal", "180g")
        
    with st.form("food_form"):
        cals = st.number_input("Calories Eaten", step=50)
        prot = st.number_input("Protein Eaten (g)", step=5)
        submit = st.form_submit_button("Log Food")
        
        if submit:
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "calories": cals, "protein": prot}
            data["calories"].append(entry)
            save_data(data)
            
            # Feedback
            diff_cals = cals - 2300
            diff_prot = prot - 180
            
            if diff_cals > 0: st.warning(f"⚠️ {diff_cals} Calories over limit.")
            else: st.success(f"✅ {abs(diff_cals)} Calories remaining!")
            
            if diff_prot >= 0: st.success(f"🔥 Protein Goal Hit! (+{diff_prot}g)")
            else: st.error(f"🥩 Missing {abs(diff_prot)}g of protein.")

# --- PAGE 4: GRAPHS ---
elif page == "Progress Graphs":
    st.title("📈 Progress Dashboard")
    
    tab1, tab2 = st.tabs(["Body Weight", "Calories"])
    
    with tab1:
        if data["body_weight"]:
            df_w = pd.DataFrame(data["body_weight"])
            st.line_chart(df_w, x="date", y="weight")
            st.write(f"Current Weight: **{data['body_weight'][-1]['weight']} lbs**")
        else:
            st.info("No weight data yet.")
            
    with tab2:
        if data["calories"]:
            df_c = pd.DataFrame(data["calories"])
            st.bar_chart(df_c, x="date", y="calories")
        else:
            st.info("No nutrition data yet.")
