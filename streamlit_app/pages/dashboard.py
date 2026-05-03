import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from database import (
    get_connection, get_latest_consumption, get_all_billing, 
    get_payments_by_period, get_active_rate
)
from api_client import create_client_from_env, WattWiseClient

def show():
    st.title("⚡ Electricity Consumption Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        latest = get_latest_consumption()
        if latest:
            with col1:
                st.metric("Cumulative kWh", f"{latest['cumulative_kwh']:.2f}")
            with col2:
                res = latest.get('residual_amount')
                st.metric("Residual Amount", f"₦{res:.2f}" if res else "N/A")
            with col3:
                snapshot_date = datetime.fromisoformat(latest['snapshot_date'].replace('Z', '+00:00'))
                days_ago = (datetime.now() - snapshot_date).days
                st.metric("Last Update", f"{days_ago} days ago")
            with col4:
                active_rate = get_active_rate(datetime.now().strftime('%Y-%m-%d'))
                if active_rate:
                    st.metric("Active Rate", f"₦{active_rate['rate_per_kwh']:.2f}/kWh")
                else:
                    st.metric("Active Rate", "Not set")
        
        st.markdown("---")
        
        tab1, tab2, tab3 = st.tabs(["Consumption Trend", "Payment History", "Bill Comparison"])
        
        with tab1:
            df = pd.read_sql_query("SELECT * FROM consumption ORDER BY snapshot_date", conn)
            if not df.empty:
                df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
                fig = px.line(df, x='snapshot_date', y='cumulative_kwh', 
                           title='Cumulative Consumption (kWh)', 
                           labels={'cumulative_kwh': 'kWh', 'snapshot_date': 'Date'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No consumption data available. Poll WattWiseNG API or upload bills.")
        
        with tab2:
            billing_df = pd.read_sql_query("SELECT * FROM billing ORDER BY billing_period_start DESC LIMIT 6", conn)
            if not billing_df.empty:
                st.dataframe(billing_df[['billing_period_start', 'billing_period_end', 'total_kwh', 'total_bill_amount', 'payment_status']], 
                            use_container_width=True)
        
        with tab3:
            bills_df = pd.read_sql_query("SELECT * FROM billing ORDER BY billing_period_start DESC", conn)
            if not bills_df.empty and latest:
                for _, bill in bills_df.head(3).iterrows():
                    rate = get_active_rate(bill['billing_period_start'])
                    if rate:
                        kwh = bill['total_kwh']
                        calculated = kwh * rate['rate_per_kwh'] if kwh else None
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric(f"Bill {str(bill['billing_period_start'])[:7]}", 
                                      f"₦{bill['total_bill_amount']:.2f}", 
                                      f"Calculated: ₦{calculated:.2f}" if calculated else "N/A")
                        with col_b:
                            if calculated:
                                variance = ((bill['total_bill_amount'] - calculated) / calculated) * 100
                                st.metric("Variance", f"{variance:.1f}%")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
    
    st.markdown("---")
    col_poll, col_refresh = st.columns(2)
    with col_poll:
        if st.button("🔄 Poll WattWiseNG API Now"):
            try:
                client = create_client_from_env()
                if client.login():
                    meter_data = client.get_meter_overview()
                    if meter_data:
                        from database import insert_consumption
                        insert_consumption(
                            snapshot_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            cumulative_kwh=float(meter_data.get('cumulative_total_consumption', 0)),
                            residual_amount=float(meter_data.get('residual_amount', 0)) if meter_data.get('residual_amount') else None
                        )
                        st.success("Data polled successfully!")
                        st.rerun()
                    else:
                        st.warning("No data returned from API")
                else:
                    st.error("Login failed - check credentials in .env")
            except Exception as e:
                st.error(f"Poll failed: {str(e)}")
    
    with col_refresh:
        if st.button("🔃 Refresh Dashboard"):
            st.rerun()
