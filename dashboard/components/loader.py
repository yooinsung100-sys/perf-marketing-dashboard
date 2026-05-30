import os
import pandas as pd
import streamlit as st

# Streamlit Cloud와 로컬 양쪽 경로 대응
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DASHBOARD_DIR = os.path.dirname(_THIS_DIR)
_PROJECT_DIR = os.path.dirname(_DASHBOARD_DIR)

# dashboard/ 기준으로 실행될 수도 있고, 프로젝트 루트에서 실행될 수도 있음
for _candidate in [
    os.path.join(_PROJECT_DIR, "data", "processed", "validated"),
    os.path.join(_DASHBOARD_DIR, "data", "processed", "validated"),
    os.path.join(os.getcwd(), "data", "processed", "validated"),
    os.path.join(os.getcwd(), "..", "data", "processed", "validated"),
]:
    if os.path.isdir(_candidate):
        VALIDATED = _candidate
        break
else:
    VALIDATED = os.path.join(_PROJECT_DIR, "data", "processed", "validated")


@st.cache_data
def load_master() -> pd.DataFrame:
    path = os.path.join(VALIDATED, "master_with_kpi.parquet")
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data
def load_braze_campaigns() -> pd.DataFrame:
    return pd.read_parquet(os.path.join(VALIDATED, "braze_campaigns.parquet"))


@st.cache_data
def load_braze_purchases() -> pd.DataFrame:
    return pd.read_parquet(os.path.join(VALIDATED, "braze_purchases.parquet"))


@st.cache_data
def load_braze_users() -> pd.DataFrame:
    return pd.read_parquet(os.path.join(VALIDATED, "braze_users.parquet"))
