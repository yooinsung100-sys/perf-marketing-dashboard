import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import altair as alt
import pandas as pd
import streamlit as st

from components.loader import load_braze_campaigns, load_braze_purchases, load_braze_users

st.set_page_config(page_title="Braze CRM", page_icon=":material/mail:", layout="wide")

camps    = load_braze_campaigns()
purchases = load_braze_purchases()
users    = load_braze_users()

SEG_ORDER  = ["Champion","Loyal","Potential","At-Risk","Hibernating","New","Lost"]
SEG_COLORS = ["#2ECC71","#27AE60","#3498DB","#F39C12","#E67E22","#9B59B6","#E74C3C"]

with st.sidebar:
    st.markdown("### :material/filter_list: 필터")
    round_opts = {"1월 (Round 1)":1, "2월 (Round 2)":2, "3월 (Round 3)":3}
    rounds = st.multiselect("라운드", list(round_opts.keys()), default=list(round_opts.keys()))
    selected_months = [round_opts[r] for r in rounds]

    segments = st.multiselect("세그먼트", SEG_ORDER, default=SEG_ORDER)
    ch_braze = st.multiselect("채널", sorted(camps["channel"].unique()),
                               default=sorted(camps["channel"].unique()))

camps = camps[camps["sent_at"].dt.month.isin(selected_months)]
camps = camps[camps["target_segment"].isin(segments)]
camps = camps[camps["channel"].isin(ch_braze)]

with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"):
    st.markdown("## :material/mail: Braze CRM 분석")
    if st.button(":material/restart_alt: 초기화", type="tertiary"):
        st.session_state.clear()
        st.rerun()

# ── 캠페인 집계 ───────────────────────────────────────────────────────────────
camp_agg = camps.groupby(["campaign_id","canvas_name","channel","target_segment","variant"]).agg(
    sent=("delivered","count"),
    delivered=("delivered","sum"),
    opened=("opened","sum"),
    clicked=("clicked","sum"),
    converted=("converted","sum"),
    conversion_value=("conversion_value","sum"),
    unsubscribed=("unsubscribed","sum"),
).reset_index()

camp_agg["open_rate"]  = (camp_agg["opened"]  / camp_agg["delivered"] * 100).where(camp_agg["delivered"] > 0)
camp_agg["click_rate"] = (camp_agg["clicked"] / camp_agg["delivered"] * 100).where(camp_agg["delivered"] > 0)
camp_agg["conv_rate"]  = (camp_agg["converted"] / camp_agg["delivered"] * 100).where(camp_agg["delivered"] > 0)
camp_agg["unsub_rate"] = (camp_agg["unsubscribed"] / camp_agg["delivered"] * 100).where(camp_agg["delivered"] > 0)

# ── KPI 카드 ──────────────────────────────────────────────────────────────────
total_del  = camp_agg["delivered"].sum()
total_conv = camp_agg["converted"].sum()
total_val  = camp_agg["conversion_value"].sum()
avg_open   = camp_agg["opened"].sum() / total_del * 100 if total_del else 0
avg_conv   = total_conv / total_del * 100 if total_del else 0

# 월별 발송 트렌드 (스파크라인용)
monthly_sent = camps.groupby(camps["sent_at"].dt.month)["delivered"].sum().tolist()

with st.container(horizontal=True):
    st.metric(":material/send: 도달", f"{total_del:,}",
              border=True, chart_data=monthly_sent, chart_type="bar")
    st.metric(":material/visibility: 오픈율", f"{avg_open:.1f}%", border=True)
    st.metric(":material/touch_app: 전환율", f"{avg_conv:.2f}%", border=True)
    st.metric(":material/shopping_cart: 전환건수", f"{total_conv:,}", border=True)
    st.metric(":material/payments: 전환매출", f"₩{total_val:,}", border=True)

