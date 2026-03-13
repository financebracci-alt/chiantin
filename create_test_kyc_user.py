"""
Create a test user with verified email and submit KYC for frontend testing
"""
import requests
import time
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta

BASE_URL = "https://user-alert-system-2.preview.emergentagent.com/api/v1"
MONGO_URL = "mongodb+srv://pierangelamarcio232_db_user:yo123mama@cluster0.jqvhvbe.mongodb.net/ecommbx-prod?retryWrites=true&w=majority"

# Create unique test user
TEST_EMAIL = f"kycfrontend_{int(time.time())}@test.com"
TEST_PASSWORD = "TestPassword123!"

print(f"Creating test user: {TEST_EMAIL}")

# 1. Register user
response = requests.post(
    f"{BASE_URL}/auth/signup",
    json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "first_name": "Frontend",
        "last_name": "TestUser",
        "phone": "+1234567890"
    }
)

if response.status_code != 201:
    print(f"Failed to register user: {response.status_code} - {response.text}")
    exit(1)

user_data = response.json()
user_id = user_data["id"]
print(f"✅ User registered: {user_id}")

# 2. Manually verify email in database
client = MongoClient(MONGO_URL)
db = client["ecommbx-prod"]

# Try both string and ObjectId
result = db.users.update_one(
    {"_id": user_id},
    {"$set": {"email_verified": True}}
)

if result.modified_count == 0:
    # Try with ObjectId
    try:
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"email_verified": True}}
        )
    except:
        pass

if result.modified_count > 0:
    print(f"✅ Email verified in database")
else:
    print(f"⚠️  Could not verify email")
    # Check if user exists
    user = db.users.find_one({"_id": user_id})
    if not user:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        print(f"   User found: {user.get('email')}, email_verified: {user.get('email_verified')}")

# 3. Login as user
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
)

if response.status_code != 200:
    print(f"Failed to login: {response.status_code} - {response.text}")
    exit(1)

user_token = response.json()["access_token"]
print(f"✅ User logged in")

# 4. Submit KYC application
response = requests.post(
    f"{BASE_URL}/kyc/submit",
    headers={"Authorization": f"Bearer {user_token}"},
    json={
        "full_name": "Frontend TestUser",
        "date_of_birth": "1990-01-01",
        "nationality": "US",
        "country": "US",
        "street_address": "123 Test St",
        "city": "Test City",
        "postal_code": "12345",
        "tax_residency": "US",
        "tax_id": "123-45-6789",
        "terms_accepted": True,
        "privacy_accepted": True
    }
)

if response.status_code != 200:
    print(f"Failed to submit KYC: {response.status_code} - {response.text}")
    exit(1)

kyc_data = response.json()
print(f"✅ KYC submitted: {kyc_data['id']}")

print(f"\n" + "="*80)
print(f"TEST USER CREATED FOR FRONTEND TESTING")
print(f"="*80)
print(f"Email: {TEST_EMAIL}")
print(f"Password: {TEST_PASSWORD}")
print(f"User ID: {user_id}")
print(f"KYC Application ID: {kyc_data['id']}")
print(f"="*80)
