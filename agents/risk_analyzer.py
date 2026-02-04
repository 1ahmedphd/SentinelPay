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


