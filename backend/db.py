from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

def get_database():

    client = MongoClient(os.getenv('MONGODB_URL'))

    return client[os.getenv('DB')]

db = get_database()

def get_user_details(user_name: str):

    user_collection = db[os.getenv('USER_COLLECTION')]

    user_details = user_collection.find({"user_name": user_name.lower()})

    return user_details

def get_insurance_policy_details(user_id):

    insurance_collection = db[os.getenv('INSURANCE_COLLECTION')]

    policy = insurance_collection.find_one({"patient_id": user_id})

    return policy

def get_treatment_details(treatment: str):

    treatment_collection = db[os.getenv('TREATMENT_COLLECTION')]

    treatment_details = treatment_collection.find({"test_name": treatment})

    return treatment_details

def get_report_details(user_name: str):

    user_details = get_user_details(user_name)

    report_collection = db[os.getenv('REPORT_COLLECTION')]

    report_details = report_collection.find({"user_id": user_details[0]["_id"]})

    return report_details

def get_booked_test_details(user_name: str):

    user_details = get_user_details(user_name)

    test_collection = db[os.getenv('TEST_COLLECTION')]

    test_details = test_collection.find({"patient_id": user_details[0]["_id"]})

    return test_details

def get_available_tests():

    test_collection = db[os.getenv('TREATMENT_COLLECTION')]

    test_details = test_collection.find({})

    return test_details


