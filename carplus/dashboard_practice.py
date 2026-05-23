import pathlib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="我的儀表板", layout="wide")
st.title("🚲 我的共享單車分析")

# ── 載入資料 ──────────────────────────────────────────────────

orders = pd.read_csv(
     "./orders.csv"),parse_dates=["rent_start_dt"])
orders["month"] = orders["rent_start_dt"].dt.to_period("M").astype(str)
orders["date"] = orders["rent_start_dt"].dt.normalize()

station_df = pd.read_csv(DATA_DIR / "irent.csv")
parking_df = pd.read_csv(DATA_DIR / "parking_lots.csv")
available_cars = pd.read_csv(DATA_DIR / "available_cars.csv", parse_dates=["available_date"])
map_browsing = pd.read_csv(DATA_DIR / "map_browsing.csv", parse_dates=["click_date"])

# ── 建立 Tab ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 總覽", "🗺️ 站點地圖", "📈 需求分析"])

# ════════════════════════════════════════════════════════════
# TAB 1 — 總覽
# ════════════════════════════════════════════════════════════
with tab1:
    st.subheader("月借車趨勢")

    monthly = orders.groupby("month").size().reset_index(name="借車次數")

    fig = px.bar(
        monthly,
        x="month",
        y="借車次數",
        title="月借車趨勢",
        color="借車次數",
        color_continuous_scale="Blues",
    )
    fig.update_layout(coloraxis_showscale=False, xaxis_title="月份")
    fig.update_xaxes(tickangle=45)

    x_num = np.arange(len(monthly))
    y = monthly["借車次數"].values
    z = np.polyfit(x_num, y, 1)
    trend = np.poly1d(z)(x_num)

    fig.add_trace(go.Scatter(
        x=monthly["month"],
        y=trend,
        mode="lines",
        name="趨勢線",
        line=dict(color="red", width=2, dash="dash"),
    ))

    st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 2 — 站點地圖
# ════════════════════════════════════════════════════════════
with tab2:
    station_df = station_df.rename(columns={
        "station_id": "id",
        "station_name": "name",
        "city": "city",
        "district": "district",
        "address": "address",
        "latitude": "latitude",
        "longitude": "longitude",
    })
    station_df["brand"] = "iRent"

    parking_df = parking_df.rename(columns={
        "parking_lot_id": "id",
        "parking_lot_name": "name",
        "parking_lot_city": "city",
        "parking_lot_area": "district",
        "parking_lot_latitude": "latitude",
        "parking_lot_longitude": "longitude",
        "parking_lot_biz_type_desc": "biz_type",
    })
    parking_df["brand"] = "停車場站點"

    station_cols = ["id", "name", "city", "district", "address", "latitude", "longitude", "brand"]
    parking_cols = ["id", "name", "city", "district", "latitude", "longitude", "brand", "biz_type"]

    station_df = station_df[station_cols]
    parking_df = parking_df[parking_cols]

    stations = pd.concat([station_df, parking_df], ignore_index=True)

    stations["latitude"] = pd.to_numeric(stations["latitude"], errors="coerce")
    stations["longitude"] = pd.to_numeric(stations["longitude"], errors="coerce")
    stations = stations.dropna(subset=["latitude", "longitude"])

    order_counts = (
        orders.groupby("depart_parking_lot_id")
        .size()
        .reset_index(name="訂單數")
        .rename(columns={"depart_parking_lot_id": "id"})
    )
    stations = stations.merge(order_counts, on="id", how="left")
    stations["訂單數"] = stations["訂單數"].fillna(0)

    st.metric("總站點數", f"{len(stations):,} 筆")

    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        brand_selected = st.selectbox(
            "選擇站點類型",
            options=["全部"] + list(stations["brand"].dropna().unique())
        )
    with col_filter2:
        district_selected = st.selectbox(
            "選擇行政區",
            options=["全部"] + sorted(stations["district"].dropna().unique())
        )
    with col_filter3:
        color_by = st.radio(
            "顏色依據",
            ["品牌類型", "需求密度（訂單數）"],
            horizontal=True,
        )

    filtered = stations.copy()
    if brand_selected != "全部":
        filtered = filtered[filtered["brand"] == brand_selected]
    if district_selected != "全部":
        filtered = filtered[filtered["district"] == district_selected]

    st.write(f"目前顯示：{len(filtered):,} 筆資料")

    if filtered.empty:
        st.warning("目前篩選條件下沒有資料，請重新選擇。")
    else:
        col1, col2 = st.columns([1, 3])

        with col1:
            st.dataframe(
                filtered[["brand", "name", "city", "district", "訂單數"]].head(50),
                use_container_width=True,
            )

        with col2:
            if color_by == "品牌類型":
                fig = px.scatter_mapbox(
                    filtered,
                    lat="latitude",
                    lon="longitude",
                    color="brand",
                    hover_name="name",
                    hover_data={
                        "brand": True,
                        "city": True,
                        "district": True,
                        "id": True,
                        "訂單數": True,
                        "latitude": False,
                        "longitude": False,
                    },
                    mapbox_style="open-street-map",
                    zoom=11,
                    center={
                        "lat": filtered["latitude"].mean(),
                        "lon": filtered["longitude"].mean(),
                    },
                    height=600,
                    title="站點分布地圖（品牌類型）",
                )
            else:
                fig = px.scatter_mapbox(
                    filtered,
                    lat="latitude",
                    lon="longitude",
                    color="訂單數",
                    size=filtered["訂單數"].clip(lower=1),
                    size_max=20,
                    color_continuous_scale="YlOrRd",
                    hover_name="name",
                    hover_data={
                        "brand": True,
                        "city": True,
                        "district": True,
                        "id": True,
                        "訂單數": True,
                        "latitude": False,
                        "longitude": False,
                    },
                    mapbox_style="open-street-map",
                    zoom=11,
                    center={
                        "lat": filtered["latitude"].mean(),
                        "lon": filtered["longitude"].mean(),
                    },
                    height=600,
                    title="站點需求密度地圖（訂單數越多越紅）",
                )

            fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})
            st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════
