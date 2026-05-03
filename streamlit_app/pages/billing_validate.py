import streamlit as st
import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from database import get_all_billing, get_active_rate, get_payments_by_period
from api_client import create_client_from_env

def show():
    st.title("✅ Billing Validation")
    st.caption("Compare calculated costs (kWh × rate) vs actual bill amounts")
    
    try:
        bills = get_all_billing()
        if not bills:
            st.warning("No bills available. Upload bills first.")
            return
        
        active_rate = get_active_rate(datetime.now().strftime('%Y-%m-%d'))
        
        st.subheader("Bill Comparison")
        for bill in bills[:5]:  # Show last 5 bills
            with st.expander(f"Bill: {bill['billing_period_start'][:7]} to {bill['billing_period_end'][:7]} - ₦{bill['total_bill_amount']:.2f}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Bill Amount", f"₦{bill['total_bill_amount']:.2f}")
                    if bill['total_kwh']:
                        st.metric("Consumption", f"{bill['total_kwh']:.2f} kWh")
                
                with col2:
                    rate_at_bill = get_active_rate(bill['billing_period_start'])
                    if rate_at_bill:
                        st.metric("Rate Used", f"₦{rate_at_bill['rate_per_kwh']:.2f}/kWh")
                        if bill['total_kwh']:
                            calculated = bill['total_kwh'] * rate_at_bill['rate_per_kwh']
                            st.metric("Calculated", f"₦{calculated:.2f}")
                            variance = ((bill['total_bill_amount'] - calculated) / calculated) * 100
                            st.metric("Variance", f"{variance:.1f}%")
                    else:
                        st.warning("No rate found for this period")
                
                with col3:
                    st.metric("Gateway Payment", f"₦{bill.get('payment_gateway', 0):.2f}")
                    st.metric("Transfer Payment", f"₦{bill.get('payment_transfer', 0):.2f}")
                    st.metric("Status", bill['payment_status'].upper())
        
        st.markdown("---")
        st.subheader("API vs Manual Comparison")
        
        try:
            client = create_client_from_env()
            if client.login():
                api_data = client.get_monthly_data()
                if api_data:
                    st.success("API connection successful")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("API Gross Revenue", f"₦{api_data.get('gross_revenue', 0)}")
                    with col2:
                        st.metric("API Energy Purchased", f"₦{api_data.get('energy_purchased', 0)}")
                else:
                    st.warning("API returned no data")
            else:
                st.error("API login failed - check .env credentials")
        except ValueError:
            st.info("API credentials not configured (.env file missing)")
        except Exception as e:
            st.error(f"API error: {str(e)}")
        
        st.markdown("---")
        st.subheader("Payment Matching")
        if bills:
            selected_bill = st.selectbox("Select Bill to Match Payments", 
                                     [f"{b['billing_period_start']} to {b['billing_period_end']} - ₦{b['total_bill_amount']:.2f}" for b in bills[:5]])
            
            if selected_bill:
                # Simplified - in real app, parse selection
                bill = bills[0]  
                payments = get_payments_by_period(bill['billing_period_start'], bill['billing_period_end'])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Bill Payments**")
                    st.write(f"Gateway: ₦{bill.get('payment_gateway', 0):.2f}")
                    st.write(f"Transfer: ₦{bill.get('payment_transfer', 0):.2f}")
                    total_paid = (bill.get('payment_gateway', 0) + bill.get('payment_transfer', 0))
                    st.write(f"**Total Paid: ₦{total_paid:.2f}**")
                
                with col2:
                    st.markdown("**Manual Payments**")
                    if payments:
                        for p in payments:
                            st.write(f"{p['payment_date'][:10]}: ₦{p['amount']:.2f} via {p['method']}")
                    else:
                        st.info("No manual payments recorded")
                    
                    if st.button("➕ Add Payment"):
                        st.info("Use Manual Entry form (future feature)")
        
    except Exception as e:
        st.error(f"Error loading validation page: {str(e)}")
