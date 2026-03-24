import requests

BASE_URL = "https://bank-staging.preview.emergentagent.com/api/v1"
ADMIN_EMAIL = "admin@ecommbx.io"
ADMIN_PASSWORD = "Admin@123456"

# Login as admin
response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
)

if response.status_code == 200:
    admin_token = response.json()["access_token"]
    
    # Get pending KYC applications
    response = requests.get(
        f"{BASE_URL}/admin/kyc/pending",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        apps = response.json()
        print(f"Found {len(apps)} pending KYC applications:")
        for app in apps:
            print(f"  - ID: {app['id']}, User: {app['user_id']}, Name: {app.get('full_name', 'N/A')}, Status: {app['status']}")
    else:
        print(f"Failed to get pending KYC: {response.status_code}")
else:
    print(f"Failed to login: {response.status_code}")
