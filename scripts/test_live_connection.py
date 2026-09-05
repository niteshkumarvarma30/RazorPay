import os
import sys
from dotenv import load_dotenv
import razorpay

load_dotenv()

def test_connection():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    print(f"Testing Razorpay API connection with Key ID: {key_id[:8]}... (secret: {'*' * 6})")
    
    if not key_id or not key_secret:
        print("ERROR: RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET missing in .env")
        return False

    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        payments = client.payment.all({"count": 5})
        print(f"SUCCESS! Retrieved {len(payments.get('items', []))} live test payments from Razorpay.")
        for p in payments.get("items", [])[:2]:
            print(f" - Payment ID: {p.get('id')}, Amount: ₹{p.get('amount')/100}, Status: {p.get('status')}")
        
        try:
            settlements = client.settlement.all({"count": 5})
            print(f"SUCCESS! Retrieved {len(settlements.get('items', []))} live settlements.")
        except Exception as se:
            print(f"Note on settlements endpoint: {se}")

        return True
    except Exception as e:
        print(f"Razorpay Connection Error: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
