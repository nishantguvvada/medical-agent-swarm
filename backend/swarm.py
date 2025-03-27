from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph_swarm import create_handoff_tool, create_swarm
import datetime
from dotenv import load_dotenv
from db import get_database
import os

load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash', api_key=os.getenv('GEMINI_API_KEY'))

@tool
def fetch_report(user_name: str) -> list:
    """Fetch a list of medical or health reports from the database for the given user"""

    db = get_database()
    collection = db[os.getenv('REPORT_COLLECTION')]

    item_details = collection.find({"user_name": user_name.lower()})
    
    reports = item_details[0]['user_reports']

    return reports

# report manager
ferta = create_react_agent(
    llm,
    [fetch_report, create_handoff_tool(agent_name="Apbo", description="Transfer to Apbo for anything related to booking medical tests.")],
    prompt="""
        You are Ferta, a medical health report manager.  
        You provide a 20 word summary of all the reports fetched from the database given a user's name.
        ALWAYS include a suggested action at the end of the summary.
        """,
    name="Ferta",
)

@tool
def book_tests(user_name: str, tests: list[str]):
    """Create a booking appointment and store it in the database. 
        Extract the user name and the list of tests.
    """

    db = get_database()

    user_collection = db[os.getenv('USER_COLLECTION')]
    test_collection = db[os.getenv('TEST_COLLECTION')]

    user_details = user_collection.find({"user_name": user_name.lower()})

    booking_details = {
        "patient_id": user_details[0]['_id'],
        # "lab_name": lab_name,
        "test_name": tests,
        "date_time": f"{datetime.datetime.now()}",
        "status": "Confirmed"
    }

    test_details = test_collection.insert_one(booking_details)

    if test_details.inserted_id:
        return True
    else:
        return False
    
@tool
def find_tests() -> list[str]:
    """Find the relevant tests for the given list of symptoms"""
    symptom_lab_map = {
    "fever": ["Complete Blood Count (CBC)", "Malaria Test", "Dengue NS1 Antigen Test"],
    "chest pain": ["Electrocardiogram (ECG)", "Troponin Test", "Lipid Profile", "Chest X-ray"],
    "fatigue": ["Thyroid Function Test (T3, T4, TSH)", "Iron Deficiency Test", "Vitamin B12 Test"],
    "persistent cough": ["Chest X-ray", "Sputum Culture", "COVID-19 PCR Test", "Tuberculosis (TB) Test"],
    "abdominal pain": ["Abdominal Ultrasound", "Liver Function Test (LFT)", "Amylase & Lipase Test"],
    "shortness of breath": ["Pulmonary Function Test (PFT)", "D-Dimer Test", "Chest CT Scan"],
    "joint pain": ["Rheumatoid Factor (RF) Test", "C-Reactive Protein (CRP)", "Uric Acid Test"],
    "frequent urination": ["Urine Routine & Microscopy", "Blood Sugar Test (Fasting & PP)", "Kidney Function Test (KFT)"],
    "dizziness": ["Blood Pressure Check", "Electrolyte Panel", "Blood Glucose Test"],
    "unexplained weight loss": ["Thyroid Function Test", "Hemoglobin A1C (HbA1c)", "Cancer Marker Tests (CA-125, PSA)"]
    }
    
    return list(symptom_lab_map["fever"])


apbo = create_react_agent(
    llm,
    [find_tests, book_tests, create_handoff_tool(agent_name="Ferta", description="Transfer to Ferta for anything related to health reports.")],
    prompt="""
        You are Apbo, a medical test booking assistant. For the user's symptoms, you book the relevant medical test for the user.
        You find the relevant tests first and then book the tests.
    """,
    name="Apbo",
)

checkpointer = InMemorySaver() # checkpointer.list(config) store in MongoDB
store = InMemoryStore()

workflow = create_swarm(
    [ferta, apbo],
    default_active_agent="Apbo"
)
app = workflow.compile(
    checkpointer=checkpointer,
    store=store
    )

config = {"configurable": {"thread_id": "2"}}
turn_1 = app.invoke(
    {"messages": [{"role": "user", "content": "jannet has a fever, book a test for jannet. Do not ask for confirmation. JUST BOOK THE TEST."}]},
    config,
)

print(turn_1)

# turn_2 = app.invoke(
#     {"messages": [{"role": "user", "content": "what is the health summary of Jannet?"}]},
#     config,
# )
# print(turn_2)



