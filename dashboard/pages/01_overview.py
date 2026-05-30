import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import altair as alt
import pandas as pd
import streamlit as st

from components.loader import load_master

st.set_page_config(
    page_title="Overview",
    page_icon=":material/monitoring:",
    layout="wide",
)

df = load_master()

# ── 사이드바 필터 ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### :material/filter_list: 필터")
    date_min, date_max = df["date"].min().date(), df["date"].max().date()
    date_range = st.date_input("기간", value=(date_min, date_max),
                               min_value=date_min, max_value=date_max)
    channels = st.multiselect("채널", sorted(df["channel"].unique()),
                               default=sorted(df["channel"].unique()))
    goals = st.multiselect("캠페인 목적", sorted(df["campaign_goal"].unique()),
                            default=sorted(df["campaign_goal"].unique()))

if len(date_range) == 2:
    s, e = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[(df["date"] >= s) & (df["date"] <= e)]
if channels:
    df = df[df["channel"].isin(channels)]
if goals:
    df = df[df["campaign_goal"].isin(goals)]

# ── 헤더 ──────────────────────────────────────────────────────────────────────
with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.markdown("## :material/monitoring: Overview")
    if st.button(":material/restart_alt: 초기화", type="tertiary"):
        st.session_state.clear()
        st.rerun()

# ── KPI 집계 ──────────────────────────────────────────────────────────────────
cost        = df["cost"].sum()
impressions = df["impressions"].sum()
clicks      = df["clicks_ch"].sum()
signups     = df["signups_ch"].sum()
purchases   = df["purchases_ch"].sum()
revenue     = df["revenue_ch"].sum()
ctr         = clicks / impressions * 100 if impressions else 0
cpa_signup  = cost / signups if signups else 0
cpa_purch   = cost / purchases if purchases else 0
roas        = revenue / cost * 100 if cost else 0

# 스파크라인용 주간 트렌드
weekly = df.copy()
weekly["week"] = df["date"].dt.to_period("W").apply(lambda p: p.start_time)
wk = weekly.groupby("week").agg(
    cost=("cost","sum"), signups=("signups_ch","sum"),
    purchases=("purchases_ch","sum"), revenue=("revenue_ch","sum"),
    clicks=("clicks_ch","sum"), impressions=("impressions","sum"),
).reset_index().sort_values("week")
wk["roas"] = (wk["revenue"] / wk["cost"] * 100).fillna(0)
wk["cpa"]  = (wk["cost"] / wk["signups"]).fillna(0)
wk["ctr"]  = (wk["clicks"] / wk["impressions"] * 100).fillna(0)

# ── KPI 카드 (스파크라인 포함) ─────────────────────────────────────────────────
with st.container(horizontal=True):
    st.metric(
        ":material/payments: 총 광고비",
        f"₩{cost/1e6:.1f}M",
        border=True,
        chart_data=wk["cost"].tolist(),
        chart_type="bar",
    )
    st.metric(
        ":material/visibility: 노출",
        f"{impressions/1e6:.1f}M",
        border=True,
        chart_data=wk["impressions"].tolist(),
        chart_type="line",
    )
    st.metric(
        ":material/ads_click: CTR",
        f"{ctr:.2f}%",
        border=True,
        chart_data=wk["ctr"].tolist(),
        chart_type="line",
    )
    st.metric(
        ":material/person_add: 회원가입",
        f"{signups:,}",
        border=True,
        chart_data=wk["signups"].tolist(),
        chart_type="bar",
    )
    st.metric(
        ":material/shopping_cart: 구매",
        f"{purchases:,}",
        border=True,
        chart_data=wk["purchases"].tolist(),
        chart_type="bar",
    )
    st.metric(
        ":material/price_check: CPA(가입)",
        f"₩{cpa_signup:,.0f}",
        border=True,
        chart_data=wk["cpa"].tolist(),
        chart_type="line",
    )
    st.metric(
        ":material/trending_up: ROAS",
        f"{roas:.0f}%",
        border=True,
        chart_data=wk["roas"].tolist(),
        chart_type="line",
    )

# ── 일별 트렌드 차트 ──────────────────────────────────────────────────────────
daily = df.groupby("date").agg(
    cost=("cost","sum"), impressions=("impressions","sum"),
    clicks_ch=("clicks_ch","sum"), signups_ch=("signups_ch","sum"),
    purchases_ch=("purchases_ch","sum"), revenue_ch=("revenue_ch","sum"),
).reset_index()
daily["ctr"]  = daily["clicks_ch"] / daily["impressions"] * 100
daily["roas"] = daily["revenue_ch"] / daily["cost"] * 100
daily["cpa"]  = daily["cost"] / daily["signups_ch"]

