"""
04_insights.py
- KPI 계산: CTR, CPC, CVR, CPA, ROAS
- 이상치 플래그
- processed/validated/master_with_kpi.parquet 저장
"""
import os
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATED_DIR = os.path.join(BASE, "data", "processed", "validated")


def calc_kpi(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # KPI 계산 (분모 0 → NaN)
    df["ctr"]         = np.where(df["impressions"] > 0, df["clicks_ch"] / df["impressions"] * 100, np.nan)
    df["cpc"]         = np.where(df["clicks_ch"] > 0, df["cost"] / df["clicks_ch"], np.nan)
    df["cvr_signup"]  = np.where(df["clicks_af"] > 0, df["signups_af"] / df["clicks_af"] * 100, np.nan)
    df["cvr_purchase"]= np.where(df["signups_af"] > 0, df["purchases_af"] / df["signups_af"] * 100, np.nan)
    df["cpa_signup"]  = np.where(df["signups_ch"] > 0, df["cost"] / df["signups_ch"], np.nan)
    df["cpa_purchase"]= np.where(df["purchases_ch"] > 0, df["cost"] / df["purchases_ch"], np.nan)
    df["roas"]        = np.where(df["cost"] > 0, df["revenue_ch"] / df["cost"] * 100, np.nan)

    return df


def flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    flags = pd.Series([""] * len(df), index=df.index)

    flags = flags.where(~(df["ctr"] > 15), flags + "CTR>15% ")
    flags = flags.where(~(df["cpa_signup"].notna() & (df["cpa_signup"] < 500)), flags + "CPA가입<500 ")
    flags = flags.where(~(df["cpc"].notna() & (df["cpc"] < 100)), flags + "CPC<100 ")

    # 전주 대비 CPA 변동 ±20% 플래그
    weekly = df.copy()
    weekly["week"] = df["date"].dt.isocalendar().week
    weekly_cpa = weekly.groupby(["week", "channel"])["cpa_signup"].mean().reset_index()
    weekly_cpa["cpa_prev"] = weekly_cpa.groupby("channel")["cpa_signup"].shift(1)
    weekly_cpa["cpa_chg"] = ((weekly_cpa["cpa_signup"] - weekly_cpa["cpa_prev"]) / weekly_cpa["cpa_prev"]).abs()
    anomaly_weeks = set(
        weekly_cpa[weekly_cpa["cpa_chg"] > 0.20].apply(lambda r: (r["week"], r["channel"]), axis=1)
    )
    df["week"] = df["date"].dt.isocalendar().week
    mask_weekly = df.apply(lambda r: (r["week"], r["channel"]) in anomaly_weeks, axis=1)
    flags = flags.where(~mask_weekly, flags + "CPA주간변동>20% ")
    df.drop(columns=["week"], inplace=True)

    df["anomaly_flag"] = flags.str.strip()
    n_flagged = (df["anomaly_flag"] != "").sum()
    if n_flagged:
        print(f"[WARN] 이상치 {n_flagged}건 플래그 - anomaly_flag 컬럼 확인")

    return df


def run():
    print("=== 04_insights: KPI 계산 + 이상치 플래그 ===")

    master = pd.read_parquet(os.path.join(VALIDATED_DIR, "master.parquet"))
    master = calc_kpi(master)
    master = flag_anomalies(master)

    out_path = os.path.join(VALIDATED_DIR, "master_with_kpi.parquet")
    master.to_parquet(out_path, index=False)

    print(f"[DONE] master_with_kpi.parquet 저장 → {out_path}")
    print(f"       KPI 컬럼: ctr, cpc, cvr_signup, cvr_purchase, cpa_signup, cpa_purchase, roas\n")


if __name__ == "__main__":
    run()
