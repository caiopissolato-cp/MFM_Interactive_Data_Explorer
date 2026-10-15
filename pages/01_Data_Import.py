import streamlit as st
import pandas as pd

st.title("Data Import")
st.caption("Upload and validate an MPFM translated raw-data file.")

uploaded = st.file_uploader("Choose a TXT file", type=["txt"])

if uploaded is not None:
    delimiter_label = st.selectbox(
        "Delimiter",
        ["Tab", "Comma", "Semicolon", "Space"],
        index=0,
    )
    delimiters = {"Tab": "\\t", "Comma": ",", "Semicolon": ";", "Space": r"\\s+"}
    try:
        df = pd.read_csv(uploaded, sep=delimiters[delimiter_label], engine="python")
        st.success(f"Loaded {len(df):,} rows and {len(df.columns):,} columns.")
        st.write("Detected columns")
        st.dataframe(pd.DataFrame({"Column": df.columns}), use_container_width=True)
        st.write("Preview")
        st.dataframe(df.head(20), use_container_width=True)
    except Exception as exc:
        st.error("Could not read the file. Check the delimiter and file format.")
        st.exception(exc)
else:
    st.info("Upload a file to begin.")
