import streamlit as st
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

st.set_page_config(
    page_title="WattWise Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("⚡ WattWise Dashboard")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Rate Manager", "Bill Upload", "Billing Validate"]
)

if page == "Dashboard":
    from pages import dashboard
    dashboard.show()
elif page == "Rate Manager":
    from pages import rate_manager
    rate_manager.show()
elif page == "Bill Upload":
    from pages import bill_upload
    bill_upload.show()
elif page == "Billing Validate":
    from pages import billing_validate
    billing_validate.show()

st.sidebar.markdown("---")
st.sidebar.caption(f"Data directory: `{os.path.join(os.path.dirname(__file__), '..', 'data')}`")
