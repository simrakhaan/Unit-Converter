import json
import streamlit as st
import pandas as pd
import requests
import datetime
import altair as alt
from collections import defaultdict

# Set page config
st.set_page_config(page_title="Advanced Unit Converter", layout="wide")

# Function to get supported units
def get_supported_units(category):
    categories = {
        "Length": ["Meter", "Kilometer", "Centimeter", "Mile"],
        "Weight": ["Kilogram", "Gram", "Pound", "Ounce"],
        "Temperature": ["Celsius", "Fahrenheit"],
        "Speed": ["m/s", "km/h", "mph"],
        "Currency": ["USD", "EUR", "GBP", "INR", "PKR"]
    }
    return categories.get(category, [])

# Load conversion history
def load_history():
    try:
        with open("history.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Save conversion history
def save_history(conversion):
    history = load_history()
    history.append(conversion)
    with open("history.json", "w") as f:
        json.dump(history, f)

# Clear conversion history
def clear_history():
    with open("history.json", "w") as f:
        json.dump([], f)

# Multi-step conversion
def multi_step_conversion(category, from_unit, to_unit, value):
    factors = {
        "Length": {"Meter": 1, "Kilometer": 1000, "Centimeter": 0.01, "Mile": 1609.34},
        "Weight": {"Kilogram": 1, "Gram": 0.001, "Pound": 0.453592, "Ounce": 0.0283495},
        "Speed": {"m/s": 1, "km/h": 3.6, "mph": 2.237}
    }
    if category in factors:
        return round((value * factors[category][from_unit]) / factors[category][to_unit], 4)
    elif category == "Temperature":
        if from_unit == "Celsius" and to_unit == "Fahrenheit":
            return round((value * 9/5) + 32, 2)
        elif from_unit == "Fahrenheit" and to_unit == "Celsius":
            return round((value - 32) * 5/9, 2)
    return None

# Fetch & Store Currency Rates
def update_currency_rates():
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    response = requests.get(url).json()
    with open("currency_rates.json", "w") as f:
        json.dump(response["rates"], f)
    return response["rates"]

# Convert currency with offline caching
def convert_currency(amount, from_currency, to_currency):
    try:
        with open("currency_rates.json", "r") as f:
            offline_rates = json.load(f)
        if from_currency in offline_rates and to_currency in offline_rates:
            return round(amount * offline_rates[to_currency] / offline_rates[from_currency], 2)
    except FileNotFoundError:
        offline_rates = update_currency_rates()

    if from_currency in offline_rates and to_currency in offline_rates:
        return round(amount * offline_rates[to_currency] / offline_rates[from_currency], 2)
    return f"❌ Conversion not available for {from_currency} to {to_currency}"

# UI Design
st.title("🔄 Advanced Unit Converter")

# Dark Mode Toggle
dark_mode = st.checkbox("🌙 Enable Dark Mode")
if dark_mode:
    st.markdown(
        "<style>body {background-color: #222; color: white;} .stButton>button {background-color: #444; color: white;}</style>",
        unsafe_allow_html=True,
    )

# Main Conversion
group = st.selectbox("Select Category", ["Length", "Weight", "Temperature", "Speed", "Currency"])
units = get_supported_units(group)
from_unit = st.selectbox("From Unit", units)
to_unit = st.selectbox("To Unit", units)
values = st.text_input("Enter Values (comma-separated for batch conversion)")

# Reverse Conversion
if st.button("🔄 Reverse Conversion"):
    from_unit, to_unit = to_unit, from_unit

if st.button("Convert"):
    if "," in values:
        values_list = [float(v.strip()) for v in values.split(",")]
        results = [(v, multi_step_conversion(group, from_unit, to_unit, v) if group != "Currency" else convert_currency(v, from_unit, to_unit)) for v in values_list]
        for v, r in results:
            st.success(f"{v} {from_unit} = {r} {to_unit}")
            save_history([v, from_unit, to_unit, r])
    else:
        value = float(values)
        result = multi_step_conversion(group, from_unit, to_unit, value) if group != "Currency" else convert_currency(value, from_unit, to_unit)
        if result is not None:
            st.success(f"{value} {from_unit} = {result} {to_unit}")
            save_history([value, from_unit, to_unit, result])
        else:
            st.error("❌ Invalid conversion.")

# Display Conversion History
st.subheader("📜 Conversion History")
history = load_history()
if history:
    history_df = pd.DataFrame(history, columns=["Value", "From", "To", "Result"])
    st.dataframe(history_df)
    if st.button("🗑️ Clear All History"):
        clear_history()
        st.rerun()
else:
    st.write("No history available.")

# Download Options
if history:
    st.download_button("⬇️ Download History (CSV)", history_df.to_csv(index=False), file_name="history.csv", mime="text/csv")
    st.download_button("⬇️ Download History (JSON)", json.dumps(history, indent=4), file_name="history.json", mime="application/json")

# Visualization of Conversions
st.subheader("📊 Conversion Summary")

# ✅ FIXED: Count conversions dynamically
category_counts = defaultdict(int)
categories = ["Length", "Weight", "Temperature", "Speed", "Currency"]

for record in history:
    from_unit = record[1]
    for category in categories:
        if from_unit in get_supported_units(category):
            category_counts[category] += 1
            break  # Stop checking after finding the correct category

conversion_data = pd.DataFrame({
    "Category": list(category_counts.keys()),
    "Conversions": list(category_counts.values())
})

chart = alt.Chart(conversion_data).mark_bar().encode(
    x=alt.X("Category", sort="-y"),
    y="Conversions",
    color="Category",
    tooltip=["Category", "Conversions"]
).properties(
    width=600,
    height=300
)

st.altair_chart(chart, use_container_width=True)

# Unit Information Section
def unit_info(unit):
    info = {
        "Meter": "Basic unit of length in the metric system.",
        "Kilogram": "Standard unit of mass in the metric system.",
        "Celsius": "Temperature scale used worldwide.",
        "USD": "United States Dollar, the global reserve currency."
    }
    return info.get(unit, "ℹ️ No additional information available.")

st.subheader("ℹ️ Unit Information")
st.write(f"**{from_unit}**: {unit_info(from_unit)}")