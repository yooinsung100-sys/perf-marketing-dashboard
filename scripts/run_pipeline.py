"""
run_pipeline.py
파이프라인 원클릭 실행: 01 → 02 → 03 → 04
"""
import sys, os, importlib.util

scripts_dir = os.path.dirname(__file__)


def run_step(fname: str):
    spec = importlib.util.spec_from_file_location(fname, os.path.join(scripts_dir, f"{fname}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.run()


if __name__ == "__main__":
    for step in ["01_ingest", "02_preprocess", "03_join", "04_insights"]:
        run_step(step)
    print("=== 파이프라인 완료 ===")