# ── 탭 ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    ":material/campaign: 캠페인 분석",
    ":material/people: 세그먼트 분석",
    ":material/cell_tower: 채널별 성과",
    ":material/person: 유저 분석",
])

# ── TAB 1: 캠페인 분석 ────────────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**:material/scatter_plot: 오픈율 vs 전환율**")
            scatter = (
                alt.Chart(camp_agg.dropna(subset=["open_rate","conv_rate"]))
                .mark_circle(opacity=0.8)
                .encode(
                    x=alt.X("open_rate:Q", title="오픈율(%)"),
                    y=alt.Y("conv_rate:Q", title="전환율(%)"),
                    size=alt.Size("delivered:Q", legend=None, scale=alt.Scale(range=[100,1500])),
                    color=alt.Color("target_segment:N", title="세그먼트",
                        scale=alt.Scale(domain=SEG_ORDER, range=SEG_COLORS),
                        legend=alt.Legend(orient="bottom")),
                    shape=alt.Shape("channel:N", title="채널",
                                    legend=alt.Legend(orient="bottom")),
                    tooltip=[
                        alt.Tooltip("canvas_name:N", title="캠페인"),
                        alt.Tooltip("target_segment:N", title="세그먼트"),
                        alt.Tooltip("channel:N", title="채널"),
                        alt.Tooltip("open_rate:Q", title="오픈율(%)", format=".1f"),
                        alt.Tooltip("conv_rate:Q", title="전환율(%)", format=".2f"),
                        alt.Tooltip("delivered:Q", title="도달", format=",d"),
                    ],
                )
                .properties(height=360)
            )
            st.altair_chart(scatter)

    with col2:
        with st.container(border=True):
            st.markdown("**:material/filter_alt: 캠페인별 발송 퍼널**")
            camp_total = camp_agg.groupby("canvas_name").agg(
                delivered=("delivered","sum"), opened=("opened","sum"),
                clicked=("clicked","sum"), converted=("converted","sum"),
            ).reset_index()
            for _, row in camp_total.head(5).iterrows():
                with st.container(border=True):
                    st.caption(row["canvas_name"])
                    funnel_cols = st.columns(4)
                    stages = [("도달",row["delivered"]),("오픈",row["opened"]),
                               ("클릭",row["clicked"]),("전환",row["converted"])]
                    base = row["delivered"] or 1
                    for fc, (label, val) in zip(funnel_cols, stages):
                        fc.metric(label, f"{val:,}", f"{val/base*100:.1f}%")

    with st.container(border=True):
        st.markdown("**:material/table_chart: 캠페인 상세 테이블**")
        disp = camp_agg[["canvas_name","channel","target_segment","variant",
                          "sent","delivered","opened","clicked","converted","conversion_value",
                          "open_rate","click_rate","conv_rate","unsub_rate"]].rename(columns={
            "canvas_name":"캠페인","channel":"채널","target_segment":"세그먼트","variant":"변형",
            "sent":"발송","delivered":"도달","opened":"오픈","clicked":"클릭","converted":"전환",
            "conversion_value":"전환매출","open_rate":"오픈율(%)","click_rate":"클릭율(%)",
            "conv_rate":"전환율(%)","unsub_rate":"수신거부율(%)",
        })
        st.dataframe(
            disp.sort_values("전환율(%)", ascending=False).reset_index(drop=True)
            .style.format({
                "발송":"{:,}","도달":"{:,}","오픈":"{:,}","클릭":"{:,}",
                "전환":"{:,}","전환매출":"{:,}",
                "오픈율(%)":"{:.1f}","클릭율(%)":"{:.2f}",
                "전환율(%)":"{:.2f}","수신거부율(%)":"{:.2f}",
            }).background_gradient(subset=["전환율(%)"], cmap="Greens"),
            hide_index=True,
        )

