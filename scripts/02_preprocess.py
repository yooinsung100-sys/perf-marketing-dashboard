"""
02_preprocess.py
- 컬럼명 영문 표준화
- 미디어소스 → 채널코드 매핑
- 데이터 타입 정리
- processed/joined/ 에 channel_all.parquet, af_all.parquet 저장
"""
import os, glob
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_CH = os.path.join(BASE, "data", "raw", "channel")
RAW_AF = os.path.join(BASE, "data", "raw", "appsflyer")
OUT_DIR = os.path.join(BASE, "data", "processed", "joined")
os.makedirs(OUT_DIR, exist_ok=True)

CH_RENAME = {
    "일": "date", "채널": "channel", "채널분류": "channel_type",
    "캠페인": "campaign", "캠페인목적": "campaign_goal", "그룹": "adgroup",
    "소재": "creative", "노출": "impressions", "클릭": "clicks_ch",
    "비용": "cost", "회원가입": "signups_ch", "구매": "purchases_ch",
    "구매매출": "revenue_ch",
}

AF_RENAME = {
    "일": "date", "미디어소스": "media_source", "캠페인": "campaign",
    "그룹": "adgroup", "소재": "creative", "클릭": "clicks_af",
    "회원가입": "signups_af", "구매": "purchases_af", "구매매출": "revenue_af",
}

MEDIA_TO_CHANNEL = {
    "googleadwords_int": "구글",
    "Facebook Ads": "메타",
    "naver_search": "네이버",
}


def load_channel() -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(RAW_CH, "*.csv")))
    dfs = [pd.read_csv(f, encoding="utf-8-sig") for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df = df.rename(columns=CH_RENAME)
    df["date"] = pd.to_datetime(df["date"])
    int_cols = ["impressions", "clicks_ch", "cost", "signups_ch", "purchases_ch", "revenue_ch"]
    for c in int_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    print(f"[OK] channel: {len(df):,}행 로드 ({df['date'].min().date()} ~ {df['date'].max().date()})")
    return df


def load_appsflyer() -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(RAW_AF, "*.csv")))
    dfs = [pd.read_csv(f, encoding="utf-8-sig") for f in files]
    df = pd.concat(dfs, ignore_index=True)
    df = df.rename(columns=AF_RENAME)
    df["date"] = pd.to_datetime(df["date"])
    df["channel"] = df["media_source"].map(MEDIA_TO_CHANNEL)
    int_cols = ["clicks_af", "signups_af", "purchases_af", "revenue_af"]
    for c in int_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    print(f"[OK] appsflyer: {len(df):,}행 로드 ({df['date'].min().date()} ~ {df['date'].max().date()})")
    return df


def run():
    print("=== 02_preprocess: 컬럼 표준화 ===")
    ch = load_channel()
    af = load_appsflyer()
    ch.to_parquet(os.path.join(OUT_DIR, "channel_all.parquet"), index=False)
    af.to_parquet(os.path.join(OUT_DIR, "af_all.parquet"), index=False)
    print(f"[DONE] 저장 완료 → {OUT_DIR}\n")


if __name__ == "__main__":
    run()
