import os
import random
import razorpay
from dotenv import load_dotenv

load_dotenv()

def create_live_test_payments(count=5):
    """
    Creates real live test payments in your Razorpay Test Mode account
    using Razorpay Orders and Payment Links API.
    """
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        print("❌ RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET missing in .env")
        return

    client = razorpay.Client(auth=(key_id, key_secret))
    print(f"🚀 Connecting to Razorpay Test API ({key_id})...\n")

    sample_amounts = [799, 1299, 1999, 2499, 4999]

    created_links = []
    for i in range(count):
        amt = sample_amounts[i % len(sample_amounts)]
        payload = {
            "amount": amt * 100, # Razorpay expects amount in paise
            "currency": "INR",
            "accept_partial": False,
            "description": f"Live Test Order #{random.randint(1000, 9999)}",
            "customer": {
                "name": f"Test Customer {i+1}",
                "email": f"customer{i+1}@example.com",
                "contact": f"+9198765{random.randint(10000, 99999)}"
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": False,
            "notes": {
                "source": "AI Finance Controller Live Seed"
            }
        }

        try:
            link = client.payment_link.create(payload)
            created_links.append((amt, link.get("short_url") or link.get("url"), link.get("id")))
            print(f"✅ Created Payment Link #{i+1} for ₹{amt}: {link.get('short_url')}")
        except Exception as e:
            print(f"⚠️ Error creating payment link #{i+1}: {e}")

    print("\n" + "="*70)
    print("👉 To turn these links into CAPTURED payments:")
    print("1. Click any of the links above in your browser.")
    print("2. Choose UPI / Card -> Click 'Success' on Razorpay simulator.")
    print("3. Click '🔄 Refresh' on http://localhost:8000 to see them live!")
    print("="*70)

if __name__ == "__main__":
    create_live_test_payments(count=3)
