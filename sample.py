import pandas as pd
import numpy as np
from datetime import datetime


# Example usage

treatment_plans = pd.read_csv("data/TreatmentPlans Data.csv")
nhs_plans = pd.read_csv("data/NHS Plans Data.csv")
claims = pd.read_csv("data/Claims Data.csv")
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



claims.rename(columns={'TreatmentPlanId': 'TreatmentPlanID'}, inplace=True)

treatment_nhs_claims_merged_data = pd.merge(
    treatment_nhs_merged_data,
    claims,  # Select relevant columns
    on='TreatmentPlanID',
    how='left'  # Retain all rows from TreatmentPlans.csv
)



def checkClaimFailed(ClaimStatus):
    if pd.isna(ClaimStatus):
        return ""  # Return an empty string

    # Check if AF3 is "Invalid" or "Failed"
    if ClaimStatus in ["Invalid", "Failed"]:
        return 1  # Return 1 for "Invalid" or "Failed"

    # Default case
    return 0  # Return 0 for all other cases

treatment_nhs_claims_merged_data['isClaimFailed'] = treatment_nhs_claims_merged_data['ClaimStatus'].apply(checkClaimFailed)



def checkClaimQueued(ClaimStatus):
    if pd.isna(ClaimStatus):
        return ""  # Return an empty string

    # Check if AF3 is "Invalid" or "Failed"
    if ClaimStatus in ["Submitted", "Queued"]:
        return 1  # Return 1 for "Invalid" or "Failed"

    # Default case
    return 0  # Return 0 for all other cases

treatment_nhs_claims_merged_data['isClaimQueued'] = treatment_nhs_claims_merged_data['ClaimStatus'].apply(checkClaimQueued)




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


treatment_nhs_claims_merged_data['plansThatRequireAction'] = treatment_nhs_claims_merged_data.apply(lambda row: plansThatRequireAction(row['PlanProvider'], row['isClaimFailed'], row['isNHS'], row['Complete'], row['ClaimStatus']), axis=1)


print(treatment_nhs_claims_merged_data['plansThatRequireAction'])


def calculateAction(PlansThatRequireAction, isClaimFailed):
    if pd.isna(PlansThatRequireAction):
        return ""  # Return an empty string

    if PlansThatRequireAction == 0:
        return "No Action"


    if isClaimFailed == 1:
        return "Claim Invalid or Failed"

    # Default case
    return "Claim Not Raised"




treatment_nhs_claims_merged_data['whatAction'] = treatment_nhs_claims_merged_data.apply(lambda row: calculateAction(row['plansThatRequireAction'], row['isClaimFailed']), axis=1)



unique_providers = treatment_nhs_claims_merged_data['PlanProvider'].unique()

isFullPrivate = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['isFullPrivate'] == 1) & (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

isMixedOrNHS = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['isMixed'] == 1) & (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

isPureNHS  = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['isPNHS'] == 1) & (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

privateNotStarted  = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['CompletedTreatments'] == 0) & (treatment_nhs_claims_merged_data['isFullPrivate'] == 1) & (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

privateInProgress  = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['isFullPrivate'] == 1) & (treatment_nhs_claims_merged_data['inProgress'] == 1) & (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

privateCompleted  = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isFullPrivate'] == 1) & (treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")].shape[0]

nhsCompleted = treatment_nhs_claims_merged_data[((treatment_nhs_claims_merged_data['isMixed'] == 1) | (treatment_nhs_claims_merged_data['isPNHS'] == 1)) & (treatment_nhs_claims_merged_data['Complete'] == 1)].shape[0]
nhsInProgress = treatment_nhs_claims_merged_data[((treatment_nhs_claims_merged_data['isMixed'] == 1) | (treatment_nhs_claims_merged_data['isPNHS'] == 1)) & (treatment_nhs_claims_merged_data['inProgress'] == 1)].shape[0]
nhsNotStarted = treatment_nhs_claims_merged_data[((treatment_nhs_claims_merged_data['isMixed'] == 1) | (treatment_nhs_claims_merged_data['isPNHS'] == 1)) & (treatment_nhs_claims_merged_data['CompletedTreatments'] == 0)].shape[0]
print(isPureNHS)

print(isFullPrivate)

print(isMixedOrNHS)

print(privateNotStarted)

print(privateInProgress)

print(privateCompleted)

allNHSPlans  = isPureNHS + isMixedOrNHS

print(allNHSPlans)

print(nhsCompleted)

print(nhsNotStarted)
print(nhsInProgress)

nhsTotalUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
print(nhsTotalUDAs)

nhsCompletedUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data['Complete'] == 1)]['UDA'].sum()
print(nhsCompletedUDAs)



nhsFailedUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1)]['UDA'].sum()

print(nhsFailedUDAs)




nhsClaimsFailureRate = (nhsFailedUDAs / nhsTotalUDAs) * 100

print(nhsClaimsFailureRate)

pnhsTotalUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isPNHS'] == 1)]['UDA'].sum()
print(pnhsTotalUDAs)

pnhsCompletedUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isPNHS'] == 1) & (treatment_nhs_claims_merged_data['Complete'] == 1)]['UDA'].sum()
print(pnhsCompletedUDAs)



pnhsFailedUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isPNHS'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1)]['UDA'].sum()

