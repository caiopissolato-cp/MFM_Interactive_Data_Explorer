
import streamlit as st

from core.data_loader import load_delimited_file


st.title("Data Import")
st.caption("Upload and validate an MPFM translated raw-data file.")

uploaded = st.file_uploader(
    "Choose a TXT file",
    type=["txt"],
    key="mpfm_file_uploader",
)

delimiter_options = {
    "Tab": "\t",
    "Comma": ",",
    "Semicolon": ";",
    "Space": r"\s+",
}

delimiter_label = st.selectbox(
    "Delimiter",
    list(delimiter_options.keys()),
    index=0,
    key="mpfm_delimiter",
)

if uploaded is not None:
    try:
        file_bytes = uploaded.getvalue()
        df = load_delimited_file(
            file_bytes,
            delimiter=delimiter_options[delimiter_label],
        )

        # Share the imported data with the other application pages.
        st.session_state["dataframe"] = df
        st.session_state["source_filename"] = uploaded.name

        st.success(
            f"Loaded {len(df):,} rows and {len(df.columns):,} columns."
        )

    except Exception as exc:
        st.session_state.pop("dataframe", None)
        st.session_state.pop("source_filename", None)

        st.error(
            "Could not read the file. Check the delimiter and file format."
        )
        st.exception(exc)

else:
    st.info("Upload a file to begin.")

    # Clear previously imported data when the uploader is empty.
    st.session_state.pop("dataframe", None)
    st.session_state.pop("source_filename", None)
