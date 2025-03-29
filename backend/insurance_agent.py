from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from model import llm
from langgraph_swarm import create_handoff_tool
from db import  get_database, get_user_details, get_insurance_policy_details_from_user_id, get_insurance_policy_details_from_policy, get_treatment_details
import os
from dotenv import load_dotenv

load_dotenv()

# Insurance Tool 1: Fetch Insurance Details
@tool
def fetch_insurance_policy_details(user_name: str) -> dict:
    """
        For the given user, fetch the user's insurance policy details from the database.
        This tool must be used before checking claim eligibility or calculating coverage.
    """

    user_details = get_user_details(user_name)
    user_id = user_details[0]["_id"]

    policy = get_insurance_policy_details_from_user_id(f"{user_id}")

    return policy if policy else {"error": "No insurance policy found for this patient."}

# Insurance Tool 2: Check Insurance Claim Eligibility
@tool
def check_claim_eligibility(policy_number: str, treatment: str) -> str:
    """
        Given the policy and the desired treatment, the tool checks if a treatment is covered under the user's insurance policy ensuring user is eligible for insurance claim.
        Requires policy details and treatment first. If policy details are not available, call 'fetch_insurance_policy_details'
    """

    policy_details = get_insurance_policy_details_from_policy(policy_number)

    covered_treatments = policy_details.get("covered_treatments", [])
    
    if treatment in covered_treatments:
        return f"Treatment '{treatment}' is covered by insurance."
    else:
        return f"Treatment '{treatment}' is NOT covered under the current insurance plan."
    
# Insurance Tool 3: Calculate Estimated Coverage
@tool
def calculate_estimated_coverage(policy: str, treatment: str) -> dict:
    """
        Calculates the insurance coverage percentage provided in the policy details.
        Requires both policy details and treatment details. If missing, call 'fetch_insurance_policy_details' and 'check_claim_eligibility' first.
    """

    treatment_details = get_treatment_details(treatment)

    policy_details = get_insurance_policy_details_from_policy(policy)

    coverage_percentage = policy_details.get("coverage_percentage", 0)  # Default 0% if not found

    return coverage_percentage
    # { 
    #     "coverage_percentage": coverage_percentage, 
    #     "treatment": treatment, 
    #     "estimated_reimbursement": reimbursed_amount, 
    #     "total_cost": treatment_details[0]["cost"] 
    # }

# Insurance Tool 4: Calculate Estimated Coverage
@tool
def calculate_reimbursed_amount(policy: str, treatment: str) -> dict:
    """
        Calculates the reimbursed amount.
        Requires both policy details and treatment details. If missing, call 'fetch_insurance_policy_details' and 'check_claim_eligibility' first.
    """ 

    treatment_details = get_treatment_details(treatment)

    policy_details = get_insurance_policy_details_from_policy(policy)

    coverage_percentage = policy_details.get("coverage_percentage", 0)  # Default 0% if not found
    reimbursed_amount = (coverage_percentage / 100) * treatment_details[0]["cost"]

    return reimbursed_amount

# Insurance Tool 5: Submit Claim 
@tool
def submit_insurance_claim(user_name: str, treatment: str, reimbursed_amount: float) -> str:
    """
        Submits an insurance claim for approval.
        Requires an estimated coverage amount and reimbursed amount before submitting. 
        If missing, call 'calculate_estimated_coverage' and 'calculate_reimbursed_amount' first.
    """

    user_details = get_user_details(user_name)
    user_id = user_details[0]["_id"]
    policy_details = get_insurance_policy_details_from_user_id(f"{user_id}")
    treatment_details = get_treatment_details(treatment)
    total_cost = treatment_details[0]["cost"] 

    coverage_details = { 
        "patient_id": user_id,
        "coverage_percentage": policy_details.get("coverage_percentage", 0), 
        "treatment": treatment, 
        "total_cost": total_cost,
        "reimbursed_amount": reimbursed_amount
    }

    db = get_database()

    claim_collection = db[os.getenv('CLAIM_COLLECTION')]

    claim_details = claim_collection.insert_one(coverage_details)

    # Simulate claim submission
    claim_id = f"CLAIM-{claim_details.inserted_id}"
    return f"Claim Submitted! ID: {claim_id}\n{coverage_details}"

# Insurance Agent
insurance_agent = create_react_agent(
    llm,
    [
        fetch_insurance_policy_details, 
        check_claim_eligibility, 
        calculate_estimated_coverage,
        calculate_reimbursed_amount,
        submit_insurance_claim,
        create_handoff_tool(agent_name="report_analyst", description="Transfer to report_analyst to analyze and summarize user's medical reports."),
        create_handoff_tool(agent_name="book_test", description="Transfer to book_test to book medical tests from the available list of tests in the database.")
    ],
    prompt="""
        You are check_insurance, an intelligent medical insurance assistant 
        that helps users with their medical insurance coverage and claims. 
        
        **Your Responsibilities:**

        - Always **fetch policy details first** if they are required and missing.
        - If the user asks to **check coverage**, ensure that you:
        1. Fetch the insurance policy.
        2. Check claim eligibility.
        3. Calculate estimated coverage.
        - If the user asks to **check reimbursed amount**, ensure that you:
        1. Fetch the insurance policy.
        2. Check claim eligibility.
        3. Calculate reimbursed amount.
        - If the user wants to **submit a claim**, ensure that:
        1. Policy details are available.
        2. Claim eligibility is checked.
        3. Estimated coverage is calculated.
        4. The claim is submitted.

        Always **call the required tools in the correct order** to complete a user’s request.
        """,
    name="check_insurance",
)