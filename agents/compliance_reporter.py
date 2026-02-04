import json
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pylatex import Document, Section, Subsection, Tabular, MultiColumn, MultiRow, Command
from pylatex.utils import italic, NoEscape, bold
from utils.ollama_client import OllamaClient

class ComplianceReporter:
    def __init__(self, transactions, violations, ollama_client=None):
        self.transactions = transactions
        self.violations = violations
        self.ollama_client = ollama_client

    def generate_daily_summary(self):
        """
        Generates a daily summary report.
        """
        total_transactions = len(self.transactions)
        total_violations = len(self.violations)
        high_risk_transactions = [tx for tx in self.transactions if tx.get("risk_score", 0) > 5]
        
        compliance_percentage = 0
        if total_transactions > 0:
            compliant_transactions = total_transactions - len(set(v['transaction_id'] for v in self.violations))
            compliance_percentage = (compliant_transactions / total_transactions) * 100

        summary = {
            "report_date": datetime.now(timezone.utc).isoformat(),
            "total_transactions_processed": total_transactions,
            "total_violations_found": total_violations,
            "high_risk_transactions_detected": len(high_risk_transactions),
            "compliance_percentage": f"{compliance_percentage:.2f}%"
        }
        return summary

    def generate_detailed_violation_report(self):
        """
        Generates a detailed report for each violation.
        """
        report = []
        for violation in self.violations:
            report.append({
                "violation_id": violation.get("violation_id", "N/A"),
                "transaction_id": violation.get("transaction_id", "N/A"),
                "timestamp": violation.get("timestamp", "N/A"),
                "violation_type": violation.get("violation_type", "Unknown"),
                "context": self._get_transaction_context(violation.get("transaction_id")),
                "pci_requirement": self._get_pci_requirement(violation.get("violation_type")),
                "recommended_action": "Implement remediation steps as per PCI-DSS guidelines.",
                "severity_level": self._get_severity_level(violation.get("violation_type"))
            })
        return report

    def generate_llm_enhanced_report(self):
        """
        Generates a detailed violation report with LLM-powered explanations.
        """
        if not self.ollama_client:
            raise ValueError("Ollama client not provided for LLM-enhanced reporting.")

        report = self.generate_detailed_violation_report()
        print(f"--- Debug: Generating LLM explanations for {len(report)} violations. ---")
        for i, item in enumerate(report):
            print(f"--- Debug: Getting explanation for violation {i+1}/{len(report)} ---")
            print(f"--- Debug: Violation details: {item} ---")
            explanation = self.ollama_client.generate_compliance_explanation(item)
            if explanation is None:
                print(f"--- Debug: Failed to get explanation for violation {i+1}. ---")
                # Handle the case where the explanation is not generated
                item["llm_explanation"] = "Error: Could not generate explanation."
            else:
                print(f"--- Debug: Got explanation for violation {i+1}. ---")
                item["llm_explanation"] = explanation
        print("--- Debug: Finished generating LLM explanations. ---")
        return report

    def _get_transaction_context(self, transaction_id):
        """
        Retrieves the context of a transaction given its ID.
        """
        if not transaction_id:
            return "No transaction ID provided."
        for tx in self.transactions:
            if tx.get("transaction_id") == transaction_id:
                return f"Transaction Amount: {tx.get('amount')}, Cardholder: {tx['cardholder_details'].get('name')}"
        return f"Transaction with ID '{transaction_id}' not found."

    def _get_pci_requirement(self, violation_type):
        """
        Maps a violation type to a PCI-DSS requirement.
        """
        mapping = {
            "Full PAN stored": "PCI-DSS Requirement 3.4",
            "CVV in log": "PCI-DSS Requirement 3.2",
            "Expiration date stored": "PCI-DSS Requirement 3.2"
        }
        return mapping.get(violation_type, "N/A")

    def _get_severity_level(self, violation_type):
        """
        Determines the severity level of a violation.
        """
        if "PAN" in violation_type or "CVV" in violation_type:
            return "Critical"
        return "High"

    def save_as_json(self, data, filename):
        """
        Saves the given data as a JSON file.
        """
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Report saved to {filename}")

    def save_as_latex_pdf(self, report_data, filename):
        """
        Saves the given data as a stylish PDF file using LaTeX.
        """
        geometry_options = {
            "head": "40pt",
            "margin": "0.7in",
            "bottom": "0.7in",
        }
        doc = Document(geometry_options=geometry_options, documentclass="article")

        # Preamble
        doc.preamble.append(NoEscape(r'\usepackage[T1]{fontenc}'))
        doc.preamble.append(NoEscape(r'\usepackage{xcolor}'))
        doc.preamble.append(NoEscape(r'\usepackage{booktabs}'))
        doc.preamble.append(NoEscape(r'\usepackage{fancyhdr}'))
        doc.preamble.append(NoEscape(r'\usepackage{parskip}'))
        doc.preamble.append(NoEscape(r'\usepackage{graphicx}'))
        doc.preamble.append(NoEscape(r'\definecolor{sentinelblue}{HTML}{0D47A1}'))
        doc.preamble.append(NoEscape(r'\definecolor{lightgray}{HTML}{F5F5F5}'))
        doc.preamble.append(NoEscape(r'\pagestyle{fancy}'))
        doc.preamble.append(NoEscape(r'\fancyhf{}'))
        doc.preamble.append(NoEscape(r'\rhead{\small\textit{SentinelPay Analysis}}'))
        doc.preamble.append(NoEscape(r'\lhead{\small\textit{PCI-DSS Compliance Report}}'))
        doc.preamble.append(NoEscape(r'\cfoot{\thepage}'))
        
        # Title
        doc.preamble.append(Command('title', 'PCI-DSS Compliance Violation Report'))
        doc.preamble.append(Command('author', 'SentinelPay Analysis Engine'))
        doc.preamble.append(Command('date', datetime.now(timezone.utc).strftime('%B %d, %Y')))
        doc.append(NoEscape(r'\maketitle'))

        # Summary Table
        with doc.create(Section('Violations Summary', numbering=False)):
            with doc.create(Tabular(r'l l l l')) as table:
                table.add_row(['Violation ID', 'Transaction ID', 'Violation Type', 'Severity'], mapper=bold)
                table.add_hline()
                for item in report_data:
                    severity = item.get("severity_level", "N/A")
                    if severity == "Critical":
                        row = [item.get("violation_id"), item.get("transaction_id"), item.get("violation_type"), NoEscape(r'\textbf{\textcolor{red}{' + severity + '}}')]
                    else:
                        row = [item.get("violation_id"), item.get("transaction_id"), item.get("violation_type"), severity]
                    table.add_row(row)
                table.add_hline()

        doc.append(NoEscape(r'\newpage'))

        # Detailed Explanations
        with doc.create(Section('Detailed Violation Analysis', numbering=False)):
            for item in report_data:
                with doc.create(Subsection(f'Violation: {item.get("violation_id")} | Transaction: {item.get("transaction_id")}', numbering=False)):
                    doc.append(bold("Violation Type: "))
                    doc.append(item.get("violation_type"))
                    doc.append(NoEscape(r'\\'))
                    doc.append(bold("Severity: "))
                    if item.get("severity_level") == "Critical":
                         doc.append(NoEscape(r'\textbf{\textcolor{red}{Critical}}'))
                    else:
                        doc.append(item.get("severity_level", "N/A"))
                    doc.append(NoEscape(r'\\'))
                    doc.append(bold("PCI Requirement: "))
                    doc.append(item.get("pci_requirement"))
                    
                    doc.append(NoEscape(r'\vspace{4mm}'))
                    doc.append(bold("LLM Explanation:"))
                    
                    # Clean up the LLM explanation
                    explanation = item.get("llm_explanation", "No explanation provided.")
                    explanation_parts = explanation.split('\n\n')
                    
                    for part in explanation_parts:
                        if ':' in part:
                            title, content = part.split(':', 1)
                            doc.append(NoEscape(r'\vspace{2mm}'))
                            doc.append(italic(title.strip() + ":"))
                            doc.append(content.strip())
                        else:
                            doc.append(part.strip())
                    
                    doc.append(NoEscape(r'\vspace{5mm}\hrule'))

        try:
            print(f"--- Debug: Generating .tex file: {filename}.tex ---")
            # generate_tex will save the .tex file
            doc.generate_tex(filename)
            print(f"--- Debug: {filename}.tex file created. ---")

            # Read and print the content of the .tex file
            with open(f"{filename}.tex", "r") as f:
                print(f"--- Debug: Content of {filename}.tex ---")
                print(f.read())
                print("--- End of .tex content ---")

            print(f"--- Debug: Calling generate_pdf for {filename}.pdf ---")
            doc.generate_pdf(filename, clean_tex=False)
            print(f"Stylish LaTeX PDF report saved to {filename}.pdf")
        except Exception as e:
            print(f"Could not generate PDF. Ensure you have a LaTeX distribution (like MiKTeX or TeX Live) installed and in your system's PATH. Error: {e}")

