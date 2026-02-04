import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import hashlib
import json
from utils.ollama_client import OllamaClient

class DataSanitizer:
    def __init__(self, mode='regex', ollama_client=None, violation_log_file='violations.log'):
        self.mode = mode
        if self.mode == 'ollama' and not ollama_client:
            raise ValueError("Ollama client must be provided for 'ollama' mode.")
        self.ollama_client = ollama_client
        self.violation_log_file = violation_log_file

        # Regex to find potential PANs (13-19 digits, with optional spaces or dashes)
        self.pan_regex = re.compile(r'\b(?:\d[ -]*?){13,19}\b')
        self.card_patterns = {
            "Visa": re.compile(r'^4\d{12}(?:\d{3})?$'),
            "Mastercard": re.compile(r'^5[1-5]\d{14}$'),
            "Amex": re.compile(r'^3[47]\d{13}$'),
            "Discover": re.compile(r'^6(?:011|5\d{2})\d{12}$'),
            "JCB": re.compile(r'^(?:2131|1800|35\d{3})\d{11}$'),
        }

    def mask_pan(self, pan):
        """
        Masks a PAN, keeping the first 6 and last 4 digits.
        """
        pan_digits = "".join(filter(str.isdigit, pan))
        if 13 <= len(pan_digits) <= 19:
            return f"{pan_digits[:6]}{'*' * (len(pan_digits) - 10)}{pan_digits[-4:]}"
        return pan

    def get_card_type(self, pan):
        """
        Identifies the card type based on the PAN.
        """
        pan_digits = "".join(filter(str.isdigit, pan))
        for card_type, pattern in self.card_patterns.items():
            if pattern.match(pan_digits):
                return card_type
        return "Unknown"

    def create_audit_hash(self, pan):
        """
        Creates a SHA-256 hash of the PAN for auditing purposes.
        """
        return hashlib.sha256(pan.encode()).hexdigest()

    def sanitize_transaction(self, transaction_log):
        """
        Sanitizes a single transaction log entry based on the selected mode.
        """
        if self.mode == 'ollama':
            structured_response = self.ollama_client.process_transaction(transaction_log)
            if structured_response:
                sanitized_log = structured_response.get("sanitized_log")
                violations = structured_response.get("violations")
                if violations:
                    self._log_violations(violations)
                return sanitized_log
            return None
        else: # regex mode
            return self._sanitize_with_regex(transaction_log)

    def _sanitize_with_regex(self, transaction_log):
        """
        Sanitizes a single transaction log entry using regex.
        """
        sanitized_log = transaction_log
        pans_found = self.pan_regex.findall(transaction_log)
        
        for pan in pans_found:
            cleaned_pan = "".join(filter(str.isdigit, pan))
            if not (13 <= len(cleaned_pan) <= 19):
                continue

            card_type = self.get_card_type(cleaned_pan)
            if card_type == "Unknown":
                continue

            masked_pan = self.mask_pan(cleaned_pan)
            audit_hash = self.create_audit_hash(cleaned_pan)
            
            sanitized_log = sanitized_log.replace(pan, masked_pan)
            
            print(f"Detected and masked PAN. Audit Hash: {audit_hash}, Card Type: {card_type}")

        return sanitized_log
        
    def _log_violations(self, violations):
        with open(self.violation_log_file, 'a') as f:
            for violation in violations:
                f.write(json.dumps(violation) + '\n')


