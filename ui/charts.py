# charts.py module
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def create_price_volume_chart(df: pd.DataFrame, ticker: str, plot_type: str = 'Candle') -> go.Figure:
    """Tạo biểu đồ Giá và Khối lượng với trục Y kép."""
    # Tạo khung biểu đồ với 2 trục Y (giá ở trên, khối lượng ở dưới)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Lớp biểu đồ Giá
    if plot_type == 'Candle':
        fig.add_trace(
            go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='Price'
            ),
            secondary_y=False
        )
    else:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color='blue')),
            secondary_y=False
        )

    # Lớp biểu đồ Khối lượng (Volume)
    fig.add_trace(
        go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='rgba(158,202,225,0.5)'),
        secondary_y=True
    )

    # Tùy chỉnh Layout (Responsive & UX)
    fig.update_layout(
        title=f"Biểu đồ kỹ thuật - {ticker}",
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=40, b=20),
        height=500,
        hovermode="x unified"
    )
    
    # Cố định tỷ lệ trục Y của Volume để nó chỉ chiếm 30% chiều cao phía dưới
    max_vol = df['Volume'].max()
    fig.update_yaxes(range=[0, max_vol * 3], showticklabels=False, secondary_y=True)
    
    return fig