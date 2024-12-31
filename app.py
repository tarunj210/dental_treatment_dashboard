import streamlit as st
import pandas as pd
import plotly.express as px

# Load CSV files
def load_data():
    treatment_plans = pd.read_csv("data/TreatmentPlans Data.csv")
    claims = pd.read_csv("data/Claims Data.csv")
    nhs_plans = pd.read_csv("data/NHS Plans Data.csv")
    return treatment_plans, claims, nhs_plans

# Save updated DataFrame back to CSV
def save_data(df, file_path):
    df.to_csv(file_path, index=False)

# Main Streamlit app
def main():
    st.title("Dental Dashboard")

    # Load data
    treatment_plans, claims, nhs_plans = load_data()

    # Sidebar for navigation
    tab1, tab2 = st.tabs(["Executive Summary Dashboard", "Plans that Need Action"])

    # Tab 1: Executive Summary Dashboard
    with tab1:
        st.header("Executive Summary Dashboard")

        # Summary of provider performance
        st.subheader("NHS Plans Data")
        st.dataframe(nhs_plans)

    # Tab 2: Plans that Need Action
    with tab2:
        st.header("Plans that Need Action")

# Run the app
if __name__ == "__main__":
    main()



