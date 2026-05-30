import streamlit as st

st.set_page_config(
    page_title="퍼포먼스 마케팅 대시보드",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.markdown("# :material/analytics: 퍼포먼스 마케팅 대시보드")
    st.caption("2025 Q1 · 구글 / 메타 / 네이버 + AppsFlyer + Braze CRM")

st.markdown("""
| 페이지 | 내용 |
|--------|------|
| :material/monitoring: Overview | 전체 KPI 카드 + 스파크라인 + 일별 트렌드 |
| :material/cell_tower: 채널 분석 | 채널별 광고비 · ROAS · CPA · 퍼널 비교 |
| :material/palette: 소재 분석 | 소재별 버블차트 + Top 랭킹 + 테이블 |
| :material/mail: Braze CRM | 발송 · 오픈 · 전환 + 세그먼트 분석 |
""")
