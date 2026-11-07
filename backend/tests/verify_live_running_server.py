import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_role(role_name, email, password):
    print(f"=== Testing {role_name} ({email}) ===")
    with httpx.Client(timeout=10.0) as client:
        res = client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200, f"Login failed: {res.text}"
        data = res.json()
        token = data["access_token"]
        user = data["user"]
        print(f"  [OK] Login successful. User: {user['full_name']} (Role: {user['role']})")
        headers = {"Authorization": f"Bearer {token}"}
        
        if user["role"] == "PLATFORM_OWNER":
            overview = client.get(f"{BASE_URL}/platform/overview", headers=headers)
            assert overview.status_code == 200, f"Platform overview failed: {overview.text}"
            od = overview.json()
            print(f"  [OK] Platform overview keys: {list(od.keys())}")
            
        elif user["role"] == "ORG_ADMIN":
            dash = client.get(f"{BASE_URL}/org/dashboard", headers=headers)
            assert dash.status_code == 200, f"Org dashboard failed: {dash.text}"
            staff = client.get(f"{BASE_URL}/org/staff", headers=headers)
            assert staff.status_code == 200, f"Org staff failed: {staff.text}"
            print(f"  [OK] Org dashboard & staff: {len(staff.json())} staff members found")
            
        elif user["role"] == "RECEPTIONIST":
            rec = client.get(f"{BASE_URL}/reception/overview", headers=headers)
            assert rec.status_code == 200, f"Reception overview failed: {rec.text}"
            queue = client.get(f"{BASE_URL}/appointments/queue", headers=headers)
            assert queue.status_code == 200, f"Queue failed: {queue.text}"
            dup = client.get(f"{BASE_URL}/patients/check-duplicates?mobile_number=9876543210", headers=headers)
            assert dup.status_code == 200, f"Dup check failed: {dup.text}"
            print(f"  [OK] Reception overview, queue & duplicate check responsive")
            
        elif user["role"] == "DOCTOR":
            doc = client.get(f"{BASE_URL}/doctor/dashboard", headers=headers)
            assert doc.status_code == 200, f"Doctor dashboard failed: {doc.text}"
            print(f"  [OK] Doctor dashboard responsive. Active consultation: {doc.json().get('active_consultation') is not None}")


if __name__ == "__main__":
    test_role("PLATFORM OWNER", "superadmin@arogyascribe.in", "Admin@12345")
    test_role("ORG ADMIN", "orgadmin@arogyacare.in", "OrgAdmin@123")
    test_role("RECEPTIONIST", "reception@arogyacare.in", "Reception@123")
    test_role("DOCTOR", "dr.sharma@arogyacare.in", "Doctor@123")
    print("\n*** ALL 4 ROLES VERIFIED LIVE AGAINST RUNNING BACKEND SERVER (100% SUCCESS) ***")
