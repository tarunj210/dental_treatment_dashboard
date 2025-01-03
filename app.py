import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

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
    st.set_page_config(layout="wide")
    st.title("Dental Dashboard")

    # Load data




    # Sidebar for navigation
    tab1, tab2 = st.tabs(["Executive Summary Dashboard", "Plans that Need Action"])
    # Tab 1: Executive Summary Dashboard


    with tab1:
        st.header("Executive Summary Dashboard")
        treatment_plans, claims, nhs_plans = load_data()
        attribute_counts = treatment_plans['Description'].value_counts()

        private_filtered = treatment_plans[treatment_plans['Payor'] == 'Private']

        private_unique_counts = private_filtered['Description'].value_counts()

        nhs_filtered = treatment_plans[treatment_plans['Payor'] != 'Private']
        nhs_unique_counts = nhs_filtered['Description'].value_counts()

        treatment_plans['PlanProvider'] = treatment_plans['TreatmentProviders'].apply(lambda x: x.split(";")[0])

        def process_date(datestr):
            if datestr == "No Codes Completed":  # Check for "No Codes Completed"
                return ""  # Return empty string
            try:
                # Attempt to parse the date
                return pd.to_datetime(datestr).date()  # Convert to date
            except Exception as e:
                return None  # Handle invalid date strings

        # Apply the function to each value in the column
        treatment_plans['FirstCompletedDate'] = treatment_plans['FirstCompletion'].apply(process_date)
        treatment_plans['LastCompletedDate'] = treatment_plans['LastCompletion'].apply(process_date)

        treatment_plans['HygienePlans'] = treatment_plans['PlanProvider'].apply(
            lambda x: 1 if x in ["MH", "RP", "MK"] else ("" if x == "" else 0))

        treatment_nhs_merged_data = pd.merge(
            treatment_plans,
            nhs_plans,  # Select relevant columns
            on='TreatmentPlanID',
            how='left'  # Retain all rows from TreatmentPlans.csv
        )
        treatment_nhs_merged_data['TotalNHSCodes'] = treatment_nhs_merged_data['TotalNHSCodes'].fillna("")
        treatment_nhs_merged_data['NHSFee'] = treatment_nhs_merged_data['NHSFee'].fillna("")

        treatment_nhs_merged_data['TotalNHSCodes'] = treatment_nhs_merged_data['TotalNHSCodes'].replace("", np.nan)
        treatment_nhs_merged_data['TotalTreatments'] = treatment_nhs_merged_data['TotalTreatments'].replace("", np.nan)

        treatment_nhs_merged_data['TotalNHSCodes'] = treatment_nhs_merged_data['TotalNHSCodes'].astype(float)
        treatment_nhs_merged_data['TotalTreatments'] = treatment_nhs_merged_data['TotalTreatments'].astype(float)

        def checkMixed(PlanProvider, TotalNHSCodes, TotalTreatments):
            if PlanProvider == "":
                return ""
            elif TotalNHSCodes > 0:
                return 1 if TotalNHSCodes < TotalTreatments else 0
            else:
                return 0

        def checkPrivateNHS(PlanProvider, TotalNHSCodes, TotalTreatments):
            if PlanProvider == "":
                return ""
            elif TotalNHSCodes > 0:
                return 1 if TotalNHSCodes == TotalTreatments else 0
            else:
                return 0

        def checkFullPrivateNHS(PlanProvider, TotalNHSCodes, TotalTreatments):
            if PlanProvider == "":
                return ""
            elif pd.isna(TotalNHSCodes):
                return 1
            else:
                return 0

        treatment_nhs_merged_data['isMixed'] = treatment_nhs_merged_data.apply(
            lambda row: checkMixed(row['PlanProvider'], row['TotalNHSCodes'], row['TotalTreatments']), axis=1)

        treatment_nhs_merged_data['isPNHS'] = treatment_nhs_merged_data.apply(
            lambda row: checkPrivateNHS(row['PlanProvider'], row['TotalNHSCodes'], row['TotalTreatments']), axis=1)

        treatment_nhs_merged_data['isFullPrivate'] = treatment_nhs_merged_data.apply(
            lambda row: checkFullPrivateNHS(row['PlanProvider'], row['TotalNHSCodes'], row['TotalTreatments']), axis=1)

        def calculateInProgress(PlanProvider, CompletedTreatments, TotalTreatments):
            if PlanProvider == "":
                return ""

            # Check if S3 equals 0
            if CompletedTreatments == 0:
                return 0

            # Check if S3 is less than R3
            return 1 if CompletedTreatments < TotalTreatments else 0

        def calculateCompleted(PlanProvider, CompletedTreatments, TotalTreatments):
            if PlanProvider == "":
                return ""

            # Check if S3 equals 0
            if CompletedTreatments == 0:
                return 0

            # Check if S3 is less than R3
            return 1 if CompletedTreatments == TotalTreatments else 0

        treatment_nhs_merged_data['inProgress'] = treatment_nhs_merged_data.apply(
            lambda row: calculateInProgress(row['PlanProvider'], row['CompletedTreatments'], row['TotalTreatments']),
            axis=1)
        treatment_nhs_merged_data['Complete'] = treatment_nhs_merged_data.apply(
            lambda row: calculateCompleted(row['PlanProvider'], row['CompletedTreatments'], row['TotalTreatments']),
            axis=1)

        def calculatePendingFee(PlanProvider, TotalFee, CompletedTreatmentFee):
            if PlanProvider == "":
                return ""  # Return an empty string
            return TotalFee - CompletedTreatmentFee

        treatment_nhs_merged_data['PendingFee'] = treatment_nhs_merged_data.apply(
            lambda row: calculatePendingFee(row['PlanProvider'], row['TotalFee'], row['CompletedTreatmentsFee']),
            axis=1)

        def checkIsNHS(isMixed, isPNHS):
            if isPNHS == "":
                return ""
            return isMixed + isPNHS

        treatment_nhs_merged_data['isNHS'] = treatment_nhs_merged_data.apply(
            lambda row: checkIsNHS(row['isMixed'], row['isPNHS']), axis=1)

        claims.rename(columns={'TreatmentPlanId': 'TreatmentPlanID'}, inplace=True)

        treatment_nhs_claims_merged_data = pd.merge(
            treatment_nhs_merged_data,
            claims,  # Select relevant columns
            on='TreatmentPlanID',
            how='left'  # Retain all rows from TreatmentPlans.csv
        )

        st.sidebar.header("Filters")
        account_id = st.sidebar.selectbox("Select Account ID", options=["All"] + treatment_nhs_claims_merged_data[
            "AccountID"].unique().tolist())
        treatment_nhs_claims_merged_data['FirstCompletedDate'] = pd.to_datetime(
            treatment_nhs_claims_merged_data['FirstCompletedDate'], errors='coerce'
        )
        treatment_nhs_claims_merged_data['LastCompletedDate'] = pd.to_datetime(
            treatment_nhs_claims_merged_data['LastCompletedDate'], errors='coerce'
        )

        # Filter out rows with invalid dates (1970 and greater than the current date)
        treatment_nhs_claims_merged_data = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['FirstCompletedDate'].dt.year >= 2007) &
            (treatment_nhs_claims_merged_data['LastCompletedDate'].dt.year >= 2007)
            ]

        # Calculate the min and max dates for the year 2024
        if not treatment_nhs_claims_merged_data.empty:
            min_date = treatment_nhs_claims_merged_data['FirstCompletedDate'].min().date()
            max_date = treatment_nhs_claims_merged_data['LastCompletedDate'].max().date()
        else:
            min_date = None
            max_date = None

        # Add date filters to sidebar
        start_date = st.sidebar.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

        # Apply the filters to the dataset
        treatment_nhs_claims_merged_data = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['FirstCompletedDate'] >= pd.Timestamp(start_date)) &
            (treatment_nhs_claims_merged_data['LastCompletedDate'] <= pd.Timestamp(end_date))
            ]

        if account_id != "All":
            treatment_nhs_claims_merged_data = treatment_nhs_claims_merged_data[
                treatment_nhs_claims_merged_data["AccountID"] == account_id
                ]

        def checkClaimFailed(ClaimStatus):
            if pd.isna(ClaimStatus):
                return ""  # Return an empty string

            # Check if AF3 is "Invalid" or "Failed"
            if ClaimStatus in ["Invalid", "Failed"]:
                return 1  # Return 1 for "Invalid" or "Failed"

            # Default case
            return 0  # Return 0 for all other cases

        treatment_nhs_claims_merged_data['isClaimFailed'] = treatment_nhs_claims_merged_data['ClaimStatus'].apply(
            checkClaimFailed)

        def checkClaimQueued(ClaimStatus):
            if pd.isna(ClaimStatus):
                return ""  # Return an empty string

            # Check if AF3 is "Invalid" or "Failed"
            if ClaimStatus in ["Submitted", "Queued"]:
                return 1  # Return 1 for "Invalid" or "Failed"

            # Default case
            return 0  # Return 0 for all other cases

        treatment_nhs_claims_merged_data['isClaimQueued'] = treatment_nhs_claims_merged_data['ClaimStatus'].apply(
            checkClaimQueued)

        def plansThatRequireAction(PlanProvider, isClaimFailed, isNHS, complete, ClaimStatus):
            if pd.isna(PlanProvider):
                return ""  # Return an empty string

            if isClaimFailed == 1:
                return 1
            if isNHS == 1:
                if complete == 1:
                    return 1 if pd.isna(ClaimStatus) else 0
                return 0
            return 0

        treatment_nhs_claims_merged_data['plansThatRequireAction'] = treatment_nhs_claims_merged_data.apply(
            lambda row: plansThatRequireAction(row['PlanProvider'], row['isClaimFailed'], row['isNHS'], row['Complete'],
                                               row['ClaimStatus']), axis=1)

        print(treatment_nhs_claims_merged_data['plansThatRequireAction'])

        band_to_udas = {
            'Band2': 3,
            'Band1': 1,
            'Band2b': 5,
            'Band3': 12,
            'Band4': 1.2,
            'Band2c': 7
        }

        # Create a new column 'UDAs' by mapping the 'band' attribute
        treatment_nhs_claims_merged_data['UDAs'] = treatment_nhs_claims_merged_data['Band_x'].map(band_to_udas)

        def calculateAction(PlansThatRequireAction, isClaimFailed):
            if pd.isna(PlansThatRequireAction):
                return ""  # Return an empty string

            if PlansThatRequireAction == 0:
                return "No Action"

            if isClaimFailed == 1:
                return "Claim Invalid or Failed"

            # Default case
            return "Claim Not Raised"

        treatment_nhs_claims_merged_data['whatAction'] = treatment_nhs_claims_merged_data.apply(
            lambda row: calculateAction(row['plansThatRequireAction'], row['isClaimFailed']), axis=1)

        unique_providers = treatment_nhs_claims_merged_data['PlanProvider'].unique()

        isFullPrivate = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['isFullPrivate'] == 1) & (
                treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

        isMixedOrNHS = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['isMixed'] == 1) & (
                treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

        isPureNHS = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['isPNHS'] == 1) & (
                treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

        privateNotStarted = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['CompletedTreatments'] == 0) & (
                    treatment_nhs_claims_merged_data['isFullPrivate'] == 1) & (
                    treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

        privateInProgress = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['isFullPrivate'] == 1) & (
                treatment_nhs_claims_merged_data['inProgress'] == 1) & (treatment_nhs_claims_merged_data[
                                                                            'PlanProvider'] != "All Providers")].shape[
            0]

        privateCompleted = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['Complete'] == 1) & (
                treatment_nhs_claims_merged_data['isFullPrivate'] == 1) & (treatment_nhs_claims_merged_data[
                                                                               'PlanProvider'] != "All Providers")].shape[
            0]

        nhsCompleted = treatment_nhs_claims_merged_data[
            ((treatment_nhs_claims_merged_data['isMixed'] == 1) | (treatment_nhs_claims_merged_data['isPNHS'] == 1)) & (
                    treatment_nhs_claims_merged_data['Complete'] == 1)].shape[0]
        nhsInProgress = treatment_nhs_claims_merged_data[
            ((treatment_nhs_claims_merged_data['isMixed'] == 1) | (treatment_nhs_claims_merged_data['isPNHS'] == 1)) & (
                    treatment_nhs_claims_merged_data['inProgress'] == 1)].shape[0]
        nhsNotStarted = treatment_nhs_claims_merged_data[
            ((treatment_nhs_claims_merged_data['isMixed'] == 1) | (treatment_nhs_claims_merged_data['isPNHS'] == 1)) & (
                    treatment_nhs_claims_merged_data['CompletedTreatments'] == 0)].shape[0]
        print(isPureNHS)

        print(isFullPrivate)

        print(isMixedOrNHS)

        print(privateNotStarted)

        print(privateInProgress)

        print(privateCompleted)

        allNHSPlans = isPureNHS + isMixedOrNHS

        print(allNHSPlans)

        print(nhsCompleted)

        print(nhsNotStarted)
        print(nhsInProgress)

        nhsTotalUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDAs'].sum()
        print(nhsTotalUDAs)

        nhsClaimedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
        print(nhsTotalUDAs)

        nhsCompletedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1) & (
                    treatment_nhs_claims_merged_data['Complete'] == 1)]['UDAs'].sum()
        print(nhsCompletedUDAs)

        nhsFailedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1) & (
                    treatment_nhs_claims_merged_data['isClaimFailed'] == 1)]['UDA'].sum()

        print(nhsFailedUDAs)

        nhsClaimsFailureRate = (nhsFailedUDAs / nhsTotalUDAs) * 100

        print(nhsClaimsFailureRate)

        pnhsTotalUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isPNHS'] == 1)]['UDAs'].sum()
        print(pnhsTotalUDAs)

        pnhsClaimedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isPNHS'] == 1)]['UDA'].sum()
        print(pnhsTotalUDAs)

        pnhsCompletedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isPNHS'] == 1) & (
                    treatment_nhs_claims_merged_data['Complete'] == 1)]['UDAs'].sum()
        print(pnhsCompletedUDAs)

        pnhsFailedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isPNHS'] == 1) & (
                    treatment_nhs_claims_merged_data['isClaimFailed'] == 1)]['UDA'].sum()

        print(pnhsFailedUDAs)

        pnhsClaimsFailureRate = (pnhsFailedUDAs / pnhsTotalUDAs) * 100

        print(pnhsClaimsFailureRate)

        mixedTotalUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isMixed'] == 1)]['UDAs'].sum()
        print(mixedTotalUDAs)

        mixedCompletedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isMixed'] == 1) & (
                    treatment_nhs_claims_merged_data['Complete'] == 1)]['UDAs'].sum()
        print(mixedCompletedUDAs)

        mixedClaimedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isMixed'] == 1)]['UDA'].sum()
        print(mixedTotalUDAs)

        mixedFailedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isMixed'] == 1) & (
                    treatment_nhs_claims_merged_data['isClaimFailed'] == 1)]['UDA'].sum()

        print(mixedFailedUDAs)

        mixedClaimsFailureRate = (mixedFailedUDAs / mixedTotalUDAs) * 100

        print(mixedClaimsFailureRate)

        totalUDAs = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")][
            'UDAs'].sum()
        print(totalUDAs)

        completedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['Complete'] == 1)]['UDAs'].sum()
        print(completedUDAs)

        failedUDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (
                    treatment_nhs_claims_merged_data['isClaimFailed'] == 1)]['UDA'].sum()

        print(failedUDAs)

        claimsFailureRate = (failedUDAs / totalUDAs) * 100

        print(claimsFailureRate)

        categories = ['HM', 'GA', 'MJ', 'MM', 'LL', 'RM']

        # Filter the DataFrame to include only the specified categories
        filtered_df = treatment_nhs_claims_merged_data[
            treatment_nhs_claims_merged_data['PlanProvider'].isin(categories)]

        # Group by PlanProvider and calculate the total UDA
        uda_totals = filtered_df.groupby('PlanProvider')['UDA'].sum().reset_index()

        # Rename columns for clarity
        uda_totals.columns = ['PlanProvider', 'TotalUDA']

        # Display the results
        print(uda_totals)

        hm_uda_completed = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "HM") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UDAs'].sum()

        hm_uda_successful = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "HM") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UdaConfirmed'].sum()
        hm_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "HM") & (
                treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data[
                                                                       'isClaimFailed'] == 1)]['UDA'].sum()

        hm_claimed_UDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] == "HM") & (
                        treatment_nhs_claims_merged_data['Complete'] == 1) & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
        print(mixedTotalUDAs)
        print(hm_uda_successful)
        print(hm_uda_completed)
        print(hm_uda_failed)
        hm_uda_failure_rate = (hm_uda_failed / hm_uda_completed) * 100
        print(hm_uda_failure_rate)

        ga_uda_completed = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "GA") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UDAs'].sum()

        ga_uda_successful = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "GA") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UdaConfirmed'].sum()
        ga_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "GA") & (
                treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data[
                                                                       'isClaimFailed'] == 1)]['UDA'].sum()

        ga_claimed_UDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] == "GA") & (
                    treatment_nhs_claims_merged_data['Complete'] == 1) & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()

        ga_uda_failure_rate = (ga_uda_failed / ga_uda_completed) * 100
        print(ga_uda_successful)
        print(ga_uda_completed)
        print(ga_uda_failed)
        print(ga_uda_failure_rate)

        mj_uda_completed = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MJ") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UDAs'].sum()
        mj_uda_successful = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MJ") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UdaConfirmed'].sum()
        mj_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MJ") & (
                treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data[
                                                                       'isClaimFailed'] == 1)]['UDA'].sum()
        mj_uda_failure_rate = (mj_uda_failed / mj_uda_completed) * 100

        mj_claimed_UDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] == "MJ") & (
                    treatment_nhs_claims_merged_data['Complete'] == 1) & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
        print(mj_uda_successful)
        print(mj_uda_completed)
        print(mj_uda_failed)
        print(mj_uda_failure_rate)

        mm_uda_completed = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MM") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UDAs'].sum()
        mm_uda_successful = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MM") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UdaConfirmed'].sum()
        mm_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MM") & (
                treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data[
                                                                       'isClaimFailed'] == 1)]['UDA'].sum()

        mm_claimed_UDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] == "MM") & (
                    treatment_nhs_claims_merged_data['Complete'] == 1) & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
        mm_uda_failure_rate = (mm_uda_failed / mm_uda_completed) * 100
        print(mm_uda_successful)
        print(mm_uda_completed)
        print(mm_uda_failed)
        print(mm_uda_failure_rate)

        ll_uda_completed = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "LL") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UDAs'].sum()
        ll_uda_successful = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "LL") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UdaConfirmed'].sum()
        ll_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "LL") & (
                treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data[
                                                                       'isClaimFailed'] == 1)]['UDA'].sum()

        ll_claimed_UDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] == "LL") & (
                    treatment_nhs_claims_merged_data['Complete'] == 1) & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
        ll_uda_failure_rate = (ll_uda_failed / ll_uda_completed) * 100
        print(ll_uda_successful)
        print(ll_uda_completed)
        print(ll_uda_failed)
        print(ll_uda_failure_rate)

        rm_uda_completed = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "RM") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UDAs'].sum()
        rm_uda_successful = \
        treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "RM") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UdaConfirmed'].sum()
        rm_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "RM") & (
                treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data[
                                                                       'isClaimFailed'] == 1)]['UDA'].sum()

        rm_claimed_UDAs = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['PlanProvider'] == "RM") & (
                    treatment_nhs_claims_merged_data['Complete'] == 1) & (
                    treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
        rm_uda_failure_rate = (rm_uda_failed / rm_uda_completed) * 100
        print(rm_uda_successful)
        print(rm_uda_completed)
        print(rm_uda_failed)
        print(rm_uda_failure_rate)

        total_uda = hm_uda_completed + rm_uda_completed + ll_uda_completed + mm_uda_completed + mj_uda_completed + ga_uda_completed

        print(total_uda)

        total_uda_failed = hm_uda_failed + rm_uda_failed + ll_uda_failed + mm_uda_failed + mj_uda_failed + ga_uda_failed
        print(total_uda_failed)

        uda_failure_rate = (total_uda_failed / total_uda) * 100

        print(uda_failure_rate)

        isPNHSAwaitingResponse = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['isClaimQueued'] == 1) &
            (treatment_nhs_claims_merged_data['Complete'] == 1) &
            (treatment_nhs_claims_merged_data['isPNHS'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")
            ]['UDA'].sum()

        hm_awaiting_response = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['isClaimQueued'] == 1) &
            (treatment_nhs_claims_merged_data['Complete'] == 1) &
            (treatment_nhs_claims_merged_data['isNHS'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] == "HM")
            ]['UDA'].sum()

        ga_awaiting_response = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['isClaimQueued'] == 1) &
            (treatment_nhs_claims_merged_data['Complete'] == 1) &
            (treatment_nhs_claims_merged_data['isNHS'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] == "GA")
            ]['UDA'].sum()

        mm_awaiting_response = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['isClaimQueued'] == 1) &
            (treatment_nhs_claims_merged_data['Complete'] == 1) &
            (treatment_nhs_claims_merged_data['isNHS'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] == "MM")
            ]['UDA'].sum()

        mj_awaiting_response = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['isClaimQueued'] == 1) &
            (treatment_nhs_claims_merged_data['Complete'] == 1) &
            (treatment_nhs_claims_merged_data['isNHS'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] == "MJ")
            ]['UDA'].sum()
        rm_awaiting_response = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['isClaimQueued'] == 1) &
            (treatment_nhs_claims_merged_data['Complete'] == 1) &
            (treatment_nhs_claims_merged_data['isNHS'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] == "RM")
            ]['UDA'].sum()

        ll_awaiting_response = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['isClaimQueued'] == 1) &
            (treatment_nhs_claims_merged_data['Complete'] == 1) &
            (treatment_nhs_claims_merged_data['isNHS'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] == "LL")
            ]['UDA'].sum()

        print(isPNHSAwaitingResponse)

        isMixedAwaitingResponse = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['isClaimQueued'] == 1) &
            (treatment_nhs_claims_merged_data['Complete'] == 1) &
            (treatment_nhs_claims_merged_data['isMixed'] == 1) & (
                    treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")
            ]['UDA'].sum()

        print(isMixedAwaitingResponse)

        allNHSAwaitingResponse = isMixedAwaitingResponse + isPNHSAwaitingResponse

        isPNHSUDASuccessful = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isPNHS'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")]['UdaConfirmed'].sum()

        isMixedUdaSuccessful = treatment_nhs_claims_merged_data[
            (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isMixed'] == 1) & (
                        treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")]['UdaConfirmed'].sum()

        allNHSUdaSuccessful = isMixedUdaSuccessful + isPNHSUDASuccessful
        # Summary of provider performance
        counts = {
            "Private Plans": {
                "Active Plans": isFullPrivate,
                "Not Yet Started": privateNotStarted,
                "In Progress": privateInProgress,
                "Completed": privateCompleted,
            },
            "NHS or Mixed Plans": {
                "Active Plans": allNHSPlans,
                "Not Yet Started": nhsNotStarted,
                "In Progress": nhsInProgress,
                "Completed": nhsCompleted,
            }
        }

        udaCounts = {
            "UDA Breakdown": {
                "Completed Plan UDAs": nhsCompletedUDAs,
                "Yet To Claim UDAs": abs(nhsCompletedUDAs - nhsClaimedUDAs),
                "UDAs Claimed": nhsClaimedUDAs,
                "UDAs Awaiting Response ": allNHSAwaitingResponse,
                "UDAs Successful": allNHSUdaSuccessful,
                "UDAs Failed": nhsFailedUDAs,
                "UDAs Failure Rate": (nhsFailedUDAs / (nhsFailedUDAs + allNHSUdaSuccessful)) * 100
            }
        }

        # Streamlit app
        st.title("Plans Summary")

        # Enhanced UI with styled layout
        for row_name, statuses in counts.items():
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"<h2 style='color:#ff4b4b;'>{row_name}</h2>", unsafe_allow_html=True)
                for status, count in statuses.items():
                    st.markdown(f"<p style='font-size:18px; margin-left:20px;'>{status}: <strong>{count}</strong></p>",
                                unsafe_allow_html=True)

            with col2:
                # Filter pie chart data for relevant statuses
                pie_chart_data = pd.DataFrame({
                    "Status": [key for key in statuses.keys() if
                               key in ["Not Yet Started", "In Progress", "Completed"]],
                    "Count": [value for key, value in statuses.items() if
                              key in ["Not Yet Started", "In Progress", "Completed"]]
                })
                if not pie_chart_data.empty:
                    fig = px.pie(pie_chart_data, names="Status", values="Count", title=f"{row_name} Distribution")
                    st.plotly_chart(fig, use_container_width=True)

        for row_name, statuses in udaCounts.items():
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"<h2 style='color:#ff4b4b;'>{row_name}</h2>", unsafe_allow_html=True)
                for status, count in statuses.items():
                    st.markdown(f"<p style='font-size:18px; margin-left:20px;'>{status}: <strong>{count}</strong></p>",
                                unsafe_allow_html=True)

            with col2:
                # Filter pie chart data for relevant statuses
                pie_chart_data = pd.DataFrame({
                    "Status": [key for key in statuses.keys() if
                               key in ["Yet To Claim UDAs", "UDAs Claimed"]],
                    "Count": [value for key, value in statuses.items() if
                              key in ["Yet To Claim UDAs", "UDAs Claimed"]]
                })
                if not pie_chart_data.empty:
                    fig = px.pie(pie_chart_data, names="Status", values="Count", title=f"{row_name} Distribution")
                    st.plotly_chart(fig, use_container_width=True)

        planProviderUDAs = {
            "Plan Providers": ["HM", "GA", "MJ", "MM", "LL", "RM", "Total"],
            "Completed UDAs": [hm_uda_completed, ga_uda_completed, mj_uda_completed, mm_uda_completed, ll_uda_completed, rm_uda_completed, hm_uda_completed + ga_uda_completed + mj_uda_completed + mm_uda_completed + ll_uda_completed + rm_uda_completed],
            "UDAs Claimed": [hm_claimed_UDAs, ga_claimed_UDAs, mj_claimed_UDAs, mm_claimed_UDAs, ll_claimed_UDAs, rm_claimed_UDAs, hm_claimed_UDAs + ga_claimed_UDAs+mj_claimed_UDAs + mm_claimed_UDAs + ll_claimed_UDAs + rm_claimed_UDAs],
            "Yet to Claim": [abs(hm_uda_completed - hm_claimed_UDAs), abs(ga_uda_completed - ga_claimed_UDAs), abs(mj_uda_completed - mj_claimed_UDAs), abs(mm_uda_completed - mm_claimed_UDAs), abs(ll_uda_completed - ll_claimed_UDAs), abs(rm_uda_completed - rm_claimed_UDAs), (hm_uda_completed - hm_claimed_UDAs) + (ga_uda_completed - ga_claimed_UDAs) + (mj_uda_completed - mj_claimed_UDAs) + (mm_uda_completed - mm_claimed_UDAs)+(ll_uda_completed - ll_claimed_UDAs) + (rm_uda_completed - rm_claimed_UDAs)],
            "UDAs Successful": [hm_uda_successful, ga_uda_successful, mj_uda_successful, mm_uda_successful, ll_uda_successful, rm_uda_successful, hm_uda_successful + ga_uda_successful + mj_uda_successful + mm_uda_successful + ll_uda_successful+rm_uda_successful],
            "UDAs Awaiting Response": [hm_awaiting_response, ga_awaiting_response, mj_awaiting_response, mm_awaiting_response, ll_awaiting_response, rm_awaiting_response, hm_awaiting_response + ga_awaiting_response + mj_awaiting_response + mm_awaiting_response+ll_awaiting_response + rm_awaiting_response],
            "UDAs Failed": [hm_uda_failed, ga_uda_failed, mj_uda_failed, mm_uda_failed, ll_uda_failed, rm_uda_failed, hm_uda_failed + ga_uda_failed + mj_uda_failed + mm_uda_failed + ll_uda_failed + rm_uda_failed],
        }
        planProviderDF = pd.DataFrame(planProviderUDAs)

        # Display the table in the Streamlit app
        st.subheader("Detailed UDA Breakdown")
        st.table(planProviderDF)
        line_chart_data = pd.DataFrame({
            "Plan Providers": ["HM", "GA", "MJ", "MM", "LL", "RM"],
            "UDAs Claimed": [hm_claimed_UDAs, ga_claimed_UDAs, mj_claimed_UDAs, mm_claimed_UDAs, ll_claimed_UDAs,
                             rm_claimed_UDAs]
        })

        # Create the line chart
        fig = px.line(
            line_chart_data,
            x="Plan Providers",
            y="UDAs Claimed",
            title="UDAs Claimed by Plan Providers",
            labels={"Plan Providers": "Plan Providers", "UDAs Claimed": "UDAs Claimed"}
        )

        # Display the line chart
        st.plotly_chart(fig, use_container_width=True)

        stacked_bar_data = pd.DataFrame({
            "Plan Providers": ["HM", "GA", "MJ", "MM", "LL", "RM"],
            "UDAs Successful": [hm_uda_successful, ga_uda_successful, mj_uda_successful, mm_uda_successful,
                                ll_uda_successful, rm_uda_successful],
            "UDAs Failed": [hm_uda_failed, ga_uda_failed, mj_uda_failed, mm_uda_failed, ll_uda_failed, rm_uda_failed]
        })

        # Melt the DataFrame for stacked bar plot
        stacked_bar_data_melted = stacked_bar_data.melt(id_vars="Plan Providers",
                                                        value_vars=["UDAs Successful", "UDAs Failed"],
                                                        var_name="UDA Type",
                                                        value_name="Count")

        # Create the stacked bar chart
        fig = px.bar(
            stacked_bar_data_melted,
            x="Plan Providers",
            y="Count",
            color="UDA Type",
            title="UDAs Successful vs UDAs Failed by Plan Providers",
            labels={"Count": "Number of UDAs", "Plan Providers": "Plan Providers"},
            barmode="stack"
        )

        # Display the chart
        st.plotly_chart(fig, use_container_width=True)

    # Tab 2: Plans that Need Action
    with tab2:
        st.header("Plans that Need Action")

# Run the app
if __name__ == "__main__":
    main()



