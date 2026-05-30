"""
01_ingest.py
raw/ 파일 존재 여부·컬럼·인코딩 검증
"""
import os, glob, sys
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_CH = os.path.join(BASE, "data", "raw", "channel")
RAW_AF = os.path.join(BASE, "data", "raw", "appsflyer")

CHANNEL_COLS = {"일", "채널", "채널분류", "캠페인", "캠페인목적", "그룹", "소재",
                "노출", "클릭", "비용", "회원가입", "구매", "구매매출"}
AF_COLS = {"일", "미디어소스", "캠페인", "그룹", "소재", "클릭", "회원가입", "구매", "구매매출"}


def validate_files(folder: str, required_cols: set, source: str) -> list[str]:
    files = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not files:
        print(f"[ERROR] {source}: 파일 없음 → {folder}")
        sys.exit(1)

    errors = []
    for f in files:
        try:
            df = pd.read_csv(f, encoding="utf-8-sig", nrows=1)
            missing = required_cols - set(df.columns)
            if missing:
                errors.append(f"{os.path.basename(f)}: 컬럼 누락 {missing}")
        except Exception as e:
            errors.append(f"{os.path.basename(f)}: 읽기 실패 - {e}")

    if errors:
        for e in errors:
            print(f"[ERROR] {source}: {e}")
        sys.exit(1)

    print(f"[OK] {source}: {len(files)}개 파일 검증 완료")
    return files


def run():
    print("=== 01_ingest: raw 파일 검증 ===")
    validate_files(RAW_CH, CHANNEL_COLS, "channel")
    validate_files(RAW_AF, AF_COLS, "appsflyer")
    print("[DONE] 검증 완료\n")


if __name__ == "__main__":
    run()
