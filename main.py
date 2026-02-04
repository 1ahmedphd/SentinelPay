import json
import os
import sys
from datetime import datetime, timezone

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.data_sanitizer import DataSanitizer
from agents.risk_analyzer import RiskAnalyzer
from agents.compliance_reporter import ComplianceReporter
from utils.ollama_client import OllamaClient

def main():
    """
    Main function to orchestrate the transaction processing pipeline.
    """
    # Configuration
    TRANSACTIONS_FILE = 'data/transactions.json'
    BATCH_SIZE = 100
    VIOLATION_LOG_FILE = 'violations.log'

    # Initialize Ollama client and agents
    ollama_client = OllamaClient()
    data_sanitizer = DataSanitizer(mode='ollama', ollama_client=ollama_client, violation_log_file=VIOLATION_LOG_FILE)
    risk_analyzer = RiskAnalyzer(ollama_client=ollama_client)
    
    # Load raw transactions
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            raw_transactions = json.load(f)
            raw_transactions = raw_transactions[:1] # Process only 1 transaction
    except FileNotFoundError:
        print(f"Error: Transactions file not found at {TRANSACTIONS_FILE}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {TRANSACTIONS_FILE}")
        return

    print(f"Loaded {len(raw_transactions)} transactions.")

    # Prepare for processing
    all_sanitized_transactions = []
    all_violations = []
    
    # Process transactions in batches
    for i in range(0, len(raw_transactions), BATCH_SIZE):
        batch = raw_transactions[i:i + BATCH_SIZE]
        print(f"\n--- Processing batch {i // BATCH_SIZE + 1} ---")

        # --- Stage 1: Data Sanitization ---
        sanitized_batch = []
        for tx_log in batch:
            try:
                # The transaction log is assumed to be a string in the list
                sanitized_log = data_sanitizer.sanitize_transaction(tx_log)
                if sanitized_log:
                    # For now, we'll create a structured transaction. 
                    # This part might need to be adjusted based on the actual structure of sanitized_log
                    # and how it relates back to the original transaction.
                    # Let's assume the sanitizer returns a dictionary now.
                    
                    # A placeholder for matching sanitized log to original transaction
                    # In a real system, we'd have a stable transaction ID
                    # For now, let's just create a new structure
                    sanitized_tx = {
                        "transaction_id": f"txn_{len(all_sanitized_transactions) + len(sanitized_batch) + 1}",
                        "original_log": tx_log,
                        "sanitized_log": sanitized_log,
                        "timestamp": datetime.now(timezone.utc),
                         # Placeholder fields for risk analysis
                        "amount": 0,
                        "cardholder_details": {"name": "Unknown"},
                        "merchant_details": {"name": "Unknown", "country": "Unknown"}
                    }
                    sanitized_batch.append(sanitized_tx)
                else:
                    print(f"Failed to sanitize transaction: {tx_log}")
                    # Per instructions, stop processing if Agent 1 fails
                    print("Stopping processing due to sanitization failure.")
                    return
            except Exception as e:
                print(f"Error during sanitization: {e}")
                print("Stopping processing due to sanitization error.")
                return
        
        all_sanitized_transactions.extend(sanitized_batch)

        # --- Stage 2: Risk Analysis ---
        risk_score_mapping = {
            "Low": 1,
            "Medium": 5,
            "High": 10
        }
        analyzed_batch = []
        for tx in sanitized_batch:
            try:
                # LLM-based risk analysis
                risk_assessment = risk_analyzer.analyze_risk_with_llm(tx)
                if risk_assessment:
                    risk_level_str = risk_assessment.get('risk_level', 'Low')
                    tx['risk_score'] = risk_score_mapping.get(risk_level_str, 1)
                    tx['risk_reasoning'] = risk_assessment.get('reasoning', '')
                else:
                    # Fallback to rule-based if LLM fails
                    tx['risk_score'] = risk_analyzer.calculate_risk_score(tx)
                    tx['risk_reasoning'] = "Rule-based fallback"
                
                analyzed_batch.append(tx)

            except Exception as e:
                print(f"Error during risk analysis for transaction {tx.get('transaction_id')}: {e}")
                # Continue with basic scoring if Agent 2 fails
                tx['risk_score'] = risk_analyzer.calculate_risk_score(tx)
                tx['risk_reasoning'] = "Rule-based fallback due to error"
                analyzed_batch.append(tx)

    print("\n--- All batches processed ---")
    
    # Load violations logged by the sanitizer
    if os.path.exists(VIOLATION_LOG_FILE):
        with open(VIOLATION_LOG_FILE, 'r') as f:
            all_violations = [json.loads(line) for line in f]

    # --- Stage 3: Compliance Reporting ---
    print("\n--- Generating reports ---")
    compliance_reporter = ComplianceReporter(
        transactions=all_sanitized_transactions,
        violations=all_violations,
        ollama_client=ollama_client
    )

    # Generate and save reports
    summary_report = compliance_reporter.generate_daily_summary()
    compliance_reporter.save_as_json(summary_report, "daily_summary.json")

    detailed_report = compliance_reporter.generate_detailed_violation_report()
    compliance_reporter.save_as_json(detailed_report, "detailed_violation_report.json")
    
    try:
        print("Attempting to generate LLM-enhanced PDF report. This requires a LaTeX distribution (like MiKTeX or TeX Live) to be installed and in your system's PATH.")
        llm_enhanced_report = compliance_reporter.generate_llm_enhanced_report()
        compliance_reporter.save_as_json(llm_enhanced_report, "llm_enhanced_report.json")
        compliance_reporter.save_as_latex_pdf(llm_enhanced_report, "llm_enhanced_latex_report")
    except Exception as e:
        print(f"Could not generate LLM-enhanced report: {e}")

    print("\n--- Pipeline complete ---")

if __name__ == '__main__':
    main()
