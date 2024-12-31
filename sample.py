import pandas as pd
import numpy as np
from datetime import datetime


# Example usage

treatment_plans = pd.read_csv("data/TreatmentPlans Data.csv")
nhs_plans = pd.read_csv("data/NHS Plans Data.csv")
attribute_counts = treatment_plans['Description'].value_counts()


private_filtered = treatment_plans[treatment_plans['Payor'] == 'Private']

# Get unique values and counts for another attribute (AttributeX) for 'private'
private_unique_counts = private_filtered['Description'].value_counts()


# Repeat for 'nhs'
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

treatment_plans['HygienePlans'] = treatment_plans['PlanProvider'].apply(lambda x: 1 if x in ["MH", "RP", "MK"] else ("" if x == "" else 0))

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

treatment_nhs_merged_data['isMixed'] = treatment_nhs_merged_data.apply(lambda row: checkMixed(row['PlanProvider'], row['TotalNHSCodes'], row['TotalTreatments']), axis=1)

treatment_nhs_merged_data['isPNHS'] = treatment_nhs_merged_data.apply(lambda row: checkPrivateNHS(row['PlanProvider'], row['TotalNHSCodes'], row['TotalTreatments']), axis=1)

treatment_nhs_merged_data['isFullPrivate'] = treatment_nhs_merged_data.apply(lambda row: checkFullPrivateNHS(row['PlanProvider'], row['TotalNHSCodes'], row['TotalTreatments']), axis=1)



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

treatment_nhs_merged_data['inProgress'] = treatment_nhs_merged_data.apply(lambda row: calculateInProgress(row['PlanProvider'], row['CompletedTreatments'], row['TotalTreatments']), axis=1)
treatment_nhs_merged_data['Complete'] = treatment_nhs_merged_data.apply(lambda row: calculateCompleted(row['PlanProvider'], row['CompletedTreatments'], row['TotalTreatments']), axis=1)


def calculatePendingFee(PlanProvider, TotalFee, CompletedTreatmentFee):
    if PlanProvider == "":
        return ""  # Return an empty string
    return TotalFee - CompletedTreatmentFee


treatment_nhs_merged_data['PendingFee'] = treatment_nhs_merged_data.apply(lambda row: calculatePendingFee(row['PlanProvider'], row['TotalFee'], row['CompletedTreatmentsFee']), axis=1)




def checkIsNHS(isMixed, isPNHS):
    if isPNHS == "":
        return ""
    return isMixed + isPNHS


treatment_nhs_merged_data['isNHS'] = treatment_nhs_merged_data.apply(lambda row: checkIsNHS(row['isMixed'], row['isPNHS']), axis=1)
print(treatment_nhs_merged_data)