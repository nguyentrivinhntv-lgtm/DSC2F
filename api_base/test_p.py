import asyncio
import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from app.security.security import create_access_token
from app.routers.payment import create_payment_url, PaymentRequest
from fastapi import Request

async def main():
    try:
        token = create_access_token(data={"sub": "1"})
        print("Token:", token[:10])
        
        class MockRequest:
            class Client:
                host = "127.0.0.1"
            client = Client()

        req = PaymentRequest(amount=10000, tokens=10)
        ret = await create_payment_url(request=MockRequest(), body=req, current_user={"id": 1, "username": "test"})
        print("URL:", ret)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