# ── TAB 2: 세그먼트 분석 ──────────────────────────────────────────────────────
with tab2:
    seg_agg = camps.groupby("target_segment").agg(
        delivered=("delivered","sum"), opened=("opened","sum"),
        clicked=("clicked","sum"), converted=("converted","sum"),
        conversion_value=("conversion_value","sum"),
    ).reset_index()
    seg_agg["open_rate"] = seg_agg["opened"] / seg_agg["delivered"] * 100
    seg_agg["conv_rate"] = seg_agg["converted"] / seg_agg["delivered"] * 100
    seg_agg["target_segment"] = pd.Categorical(seg_agg["target_segment"], SEG_ORDER, ordered=True)
    seg_agg = seg_agg.sort_values("target_segment")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("**:material/bar_chart: 세그먼트별 오픈율 & 전환율**")
            seg_long = seg_agg.melt(
                id_vars="target_segment",
                value_vars=["open_rate","conv_rate"],
                var_name="metric", value_name="rate",
            )
            seg_long["metric"] = seg_long["metric"].map({"open_rate":"오픈율(%)","conv_rate":"전환율(%)"})
            bar_seg = (
                alt.Chart(seg_long)
                .mark_bar()
                .encode(
                    x=alt.X("target_segment:N", title=None, sort=SEG_ORDER),
                    y=alt.Y("rate:Q", title="비율(%)"),
                    color=alt.Color("metric:N", title=None,
                                    legend=alt.Legend(orient="bottom")),
                    xOffset="metric:N",
                    tooltip=[alt.Tooltip("target_segment:N"), alt.Tooltip("metric:N"),
                             alt.Tooltip("rate:Q", format=".2f")],
                )
                .properties(height=320)
            )
            st.altair_chart(bar_seg)

    with col2:
        with st.container(border=True):
            st.markdown("**:material/payments: 세그먼트별 전환 매출**")
            bar_val = (
                alt.Chart(seg_agg)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("target_segment:N", title=None, sort=SEG_ORDER),
                    y=alt.Y("conversion_value:Q", title="전환매출(₩)"),
                    color=alt.Color("target_segment:N",
                        scale=alt.Scale(domain=SEG_ORDER, range=SEG_COLORS),
                        legend=None),
                    tooltip=[alt.Tooltip("target_segment:N"),
                             alt.Tooltip("conversion_value:Q", format=",d")],
                )
                .properties(height=320)
            )
            st.altair_chart(bar_val)

# ── TAB 3: 채널별 성과 ────────────────────────────────────────────────────────
with tab3:
    ch_agg = camps.groupby("channel").agg(
        delivered=("delivered","sum"), opened=("opened","sum"),
        clicked=("clicked","sum"), converted=("converted","sum"),
    ).reset_index()
    ch_agg["open_rate"]  = ch_agg["opened"]  / ch_agg["delivered"] * 100
    ch_agg["click_rate"] = ch_agg["clicked"] / ch_agg["delivered"] * 100
    ch_agg["conv_rate"]  = ch_agg["converted"] / ch_agg["delivered"] * 100

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**:material/bar_chart: 채널별 오픈 · 클릭 · 전환율**")
            ch_long = ch_agg.melt(id_vars="channel",
                value_vars=["open_rate","click_rate","conv_rate"],
                var_name="metric", value_name="rate")
            ch_long["metric"] = ch_long["metric"].map({
                "open_rate":"오픈율(%)","click_rate":"클릭율(%)","conv_rate":"전환율(%)"
            })
            ch_bar = (
                alt.Chart(ch_long)
                .mark_bar()
                .encode(
                    x=alt.X("channel:N", title=None),
                    y=alt.Y("rate:Q", title="비율(%)"),
                    color=alt.Color("metric:N", legend=alt.Legend(orient="bottom")),
                    xOffset="metric:N",
                    tooltip=[alt.Tooltip("channel:N"), alt.Tooltip("metric:N"),
                             alt.Tooltip("rate:Q", format=".2f")],
                )
                .properties(height=300)
            )
            st.altair_chart(ch_bar)

    with col2:
        with st.container(border=True):
            st.markdown("**:material/pie_chart: 채널별 발송 비율**")
            pie = (
                alt.Chart(ch_agg)
                .mark_arc(innerRadius=60, outerRadius=110)
                .encode(
                    theta="delivered:Q",
                    color=alt.Color("channel:N",
                                    legend=alt.Legend(orient="bottom")),
                    tooltip=[alt.Tooltip("channel:N"),
                             alt.Tooltip("delivered:Q", format=",d", title="도달")],
                )
                .properties(height=300)
            )
            st.altair_chart(pie)

