import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 페이지 설정
st.set_page_config(
    page_title="AI 주식 분석 대시보드",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI 관련 주식 분석 대시보드")
st.markdown("AI 시대를 이끄는 주요 기업들의 수익률과 차트를 한눈에 비교해보세요!")

# AI 관련 종목 (카테고리별 분류)
AI_STOCKS = {
    "🔧 AI 반도체": {
        "NVIDIA (엔비디아)": "NVDA",
        "AMD": "AMD",
        "Broadcom (브로드컴)": "AVGO",
        "TSMC (대만 반도체)": "TSM",
        "ASML": "ASML",
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
    },
    "☁️ 빅테크 / 클라우드": {
        "Microsoft (마이크로소프트)": "MSFT",
        "Google (구글)": "GOOGL",
        "Amazon (아마존)": "AMZN",
        "Meta (메타)": "META",
        "Apple (애플)": "AAPL",
    },
    "💡 AI 소프트웨어 / 플랫폼": {
        "Palantir (팔란티어)": "PLTR",
        "Tesla (테슬라)": "TSLA",
        "Adobe (어도비)": "ADBE",
        "Salesforce (세일즈포스)": "CRM",
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
    },
}

# 카테고리와 종목을 하나의 딕셔너리로 합치기 (이름: 티커)
ALL_STOCKS = {}
for category, stocks in AI_STOCKS.items():
    ALL_STOCKS.update(stocks)

# 사이드바 설정
st.sidebar.header("⚙️ 설정")

# 카테고리 선택
st.sidebar.subheader("📂 카테고리별 빠른 선택")
selected_categories = st.sidebar.multiselect(
    "관심 분야를 선택하면 종목이 자동 추가됩니다",
    options=list(AI_STOCKS.keys()),
    default=["🔧 AI 반도체"]
)

# 카테고리에서 선택된 종목들을 기본값으로
default_stocks = []
for cat in selected_categories:
    default_stocks.extend(list(AI_STOCKS[cat].keys()))

# 종목 직접 선택 (다중 선택)
st.sidebar.subheader("🎯 종목 직접 선택")
selected_names = st.sidebar.multiselect(
    "비교할 종목을 선택/추가하세요",
    options=list(ALL_STOCKS.keys()),
    default=default_stocks
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


# 데이터 불러오기 함수 (캐시 적용)
@st.cache_data(ttl=3600)  # 1시간 동안 캐시 유지
def load_stock_data(ticker, period):
    """yfinance로 주식 데이터를 불러오는 함수"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        return df
    except Exception:
        return None


# 메인 로직
if not selected_names:
    st.warning("⚠️ 왼쪽 사이드바에서 비교할 종목을 하나 이상 선택해주세요!")
else:
    # 선택한 종목들의 데이터 저장
    stock_data = {}
    failed_stocks = []

    with st.spinner("📡 AI 주식 데이터를 불러오는 중..."):
        for name in selected_names:
            ticker = ALL_STOCKS[name]
            df = load_stock_data(ticker, selected_period)
            if df is not None and not df.empty:
                stock_data[name] = df
            else:
                failed_stocks.append(name)

    if failed_stocks:
        st.error(f"❌ 다음 종목의 데이터를 불러오지 못했습니다: {', '.join(failed_stocks)}")

    if stock_data:
        # ===== 핵심 지표 카드 (상위 요약) =====
        st.subheader("⭐ 핵심 요약")

        # 수익률 계산해서 정렬용 리스트 생성
        return_summary = []
        for name, df in stock_data.items():
            ret = (df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100
            return_summary.append((name, ret))

        # 최고/최저 수익률 종목 찾기
        best = max(return_summary, key=lambda x: x[1])
        worst = min(return_summary, key=lambda x: x[1])
        avg_return = sum(r for _, r in return_summary) / len(return_summary)

        col1, col2, col3 = st.columns(3)
        col1.metric("📈 최고 수익률", best[0], f"{best[1]:+.2f}%")
        col2.metric("📉 최저 수익률", worst[0], f"{worst[1]:+.2f}%")
        col3.metric("📊 평균 수익률", f"{len(stock_data)}개 종목", f"{avg_return:+.2f}%")

        # ===== 1. 수익률 비교 (정규화된 차트) =====
        st.subheader(f"📊 누적 수익률 비교 ({selected_period_label})")
        st.caption("기간 시작일을 0%로 맞춰 각 종목의 상대적 수익률을 비교합니다.")

        fig_return = go.Figure()

        for name, df in stock_data.items():
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
        fig_return.add_hline(y=0, line_dash="dash", line_color="gray")

        st.plotly_chart(fig_return, use_container_width=True)

        # ===== 2. 수익률 막대 그래프 (순위 비교) =====
        st.subheader("🏆 수익률 순위")

        # 수익률 기준 내림차순 정렬
        sorted_returns = sorted(return_summary, key=lambda x: x[1], reverse=True)
        names_sorted = [x[0] for x in sorted_returns]
        returns_sorted = [x[1] for x in sorted_returns]

        # 양수는 빨강, 음수는 파랑
        bar_colors = ["crimson" if r > 0 else "royalblue" for r in returns_sorted]

        fig_bar = go.Figure(go.Bar(
            x=returns_sorted,
            y=names_sorted,
            orientation="h",
            marker_color=bar_colors,
            text=[f"{r:+.2f}%" for r in returns_sorted],
            textposition="auto"
        ))
        fig_bar.update_layout(
            xaxis_title="수익률 (%)",
            template="plotly_white",
            height=max(300, len(names_sorted) * 40),
            yaxis=dict(autorange="reversed")  # 1등이 위로 오도록
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ===== 3. 수익률 요약 표 =====
        st.subheader("📋 상세 데이터")

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

        # ===== 4. 개별 종목 캔들스틱 차트 =====
        st.subheader("🕯️ 개별 종목 상세 차트")

        chart_name = st.selectbox(
            "캔들스틱 차트로 볼 종목을 선택하세요",
            options=list(stock_data.keys())
        )

        df_selected = stock_data[chart_name]

        # 이동평균선 계산 (5일, 20일)
        df_selected = df_selected.copy()
        df_selected["MA5"] = df_selected["Close"].rolling(window=5).mean()
        df_selected["MA20"] = df_selected["Close"].rolling(window=20).mean()

        fig_candle = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
            subplot_titles=("주가 (캔들스틱 + 이동평균선)", "거래량")
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
                increasing_line_color="red",
                decreasing_line_color="blue"
            ),
            row=1, col=1
        )

        # 5일 이동평균선
        fig_candle.add_trace(
            go.Scatter(
                x=df_selected.index, y=df_selected["MA5"],
                name="5일 평균", line=dict(color="orange", width=1.5)
            ),
            row=1, col=1
        )
        # 20일 이동평균선
        fig_candle.add_trace(
            go.Scatter(
                x=df_selected.index, y=df_selected["MA20"],
                name="20일 평균", line=dict(color="purple", width=1.5)
            ),
            row=1, col=1
        )

        # 거래량
        fig_candle.add_trace(
            go.Bar(
                x=df_selected.index,
                y=df_selected["Volume"],
                name="거래량",
                
