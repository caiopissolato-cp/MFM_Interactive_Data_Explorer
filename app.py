import streamlit as st

st.set_page_config(
    page_title="MFM Interactive Data Explorer",
    page_icon="📊",
    layout="wide",
)

st.title("MFM Interactive Data Explorer")
st.caption("MPFM Data Analysis & Diagnostics")

st.info(
    "Project scaffold created. Start with Data Import, then migrate the existing "
    "analysis functions into the shared core modules."
)

st.markdown("""
### Getting started
1. Open **Data Import** from the pages menu.
2. Upload a translated raw-data TXT file.
3. Confirm the detected columns and time range.
4. Continue to Overview and Trends after the import module is implemented.
""")
