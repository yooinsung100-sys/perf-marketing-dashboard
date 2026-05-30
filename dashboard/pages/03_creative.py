import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import altair as alt
import pandas as pd
import streamlit as st

from components.loader import load_master

st.set_page_config(page_title="소재 분석", page_icon=":material/palette:", layout="wide")

df = load_master()

CHANNEL_COLORS = {"구글": "#4285F4", "메타": "#1877F2", "네이버": "#03C75A"}
TYPE_COLORS = {"영상": "#EA4335", "이미지": "#4285F4", "카루셀": "#FBBC04", "배너": "#34A853", "기타": "#9AA0A6"}

with st.sidebar:
    st.markdown("### :material/filter_list: 필터")
    date_min, date_max = df["date"].min().date(), df["date"].max().date()
    date_range = st.date_input("기간", value=(date_min, date_max),
                               min_value=date_min, max_value=date_max)
    channels = st.multiselect("채널", sorted(df["channel"].unique()),
                               default=sorted(df["channel"].unique()))
    goals = st.multiselect("캠페인 목적", sorted(df["campaign_goal"].unique()),
                            default=sorted(df["campaign_goal"].unique()))

    st.markdown("---")
    x_opts = {"CTR(%)": "ctr", "노출": "impressions", "CPC(₩)": "cpc"}
    y_opts = {"ROAS(%)": "roas", "CPA 가입(₩)": "cpa_signup", "CPA 구매(₩)": "cpa_purchase"}
    x_label = st.selectbox("버블차트 X축", list(x_opts.keys()))
    y_label = st.selectbox("버블차트 Y축", list(y_opts.keys()))
    top_n = st.slider("Top N 소재", 10, 48, 20)

if len(date_range) == 2:
    s, e = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[(df["date"] >= s) & (df["date"] <= e)]
if channels:
    df = df[df["channel"].isin(channels)]
if goals:
    df = df[df["campaign_goal"].isin(goals)]

with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.markdown("## :material/palette: 소재별 성과 분석")
    if st.button(":material/restart_alt: 초기화", type="tertiary"):
        st.session_state.clear()
        st.rerun()

# ── 소재 집계 ─────────────────────────────────────────────────────────────────
def parse_type(name):
    n = str(name).upper()
    if n.startswith("VID"): return "영상"
    if n.startswith("IMG"): return "이미지"
    if n.startswith("CRS"): return "카루셀"
    if n.startswith("BNR"): return "배너"
    return "기타"

cr = df.groupby(["channel","campaign_goal","campaign","adgroup","creative"]).agg(
    cost=("cost","sum"), impressions=("impressions","sum"),
    clicks_ch=("clicks_ch","sum"), signups_ch=("signups_ch","sum"),
    purchases_ch=("purchases_ch","sum"), revenue_ch=("revenue_ch","sum"),
    clicks_af=("clicks_af","sum"), signups_af=("signups_af","sum"),
).reset_index()

cr["ctr"]          = (cr["clicks_ch"] / cr["impressions"] * 100).where(cr["impressions"] > 0)
cr["cpc"]          = (cr["cost"] / cr["clicks_ch"]).where(cr["clicks_ch"] > 0)
cr["cpa_signup"]   = (cr["cost"] / cr["signups_ch"]).where(cr["signups_ch"] > 0)
cr["cpa_purchase"] = (cr["cost"] / cr["purchases_ch"]).where(cr["purchases_ch"] > 0)
cr["roas"]         = (cr["revenue_ch"] / cr["cost"] * 100).where(cr["cost"] > 0)
cr["creative_type"] = cr["creative"].apply(parse_type)

x_col = x_opts[x_label]
y_col = y_opts[y_label]

# ── 소재 유형별 KPI 요약 카드 ─────────────────────────────────────────────────
type_agg = cr.groupby("creative_type").agg(
    count=("creative","count"),
    roas=("roas","mean"), ctr=("ctr","mean"), cpa_signup=("cpa_signup","mean"),
    cost=("cost","sum"),
).reset_index()

with st.container(horizontal=True):
    for _, row in type_agg.iterrows():
        with st.container(border=True):
            st.markdown(f"**{row['creative_type']}** :material/image:")
            st.caption(f"{int(row['count'])}개 소재")
            st.metric("평균 ROAS", f"{row['roas']:.0f}%")
            st.metric("평균 CTR", f"{row['ctr']:.2f}%")
            st.metric("평균 CPA", f"₩{row['cpa_signup']:,.0f}")

