# Secure LLM Agent for PCI-Compliant Card Transaction Intelligence

## Project Overview

The Secure LLM Agent for PCI-Compliant Card Transaction Intelligence is a sophisticated system designed to enhance security, ensure compliance, and provide actionable insights from simulated card transaction logs. Leveraging Large Language Models (LLMs), this project automates the process of data ingestion, sanitization, risk analysis, and comprehensive compliance reporting, making it an invaluable tool for organizations handling sensitive payment data.

## Key Features

The system is built around a multi-agent architecture, each specialized in a critical aspect of transaction intelligence:

1.  **Data Sanitization Agent:**
    *   **Purpose:** Ensures data privacy and compliance by meticulously identifying and removing Payment Account Numbers (PAN) and masking Personally Identifiable Information (PII) from ingested transaction logs.
    *   **Benefit:** Reduces the risk of data breaches and supports adherence to PCI DSS requirements.

2.  **Risk Analysis Agent:**
    *   **Purpose:** Employs advanced analytical techniques, powered by LLMs, to detect anomalies, identify potential fraud patterns, and flag suspicious transactions within the sanitized data.
    *   **Benefit:** Proactively identifies and mitigates financial risks, enhancing the security posture of transaction processing.

3.  **Compliance Explanation Agent:**
    *   **Purpose:** Generates clear, human-readable compliance reports that explain PCI DSS violations, their implications, and recommended remediation steps.
    *   **Benefit:** Simplifies complex compliance documentation, facilitates auditing, and aids in rapid decision-making for compliance officers.

## Architecture

The project employs a robust and integrated architecture:

*   **Data Ingestion:** Simulated card transaction logs serve as the input, designed to mimic real-world scenarios.
*   **Central LLM Integration (`ollama_client.py`):** A core component that provides intelligent capabilities to all agents, enabling sophisticated data processing, analysis, and natural language generation.
*   **Automated Pipeline:** All agents are seamlessly integrated into an automated pipeline, ensuring a smooth flow of data from ingestion through analysis to final reporting.
*   **Comprehensive Reporting:** The system generates detailed reports in both JSON and PDF formats, offering flexible options for data consumption and presentation.

## Getting Started

To run the Streamlit application, execute the following command in your terminal:

```bash
streamlit run app.py
```

## Reporting

The system produces:

*   **JSON Reports:** Machine-readable outputs for integration with other systems or for programmatic analysis.
*   **PDF Compliance Reports:** Professional, human-readable documents suitable for auditors, compliance officers, and management, detailing violations and explanations.