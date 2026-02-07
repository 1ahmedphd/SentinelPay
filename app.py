import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from main import run_pipeline # Import the refactored pipeline function

def main():
    st.set_page_config(layout="wide")
    st.title("SentinelPay - PCI-Compliant Card Transaction Intelligence")

    # Initialize session state variables
    if 'reports' not in st.session_state:
        st.session_state.reports = None
    if 'sanitized_transactions' not in st.session_state:
        st.session_state.sanitized_transactions = None
    if 'violations' not in st.session_state:
        st.session_state.violations = None

    # Sidebar for navigation/options
    st.sidebar.title("Options")

    # 1. Transaction upload area
    uploaded_file = st.sidebar.file_uploader("Upload transaction log file (CSV or JSON)", type=["csv", "json"])

    process_button = st.sidebar.button("Process Transactions")

    if uploaded_file is not None and process_button:
        st.sidebar.success("File uploaded successfully!")
        
        file_details = {"filename": uploaded_file.name, "filetype": uploaded_file.type, "filesize": uploaded_file.size}
        st.sidebar.write(file_details)

        raw_transactions_data = []
        if uploaded_file.type == "application/json":
            raw_transactions_data = json.load(uploaded_file)
        elif uploaded_file.type == "text/csv":
            df = pd.read_csv(uploaded_file)
            raw_transactions_data = df.to_dict(orient='records')
        
        if raw_transactions_data:
            with st.spinner('Processing transactions... This may take a while for LLM interactions.'):
                # Ensure a temporary output directory exists for reports
                output_dir = "streamlit_reports"
                os.makedirs(output_dir, exist_ok=True)

                st.session_state.reports, st.session_state.sanitized_transactions, st.session_state.violations = \
                    run_pipeline(raw_transactions_data, output_dir=output_dir)
            st.success("Processing complete!")
        else:
            st.sidebar.error("Could not read transaction data from the uploaded file.")

    # Main dashboard area
    st.header("Transaction Dashboard")

    if st.session_state.sanitized_transactions:
        df_transactions = pd.DataFrame(st.session_state.sanitized_transactions)
        
        # Convert timestamp to datetime objects for filtering
        if 'timestamp' in df_transactions.columns:
            df_transactions['timestamp'] = pd.to_datetime(df_transactions['timestamp'])
        
        filtered_df_transactions = df_transactions.copy()

        # Advanced Features - Search & Filter
        st.sidebar.header("Search & Filter")

        # Search by transaction ID
        transaction_id_search = st.sidebar.text_input("Search by Transaction ID")
        if transaction_id_search:
            filtered_df_transactions = filtered_df_transactions[
                filtered_df_transactions['transaction_id'].str.contains(transaction_id_search, case=False, na=False)
            ]

        # Filter by risk score
        risk_score_range = st.sidebar.slider("Filter by Risk Score", 0, 100, (0, 100))
        filtered_df_transactions = filtered_df_transactions[
            (filtered_df_transactions['risk_score'] >= risk_score_range[0]) & 
            (filtered_df_transactions['risk_score'] <= risk_score_range[1])
        ]

        # Date range selection
        date_range = st.sidebar.date_input("Filter by Date Range", [])
        if len(date_range) == 2:
            start_date = pd.to_datetime(date_range[0])
            end_date = pd.to_datetime(date_range[1])
            filtered_df_transactions = filtered_df_transactions[
                (filtered_df_transactions['timestamp'] >= start_date) & 
                (filtered_df_transactions['timestamp'] <= end_date)
            ]

        # Merchant filtering
        merchant_filter = st.sidebar.text_input("Filter by Merchant")
        if merchant_filter:
            # Assuming 'merchant_details' is a dictionary with a 'name' key
            if 'merchant_details' in filtered_df_transactions.columns:
                filtered_df_transactions = filtered_df_transactions[
                    filtered_df_transactions['merchant_details'].apply(
                        lambda x: merchant_filter.lower() in x.get('name', '').lower() if isinstance(x, dict) else False
                    )
                ]
            else:
                st.sidebar.warning("Merchant details not available for filtering.")


        # 3. Violation alerts
        st.subheader("Violation Alerts")
        if st.session_state.violations:
            for i, violation in enumerate(st.session_state.violations):
                # Only display violations for transactions that are still in the filtered view
                if any(filtered_df_transactions['transaction_id'] == violation.get('transaction_id')):
                    st.warning(f"Violation {i+1}: {violation.get('description', 'No description')} for transaction ID: {violation.get('transaction_id', 'N/A')}")
        else:
            st.info("No violations detected.")

        # 4. Risk score visualization
        st.subheader("Risk Score Distribution")
        if not filtered_df_transactions.empty and 'risk_score' in filtered_df_transactions.columns:
            risk_scores = filtered_df_transactions['risk_score'].value_counts().sort_index()
            st.bar_chart(risk_scores)
        else:
            st.info("No risk score data available for visualization based on current filters.")

        st.subheader("Sanitized Transactions Overview (Filtered)")
        if not filtered_df_transactions.empty:
            st.dataframe(filtered_df_transactions)
        else:
            st.info("No transactions match the current filter criteria.")

    else:
        st.info("Upload a transaction file and click 'Process Transactions' to see the dashboard.")

    # 5. Report download buttons
    st.sidebar.header("Download Reports")
    if st.session_state.reports:
        # Download JSON reports
        if st.session_state.reports.get('daily_summary'):
            st.sidebar.download_button(
                label="Download Daily Summary (JSON)",
                data=json.dumps(st.session_state.reports['daily_summary'], indent=2),
                file_name="daily_summary.json",
                mime="application/json"
            )
        if st.session_state.reports.get('detailed_violation_report'):
            st.sidebar.download_button(
                label="Download Detailed Violation Report (JSON)",
                data=json.dumps(st.session_state.reports['detailed_violation_report'], indent=2),
                file_name="detailed_violation_report.json",
                mime="application/json"
            )
        if st.session_state.reports.get('llm_enhanced_report'):
            st.sidebar.download_button(
                label="Download LLM Enhanced Report (JSON)",
                data=json.dumps(st.session_state.reports['llm_enhanced_report'], indent=2),
                file_name="llm_enhanced_report.json",
                mime="application/json"
            )
        
        # Download PDF report
        if st.session_state.reports.get('llm_enhanced_pdf_path') and os.path.exists(st.session_state.reports['llm_enhanced_pdf_path']):
            with open(st.session_state.reports['llm_enhanced_pdf_path'], "rb") as pdf_file:
                st.sidebar.download_button(
                    label="Download LLM Enhanced Report (PDF)",
                    data=pdf_file.read(),
                    file_name=os.path.basename(st.session_state.reports['llm_enhanced_pdf_path']),
                    mime="application/pdf"
                )
        elif st.session_state.reports.get('llm_enhanced_report_error'):
            st.sidebar.error(f"PDF report error: {st.session_state.reports['llm_enhanced_report_error']}")

    else:
        st.sidebar.info("Upload and process transactions to enable report downloads.")

if __name__ == "__main__":
    main()

