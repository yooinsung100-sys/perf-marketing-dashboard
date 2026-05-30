"""
03_join.py
- channel + AppsFlyer LEFT JOIN (일+캠페인+그룹+소재 기준)
- 결합률 80% 미만 → 경고 후 중단
- processed/validated/master.parquet 저장
"""
import os, sys
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOINED_DIR = os.path.join(BASE, "data", "processed", "joined")
VALIDATED_DIR = os.path.join(BASE, "data", "processed", "validated")
os.makedirs(VALIDATED_DIR, exist_ok=True)

JOIN_KEYS = ["date", "campaign", "adgroup", "creative"]
MIN_MATCH_RATE = 0.80


def run():
    print("=== 03_join: channel + AppsFlyer 조인 ===")

    ch = pd.read_parquet(os.path.join(JOINED_DIR, "channel_all.parquet"))
    af = pd.read_parquet(os.path.join(JOINED_DIR, "af_all.parquet"))

    # AF에서 조인에 필요한 컬럼만 선택
    af_slim = af[JOIN_KEYS + ["clicks_af", "signups_af", "purchases_af", "revenue_af", "media_source"]]

    merged = ch.merge(af_slim, on=JOIN_KEYS, how="left")

    match_rate = merged["clicks_af"].notna().mean()
    print(f"[INFO] 결합률: {match_rate:.1%} ({merged['clicks_af'].notna().sum():,}/{len(merged):,}행)")

    if match_rate < MIN_MATCH_RATE:
        print(f"[ERROR] 결합률 {match_rate:.1%} < 80% — 조인 키 불일치 확인 필요")
        # 미매칭 샘플 출력
        unmatched = merged[merged["clicks_af"].isna()][JOIN_KEYS + ["channel"]].head(10)
        print("미매칭 샘플:")
        print(unmatched.to_string(index=False))
        sys.exit(1)

    # AF NaN → 0 채우기
    af_cols = ["clicks_af", "signups_af", "purchases_af", "revenue_af"]
    for c in af_cols:
        merged[c] = merged[c].fillna(0).astype(int)

    out_path = os.path.join(VALIDATED_DIR, "master.parquet")
    merged.to_parquet(out_path, index=False)
    print(f"[DONE] master.parquet 저장 → {out_path}")
    print(f"       rows: {len(merged):,} | 기간: {merged['date'].min().date()} ~ {merged['date'].max().date()}\n")


if __name__ == "__main__":
    run()
