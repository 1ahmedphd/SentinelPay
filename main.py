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

def run_pipeline(raw_transactions, output_dir='.'):
    """
    Main function to orchestrate the transaction processing pipeline.
    """
    # Configuration
    BATCH_SIZE = 100
    VIOLATION_LOG_FILE = os.path.join(output_dir, 'violations.log')

    # Initialize Ollama client and agents
    ollama_client = OllamaClient()
    data_sanitizer = DataSanitizer(mode='ollama', ollama_client=ollama_client, violation_log_file=VIOLATION_LOG_FILE)
    risk_analyzer = RiskAnalyzer(ollama_client=ollama_client)
    compliance_reporter = ComplianceReporter(
        transactions=[],  # Will be populated later
        violations=[],    # Will be populated later
        ollama_client=ollama_client
    )

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
        for idx, tx_log in enumerate(batch):
            print(f"  [Batch {i // BATCH_SIZE + 1}] Sanitizing transaction {idx + 1}/{len(batch)}...")
            try:
                sanitized_log = data_sanitizer.sanitize_transaction(tx_log)
                if sanitized_log:
                    sanitized_tx = {
                        "transaction_id": f"txn_{len(all_sanitized_transactions) + len(sanitized_batch) + 1}",
                        "original_log": tx_log,
                        "sanitized_log": sanitized_log,
                        "timestamp": datetime.now(timezone.utc).isoformat(), # Store as ISO format string
                         # Placeholder fields for risk analysis
                        "amount": 0,
                        "cardholder_details": {"name": "Unknown"},
                        "merchant_details": {"name": "Unknown", "country": "Unknown"}
                    }
                    sanitized_batch.append(sanitized_tx)
                    print(f"  [Batch {i // BATCH_SIZE + 1}] Sanitization for transaction {idx + 1} successful.")
                else:
                    print(f"  [Batch {i // BATCH_SIZE + 1}] Failed to sanitize transaction: {tx_log}")
                    print("  Skipping transaction due to sanitization failure.") # Continue instead of stopping
            except Exception as e:
                print(f"  [Batch {i // BATCH_SIZE + 1}] Error during sanitization for transaction {tx_log}: {e}")
                print("  Skipping transaction due to sanitization error.") # Continue instead of stopping
        
        all_sanitized_transactions.extend(sanitized_batch)
        print(f"--- Batch {i // BATCH_SIZE + 1} sanitization complete. ---")

        # --- Stage 2: Risk Analysis ---
        risk_score_mapping = {
            "Low": 1,
            "Medium": 5,
            "High": 10
        }
        analyzed_batch = []
        for idx, tx in enumerate(sanitized_batch):
            print(f"  [Batch {i // BATCH_SIZE + 1}] Analyzing risk for transaction {idx + 1}/{len(sanitized_batch)}...")
            try:
                # LLM-based risk analysis
                risk_assessment = risk_analyzer.analyze_risk_with_llm(tx)
                if risk_assessment:
                    risk_level_str = risk_assessment.get('risk_level', 'Low')
                    tx['risk_score'] = risk_score_mapping.get(risk_level_str, 1)
                    tx['risk_reasoning'] = risk_assessment.get('reasoning', '')
                    print(f"  [Batch {i // BATCH_SIZE + 1}] Risk analysis for transaction {idx + 1} successful (LLM).")
                else:
                    # Fallback to rule-based if LLM fails
                    tx['risk_score'] = risk_analyzer.calculate_risk_score(tx)
                    tx['risk_reasoning'] = "Rule-based fallback"
                    print(f"  [Batch {i // BATCH_SIZE + 1}] Risk analysis for transaction {idx + 1} successful (Rule-based fallback).")
                
                analyzed_batch.append(tx)

            except Exception as e:
                print(f"  [Batch {i // BATCH_SIZE + 1}] Error during risk analysis for transaction {tx.get('transaction_id')}: {e}")
                # Continue with basic scoring if Agent 2 fails
                tx['risk_score'] = risk_analyzer.calculate_risk_score(tx)
                tx['risk_reasoning'] = "Rule-based fallback due to error"
                analyzed_batch.append(tx)
                print(f"  [Batch {i // BATCH_SIZE + 1}] Risk analysis for transaction {idx + 1} completed with error (Rule-based fallback).")
        print(f"--- Batch {i // BATCH_SIZE + 1} risk analysis complete. ---")
    
    # Update compliance reporter with all processed transactions
    compliance_reporter.transactions = all_sanitized_transactions

    print("\n--- All batches processed ---")
    
    # Load violations logged by the sanitizer
    if os.path.exists(VIOLATION_LOG_FILE):
        with open(VIOLATION_LOG_FILE, 'r') as f:
            all_violations = [json.loads(line) for line in f]
        compliance_reporter.violations = all_violations


    # --- Stage 3: Compliance Reporting ---
    print("\n--- Generating reports ---")
    
    reports = {}

    summary_report = compliance_reporter.generate_daily_summary()
    reports['daily_summary'] = summary_report
    compliance_reporter.save_as_json(summary_report, os.path.join(output_dir, "daily_summary.json"))

    detailed_report = compliance_reporter.generate_detailed_violation_report()
    reports['detailed_violation_report'] = detailed_report
    compliance_reporter.save_as_json(detailed_report, os.path.join(output_dir, "detailed_violation_report.json"))
    
    try:
        print("Attempting to generate LLM-enhanced PDF report. This requires a LaTeX distribution (like MiKTeX or TeX Live) to be installed and in your system's PATH.")
        llm_enhanced_report = compliance_reporter.generate_llm_enhanced_report()
        reports['llm_enhanced_report'] = llm_enhanced_report
        compliance_reporter.save_as_json(llm_enhanced_report, os.path.join(output_dir, "llm_enhanced_report.json"))
        compliance_reporter.save_as_latex_pdf(llm_enhanced_report, os.path.join(output_dir, "llm_enhanced_latex_report"))
        reports['llm_enhanced_pdf_path'] = os.path.join(output_dir, "llm_enhanced_latex_report.pdf")
    except Exception as e:
        print(f"Could not generate LLM-enhanced report: {e}")
        reports['llm_enhanced_report_error'] = str(e)

    print("\n--- Pipeline complete ---")
    return reports, all_sanitized_transactions, all_violations

if __name__ == '__main__':
    TRANSACTIONS_FILE = 'data/transactions.json'
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            raw_transactions = json.load(f)
    except FileNotFoundError:
        print(f"Error: Transactions file not found at {TRANSACTIONS_FILE}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {TRANSACTIONS_FILE}")
        sys.exit(1)
    
    reports, _, _ = run_pipeline(raw_transactions)
    print("\nGenerated Reports:")
    for key, value in reports.items():
        if isinstance(value, dict):
            print(f"- {key}: {len(json.dumps(value))} bytes (JSON)")
        else:
            print(f"- {key}: {value}")