tab1, tab2, tab3 = st.tabs([
    ":material/bar_chart: 광고비 & ROAS",
    ":material/group: 가입 & 구매",
    ":material/query_stats: CTR & CPA",
])

def altair_dual(df, x, y1, y2, y1_label, y2_label, y1_fmt=",d", y2_fmt=".1f"):
    base = alt.Chart(df).encode(x=alt.X(f"{x}:T", title=None))
    bar = base.mark_bar(opacity=0.7, color="#4285F4").encode(
        y=alt.Y(f"{y1}:Q", title=y1_label, axis=alt.Axis(format=y1_fmt)),
        tooltip=[alt.Tooltip(f"{x}:T", title="날짜", format="%Y-%m-%d"),
                 alt.Tooltip(f"{y1}:Q", title=y1_label, format=y1_fmt)],
    )
    line = base.mark_line(color="#EA4335", strokeWidth=2).encode(
        y=alt.Y(f"{y2}:Q", title=y2_label, axis=alt.Axis(format=y2_fmt)),
        tooltip=[alt.Tooltip(f"{x}:T", title="날짜", format="%Y-%m-%d"),
                 alt.Tooltip(f"{y2}:Q", title=y2_label, format=y2_fmt)],
    )
    return alt.layer(bar, line).resolve_scale(y="independent").properties(height=320)

def altair_multi_line(df, x, y_cols, colors, labels):
    dfs = []
    for col, label in zip(y_cols, labels):
        tmp = df[["date", col]].copy()
        tmp.columns = ["date", "value"]
        tmp["series"] = label
        dfs.append(tmp)
    long = pd.concat(dfs)
    color_map = dict(zip(labels, colors))
    return (
        alt.Chart(long)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("value:Q", title=None),
            color=alt.Color("series:N", title=None,
                            scale=alt.Scale(domain=labels, range=colors),
                            legend=alt.Legend(orient="bottom")),
            tooltip=[alt.Tooltip("date:T", title="날짜", format="%Y-%m-%d"),
                     alt.Tooltip("value:Q", title="값", format=",d"),
                     alt.Tooltip("series:N", title="지표")],
        )
        .properties(height=320)
    )

with tab1:
    st.altair_chart(altair_dual(daily, "date", "cost", "roas", "광고비(₩)", "ROAS(%)", ",d", ".0f"))

with tab2:
    st.altair_chart(altair_multi_line(daily, "date",
        ["signups_ch", "purchases_ch"], ["#4285F4", "#34A853"], ["회원가입", "구매"]))

with tab3:
    st.altair_chart(altair_dual(daily, "date", "cpa", "ctr", "CPA가입(₩)", "CTR(%)", ",.0f", ".2f"))

# ── 월별 요약 ─────────────────────────────────────────────────────────────────
df["month"] = df["date"].dt.to_period("M").astype(str)
monthly = df.groupby("month").agg(
    cost=("cost","sum"), impressions=("impressions","sum"),
    clicks=("clicks_ch","sum"), signups=("signups_ch","sum"),
    purchases=("purchases_ch","sum"), revenue=("revenue_ch","sum"),
).reset_index()
monthly["CTR(%)"]     = (monthly["clicks"] / monthly["impressions"] * 100).round(2)
monthly["CPA가입(₩)"] = (monthly["cost"] / monthly["signups"]).round(0).astype(int)
monthly["ROAS(%)"]    = (monthly["revenue"] / monthly["cost"] * 100).round(0).astype(int)

with st.container(border=True):
    st.markdown("**:material/calendar_month: 월별 성과 요약**")
    st.dataframe(
        monthly.rename(columns={
            "month":"월","cost":"광고비","impressions":"노출","clicks":"클릭",
            "signups":"회원가입","purchases":"구매","revenue":"매출",
        }).style.format({
            "광고비":"{:,}","노출":"{:,}","클릭":"{:,}","회원가입":"{:,}",
            "구매":"{:,}","매출":"{:,}","CTR(%)":"{:.2f}","CPA가입(₩)":"{:,}","ROAS(%)":"{:,}",
        }),
        hide_index=True,
    )

# ── 이상치 ────────────────────────────────────────────────────────────────────
anomalies = df[df["anomaly_flag"] != ""][
    ["date","channel","campaign","adgroup","creative","ctr","cpa_signup","roas","anomaly_flag"]
].sort_values("date", ascending=False)

if not anomalies.empty:
    with st.expander(f":material/warning: 이상치 {len(anomalies)}건", icon=":material/warning:"):
        st.dataframe(anomalies.reset_index(drop=True).style.format({
            "ctr":"{:.2f}","cpa_signup":"{:,.0f}","roas":"{:.0f}",
        }), hide_index=True)
