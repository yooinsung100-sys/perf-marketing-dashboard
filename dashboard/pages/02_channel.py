import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import altair as alt
import pandas as pd
import streamlit as st

from components.loader import load_master

st.set_page_config(page_title="채널 분석", page_icon=":material/cell_tower:", layout="wide")

df = load_master()

CHANNEL_COLORS = {"구글": "#4285F4", "메타": "#1877F2", "네이버": "#03C75A"}

with st.sidebar:
    st.markdown("### :material/filter_list: 필터")
    date_min, date_max = df["date"].min().date(), df["date"].max().date()
    date_range = st.date_input("기간", value=(date_min, date_max),
                               min_value=date_min, max_value=date_max)
    kpi_map = {
        "ROAS(%)": "roas", "CTR(%)": "ctr", "CPC(₩)": "cpc",
        "CPA 가입(₩)": "cpa_signup", "CPA 구매(₩)": "cpa_purchase",
    }
    kpi_label = st.selectbox(":material/query_stats: 비교 KPI", list(kpi_map.keys()))
    kpi_col = kpi_map[kpi_label]

if len(date_range) == 2:
    s, e = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[(df["date"] >= s) & (df["date"] <= e)]

with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.markdown("## :material/cell_tower: 채널별 성과 분석")
    if st.button(":material/restart_alt: 초기화", type="tertiary"):
        st.session_state.clear()
        st.rerun()

# ── 채널별 집계 ───────────────────────────────────────────────────────────────
def agg_ch(g):
    c=g["cost"].sum(); i=g["impressions"].sum(); k=g["clicks_ch"].sum()
    s=g["signups_ch"].sum(); p=g["purchases_ch"].sum(); r=g["revenue_ch"].sum()
    return pd.Series({
        "cost":c,"impressions":i,"clicks_ch":k,"signups_ch":s,"purchases_ch":p,"revenue_ch":r,
        "ctr":  k/i*100  if i else None,
        "cpc":  c/k      if k else None,
        "cpa_signup":   c/s if s else None,
        "cpa_purchase": c/p if p else None,
        "roas": r/c*100  if c else None,
    })

ch_agg = df.groupby("channel").apply(agg_ch, include_groups=False).reset_index()

# ── 채널별 KPI 카드 ───────────────────────────────────────────────────────────
with st.container(horizontal=True):
    for _, row in ch_agg.iterrows():
        with st.container(border=True):
            ch = row["channel"]
            color = CHANNEL_COLORS.get(ch, "#636EFA")
            st.markdown(f"**{ch}**")
            st.metric("광고비", f"₩{row['cost']/1e6:.1f}M")
            st.metric("ROAS", f"{row['roas']:.0f}%")
            st.metric("CTR", f"{row['ctr']:.2f}%")
            st.metric("CPA(가입)", f"₩{row['cpa_signup']:,.0f}")

# ── 바차트 + 도넛 ─────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown(f"**:material/bar_chart: 채널별 {kpi_label}**")
        bar = (
            alt.Chart(ch_agg.dropna(subset=[kpi_col]).sort_values(kpi_col, ascending=False))
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("channel:N", title=None, sort="-y"),
                y=alt.Y(f"{kpi_col}:Q", title=kpi_label),
                color=alt.Color("channel:N",
                    scale=alt.Scale(
                        domain=list(CHANNEL_COLORS.keys()),
                        range=list(CHANNEL_COLORS.values())
                    ), legend=None),
                tooltip=[alt.Tooltip("channel:N", title="채널"),
                         alt.Tooltip(f"{kpi_col}:Q", title=kpi_label, format=",.1f")],
            )
            .properties(height=280)
        )
        st.altair_chart(bar)

with col2:
    with st.container(border=True):
        st.markdown("**:material/pie_chart: 채널별 광고비 점유율**")
        pie = (
            alt.Chart(ch_agg)
            .mark_arc(innerRadius=70, outerRadius=120)
            .encode(
                theta=alt.Theta("cost:Q"),
                color=alt.Color("channel:N",
                    scale=alt.Scale(
                        domain=list(CHANNEL_COLORS.keys()),
                        range=list(CHANNEL_COLORS.values())
                    )),
                tooltip=[alt.Tooltip("channel:N", title="채널"),
                         alt.Tooltip("cost:Q", title="광고비", format=",d")],
            )
            .properties(height=280)
        )
        st.altair_chart(pie)

