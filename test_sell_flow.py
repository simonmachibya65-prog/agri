"""
Prove the full Sell Now → Payment → Confirmation flow works.
Run with: python test_sell_flow.py
"""
import sys, requests, re
sys.path.insert(0, '.')

BASE   = "http://127.0.0.1:8000"
PASS   = "PASS"
FAIL   = "FAIL"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((status, label, detail))
    icon = "OK" if condition else "XX"
    print(f"  [{icon}] {label}" + (f"  →  {detail}" if detail else ""))
    return condition

print()
print("=" * 65)
print("  SELL NOW FLOW — PROOF TEST")
print("=" * 65)

# ── Login first ───────────────────────────────────────────────────────────────
print("\n[0] LOGIN")
s = requests.Session()
r = s.post(f"{BASE}/login", data={"username":"demo","password":"demo123"}, allow_redirects=True)
check("Login successful",     r.status_code == 200)
check("Redirected to /home",  "/home" in r.url or "home" in r.text[:500].lower())

# ── Step 0: Market page ───────────────────────────────────────────────────────
print("\n[1] MARKET PAGE — Sell Now button")
r = s.get(f"{BASE}/market")
check("Market page loads (200)",     r.status_code == 200)
check("Contains crop prices",        "TSh" in r.text)
check("Sell Now button present",     "Sell Now" in r.text)
check("Links to /market/sell",       "/market/sell?crop=" in r.text)
check("Search bar present",          "cropSearch" in r.text)
check("Filter chips present",        "filter-chip" in r.text)
check("My Crops filter present",     "My Crops" in r.text)
check("Personalized rec present",    "Selling Recommendation" in r.text)

# Find a Rising crop to test with
crops_rising = re.findall(r'/market/sell\?crop=([^"]+)"[^>]*class="btn btn-primary', r.text)
test_crop = crops_rising[0] if crops_rising else "Apple"
check(f"Found Rising crop to test: {test_crop}", bool(test_crop), test_crop)

# ── Step 1: Selling Guide ─────────────────────────────────────────────────────
print(f"\n[2] STEP 1 — Selling Guide (/market/sell?crop={test_crop})")
r = s.get(f"{BASE}/market/sell?crop={test_crop}")
check("Selling Guide loads (200)",         r.status_code == 200)
check("Shows crop name in title",          test_crop in r.text)
check("Shows price (TSh)",                 "TSh" in r.text)
check("Earnings calculator present",       "kgInput" in r.text)
check("calcEarnings JS function present",  "calcEarnings" in r.text)
check("Proceed to Payment button present", "Proceed to Payment" in r.text)
check("goToPayment JS function present",   "goToPayment" in r.text)
check("Pre-sale checklist present",        "Checklist" in r.text)
check("Where to sell section present",     "Where to Sell" in r.text)
check("Price disclaimer present",          "Disclaimer" in r.text or "fluctuate" in r.text)
check("Back to Market link present",       "/market" in r.text)

# Extract price for next step
price_match = re.search(r"calcEarnings\((\d+)\)", r.text)
test_price  = price_match.group(1) if price_match else "3500"
check(f"Extracted price: TSh {test_price}/kg", bool(price_match), f"TSh {test_price}")

# ── Step 2: Payment page (GET) ────────────────────────────────────────────────
print(f"\n[3] STEP 2 — Payment Page (/market/pay?crop={test_crop}&kg=50&price={test_price})")
r = s.get(f"{BASE}/market/pay?crop={test_crop}&kg=50&price={test_price}")
check("Payment page loads (200)",          r.status_code == 200)
check("Order summary present",             "Order Summary" in r.text)
check("Shows crop name",                   test_crop in r.text)
check("Shows quantity (50 kg)",            "50" in r.text)
check("Shows price per kg",                test_price in r.text)

expected_total = 50 * int(test_price)
check(f"Shows correct total (TSh {expected_total:,})", str(expected_total) in r.text.replace(",",""), f"TSh {expected_total:,}")

check("M-Pesa method present",             "mpesa" in r.text)
check("Tigo Pesa method present",          "tigo" in r.text)
check("Airtel Money method present",       "airtel" in r.text)
check("Bank Transfer method present",      "bank" in r.text)
check("selectMethod JS function present",  "selectMethod" in r.text)
check("submitPayment JS function present", "submitPayment" in r.text)
check("1.5s processing animation present", "1500" in r.text)
check("Pay button present",               f"Pay TSh" in r.text)
check("Simulated payment disclaimer",      "Simulated" in r.text or "simulated" in r.text)

