import requests

API_URL = "http://localhost:8000"

try:
    # 1. Register
    requests.post(f"{API_URL}/auth/register", json={
        "fullname": "Test",
        "email": "testpayment@example.com",
        "password": "password"
    })
except Exception as e:
    pass

# 2. Login
res = requests.post(f"{API_URL}/auth/login", json={
    "email": "testpayment@example.com",
    "password": "password"
})
if res.status_code == 200:
    token = res.json()["token"]
    print("Logged in, token len:", len(token))
    
    # 3. Create payment url
    headers = {"Authorization": f"Bearer {token}"}
    res2 = requests.post(f"{API_URL}/payment/create_payment_url", json={
        "amount": 10000,
        "tokens": 10
    }, headers=headers)
    print("Payment URL status:", res2.status_code)
    print("Payment URL response:", res2.json())
else:
    print("Login failed", res.json())