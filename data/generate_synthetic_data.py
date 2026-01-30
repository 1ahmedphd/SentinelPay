import json
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

def create_fake_pan(faker_instance):
    """Generate a fake Primary Account Number (PAN)."""
    return faker_instance.credit_card_number()

def generate_transactions(num_transactions=1000):
    """Generate a list of synthetic transactions."""
    transactions = []
    pan_to_last_tx = {}

    for _ in range(num_transactions):
        pan = create_fake_pan(fake)
        is_violation = random.random() < 0.1  # 10% chance of a violation
        is_suspicious = random.random() < 0.05 # 5% chance of suspicious activity

        # --- Create a base transaction ---
        transaction = {
            "transaction_id": str(uuid.uuid4()),
            "pan": pan,
            "cardholder_name": fake.name(),
            "transaction_amount": round(random.uniform(5.0, 1500.0), 2),
            "merchant_details": fake.company(),
            "timestamp": fake.date_time_this_year().isoformat(),
            "location_data": {
                "city": fake.city(),
                "country": fake.country(),
            }
        }

        # --- Introduce intentional violations and anomalies ---

        # PCI-DSS Rule 3.2 Violation: Storing CVV
        if is_violation:
            transaction["cvv"] = fake.credit_card_security_code()

        # Suspicious Pattern: Unusually high transaction amount
        if is_suspicious:
            transaction["transaction_amount"] = round(random.uniform(5000.0, 25000.0), 2)
            transaction["suspicion_reason"] = "Unusually high transaction amount"

        # Suspicious Pattern: Rapid transactions from different locations
        if pan in pan_to_last_tx and not is_suspicious:
            last_tx_time_str, last_location = pan_to_last_tx[pan]
            last_tx_time = datetime.fromisoformat(last_tx_time_str)
            current_time = datetime.fromisoformat(transaction["timestamp"])
            current_location = transaction["location_data"]["country"]

            if (current_time - last_tx_time) < timedelta(hours=1) and current_location != last_location:
                transaction["suspicion_reason"] = "Rapid transaction from a different geographic location"
                # Also flag the previous transaction
                for t in reversed(transactions):
                    if t["pan"] == pan:
                        t["suspicion_reason"] = "Rapid transaction followed by another from a different location"
                        break
        
        pan_to_last_tx[pan] = (transaction["timestamp"], transaction["location_data"]["country"])


        transactions.append(transaction)

    return transactions

def save_transactions_to_json(transactions, filename="transactions.json"):
    """Save transactions to a JSON file."""
    with open(filename, "w") as f:
        json.dump(transactions, f, indent=4)

if __name__ == "__main__":
    num_records = 2000
    print(f"Generating {num_records} synthetic transactions...")
    synthetic_transactions = generate_transactions(num_records)
    
    output_filename = "transactions.json"
    save_transactions_to_json(synthetic_transactions, output_filename)
    
    print(f"Successfully generated and saved transactions to '{output_filename}'.")
    print("Sample transaction:")
    print(json.dumps(synthetic_transactions[0], indent=4))