print(pnhsFailedUDAs)




pnhsClaimsFailureRate = (pnhsFailedUDAs / pnhsTotalUDAs) * 100

print(pnhsClaimsFailureRate)


mixedTotalUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isMixed'] == 1)]['UDA'].sum()
print(mixedTotalUDAs)

mixedCompletedUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isMixed'] == 1) & (treatment_nhs_claims_merged_data['Complete'] == 1)]['UDA'].sum()
print(mixedCompletedUDAs)



mixedFailedUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isMixed'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1)]['UDA'].sum()

print(mixedFailedUDAs)




mixedClaimsFailureRate = (mixedFailedUDAs / mixedTotalUDAs) * 100

print(mixedClaimsFailureRate)

totalUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers")]['UDA'].sum()
print(totalUDAs)

completedUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['Complete'] == 1)]['UDA'].sum()
print(completedUDAs)



failedUDAs = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] != "All Providers") & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1)]['UDA'].sum()

print(failedUDAs)




claimsFailureRate = (failedUDAs / totalUDAs) * 100

print(claimsFailureRate)

categories = ['HM', 'GA', 'MJ', 'MM', 'LL', 'RM']

# Filter the DataFrame to include only the specified categories
filtered_df = treatment_nhs_claims_merged_data[treatment_nhs_claims_merged_data['PlanProvider'].isin(categories)]

# Group by PlanProvider and calculate the total UDA
uda_totals = filtered_df.groupby('PlanProvider')['UDA'].sum().reset_index()

# Rename columns for clarity
uda_totals.columns = ['PlanProvider', 'TotalUDA']

# Display the results
print(uda_totals)

hm_uda_total = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "HM") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()

hm_uda_successful = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "HM") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1) ]['UDA'].sum()
hm_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "HM")  & (treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1) ]['UDA'].sum()
print(hm_uda_successful)
print(hm_uda_total)
print(hm_uda_failed)
hm_uda_failure_rate = (hm_uda_failed / hm_uda_total) * 100
print(hm_uda_failure_rate)

ga_uda_total = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "GA") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()

ga_uda_successful = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "GA") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1) ]['UDA'].sum()
ga_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "GA")  & (treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1) ]['UDA'].sum()
ga_uda_failure_rate = (ga_uda_failed / ga_uda_total) * 100
print(ga_uda_successful)
print(ga_uda_total)
print(ga_uda_failed)
print(ga_uda_failure_rate)

mj_uda_total = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MJ") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
mj_uda_successful = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MJ") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1) ]['UDA'].sum()
mj_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MJ")  & (treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1) ]['UDA'].sum()
mj_uda_failure_rate = (mj_uda_failed / mj_uda_total) * 100
print(mj_uda_successful)
print(mj_uda_total)
print(mj_uda_failed)
print(mj_uda_failure_rate)

mm_uda_total = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MM") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
mm_uda_successful = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MM") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1) ]['UDA'].sum()
mm_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "MM")  & (treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1) ]['UDA'].sum()
mm_uda_failure_rate = (mm_uda_failed / mm_uda_total) * 100
print(mm_uda_successful)
print(mm_uda_total)
print(mm_uda_failed)
print(mm_uda_failure_rate)

ll_uda_total = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "LL") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
ll_uda_successful = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "LL") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1) ]['UDA'].sum()
ll_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "LL")  & (treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1) ]['UDA'].sum()
ll_uda_failure_rate = (ll_uda_failed / ll_uda_total) * 100
print(ll_uda_successful)
print(ll_uda_total)
print(ll_uda_failed)
print(ll_uda_failure_rate)

rm_uda_total = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "RM") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1)]['UDA'].sum()
rm_uda_successful = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "RM") & (treatment_nhs_claims_merged_data['Complete'] == 1) & (treatment_nhs_claims_merged_data['isNHS'] == 1) ]['UDA'].sum()
rm_uda_failed = treatment_nhs_claims_merged_data[(treatment_nhs_claims_merged_data['PlanProvider'] == "RM")  & (treatment_nhs_claims_merged_data['isNHS'] == 1) & (treatment_nhs_claims_merged_data['isClaimFailed'] == 1) ]['UDA'].sum()
rm_uda_failure_rate = (rm_uda_failed / rm_uda_total) * 100
print(rm_uda_successful)
print(rm_uda_total)
print(rm_uda_failed)
print(rm_uda_failure_rate)


total_uda = hm_uda_total + rm_uda_total + ll_uda_total + mm_uda_total + mj_uda_total + ga_uda_total

print(total_uda)

total_uda_failed = hm_uda_failed + rm_uda_failed + ll_uda_failed + mm_uda_failed + mj_uda_failed + ga_uda_failed
print(total_uda_failed)

uda_failure_rate = (total_uda_failed / total_uda) * 100

print(uda_failure_rate)


categories = ["Private Plans", "NHS or Mixed Plans", "UDA Breakdown"]
statuses = ["Active Plans", "Not Yet Started", "In Progress", "Completed"]

# Loop through each category and display counts for each status
for category in categories:
    st.subheader(f"{category} Summary")
    for status in statuses:
        count = df.loc[(df["Category"] == category) & (df["Status"] == status), "Count"].values[0]
        st.write(f"{status}: {count}")

