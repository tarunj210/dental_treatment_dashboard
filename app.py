import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pandas.api.types import (
    is_object_dtype,
    is_categorical_dtype,
    is_numeric_dtype,
    is_datetime64_any_dtype,
)
import plotly.subplots as sp
import plotly.graph_objects as go


from ipyvizzu import Data, Config, Style


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

    st.image("carestack.jpeg", width=300)
    # Load data




    # Sidebar for navigation
    tab1, tab2, tab3 = st.tabs(["Executive Summary Dashboard", "Plans that Need Action","Provider Summary Dashboard"])
    # Tab 1: Executive Summary Dashboard


    with tab1:
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
        treatment_plans['CreatedDate'] = treatment_plans['CreatedDate'].apply(process_date)

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

        treatment_nhs_claims_merged_data['CreatedDate'] = pd.to_datetime(
            treatment_nhs_claims_merged_data['CreatedDate'], errors='coerce'
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

        hm_uda_completed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "HM") & (
                treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)][
            'UDAs'].sum()

        hm_uda_successful = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "HM") & (
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
                "Active Plans": round(isFullPrivate,2),
                "Not Yet Started": round(privateNotStarted,2),
                "In Progress": round(privateInProgress,2),
                "Completed": round(privateCompleted,2),
            },
            "NHS or Mixed Plans": {
                "Active Plans": round(allNHSPlans,2),
                "Not Yet Started": round(nhsNotStarted,2),
                "In Progress": round(nhsInProgress,2),
                "Completed": round(nhsCompleted,2),
            }
        }

        udaCounts = {
            "  UDA Breakdown  ": {
                "Completed Plan UDAs": round(nhsCompletedUDAs,2),
                "Yet To Claim UDAs": round(abs(nhsCompletedUDAs - nhsClaimedUDAs),2),
                "UDAs Claimed": round(nhsClaimedUDAs,2),
                "UDAs Awaiting Response ": round(allNHSAwaitingResponse,2),
                "UDAs Successful": round(allNHSUdaSuccessful,2),
                "UDAs Failed": round(nhsFailedUDAs,2),
                "UDAs Failure Rate": round((nhsFailedUDAs / (nhsFailedUDAs + allNHSUdaSuccessful)) * 100,2)
            }
        }

        treatment_nhs_claims_merged_data = treatment_nhs_claims_merged_data.round(2)

        # Streamlit app
        st.subheader("Plans Summary")

        for row_name, statuses in counts.items():
            with st.expander(f"{row_name} Distribution", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    for status, count in statuses.items():
                        st.markdown(
                            f"<p>{status}: <strong>{count}</strong></p>",
                            unsafe_allow_html=True
                        )

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

        # Enhanced UI with styled layout

        with st.expander(f"UDA Breakdown", expanded=False):
            for row_name, statuses in udaCounts.items():
                col1, col2 = st.columns(2)

                with col1:
                    for status, count in statuses.items():
                        st.markdown(
                            f"<p>{status}: <strong>{count}</strong></p>",
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
        planProviderDF.set_index("Plan Providers", inplace=True)
        planProviderDF.style.format("{:.2f}")
        # Display the table in the Streamlit app
        with st.expander(f"Detailed UDA Breakdown", expanded=False):

            # Use hide_index=True within st.dataframe
            st.dataframe(planProviderDF, use_container_width=True)
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
        action_counts = treatment_nhs_claims_merged_data['whatAction'].value_counts()

        # Convert the counts to a dictionary
        action_counts_dict = action_counts.to_dict()

        # Access the counts for each category
        no_action_count = action_counts_dict.get('No Action', 0)
        claim_not_raised_count = action_counts_dict.get('Claim Not Raised', 0)
        claim_invalid_failed_count = action_counts_dict.get('Claim Invalid or Failed', 0)

        print(claim_invalid_failed_count)

        claimsData  = treatment_nhs_claims_merged_data[
            treatment_nhs_claims_merged_data['whatAction'].isin(['Claim Not Raised', 'Claim Invalid or Failed'])
        ]

        claimNotRaisedUDA = treatment_nhs_claims_merged_data[
            treatment_nhs_claims_merged_data['whatAction'].isin(['Claim Not Raised'])
        ]



        claimInvalidFailedUDA = treatment_nhs_claims_merged_data[
            treatment_nhs_claims_merged_data['whatAction'].isin(['Claim Invalid or Failed'])
        ]

        # Sum the UDAs for the filtered rows
        claim_not_raised_udas = claimNotRaisedUDA['UDAs'].sum()
        claim_invalid_failed_udas = claimInvalidFailedUDA['UDAs'].sum()

        print(claim_invalid_failed_udas)

        total_claim = claim_not_raised_count + claim_invalid_failed_count
        total_claim_udas = claim_not_raised_udas + claim_invalid_failed_udas
        claimData = {
            "Total Plans": [claim_not_raised_count, claim_invalid_failed_count, total_claim],
            "UDAs": [claim_not_raised_udas, claim_invalid_failed_udas, total_claim_udas]
        }
        index = ["Claim Not Raised", "Claim Invalid or Failed", "Total"]

        # Create a DataFrame
        table_df = pd.DataFrame(claimData, index=index)

        # Streamlit app to display the table
        st.subheader("Claims Summary")
        st.dataframe(table_df)
        filtered_providers = ["MM", "HM", "GA", "LL", "MJ", "RM"]

        # Pivot the data to create the desired structure
        pivot_table = pd.pivot_table(
            claimsData,
            index="PlanProvider",
            columns="whatAction",
            values="UDAs",
            aggfunc="sum",
            fill_value=0
        )

        # Flatten the columns for easier readability
        pivot_table.columns = [col for col in pivot_table.columns]
        pivot_table.reset_index(inplace=True)

        # Add Total row
        total_row = {
            "PlanProvider": "Total",
            "Claim Not Raised": pivot_table["Claim Not Raised"].sum(),
            "Claim Invalid or Failed": pivot_table["Claim Invalid or Failed"].sum()
        }
        pivot_table = pd.concat([pivot_table, pd.DataFrame([total_row])], ignore_index=True)
        pivot_table.rename(columns={"PlanProvider": "Plan Provider"}, inplace=True)
        # Streamlit app to display the table
        pivot_table_reset = pivot_table.reset_index(drop=True)
        st.subheader("Summary Table of UDAs")
        st.dataframe(pivot_table_reset)
        selected_columns = ["TreatmentPlanID","AccountID", "Band_x","PlanProvider","ClaimStatus", "FirstCompletedDate","plansThatRequireAction", "UDAs","whatAction"]
        filtered_data = claimsData[selected_columns]

        def split_frame(dataset, batch_size):
            return [dataset.iloc[i:i + batch_size].reset_index(drop=True) for i in range(0, len(dataset), batch_size)]

        # Function to implement pagination and display the DataFrame
        def paginate_df(name: str, dataset, streamlit_object: str, disabled=None, num_rows=None):
            top_menu = st.columns(3)
            with top_menu[0]:
                sort = st.radio("Sort Data", options=["Yes", "No"], horizontal=True, index=1)
            if sort == "Yes":
                with top_menu[1]:
                    sort_field = st.selectbox("Sort By", options=dataset.columns)
                with top_menu[2]:
                    sort_direction = st.radio(
                        "Direction", options=["⬆️", "⬇️"], horizontal=True
                    )
                dataset = dataset.sort_values(
                    by=sort_field, ascending=sort_direction == "⬆️", ignore_index=True
                )

            pagination = st.container()

            bottom_menu = st.columns((4, 1, 1))
            with bottom_menu[2]:
                batch_size = st.selectbox("Page Size", options=[25, 50, 100], key=f"{name}")
            with bottom_menu[1]:
                factor = 1 if len(dataset) % batch_size > 0 else 0
                total_pages = int(len(dataset) / batch_size) + factor

                current_page = st.number_input(
                    "Page", min_value=1, max_value=total_pages, step=1
                )
            with bottom_menu[0]:
                st.markdown(f"Page *{current_page}* of *{total_pages}* ")

            pages = split_frame(dataset, batch_size)

            if streamlit_object == 'df':
                # Apply formatting: retain float for 'UDAs', round others to integers
                formatted_page = pages[current_page - 1].applymap(
                    lambda x: f"{x:.2f}" if isinstance(x, float) and 'UDAs' in dataset.columns and x not in [None,
                                                                                                             np.nan]
                    else (f"{int(x)}" if isinstance(x, (int, float)) and not np.isnan(x) else x)
                )
                pagination.dataframe(data=formatted_page, hide_index=True, use_container_width=True)

            if streamlit_object == 'editable df':
                # Apply formatting: retain float for 'UDAs', round others to integers
                formatted_page = pages[current_page - 1].applymap(
                    lambda x: f"{x:.2f}" if isinstance(x, float) and 'UDAs' in dataset.columns and x not in [None,
                                                                                                             np.nan]
                    else (f"{int(x)}" if isinstance(x, (int, float)) and not np.isnan(x) else x)
                )
                pagination.data_editor(data=formatted_page, hide_index=True, disabled=disabled,
                                       num_rows=num_rows, use_container_width=True)

        # Function to filter the dataset
        def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
            df = df.copy()

            for col in df.columns:
                if is_object_dtype(df[col]):
                    try:
                        df[col] = pd.to_datetime(df[col])
                    except Exception:
                        pass

                if is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.tz_localize(None)

            modification_container = st.container()

            with modification_container:
                to_filter_columns = st.multiselect("Filter Claims Data on", df.columns)
                for column in to_filter_columns:
                    left, right = st.columns((1, 20))
                    if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                        user_cat_input = right.multiselect(
                            f"Values for {column}",
                            df[column].unique(),
                            default=list(df[column].unique()),
                        )
                        df = df[df[column].isin(user_cat_input)]
                    elif is_numeric_dtype(df[column]):
                        _min = float(df[column].min())
                        _max = float(df[column].max())
                        step = (_max - _min) / 100
                        user_num_input = right.slider(
                            f"Values for {column}",
                            min_value=_min,
                            max_value=_max,
                            value=(_min, _max),
                            step=step,
                        )
                        df = df[df[column].between(*user_num_input)]
                    elif is_datetime64_any_dtype(df[column]):
                        user_date_input = right.date_input(
                            f"Values for {column}",
                            value=(
                                df[column].min(),
                                df[column].max(),
                            ),
                        )
                        if len(user_date_input) == 2:
                            user_date_input = tuple(map(pd.to_datetime, user_date_input))
                            start_date, end_date = user_date_input
                            df = df.loc[df[column].between(start_date, end_date)]
                    else:
                        user_text_input = right.text_input(
                            f"Substring or regex in {column}",
                        )
                        if user_text_input:
                            df = df[df[column].astype(str).str.contains(user_text_input)]

            return df



        # Apply filtering and pagination
        filtered_data = filter_dataframe(filtered_data)


        # Add pagination
        paginate_df('Claims', filtered_data, 'df')

        with tab3:
            plan_providers = ["HM","GA","MJ", "MM","LL", "RM"]

            # Initialize empty lists to store results
            total_plans = []
            private_plans = []
            nhs_plans = []

            # Calculate metrics for each PlanProvider
            for provider in plan_providers:
                total = treatment_nhs_claims_merged_data["PlanProvider"].value_counts().get(provider, 0)
                private = treatment_nhs_claims_merged_data[
                    (treatment_nhs_claims_merged_data["PlanProvider"] == provider) &
                    (treatment_nhs_claims_merged_data["isFullPrivate"] == 1)
                    ].shape[0]
                nhs = treatment_nhs_claims_merged_data[
                    (treatment_nhs_claims_merged_data["PlanProvider"] == provider) &
                    (treatment_nhs_claims_merged_data["isNHS"] == 1)
                    ].shape[0]

                total_plans.append(total)
                private_plans.append(private)
                nhs_plans.append(nhs)

            # Create a DataFrame
            metrics_df = pd.DataFrame({
                "PlanProvider": plan_providers,
                "Total Plans": total_plans,
                "Private Plans": private_plans,
                "NHS Plans": nhs_plans
            })
            # Visualization: Grouped Bar Chart
            metrics_melted = metrics_df.melt(id_vars="PlanProvider", var_name="Metric", value_name="Count")

            fig = px.bar(
                metrics_melted,
                x="PlanProvider",
                y="Count",
                color="Metric",
                title="Plan Provider Metrics",
                barmode="group",
                labels={"PlanProvider": "Plan Provider", "Count": "Count", "Metric": "Plan Type"}
            )

            view_metrics = st.radio(
                "",
                ("Chart View", "Table View"),
                horizontal=True,
                key="metrics_view",
            )

            if view_metrics == "Chart View":
                with st.container(border=True):

                    st.plotly_chart(fig, use_container_width=True)
            else:
                with st.container(border=True):
                    st.subheader("Plan Provider Metrics")
                    metrics_df.set_index("PlanProvider", inplace=True)
                    st.dataframe(metrics_df)



            private_completed_list = []
            nhs_completed_list = []
            completed_plans_list = []

            # Calculate metrics for each PlanProvider
            for provider in plan_providers:
                private_completed = treatment_nhs_claims_merged_data[
                    (treatment_nhs_claims_merged_data["PlanProvider"] == provider) &
                    (treatment_nhs_claims_merged_data["isFullPrivate"] == 1) &
                    (treatment_nhs_claims_merged_data["Complete"] == 1)
                    ].shape[0]

                nhs_completed = treatment_nhs_claims_merged_data[
                    (treatment_nhs_claims_merged_data["PlanProvider"] == provider) &
                    (treatment_nhs_claims_merged_data["isNHS"] == 1) &
                    (treatment_nhs_claims_merged_data["Complete"] == 1)
                    ].shape[0]

                completed_plans = private_completed + nhs_completed

                # Append results to the lists
                private_completed_list.append(private_completed)
                nhs_completed_list.append(nhs_completed)
                completed_plans_list.append(completed_plans)

            # Create a DataFrame
            completed_data = pd.DataFrame({
                "PlanProvider": plan_providers,
                "Private Completed": private_completed_list,
                "NHS Completed": nhs_completed_list,
                "Total Completed": completed_plans_list
            })



            # Create a subplot of pie charts
            fig_completed = sp.make_subplots(
                rows=2, cols=3, specs=[[{"type": "domain"}] * 3, [{"type": "domain"}] * 3],
                subplot_titles=completed_data["PlanProvider"]
            )

            for i, provider in enumerate(completed_data["PlanProvider"]):
                row = (i // 3) + 1
                col = (i % 3) + 1
                fig_completed.add_trace(
                    go.Pie(
                        labels=["Private Completed", "NHS Completed"],
                        values=completed_data.loc[i, ["Private Completed", "NHS Completed"]],
                        name=provider
                    ),
                    row=row, col=col
                )

            fig_completed.update_layout(title_text="Completed Plans by Provider")

            if view_metrics == "Chart View":
                with st.container(border=True):
                    st.plotly_chart(fig_completed, use_container_width=True)
            else:
                with st.container(border=True):
                    st.subheader("Completed Plans by Provider")
                    completed_data.set_index("PlanProvider", inplace=True)
                    st.dataframe(completed_data)

            # Define columns for the filters
            col1, col2= st.columns([2,2])

            # Filter for view selection (Weekly or Monthly)
            with st.container(border=True):
                with col1:

                    st.subheader("")
                    view_option = st.radio("Select View", ["Weekly View", "Monthly View"], horizontal=True,index=0)
                    filtered_data = treatment_nhs_claims_merged_data[
                        treatment_nhs_claims_merged_data["PlanProvider"].isin(["HM", "GA", "LL", "MM", "MJ", "RM"])
                    ]
                    selected_provider = st.sidebar.selectbox(
                        "Select a Plan Provider", options=filtered_data["PlanProvider"].unique()
                    )
                    provider_data = filtered_data[filtered_data["PlanProvider"] == selected_provider]




                # Filters for month and year in the Monthly View

                metric_mapping = {
                    "Total UDAs": "Completed UDAs",
                    "Claimed UDAs": "Claimed UDAs",
                    "Successful UDAs": "Successful UDAs",
                    "Failed UDAs": "Failed UDAs"
                }

                # **Process Weekly & Monthly Data Based on User Selection**
                date_filter = pd.to_datetime("2024-11-17")
                carestack_sorted = provider_data[
                    (provider_data["CreatedIn"] == "Created in Carestack") &
                    (provider_data["LastCompletedDate"] > date_filter)
                    ].sort_values(by="LastCompletedDate", ascending=True)

                start_date = carestack_sorted['LastCompletedDate'].min()
                end_date = carestack_sorted['LastCompletedDate'].max()

                if view_option == "Weekly View":
                    st.subheader(f"UDA Weekly Trends for Plan Provider: {selected_provider}")

                    # Generate weekly bins
                    bins = [start_date + pd.Timedelta(weeks=i) for i in range(9)]
                    labels = [f"Week {i + 1}" for i in range(8)]

                    # Assign weeks
                    carestack_sorted['Period'] = pd.cut(
                        carestack_sorted['LastCompletedDate'], bins=bins, labels=labels, right=False,
                        include_lowest=True
                    )

                elif view_option == "Monthly View":
                    st.subheader(
                        f"UDA Monthly Trends from {start_date.strftime('%B %Y')} to {end_date.strftime('%B %Y')}")

                    # Convert date to Month-Year format
                    carestack_sorted['Period'] = carestack_sorted['LastCompletedDate'].dt.strftime('%B %Y')

                # **Calculate Metrics (Weekly or Monthly)**
                uda_totals = carestack_sorted[
                    (carestack_sorted['isNHS'] == 1) & (carestack_sorted['Complete'] == 1)
                    ].groupby(['Period'])['UDAs'].sum().reset_index()

                uda_claimed = carestack_sorted[
                    (carestack_sorted['Complete'] == 1) & (carestack_sorted['isNHS'] == 1)
                    ].groupby(['Period'])['UDA'].sum().reset_index()

                uda_successful = carestack_sorted[
                    (carestack_sorted['Complete'] == 1) & (carestack_sorted['isNHS'] == 1)
                    ].groupby(['Period'])['UdaConfirmed'].sum().reset_index()

                uda_failed = carestack_sorted[
                    (carestack_sorted['isNHS'] == 1) & (carestack_sorted['isClaimFailed'] == 1)
                    ].groupby(['Period'])['UDA'].sum().reset_index()

                # Merge metrics for visualization
                line_chart_data = uda_totals.rename(columns={"UDAs": "Total UDAs"}).copy()
                line_chart_data["Claimed UDAs"] = uda_claimed["UDA"]
                line_chart_data["Successful UDAs"] = uda_successful["UdaConfirmed"]
                line_chart_data["Failed UDAs"] = uda_failed["UDA"]

                # **Sort Data Properly**
                if view_option == "Weekly View":
                    # Ensure Weeks are sorted numerically (Week 1, Week 2, ...)
                    line_chart_data['Period'] = pd.Categorical(line_chart_data['Period'], categories=labels,
                                                               ordered=True)

                elif view_option == "Monthly View":
                    # Ensure Months are sorted correctly (Nov 2024 before Dec 2024)
                    line_chart_data['Period'] = pd.to_datetime(line_chart_data['Period'], format='%B %Y')
                    line_chart_data = line_chart_data.sort_values(by="Period")
                    line_chart_data['Period'] = line_chart_data['Period'].dt.strftime(
                        '%B %Y')  # Convert back to readable format

                # Melt data for visualization
                line_chart_data = line_chart_data.melt(
                    id_vars=["Period"],
                    value_vars=["Total UDAs", "Claimed UDAs", "Successful UDAs", "Failed UDAs"],
                    var_name="Metric",
                    value_name="Value"
                )

                # **Prepare Table Data**
                table_data = line_chart_data.pivot(index="Metric", columns="Period", values="Value").reset_index()
                table_data["Metric"] = table_data["Metric"].map(metric_mapping)

                # Convert numeric columns
                numeric_columns = [col for col in table_data.columns if col != "Metric"]
                table_data[numeric_columns] = table_data[numeric_columns].apply(pd.to_numeric, errors='coerce').fillna(
                    0)

                # **Sort Table Columns Properly**
                if view_option == "Monthly View":
                    # Extract the period column names (Months) and sort them correctly
                    sorted_columns = ["Metric"] + sorted(numeric_columns,
                                                         key=lambda x: pd.to_datetime(x, format='%B %Y'))
                    table_data = table_data[sorted_columns]  # Reorder table columns based on sorted month order

                # **Toggle Table or Chart View**

                if view_metrics == "Chart View":
                    fig = px.line(
                        line_chart_data,
                        x="Period",
                        y="Value",
                        color="Metric",
                        title=f"UDA {view_option.split(' ')[0]} Trends for Plan Provider: {selected_provider}",
                        labels={"Value": "UDAs", "Period": "Time Period"},
                        line_shape="linear"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                elif view_metrics == "Table View":
                    styled_table = table_data.copy()
                    for col in styled_table.columns[1:]:  # Skip "Metric" column
                        styled_table[col] = styled_table[col].apply(
                            lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)

                    styled_table.set_index("Metric", inplace=True)
                    st.dataframe(styled_table, use_container_width=True)


# Run the app
if __name__ == "__main__":
    main()