# ── 캠페인 목적 × 채널 CPA 히트맵 ─────────────────────────────────────────────
with st.container(border=True):
    st.markdown("**:material/grid_on: 캠페인 목적 × 채널 CPA(가입) 히트맵**")
    pivot_df = df.groupby(["campaign_goal", "channel"]).apply(
        lambda g: g["cost"].sum() / g["signups_ch"].sum() if g["signups_ch"].sum() > 0 else None,
        include_groups=False,
    ).reset_index(name="cpa_signup")

    heatmap = (
        alt.Chart(pivot_df.dropna())
        .mark_rect()
        .encode(
            x=alt.X("channel:N", title="채널"),
            y=alt.Y("campaign_goal:N", title="캠페인 목적"),
            color=alt.Color("cpa_signup:Q", title="CPA(₩)",
                            scale=alt.Scale(scheme="redyellowgreen", reverse=True)),
            tooltip=[
                alt.Tooltip("channel:N", title="채널"),
                alt.Tooltip("campaign_goal:N", title="목적"),
                alt.Tooltip("cpa_signup:Q", title="CPA(₩)", format=",.0f"),
            ],
        )
        .properties(height=250)
    )
    text = heatmap.mark_text(fontSize=12).encode(
        text=alt.Text("cpa_signup:Q", format=",.0f"),
        color=alt.value("black"),
    )
    st.altair_chart(heatmap + text)

# ── 채널별 일별 트렌드 ────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown(f"**:material/show_chart: 채널별 {kpi_label} 일별 트렌드**")
    daily_ch = df.groupby(["date", "channel"]).apply(agg_ch, include_groups=False).reset_index()

    trend = (
        alt.Chart(daily_ch.dropna(subset=[kpi_col]))
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y(f"{kpi_col}:Q", title=kpi_label),
            color=alt.Color("channel:N",
                scale=alt.Scale(
                    domain=list(CHANNEL_COLORS.keys()),
                    range=list(CHANNEL_COLORS.values())
                ),
                legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[
                alt.Tooltip("date:T", title="날짜", format="%Y-%m-%d"),
                alt.Tooltip("channel:N", title="채널"),
                alt.Tooltip(f"{kpi_col}:Q", title=kpi_label, format=",.1f"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(trend)

# ── 전환 퍼널 ────────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("**:material/filter_alt: 채널별 전환 퍼널 (비율 기준)**")
    funnel_cols = st.columns(len(ch_agg))
    stages = ["impressions", "clicks_ch", "signups_ch", "purchases_ch"]
    stage_labels = ["노출", "클릭", "가입", "구매"]

    for col, (_, row) in zip(funnel_cols, ch_agg.iterrows()):
        with col:
            with st.container(border=True):
                st.markdown(f"**{row['channel']}**")
                base = row["impressions"] if row["impressions"] > 0 else 1
                for stage, label in zip(stages, stage_labels):
                    val = row[stage]
                    pct = val / base * 100
                    st.metric(label, f"{val:,.0f}", f"{pct:.2f}%")

# ── 종합 테이블 ───────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("**:material/table_chart: 채널별 종합 지표**")
    disp = ch_agg.rename(columns={
        "channel":"채널","cost":"광고비","impressions":"노출","clicks_ch":"클릭",
        "signups_ch":"가입","purchases_ch":"구매","revenue_ch":"매출",
        "ctr":"CTR(%)","cpc":"CPC(₩)","cpa_signup":"CPA가입(₩)",
        "cpa_purchase":"CPA구매(₩)","roas":"ROAS(%)",
    })
    st.dataframe(
        disp.set_index("채널").style.format({
            "광고비":"{:,.0f}","노출":"{:,.0f}","클릭":"{:,.0f}",
            "가입":"{:,.0f}","구매":"{:,.0f}","매출":"{:,.0f}",
            "CTR(%)":"{:.2f}","CPC(₩)":"{:,.0f}",
            "CPA가입(₩)":"{:,.0f}","CPA구매(₩)":"{:,.0f}","ROAS(%)":"{:.0f}",
        }).background_gradient(subset=["ROAS(%)"], cmap="Greens"),
    )
