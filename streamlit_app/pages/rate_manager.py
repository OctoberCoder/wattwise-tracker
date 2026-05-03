import streamlit as st
import sys
import os
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from database import insert_rate, get_all_rates, get_active_rate

def show():
    st.title("⚙ Rate Manager")
    st.caption("Manage electricity rates (₦ per kWh) with effective date ranges")
    
    st.markdown("---")
    st.subheader("Add New Rate")
    
    with st.form("rate_form"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            rate_value = st.number_input("Rate (₦ per kWh)", min_value=0.0, value=0.0, step=0.01)
        with col2:
            effective_from = st.date_input("Effective From", value=datetime.now())
        with col3:
            effective_to = st.date_input("Effective To (optional)", value=None)
        with col4:
            source = st.selectbox("Source", ["manual", "api", "bill_calculated"])
        
        submitted = st.form_submit_button("➕ Add Rate")
        if submitted:
            if rate_value <= 0:
                st.error("Rate must be greater than 0")
            else:
                try:
                    rate_id = insert_rate(
                        rate_per_kwh=rate_value,
                        effective_from=effective_from.strftime('%Y-%m-%d'),
                        effective_to=effective_to.strftime('%Y-%m-%d') if effective_to else None,
                        source=source
                    )
                    st.success(f"Rate added successfully (ID: {rate_id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add rate: {str(e)}")
    
    st.markdown("---")
    st.subheader("Current Active Rate")
    active = get_active_rate(datetime.now().strftime('%Y-%m-%d'))
    if active:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rate", f"₦{active['rate_per_kwh']:.2f}/kWh")
        with col2:
            st.metric("From", active['effective_from'])
        with col3:
            st.metric("To", active['effective_to'] if active['effective_to'] else "Present")
        with col4:
            st.metric("Source", active['source'])
    else:
        st.warning("No active rate found for today. Add a rate above.")
    
    st.markdown("---")
    st.subheader("Rate History")
    try:
        rates = get_all_rates()
        if rates:
            df = [{
                'ID': r['id'],
                'Rate (₦/kWh)': f"₦{r['rate_per_kwh']:.2f}",
                'From': r['effective_from'],
                'To': r['effective_to'] if r['effective_to'] else 'Present',
                'Source': r['source'],
                'Created': r['created_at'][:10] if r['created_at'] else ''
            } for r in rates]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No rates configured yet.")
    except Exception as e:
        st.error(f"Error loading rates: {str(e)}")
