from datetime import datetime, timedelta, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ollama_client import OllamaClient
import json

class RiskAnalyzer:
    def __init__(self, ollama_client=None):
        self.risk_rules = {
            "high_transaction_value": {"threshold": 1000, "score": 3},
            "multiple_transactions_short_period": {"period": timedelta(minutes=5), "count": 3, "score": 4},
            "unusual_country": {"banned_countries": ["US", "AU"], "score": 5},
        }
        self.transaction_history = {}
        self.ollama_client = ollama_client

    def calculate_risk_score(self, transaction):
        """
        Calculates a risk score for a given transaction based on a set of rules.
        """
        risk_score = 0
        
        # Rule: High transaction value
        if transaction["amount"] > self.risk_rules["high_transaction_value"]["threshold"]:
            risk_score += self.risk_rules["high_transaction_value"]["score"]
            print(f"Risk rule triggered: High transaction value (>${self.risk_rules['high_transaction_value']['threshold']})")

        # Rule: Multiple transactions in a short period
        self._update_transaction_history(transaction)
        if self._check_multiple_transactions(transaction):
            risk_score += self.risk_rules["multiple_transactions_short_period"]["score"]
            print(f"Risk rule triggered: Multiple transactions in a short period")

        # Rule: Unusual country
        if transaction["merchant_details"]["country"] not in self.risk_rules["unusual_country"]["banned_countries"]:
            risk_score += self.risk_rules["unusual_country"]["score"]
            print(f"Risk rule triggered: Unusual country ({transaction['merchant_details']['country']})")

        return risk_score

    def _update_transaction_history(self, transaction):
        """
        Updates the transaction history for a given cardholder.
        """
        cardholder = transaction["cardholder_details"]["name"]
        if cardholder not in self.transaction_history:
            self.transaction_history[cardholder] = []
        self.transaction_history[cardholder].append(transaction)

    def _check_multiple_transactions(self, transaction):
        """
        Checks if a cardholder has made multiple transactions within a short period.
        """
        cardholder = transaction["cardholder_details"]["name"]
        now = transaction["timestamp"]
        period = self.risk_rules["multiple_transactions_short_period"]["period"]
        count = self.risk_rules["multiple_transactions_short_period"]["count"]

        recent_transactions = [
            t for t in self.transaction_history[cardholder] if now - t['timestamp'] <= period
        ]
        return len(recent_transactions) >= count

    def analyze_risk_with_llm(self, transaction):
        """
        Analyzes the risk of a transaction using the LLM.
        """
        if not self.ollama_client:
            raise ValueError("Ollama client not provided.")
        
        cardholder = transaction["cardholder_details"]["name"]
        history = self.transaction_history.get(cardholder, [])
        
        return self.ollama_client.analyze_risk(transaction, history)

if __name__ == '__main__':
    # Rule-based analysis
    print("--- Rule-based Risk Analysis ---")
    rule_analyzer = RiskAnalyzer()
    now = datetime.now(timezone.utc)
    transactions = [
        {"transaction_id": "txn_123", "timestamp": now - timedelta(minutes=6), "amount": 100, "cardholder_details": {"name": "J*** D**"}, "merchant_details": {"name": "Test Merchant", "country": "US"}},
        {"transaction_id": "txn_124", "timestamp": now - timedelta(minutes=4), "amount": 200, "cardholder_details": {"name": "J*** D**"}, "merchant_details": {"name": "Test Merchant", "country": "US"}},
        {"transaction_id": "txn_125", "timestamp": now - timedelta(minutes=3), "amount": 50, "cardholder_details": {"name": "J*** D**"}, "merchant_details": {"name": "Test Merchant", "country": "US"}},
        {"transaction_id": "txn_126", "timestamp": now, "amount": 1500, "cardholder_details": {"name": "J*** D**"}, "merchant_details": {"name": "Test Merchant", "country": "CA"}},
    ]
    for tx in transactions:
        print(f"--- Analyzing transaction {tx['transaction_id']} ---")
        score = rule_analyzer.calculate_risk_score(tx)
        print(f"Risk score: {score}")

    # LLM-based analysis
    print("\n--- LLM-based Risk Analysis ---")
    try:
        ollama_client = OllamaClient()
        llm_analyzer = RiskAnalyzer(ollama_client=ollama_client)
        # Populate history for the LLM analyzer
        for tx in transactions[:-1]:
             llm_analyzer._update_transaction_history(tx)
        
        high_risk_tx = transactions[-1]
        print(f"--- Analyzing high-risk transaction {high_risk_tx['transaction_id']} with LLM ---")
        risk_assessment = llm_analyzer.analyze_risk_with_llm(high_risk_tx)
        if risk_assessment:
            print("LLM Risk Assessment:")
            print(json.dumps(risk_assessment, indent=2))

    except Exception as e:
        print(f"Could not run LLM-based risk analysis: {e}")

