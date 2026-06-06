import mysql.connector
import random
import json
from datetime import datetime, timedelta

conn = mysql.connector.connect(host='localhost', user='root', password='jolohotdog789', database='renzrap_db')
cur = conn.cursor()

cur.execute("SELECT id, item_name, price FROM inventory")
items = cur.fetchall()
print(f"Loaded {len(items)} inventory items")

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 6, 6)
total_days = (end_date - start_date).days + 1

cur.execute("DELETE FROM sales")
conn.commit()
print("Cleared old sales")

# Monthly patterns (min_daily, max_daily, tx_min, tx_max)
# Jan: all-time highs, Feb: mid, Mar: slightly above Feb, Apr: lowest, May: rising, Jun: strong
MONTH_PATTERNS = {
    1:  (25000, 38000, 3, 8),    # Jan - mid (was Mar)
    2:  (22000, 35000, 3, 7),    # Feb - mid
    3:  (40000, 55000, 4, 10),   # Mar - HIGH (was Jan)
    4:  (12000, 22000, 2, 6),    # Apr - lowest
    5:  (20000, 38000, 3, 8),    # May - rising
    6:  (30000, 50000, 4, 9),    # Jun - strong
}

# Weekday multiplier: Mon-Fri busier, Sat-Sun slower
def weekday_mult(day_of_week):
    if day_of_week == 0 or day_of_week == 6:  # Sun=0, Sat=6
        return 0.7
    if day_of_week == 5:  # Fri
        return 1.15
    if day_of_week == 1:  # Mon
        return 1.1
    return 1.0

receipt_counter = 0

def next_receipt():
    global receipt_counter
    n = receipt_counter
    receipt_counter += 1
    return f"aaa{n:06d}"

busy_hours = list(range(8, 18))
total_sales = 0
tx_count = 0

for day_offset in range(total_days):
    current_date = start_date + timedelta(days=day_offset)
    month = current_date.month
    
    base_min, base_max, tx_min, tx_max = MONTH_PATTERNS[month]
    
    # Weekday adjustment
    wm = weekday_mult(current_date.weekday())
    
    daily_min = int(base_min * wm)
    daily_max = int(base_max * wm)
    
    # Random walk / noise within the range
    daily_target = random.randint(daily_min, daily_max)
    
    # Number of transactions
    num_tx = random.randint(tx_min, tx_max)
    
    # Split daily_target into transactions
    tx_amounts = []
    remaining = daily_target
    for t in range(num_tx):
        if t == num_tx - 1:
            tx_amounts.append(remaining)
        else:
            min_left = remaining // (num_tx - t)
            max_amt = remaining - (num_tx - t - 1) * 800
            if max_amt <= min_left:
                tx_amounts.append(min_left)
            else:
                tx_amounts.append(random.randint(min_left, max_amt))
            remaining -= tx_amounts[-1]
    
    for tx_amt in tx_amounts:
        tx_amt = round(tx_amt, 2)
        if tx_amt <= 0:
            continue
        
        receipt_id = next_receipt()
        
        num_items = random.randint(1, min(6, len(items)))
        tx_items = random.sample(items, num_items)
        
        raw_items = []
        raw_total = 0
        for item in tx_items:
            qty = random.randint(1, 3)
            price = float(item[2])
            subtotal = round(price * qty, 2)
            raw_items.append({
                "id": item[0],
                "name": item[1],
                "price": price,
                "quantity": qty,
                "subtotal": subtotal
            })
            raw_total += subtotal
        
        scale = tx_amt / raw_total if raw_total > 0 else 1
        scaled_items = []
        scaled_total = 0
        for i, it in enumerate(raw_items):
            if i == len(raw_items) - 1:
                st = round(tx_amt - scaled_total, 2)
            else:
                st = round(it["subtotal"] * scale, 2)
            scaled_items.append({
                "id": it["id"],
                "name": it["name"],
                "price": round(it["price"] * scale, 2),
                "quantity": it["quantity"],
                "subtotal": st
            })
            scaled_total += st
        
        final_total = round(scaled_total, 2)
        subtotal = round(final_total / 1.12, 2)
        vat = round(final_total - subtotal, 2)
        
        hour = random.choice(busy_hours)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        sold_at = current_date.replace(hour=hour, minute=minute, second=second)
        
        cur.execute(
            "INSERT INTO sales (id, items, subtotal, vat, total_price, sold_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (receipt_id, json.dumps(scaled_items), subtotal, vat, final_total, sold_at)
        )
        total_sales += final_total
        tx_count += 1
        
        if tx_count % 300 == 0:
            conn.commit()
            print(f"  {tx_count} tx so far...")
    
    if day_offset % 30 == 0:
        print(f"  {current_date.strftime('%Y-%m-%d')}: {num_tx} tx, daily PHP {daily_target:,}")

conn.commit()
cur.close()
conn.close()

print(f"\nDone! {tx_count} transactions across {total_days} days")
print(f"Total: PHP {total_sales:,.2f}")
