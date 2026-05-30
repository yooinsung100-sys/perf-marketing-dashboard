import os
import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
VALIDATED = os.path.join(BASE, "data", "processed", "validated")
RAW_BRAZE = os.path.join(BASE, "data", "raw", "braze")


@st.cache_data
def load_master() -> pd.DataFrame:
    path = os.path.join(VALIDATED, "master_with_kpi.parquet")
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data
def load_braze_campaigns() -> pd.DataFrame:
    path = os.path.join(VALIDATED, "braze_campaigns.parquet")
    return pd.read_parquet(path)


@st.cache_data
def load_braze_purchases() -> pd.DataFrame:
    path = os.path.join(VALIDATED, "braze_purchases.parquet")
    return pd.read_parquet(path)


@st.cache_data
def load_braze_users() -> pd.DataFrame:
    path = os.path.join(VALIDATED, "braze_users.parquet")
    return pd.read_parquet(path)