# ── TAB 4: 유저 분석 ──────────────────────────────────────────────────────────
with tab4:
    col1, col2 = st.columns(2)

    seg_dist = users["_segment_truth"].value_counts().reset_index()
    seg_dist.columns = ["segment","count"]
    seg_dist["segment"] = pd.Categorical(seg_dist["segment"], SEG_ORDER, ordered=True)
    seg_dist = seg_dist.sort_values("segment")

    with col1:
        with st.container(border=True):
            st.markdown("**:material/people: 유저 세그먼트 분포 (15,000명)**")
            bar_dist = (
                alt.Chart(seg_dist)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("segment:N", title=None, sort=SEG_ORDER),
                    y=alt.Y("count:Q", title="유저 수"),
                    color=alt.Color("segment:N",
                        scale=alt.Scale(domain=SEG_ORDER, range=SEG_COLORS),
                        legend=None),
                    tooltip=[alt.Tooltip("segment:N"), alt.Tooltip("count:Q", format=",d")],
                )
                .properties(height=300)
            )
            st.altair_chart(bar_dist)

    with col2:
        with st.container(border=True):
            st.markdown("**:material/payments: 세그먼트별 90일 구매금액 분포**")
            box_df = users[users["_segment_truth"].isin(SEG_ORDER)].copy()
            box_df["_segment_truth"] = pd.Categorical(box_df["_segment_truth"], SEG_ORDER, ordered=True)
            box = (
                alt.Chart(box_df)
                .mark_boxplot(extent="min-max")
                .encode(
                    x=alt.X("_segment_truth:N", title=None, sort=SEG_ORDER),
                    y=alt.Y("purchase_amount_90d:Q", title="90일 구매금액(₩)"),
                    color=alt.Color("_segment_truth:N",
                        scale=alt.Scale(domain=SEG_ORDER, range=SEG_COLORS),
                        legend=None),
                )
                .properties(height=300)
            )
            st.altair_chart(box)

    with st.container(border=True):
        st.markdown("**:material/stacked_bar_chart: 유입 채널별 세그먼트 분포**")
        attr_top = ["googleadwords_int","Facebook Ads","naver_search","organic","referral"]
        attr_df = users[users["attribution_source"].isin(attr_top)].groupby(
            ["attribution_source","_segment_truth"]
        ).size().reset_index(name="count")
        attr_df["_segment_truth"] = pd.Categorical(attr_df["_segment_truth"], SEG_ORDER, ordered=True)

        stacked = (
            alt.Chart(attr_df)
            .mark_bar()
            .encode(
                x=alt.X("attribution_source:N", title="유입 채널"),
                y=alt.Y("count:Q", title="유저 수"),
                color=alt.Color("_segment_truth:N", title="세그먼트",
                    scale=alt.Scale(domain=SEG_ORDER, range=SEG_COLORS),
                    legend=alt.Legend(orient="bottom")),
                order=alt.Order("_segment_truth:N"),
                tooltip=[alt.Tooltip("attribution_source:N", title="채널"),
                         alt.Tooltip("_segment_truth:N", title="세그먼트"),
                         alt.Tooltip("count:Q", format=",d")],
            )
            .properties(height=320)
        )
        st.altair_chart(stacked)
