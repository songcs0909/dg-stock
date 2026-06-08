import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(
    page_title="주식 분석 대시보드",
    page_icon="📈",
    layout="wide"
)

st.title("📈 한국·미국 주식 분석 대시보드")
st.markdown("yfinance와 Plotly로 주요 주식의 수익률과 차트를 비교해보세요!")

# 주요 종목 딕셔너리 (이름: 티커)
STOCK_DICT = {
    # 미국 주식
    "Apple (애플)": "AAPL",
    "Microsoft (마이크로소프트)": "MSFT",
    "NVIDIA (엔비디아)": "NVDA",
    "Tesla (테슬라)": "TSLA",
    "Amazon (아마존)": "AMZN",
    "Google (구글)": "GOOGL",
    "Meta (메타)": "META",
    # 한국 주식 (.KS는 코스피, .KQ는 코스닥)
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "LG에너지솔루션": "373220.KS",
    "현대차": "005380.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "셀트리온": "068270.KS",
}

# 사이드바 설정
st.sidebar.header("⚙️ 설정")

# 종목 선택 (다중 선택)
selected_names = st.sidebar.multiselect(
    "비교할 종목을 선택하세요 (여러 개 가능)",
    options=list(STOCK_DICT.keys()),
    default=["Apple (애플)", "삼성전자", "NVIDIA (엔비디아)"]
)

# 기간 선택
period_options = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
}
selected_period_label = st.sidebar.selectbox(
    "조회 기간을 선택하세요",
    options=list(period_options.keys()),
    index=3  # 기본값: 1년
)
selected_period = period_options[selected_period_label]


# 데이터 불러오기 함수 (캐시 적용으로 속도 향상)
@st.cache_data(ttl=3600)  # 1시간 동안 캐시 유지
def load_stock_data(ticker, period):
    """yfinance로 주식 데이터를 불러오는 함수"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        return df
    except Exception as e:
        return None


# 메인 로직
if not selected_names:
    st.warning("⚠️ 왼쪽 사이드바에서 비교할 종목을 하나 이상 선택해주세요!")
else:
    # 선택한 종목들의 데이터 저장
    stock_data = {}
    failed_stocks = []

    with st.spinner("📡 주식 데이터를 불러오는 중..."):
        for name in selected_names:
            ticker = STOCK_DICT[name]
            df = load_stock_data(ticker, selected_period)
            if df is not None and not df.empty:
                stock_data[name] = df
            else:
                failed_stocks.append(name)

    # 데이터 로드 실패한 종목 안내
    if failed_stocks:
        st.error(f"❌ 다음 종목의 데이터를 불러오지 못했습니다: {', '.join(failed_stocks)}")

    if stock_data:
        # ===== 1. 수익률 비교 (정규화된 차트) =====
        st.subheader(f"📊 누적 수익률 비교 ({selected_period_label})")
        st.caption("기간 시작일을 0%로 맞춰 각 종목의 상대적 수익률을 비교합니다.")

        fig_return = go.Figure()

        for name, df in stock_data.items():
            # 시작일 대비 수익률(%) 계산
            normalized = (df["Close"] / df["Close"].iloc[0] - 1) * 100
            fig_return.add_trace(go.Scatter(
                x=df.index,
                y=normalized,
                mode="lines",
                name=name,
                line=dict(width=2)
            ))

        fig_return.update_layout(
            xaxis_title="날짜",
            yaxis_title="수익률 (%)",
            hovermode="x unified",
            template="plotly_white",
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        # 0% 기준선 추가
        fig_return.add_hline(y=0, line_dash="dash", line_color="gray")

        st.plotly_chart(fig_return, use_container_width=True)

        # ===== 2. 수익률 요약 표 =====
        st.subheader("📋 수익률 요약")

        summary_list = []
        for name, df in stock_data.items():
            start_price = df["Close"].iloc[0]
            end_price = df["Close"].iloc[-1]
            total_return = (end_price / start_price - 1) * 100
            high_price = df["High"].max()
            low_price = df["Low"].min()

            summary_list.append({
                "종목": name,
                "시작가": round(start_price, 2),
                "현재가": round(end_price, 2),
                "수익률(%)": round(total_return, 2),
                "최고가": round(high_price, 2),
                "최저가": round(low_price, 2),
            })

        summary_df = pd.DataFrame(summary_list)

        # 수익률에 색상 적용하여 표시
        st.dataframe(
            summary_df.style.format({
                "시작가": "{:,.2f}",
                "현재가": "{:,.2f}",
                "수익률(%)": "{:+.2f}",
                "최고가": "{:,.2f}",
                "최저가": "{:,.2f}",
            }).applymap(
                lambda v: "color: red" if v > 0 else "color: blue",
                subset=["수익률(%)"]
            ),
            use_container_width=True
        )

        # ===== 3. 개별 종목 캔들스틱 차트 =====
        st.subheader("🕯️ 개별 종목 캔들스틱 차트")

        chart_name = st.selectbox(
            "캔들스틱 차트로 볼 종목을 선택하세요",
            options=list(stock_data.keys())
        )

        df_selected = stock_data[chart_name]

        fig_candle = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
            subplot_titles=("주가 (캔들스틱)", "거래량")
        )

        # 캔들스틱
        fig_candle.add_trace(
            go.Candlestick(
                x=df_selected.index,
                open=df_selected["Open"],
                high=df_selected["High"],
                low=df_selected["Low"],
                close=df_selected["Close"],
                name="주가",
                increasing_line_color="red",   # 한국식: 상승 빨강
                decreasing_line_color="blue"   # 한국식: 하락 파랑
            ),
            row=1, col=1
        )

        # 거래량 막대
        fig_candle.add_trace(
            go.Bar(
                x=df_selected.index,
                y=df_selected["Volume"],
                name="거래량",
                marker_color="lightgray"
            ),
            row=2, col=1
        )

        fig_candle.update_layout(
            height=600,
            template="plotly_white",
            xaxis_rangeslider_visible=False,
            showlegend=False,
            title=f"{chart_name} 상세 차트"
        )

        st.plotly_chart(fig_candle, use_container_width=True)

# 푸터
st.markdown("---")
st.caption("📌 데이터 출처: Yahoo Finance (yfinance) | 투자 판단의 책임은 본인에게 있습니다.")
