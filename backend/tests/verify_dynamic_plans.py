import httpx

# 1. Login as Platform Owner
login_res = httpx.post(
    "http://127.0.0.1:8000/api/v1/auth/login",
    json={"email": "superadmin@arogyascribe.in", "password": "Admin@12345"},
)
assert login_res.status_code == 200, f"Login failed: {login_res.text}"
token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Get Plans
plans_res = httpx.get("http://127.0.0.1:8000/api/v1/platform/plans", headers=headers)
starter_plan = next(p for p in plans_res.json() if p["code"] == "STARTER")
print("Initial Starter Price in DB: ₹", starter_plan["monthly_price"])

# 3. Super Admin changes price from 4999 to 5499
patch_res = httpx.patch(
    f"http://127.0.0.1:8000/api/v1/platform/plans/{starter_plan['id']}",
    json={"monthly_price": 5499.00},
    headers=headers,
)
assert patch_res.status_code == 200, f"Patch failed: {patch_res.text}"
print("Patched Starter Price to 5499.00 in DB")

# 4. Check Public API (Landing Page fetch)
pub_res = httpx.get("http://127.0.0.1:8000/api/v1/plans/public")
pub_starter = next(p for p in pub_res.json() if p["code"] == "STARTER")
print("Public API immediately reflects new price: ₹", pub_starter["monthly_price"])
assert float(pub_starter["monthly_price"]) == 5499.00, "Price mismatch!"

# 5. Restore to production spec: 4999.00
restore_res = httpx.patch(
    f"http://127.0.0.1:8000/api/v1/platform/plans/{starter_plan['id']}",
    json={"monthly_price": 4999.00},
    headers=headers,
)
assert restore_res.status_code == 200
pub_res2 = httpx.get("http://127.0.0.1:8000/api/v1/plans/public")
pub_starter2 = next(p for p in pub_res2.json() if p["code"] == "STARTER")
print("Restored to exact production spec: ₹", pub_starter2["monthly_price"])
assert float(pub_starter2["monthly_price"]) == 4999.00
print("\n*** DYNAMIC DATABASE-DRIVEN PRICING FULLY VERIFIED (ZERO CACHE LAG) ***")