# TAB 3 — 需求分析（每日供需雙軸折線圖）
# ════════════════════════════════════════════════════════════
with tab3:
    st.subheader("每日訂單數 vs App 瀏覽次數")

    # ── 整理三條資料線 ────────────────────────────────────────
    daily_orders = (
        orders.groupby("date")
        .size()
        .reset_index(name="訂單數")
    )

    daily_browse = (
        map_browsing.groupby("click_date")["num_click_times"]
        .sum()
        .reset_index()
        .rename(columns={"click_date": "date", "num_click_times": "瀏覽次數"})
    )

    daily = (
        daily_orders
        .merge(daily_browse, on="date", how="outer")
        .sort_values("date")
    )

    # ── 滑動視窗選擇 ──────────────────────────────────────────
    window = st.slider("滾動平均天數", min_value=1, max_value=30, value=7, step=1)

    # ── 畫雙軸折線圖 ──────────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=daily["date"],
        y=daily["訂單數"].rolling(window).mean(),
        name=f"訂單數（{window}日均）",
        line=dict(color="#e74c3c", width=2),
    ))

    fig.add_trace(go.Scatter(
        x=daily["date"],
        y=daily["瀏覽次數"].rolling(window).mean(),
        name=f"App 瀏覽（{window}日均）",
        line=dict(color="#3498db", width=2, dash="dot"),
        yaxis="y2",
    ))

    fig.update_layout(
        title=f"每日訂單數 vs App 瀏覽次數（{window}日滾動平均）",
        yaxis=dict(title="訂單數", color="#e74c3c"),
        yaxis2=dict(
            title="App 瀏覽次數",
            color="#3498db",
            overlaying="y",
            side="right",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── 小統計摘要 ────────────────────────────────────────────
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("平均每日訂單", f"{daily['訂單數'].mean():.0f} 筆")
    c2.metric("最高單日訂單", f"{daily['訂單數'].max():.0f} 筆")
    c3.metric("平均每日瀏覽", f"{daily['瀏覽次數'].mean():.0f} 次")