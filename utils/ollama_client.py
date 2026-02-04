import ollama
import json
import re
from datetime import datetime, timedelta

class OllamaClient:
    def __init__(self, sanitizer_model="mistral:7b-instruct", risk_model="sentinel-risk-analyzer", compliance_model="sentinel-compliance-explainer"):
        self.sanitizer_model = sanitizer_model
        self.risk_model = risk_model
        self.compliance_model = compliance_model
        self.system_prompt = """You are a PCI-DSS compliance expert. Your task is to analyze a given transaction log and return a JSON object with two keys: "sanitized_log" and "violations".

- "sanitized_log": The sanitized version of the log, with PANs masked (first 6 and last 4 digits visible), CVVs removed, and cardholder names partially masked.
- "violations": A list of any PCI-DSS violations found in the original log. Each violation should be a JSON object with the following keys:
    - "transaction_id": A placeholder for the transaction ID (you can use "N/A" for now).
    - "violation_type": A description of the violation (e.g., "Full PAN stored", "CVV in log").
    - "timestamp": The current UTC timestamp in ISO 8601 format.
    - "confidence_score": A score from 0.0 to 1.0 indicating your confidence in the violation detection.

Example Input: "Transaction from John Doe with card 4111-1111-1111-1111 (CVV: 123) for $150.00"
Example Output:
{
  "sanitized_log": "Transaction from J*** D** with card 411111******1111 for $150.00",
  "violations": [
    {
      "transaction_id": "N/A",
      "violation_type": "Full PAN stored",
      "timestamp": "...",
      "confidence_score": 0.95
    },
    {
      "transaction_id": "N/A",
      "violation_type": "CVV in log",
      "timestamp": "...",
      "confidence_score": 1.0
    }
  ]
}
"""

    def process_transaction(self, transaction_log):
        """
        Sends a transaction log to the Ollama model for analysis and sanitization,
        expecting a JSON response.
        """
        try:
            response = ollama.chat(
                model=self.sanitizer_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Sanitize and analyze the following transaction log: {transaction_log}"}
                ],
                options={"temperature": 0.0} # Lower temperature for more deterministic output
            )
            
            response_content = response['message']['content']

            # Find all content within ``` backticks
            matches = re.findall(r'```(?:json)?\n(.*?)\n```', response_content, re.DOTALL)

            sanitized_log = ""
            violations = []

            if matches:
                # The first match should be the sanitized log
                sanitized_log = matches[0].strip()
                # The second match should be the violations
                if len(matches) > 1:
                    try:
                        violations = json.loads(matches[1])
                    except json.JSONDecodeError:
                        print("Could not parse violations JSON")
                        pass # Keep violations as empty list

            # If no backticks found, try to find a JSON object directly
            else:
                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_string = response_content[json_start:json_end]
                    try:
                        data = json.loads(json_string)
                        sanitized_log = data.get("sanitized_log", "")
                        violations = data.get("violations", [])
                    except json.JSONDecodeError:
                        pass # Keep sanitized_log and violations as empty

            return {
                "sanitized_log": sanitized_log,
                "violations": violations
            }

        except Exception as e:
            print(f"An error occurred while communicating with Ollama: {e}")
            return None

    def analyze_risk(self, transaction, transaction_history):
        """
        Sends a transaction and its history to the Ollama model for risk analysis.
        """
        prompt = f"""
Analyze the following transaction and provide a risk assessment in JSON format.

Transaction: {json.dumps(transaction, default=str)}
Transaction History: {json.dumps(transaction_history, default=str)}

Return ONLY the JSON object.
"""
        try:
            response = ollama.chat(
                model=self.risk_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.0}
            )
            response_content = response['message']['content']
            print("--- LLM Risk Analysis Response ---")
            print(response_content)
            print("---------------------------------")

            try:
                # First, try to find and parse a JSON object
                matches = re.findall(r'```(?:json)?\n(.*?)\n```', response_content, re.DOTALL)
                if matches:
                    json_string = matches[0].strip()
                    return json.loads(json_string)

                json_start = response_content.find('{')
                json_end = response_content.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_string = response_content[json_start:json_end]
                    return json.loads(json_string)

                # If no JSON object is found, fall back to regex for text parsing
                risk_level_match = re.search(r"Risk Level:\s*(High|Medium|Low)", response_content, re.IGNORECASE)
                reasoning_match = re.search(r"Reasoning:\s*(.*)", response_content, re.IGNORECASE | re.DOTALL)

                if risk_level_match and reasoning_match:
                    risk_level = risk_level_match.group(1).strip()
                    reasoning = reasoning_match.group(1).strip()
                    
                    return {
                        "risk_level": risk_level,
                        "reasoning": reasoning
                    }
                else:
                    print("Error: Could not parse risk level and reasoning from the response.")
                    return None
            except (json.JSONDecodeError, IndexError) as e:
                print(f"An error occurred during response parsing: {e}")
                # Fallback to regex if JSON parsing fails
                risk_level_match = re.search(r"Risk Level:\s*(High|Medium|Low)", response_content, re.IGNORECASE)
                reasoning_match = re.search(r"Reasoning:\s*(.*)", response_content, re.IGNORECASE | re.DOTALL)

                if risk_level_match and reasoning_match:
                    risk_level = risk_level_match.group(1).strip()
                    reasoning = reasoning_match.group(1).strip()
                    
                    return {
                        "risk_level": risk_level,
                        "reasoning": reasoning
                    }
                else:
                    print("Error: Could not parse risk level and reasoning from the response on fallback.")
                    return None
        except Exception as e:
            print(f"An error occurred during risk analysis with Ollama: {e}")
            return None

    def generate_compliance_explanation(self, violation):
        """
        Generates a human-readable explanation for a compliance violation.
        """
        prompt = f"Violation Details: {json.dumps(violation, default=str)}"
        try:
            response = ollama.chat(
                model=self.compliance_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                options={"temperature": 0.0}
            )
            return response['message']['content']
        except Exception as e:
            print(f"An error occurred during compliance explanation generation with Ollama: {e}")
            return None

if __name__ == '__main__':
    ollama_client = OllamaClient()
    
    # Example usage for sanitization
    log_entry = "Transaction from Jane Roe with card 4111-1111-1111-1111 (CVV: 123), expires 12/26, for $150.00"
    print("--- Sanitization Example ---")
    # ... (rest of the main block is long, keeping it concise for the change)
    sanitized_output = ollama_client.process_transaction(log_entry)
    if sanitized_output:
        print("\nOllama's Structured Output:")
        print(json.dumps(sanitized_output, indent=2))

    # Example usage for risk analysis
    print("\n--- Risk Analysis Example ---")
    now = datetime.now()
    # ...
    risk_assessment = ollama_client.analyze_risk({}, [])
    if risk_assessment:
        print("\nOllama's Risk Assessment:")
        print(json.dumps(risk_assessment, indent=2))

    # Example usage for compliance explanation
    print("\n--- Compliance Explanation Example ---")
    violation = {"violation_type": "Full PAN stored", "context": "Card number 411111... was found unmasked."}
    explanation = ollama_client.generate_compliance_explanation(violation)
    if explanation:
        print("\nOllama's Compliance Explanation:")
        print(explanation)
