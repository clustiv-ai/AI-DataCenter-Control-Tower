import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
import requests
import smtplib
from email.mime.text import MIMEText
from sklearn.ensemble import RandomForestRegressor, IsolationForest
#Hiding built with streamlit Footer
st.markdown("""
    <style>
    footer, .stApp footer {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# 👇 Your app starts here
#st.title("My App")
#st.write("Content goes here...")

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(layout="wide")
REFRESH_RATE = 5

TEAMS_WEBHOOK_URL = "https://your-teams-webhook-url"
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_RECEIVER = "your_email@gmail.com"
EMAIL_APP_PASSWORD = "your_app_password"

CO2_FACTOR = 0.4  # kg CO2 per kWh

# ----------------------------
# ALERT FUNCTIONS
# ----------------------------
def send_teams_alert(message):
    try:
        if "your-teams-webhook-url" not in TEAMS_WEBHOOK_URL:
            requests.post(TEAMS_WEBHOOK_URL, json={"text": message})
    except:
        pass

def send_email_alert(subject, message):
    try:
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        st.warning(f"Email error: {e}")

def trigger_alert(subject, message):
    send_teams_alert(message)
    send_email_alert(subject, message)

# ----------------------------
# ROLE
# ----------------------------
role = st.sidebar.selectbox("Select View", ["Executive", "Operator"])

# ----------------------------
# DATA GENERATION
# ----------------------------
@st.cache_data
def generate_data(n=1000):
    np.random.seed(42)
    time_index = pd.date_range(start='2026-04-07', periods=n, freq='h')

    df = pd.DataFrame({
        'Timestamp': time_index,
        'Server_Load_%': np.random.uniform(20, 100, n),
        'Ambient_Temperature_C': np.random.uniform(18, 35, n),
        'Cooling_Efficiency_%': np.random.uniform(70, 100, n)
    })

    df['Load_Per_Cooling'] = df['Server_Load_%'] / df['Cooling_Efficiency_%']
    df['Temp_Load_Interaction'] = df['Ambient_Temperature_C'] * df['Server_Load_%']

    df['Energy_kWh'] = 50 + 0.8*df['Server_Load_%'] \
        + 0.5*(df['Ambient_Temperature_C']-20) \
        - 0.4*df['Cooling_Efficiency_%'] \
        + np.random.normal(0,5,n)

    return df

df = generate_data()

# ----------------------------
# MODEL
# ----------------------------
features = ['Server_Load_%','Ambient_Temperature_C','Cooling_Efficiency_%',
            'Load_Per_Cooling','Temp_Load_Interaction']

rf_model = RandomForestRegressor(n_estimators=200, random_state=42)
rf_model.fit(df[features], df['Energy_kWh'])

# ----------------------------
# ANOMALY DETECTION
# ----------------------------
iso = IsolationForest(contamination=0.05, random_state=42)
df['Anomaly'] = iso.fit_predict(df[features])

# ----------------------------
# DIGITAL TWIN
# ----------------------------
st.sidebar.header("🔧 Simulation Controls")

sim_load = st.sidebar.slider("Server Load (%)", 20, 100, 60)
sim_cooling = st.sidebar.slider("Cooling Efficiency (%)", 70, 100, 85)

latest_temp = df['Ambient_Temperature_C'].iloc[-1]

sim_data = pd.DataFrame({
    'Server_Load_%':[sim_load],
    'Ambient_Temperature_C':[latest_temp],
    'Cooling_Efficiency_%':[sim_cooling]
})

sim_data['Load_Per_Cooling'] = sim_data['Server_Load_%'] / sim_data['Cooling_Efficiency_%']
sim_data['Temp_Load_Interaction'] = sim_data['Ambient_Temperature_C'] * sim_data['Server_Load_%']

energy_pred = rf_model.predict(sim_data[features])[0]

# ----------------------------
# COST + CARBON
# ----------------------------
cost = energy_pred * 0.25
carbon_emission = energy_pred * CO2_FACTOR
df['CO2_kg'] = df['Energy_kWh'] * CO2_FACTOR

# ----------------------------
# RISK ENGINE
# ----------------------------
risk_level = "LOW"
failure_risk = "LOW"
alerts = []
actions = []

if energy_pred > 110:
    risk_level = "HIGH"
    alerts.append("🔥 Critical energy spike")
    actions.append("Initiate load shedding")

elif energy_pred > 95:
    risk_level = "MEDIUM"
    alerts.append("⚠️ Elevated energy usage")
    actions.append("Optimize workloads")

if sim_load > 90:
    alerts.append("🚨 Server overload")
    actions.append("Auto-scale systems")

if latest_temp > 30:
    alerts.append("🌡️ High temperature risk")
    actions.append("Increase cooling")

if sim_cooling < 75:
    alerts.append("❄️ Cooling inefficiency")
    actions.append("Maintenance required")

if sim_cooling < 75 and latest_temp > 30:
    failure_risk = "HIGH"
    alerts.append("💥 Cooling failure risk")
    actions.append("Trigger disaster recovery")

# ----------------------------
# ALERT TRIGGERS
# ----------------------------
if risk_level == "HIGH":
    trigger_alert("HIGH RISK ALERT", f"Energy spike: {energy_pred:.2f} kWh")

if failure_risk == "HIGH":
    trigger_alert("FAILURE ALERT", "Cooling failure risk detected")

if carbon_emission > 50:
    trigger_alert("CARBON ALERT", f"CO2 high: {carbon_emission:.2f} kg")

# ----------------------------
# UI
# ----------------------------
st.title("🚀 AI Data Center Control Tower")

# KPIs
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("⚡ Energy", f"{energy_pred:.2f} kWh")
col2.metric("💰 Cost", f"€{cost:.2f}")
col3.metric("⚠️ Risk", risk_level)
col4.metric("🛠 Failure", failure_risk)
col5.metric("🌱 CO₂", f"{carbon_emission:.2f} kg")

# Executive Insights
if role == "Executive":
    trend = "increasing" if df['Energy_kWh'].iloc[-1] > df['Energy_kWh'].iloc[-5] else "stable"
    anomaly_count = (df['Anomaly'] == -1).sum()

    st.info(f"""
    - Energy trend: **{trend}**
    - Anomalies: **{anomaly_count}**
    - Cost: **€{cost:.2f}**
    - CO₂: **{carbon_emission:.2f} kg**
    - Recommendation: Optimize load & cooling
    """)

# Alerts
st.subheader("🚨 Alerts")
for a in alerts:
    st.write(f"- {a}")

st.subheader("✅ Actions")
for act in actions:
    st.write(f"- {act}")

# ----------------------------
# FORECAST (RF-based)
# ----------------------------
future = []
last = df.tail(1).copy()

for i in range(24):
    new = last.copy()
    new['Timestamp'] += pd.Timedelta(hours=i+1)
    new['Energy_kWh'] = rf_model.predict(new[features])
    future.append(new)

future_df = pd.concat(future)
combined = pd.concat([df, future_df])

fig1 = px.line(combined, x='Timestamp', y='Energy_kWh',
               title="Energy Forecast (Next 24h)")
st.plotly_chart(fig1, use_container_width=True)

# Carbon trend
fig2 = px.line(df, x='Timestamp', y='CO2_kg',
               title="Carbon Emissions Over Time")
st.plotly_chart(fig2, use_container_width=True)

# Anomaly
fig3 = px.scatter(df, x='Timestamp', y='Energy_kWh',
                  color=df['Anomaly'].map({1:'Normal', -1:'Anomaly'}),
                  title="Anomaly Detection")
st.plotly_chart(fig3, use_container_width=True)

# Distributions
st.subheader("📊 Distributions")
c1, c2, c3 = st.columns(3)
c1.plotly_chart(px.histogram(df, x='Server_Load_%'))
c2.plotly_chart(px.histogram(df, x='Ambient_Temperature_C'))
c3.plotly_chart(px.histogram(df, x='Cooling_Efficiency_%'))

# Download
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Data", csv, "data.csv")

# Manual Alert
if st.button("📧 Send Test Alert"):
    trigger_alert("Test Alert", "System working")
    st.success("Alert sent!")

# Refresh
time.sleep(REFRESH_RATE)
st.rerun()
