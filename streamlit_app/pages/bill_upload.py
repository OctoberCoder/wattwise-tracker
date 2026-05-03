import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime
import io

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from database import insert_billing, get_all_billing, insert_payment

def parse_csv_upload(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        return df, None
    except Exception as e:
        return None, str(e)

def show():
    st.title("📄 Bill Upload")
    st.caption("Upload CSV bills from EKO/WattWiseNG or enter bill details manually")
    
    tab1, tab2 = st.tabs(["CSV Upload", "Manual Entry"])
    
    with tab1:
        st.subheader("Upload Bill CSV")
        st.markdown("""
        **Expected CSV format** (columns):
        - `billing_period_start` (YYYY-MM-DD)
        - `billing_period_end` (YYYY-MM-DD)
        - `total_kwh` (float)
        - `total_bill_amount` (float, ₦)
        - `payment_gateway` (float, optional)
        - `payment_transfer` (float, optional)
        - `service_charge` (float, optional)
        - `due_date` (YYYY-MM-DD, optional)
        """)
        
        uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])
        
        if uploaded_file is not None:
            df, error = parse_csv_upload(uploaded_file)
            if error:
                st.error(f"CSV parse error: {error}")
            elif df is not None:
                st.success(f"Parsed {len(df)} bill records")
                st.dataframe(df.head(10), use_container_width=True)
                
                if st.button("➕ Import All Records"):
                    success_count = 0
                    for _, row in df.iterrows():
                        try:
                            insert_billing(
                                period_start=str(row.get('billing_period_start', '')),
                                period_end=str(row.get('billing_period_end', '')),
                                total_kwh=float(row.get('total_kwh', 0)) if pd.notna(row.get('total_kwh')) else None,
                                total_amount=float(row.get('total_bill_amount', 0)),
                                gateway=float(row.get('payment_gateway', 0)) if pd.notna(row.get('payment_gateway')) else 0,
                                transfer=float(row.get('payment_transfer', 0)) if pd.notna(row.get('payment_transfer')) else 0,
                                service_charge=float(row.get('service_charge', 0)) if pd.notna(row.get('service_charge')) else None,
                                due_date=str(row.get('due_date', '')) if pd.notna(row.get('due_date')) else None,
                                status='unpaid',
                                source='csv_upload'
                            )
                            success_count += 1
                        except Exception as e:
                            st.error(f"Row error: {str(e)}")
                    st.success(f"Imported {success_count} bill records!")
                    st.rerun()
    
    with tab2:
        st.subheader("Manual Bill Entry")
        with st.form("manual_bill_form"):
            col1, col2 = st.columns(2)
            with col1:
                period_start = st.date_input("Billing Period Start", value=datetime.now().replace(day=1))
                total_kwh = st.number_input("Total kWh", min_value=0.0, value=0.0, step=0.1)
                payment_gateway = st.number_input("Payment (Gateway)", min_value=0.0, value=0.0, step=0.01)
            with col2:
                period_end = st.date_input("Billing Period End", value=datetime.now())
                total_amount = st.number_input("Total Bill Amount (₦)", min_value=0.0, value=0.0, step=0.01)
                payment_transfer = st.number_input("Payment (Transfer)", min_value=0.0, value=0.0, step=0.01)
            
            service_charge = st.number_input("Service Charge (₦)", min_value=0.0, value=0.0, step=0.01)
            due_date = st.date_input("Due Date", value=None)
            status = st.selectbox("Payment Status", ["unpaid", "partial", "paid"])
            
            submitted = st.form_submit_button("➕ Add Bill")
            if submitted:
                if total_amount <= 0:
                    st.error("Total bill amount must be greater than 0")
                else:
                    try:
                        bill_id = insert_billing(
                            period_start=period_start.strftime('%Y-%m-%d'),
                            period_end=period_end.strftime('%Y-%m-%d'),
                            total_kwh=total_kwh if total_kwh > 0 else None,
                            total_amount=total_amount,
                            gateway=payment_gateway,
                            transfer=payment_transfer,
                            service_charge=service_charge if service_charge > 0 else None,
                            due_date=due_date.strftime('%Y-%m-%d') if due_date else None,
                            status=status,
                            source='manual'
                        )
                        st.success(f"Bill added successfully (ID: {bill_id})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add bill: {str(e)}")
    
    st.markdown("---")
    st.subheader("Existing Bills")
    try:
        bills = get_all_billing()
        if bills:
            df = pd.DataFrame(bills)
            df['total_bill_amount'] = df['total_bill_amount'].apply(lambda x: f"₦{x:.2f}")
            df['total_kwh'] = df['total_kwh'].apply(lambda x: f"{x:.2f} kWh" if x else "N/A")
            st.dataframe(df[['billing_period_start', 'billing_period_end', 'total_kwh', 'total_bill_amount', 'payment_status', 'source']], 
                        use_container_width=True)
        else:
            st.info("No bills recorded yet.")
    except Exception as e:
        st.error(f"Error loading bills: {str(e)}")