# ── 버블차트 ─────────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown(f"**:material/bubble_chart: 소재 버블차트  {x_label} vs {y_label}** (크기 = 광고비)")
    plot_df = cr.dropna(subset=[x_col, y_col]).nlargest(top_n, "cost").copy()
    plot_df["cost_norm"] = (plot_df["cost"] / plot_df["cost"].max() * 1000).clip(lower=50)

    bubble = (
        alt.Chart(plot_df)
        .mark_circle(opacity=0.75)
        .encode(
            x=alt.X(f"{x_col}:Q", title=x_label),
            y=alt.Y(f"{y_col}:Q", title=y_label),
            size=alt.Size("cost:Q", title="광고비",
                          scale=alt.Scale(range=[100, 2000]), legend=None),
            color=alt.Color("channel:N", title="채널",
                scale=alt.Scale(
                    domain=list(CHANNEL_COLORS.keys()),
                    range=list(CHANNEL_COLORS.values())
                ),
                legend=alt.Legend(orient="bottom")),
            shape=alt.Shape("creative_type:N", title="소재유형",
                            legend=alt.Legend(orient="bottom")),
            tooltip=[
                alt.Tooltip("creative:N", title="소재"),
                alt.Tooltip("channel:N", title="채널"),
                alt.Tooltip("campaign_goal:N", title="목적"),
                alt.Tooltip(f"{x_col}:Q", title=x_label, format=",.2f"),
                alt.Tooltip(f"{y_col}:Q", title=y_label, format=",.0f"),
                alt.Tooltip("cost:Q", title="광고비", format=",d"),
            ],
        )
        .properties(height=480)
    )
    st.altair_chart(bubble)

# ── 채널 × 소재유형 ROAS 히트맵 ──────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("**:material/grid_on: 채널 × 소재유형 ROAS**")
        hm = cr.groupby(["channel","creative_type"]).agg(
            cost=("cost","sum"), revenue=("revenue_ch","sum")
        ).reset_index()
        hm["roas"] = hm["revenue"] / hm["cost"] * 100

        heat = (
            alt.Chart(hm)
            .mark_rect()
            .encode(
                x=alt.X("creative_type:N", title="소재유형"),
                y=alt.Y("channel:N", title="채널"),
                color=alt.Color("roas:Q", title="ROAS(%)",
                                scale=alt.Scale(scheme="blues")),
                tooltip=[alt.Tooltip("channel:N"), alt.Tooltip("creative_type:N"),
                         alt.Tooltip("roas:Q", format=",.0f", title="ROAS(%)")],
            ).properties(height=220)
        )
        text_h = heat.mark_text(fontSize=13, fontWeight="bold").encode(
            text=alt.Text("roas:Q", format=".0f"), color=alt.value("black")
        )
        st.altair_chart(heat + text_h)

with col2:
    with st.container(border=True):
        st.markdown(f"**:material/leaderboard: ROAS 상위 {top_n} 소재**")
        top = cr.nlargest(top_n, "roas").dropna(subset=["roas"])
        top_bar = (
            alt.Chart(top)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("roas:Q", title="ROAS(%)"),
                y=alt.Y("creative:N", title=None, sort="-x"),
                color=alt.Color("channel:N",
                    scale=alt.Scale(
                        domain=list(CHANNEL_COLORS.keys()),
                        range=list(CHANNEL_COLORS.values())
                    ), legend=alt.Legend(orient="bottom")),
                tooltip=[alt.Tooltip("creative:N"), alt.Tooltip("channel:N"),
                         alt.Tooltip("roas:Q", format=",.0f", title="ROAS(%)")],
            )
            .properties(height=max(300, top_n * 22))
        )
        st.altair_chart(top_bar)

# ── 전체 테이블 ───────────────────────────────────────────────────────────────
with st.container(border=True):
    st.markdown("**:material/table_chart: 소재 전체 성과 테이블**")
    with st.popover(":material/tune: 컬럼 선택", type="tertiary"):
        show_af = st.toggle("AppsFlyer 지표 포함", value=False)

    cols_base = ["channel","creative_type","campaign_goal","campaign","adgroup","creative",
                 "cost","impressions","clicks_ch","signups_ch","purchases_ch","revenue_ch",
                 "ctr","cpc","cpa_signup","cpa_purchase","roas"]
    cols_af   = ["clicks_af","signups_af"]
    show_cols = cols_base + (cols_af if show_af else [])

    disp = cr[show_cols].copy()
    disp.columns = (["채널","유형","목적","캠페인","그룹","소재",
                      "광고비","노출","클릭","가입","구매","매출",
                      "CTR(%)","CPC(₩)","CPA가입(₩)","CPA구매(₩)","ROAS(%)"]
                    + (["AF클릭","AF가입"] if show_af else []))

    fmt = {"광고비":"{:,.0f}","노출":"{:,.0f}","클릭":"{:,.0f}","가입":"{:,.0f}",
           "구매":"{:,.0f}","매출":"{:,.0f}","CTR(%)":"{:.2f}","CPC(₩)":"{:,.0f}",
           "CPA가입(₩)":"{:,.0f}","CPA구매(₩)":"{:,.0f}","ROAS(%)":"{:.0f}"}
    if show_af:
        fmt.update({"AF클릭":"{:,.0f}","AF가입":"{:,.0f}"})

    st.dataframe(
        disp.sort_values("ROAS(%)", ascending=False).reset_index(drop=True)
        .style.format(fmt).background_gradient(subset=["ROAS(%)"], cmap="Greens"),
        hide_index=True,
    )