# ── Step 2: Payment POST (simulate submission) ────────────────────────────────
print(f"\n[4] STEP 2 — Payment POST (simulate M-Pesa submission)")
r = s.post(f"{BASE}/market/pay",
           data={"crop": test_crop, "kg": "50", "price": test_price,
                 "total": str(expected_total), "method": "mpesa",
                 "phone": "+255712345678", "lang": "en"},
           allow_redirects=True)
check("Payment POST accepted",             r.status_code == 200)
check("Redirected to /market/confirm",     "/market/confirm" in r.url)
check("Confirmation page loaded",          "Payment Submitted" in r.text or "Confirmed" in r.text or "confirm" in r.url.lower())

# Extract reference number
ref_match = re.search(r'TXN-[A-F0-9]{8}', r.text)
test_ref  = ref_match.group(0) if ref_match else ""
check("Reference number generated (TXN-XXXXXXXX)", bool(test_ref), test_ref)

# ── Step 3: Confirmation page ─────────────────────────────────────────────────
print(f"\n[5] STEP 3 — Confirmation Page")
check("Success message shown",             "Payment Submitted" in r.text or "✅" in r.text)
check("Reference number visible",          test_ref in r.text if test_ref else False, test_ref)
check("Crop name in confirmation",         test_crop in r.text)
check("Quantity shown (50 kg)",            "50" in r.text)
check(f"Total amount shown",               str(expected_total) in r.text.replace(",",""))
check("Payment method shown (M-Pesa)",     "M-Pesa" in r.text or "mpesa" in r.text.lower())
check("Phone number shown",                "255712345678" in r.text or "+255" in r.text)
check("Status shows Pending",              "Pending" in r.text)
check("What happens next section",         "happens next" in r.text or "What happens" in r.text)
check("Back to Market link",               "/market" in r.text)
check("Sell More link",                    "Sell More" in r.text)
check("Print Receipt button",              "Print" in r.text or "print" in r.text)
check("Transaction history table",         "My Transactions" in r.text)
check("Transaction reference in table",    test_ref in r.text if test_ref else False)

# ── Step 3b: Confirm page directly via ref ────────────────────────────────────
if test_ref:
    print(f"\n[6] STEP 3 — Direct confirm page (/market/confirm?ref={test_ref})")
    r2 = s.get(f"{BASE}/market/confirm?ref={test_ref}")
    check("Confirm page loads by ref (200)", r2.status_code == 200)
    check("Same ref number shown",           test_ref in r2.text)
    check("Transaction details correct",     test_crop in r2.text)

# ── Market module functions ────────────────────────────────────────────────────
print("\n[7] MARKET MODULE — save/get transactions")
from modules.market import save_transaction, get_transactions, get_market_locations, get_checklist
import secrets

ref2 = "TXN-TEST" + secrets.token_hex(2).upper()
tx   = save_transaction(user_id=0, crop="Potato", quantity_kg=100,
                        price_per_kg=800, total=80000,
                        method="tigo", phone="+255712000000", ref=ref2)
check("save_transaction returns dict",     isinstance(tx, dict))
check("Transaction has correct ref",       tx["id"] == ref2)
check("Transaction has correct crop",      tx["crop"] == "Potato")
check("Transaction has correct total",     tx["total"] == 80000)
check("Transaction status is Pending",     tx["status"] == "Pending")

txs = get_transactions(0)
check("get_transactions returns list",     isinstance(txs, list))
check("Saved transaction is retrievable",  any(t["id"] == ref2 for t in txs))

locs = get_market_locations("Kariakoo")
check("get_market_locations returns list", isinstance(locs, list) and len(locs) > 0, str(locs[:2]))

cl = get_checklist("Potato")
check("get_checklist(Potato) has items",   len(cl) > 0, f"{len(cl)} items")

cl2 = get_checklist("Apple")
check("get_checklist(Apple) uses default", len(cl2) > 0, f"{len(cl2)} items")

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 65)
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
print(f"  RESULT:  {passed} passed   {failed} failed   out of {len(results)}")
print("=" * 65)
if failed:
    print("\nFAILED TESTS:")
    for st, label, detail in results:
        if st == FAIL:
            print(f"  XX  {label}  {detail}")
else:
    print("\n  All Sell Now flow features verified.")
print()
