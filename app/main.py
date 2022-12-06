import os
import pickle
import numpy as np
import pandas as pd
from pytz import timezone
from datetime import datetime, timedelta
from pandas_datareader import data as web
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import zscore

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import base64
import json

def main(ticker):
    data=web.DataReader(
        ticker,'yahoo',start='2022-06-01'
    )

    def get_adx(df, rate=20):
        high,low,close=(df['High'],df['Low'],df['Close'])
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0

        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis = 1, join = 'inner').max(axis = 1)
        atr = tr.rolling(rate).mean()

        plus_di = 100 * (plus_dm.ewm(alpha = 1/rate).mean() / atr)
        minus_di = abs(100 * (minus_dm.ewm(alpha = 1/rate).mean() / atr))
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        adx = ((dx.shift(1) * (rate - 1)) + dx) / rate
        adx_smooth = adx.ewm(alpha = 1/rate).mean()

        df['plus_di']=plus_di
        df['minus_di']=minus_di
        df['adx']=adx_smooth
        return df

    def get_sma(df, rate=20):
        df[f'sma_{rate}']=df['Close'].rolling(rate).mean()
        return df

    def get_bollinger_bands(df, rate=20):
        df = get_sma(df, rate) # <-- Get SMA for 20 days
        std = df['Close'].rolling(rate).std() # <-- Get rolling standard deviation for 20 days
        df['bollinger_up'] = df[f'sma_{rate}'] + std * 2 # Calculate top band
        df['bollinger_down'] = df[f'sma_{rate}'] - std * 2 # Calculate bottom band
        return df
    
    def getMFI(data):
        data['typical_price']=(data['High']+data['Low']+data['Close'])/3
        data['money_flow']=data['typical_price']*data['Volume']
        data['money_flow_sgn']=np.sign((data['money_flow']-data['money_flow'].shift(1)))
        data['money_flow_sgn']=data['money_flow_sgn']*data['money_flow']
        data['money_flow_gain']=data['money_flow_sgn'].rolling(14).apply(lambda x:((x>0)*x).sum(),raw=True)
        data['money_flow_loss']=data['money_flow_sgn'].rolling(14).apply(lambda x:((x<0)*x).sum(),raw=True)
        data['money_flow_index']=(100 - (100 / (1 + (data['money_flow_gain'] / abs(data['money_flow_loss'])))))
        return data
    
    def getDecision(data):
        info_row=data.iloc[-1]
        di=info_row['plus_di']>info_row['minus_di']
        ndi=info_row['plus_di']<info_row['minus_di']
        adx=info_row['adx']>20
        
        decision='undertermined'
        if di and adx and (info_row['money_flow_index']<50):
            decision='long'
        elif di and adx and (info_row['money_flow_index']<20):
            decision='buy now'
        elif ndi and adx and (info_row['money_flow_index']>50):
            decision='short'
        elif ndi and adx and (info_row['money_flow_index']>80):
            decision='sell all'
        return decision

    data=get_adx(data)
    data=get_bollinger_bands(data)
    data=getMFI(data)
    data.dropna(inplace=True)
    data['ticker']=ticker
    data.reset_index(inplace=True)
    decision=getDecision(data)
    return (data, decision)

tickers=[
    'VOO',
    'QQQ',
    'AAPL',
    'MSFT',
    'TSLA',
]
decisions={}

data=[]
for ticker in tickers:
    d, di=main(ticker)
    data.append(d)
    decisions[ticker]=di
data=pd.concat(data)


app=dash.Dash()

app_layout=[]
app_layout.append(
    html.Div(
        html.H2(
            id='title',
            style={'paddingTop':20,'padding-left':20}
        )
    )
)
app_layout.append(
    html.Div(
        html.H3(
            id='subtitle',
        ),style={'padding-left':20}
    )
)
app_layout.append(
    html.Div(
        dcc.Dropdown(id='ticker',options=[
            {'label':tick,'value':tick} for tick in tickers
        ],value='VOO'),
        style={'width':'10%','padding-left':'1000px'}
    )
)
app_layout.append(
    html.Div([
        html.Div(
            dcc.Graph(id='bollinger'),
            style={'width':'30%','padding-left':20,'display':'inline-block'}
        ),
        html.Div(
            dcc.Graph(id='adx'),
            style={'width':'30%','padding-left':5,'display':'inline-block'}
        )
    ])
)
app_layout.append(html.Div())
app_layout.append(
    html.Div([
        html.Div(
            dcc.Graph(id='mfi'),
            style={'width':'30%','padding-left':20,'display':'inline-block'}
        ),
        html.Div(
            dcc.Graph(id='flow'),
            style={'width':'30%','padding-left':5,'display':'inline-block'}
        )
    ])
)

app.layout=html.Div(
    app_layout
)


# callback functions:
@app.callback(
    Output('title','children'),
    [Input('ticker','value')]
)
def getTitle(value):
    return f'Technical Analysis for {value}'

@app.callback(
    Output('subtitle','children'),
    [Input('ticker','value')]
)
def getSubtitle(value):
    return f'suggestion: {decisions[value]}'

@app.callback(
    Output('bollinger','figure'),
    [Input('ticker','value')]
)
def getBollingerBand(value):
    subset=data[data.ticker==value]
    traces=[
        go.Scatter(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['Close'].values,
            name='Close',
            hovertemplate="%{x:%Y}@%{y:$,.2f}"
        ),
        go.Scatter(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['sma_20'].values,
            name='smoothing 20',
            line={'color':'red'},
            hovertemplate="%{x:%Y}@%{y:$,.2f}"
        ),
        go.Scatter(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['bollinger_down'].values,
            line = dict(color='orange'),
            name='Bollinger Lower',
            hovertemplate="%{x:%Y}@%{y:$,.2f}"
        ),
        go.Scatter(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['bollinger_up'].values,
            fill='tonexty',
            line = dict(color='orange'),
            name='Bollinger Upper',
            hovertemplate="%{x:%Y}@%{y:$,.2f}"
        ),
    ]
    
    return {'data':traces,'layout':go.Layout(
        title='Bollinger Band',
        xaxis={
            'title':'date',
        },
        yaxis={'title':'value'},
        hovermode="x unified"
    )}


@app.callback(
    Output('adx','figure'),
    [Input('ticker','value')]
)
def getADX(value):
    subset=data[data.ticker==value]
    traces=[
        go.Scatter(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['plus_di'].values,
            name='+dm',
            hovertemplate="%{x:%Y}@%{y:$,.2f}"
        ),
        go.Scatter(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['minus_di'].values,
            name='-dm',
            hovertemplate="%{x:%Y}@%{y:$,.2f}"
        ),
        go.Scatter(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['adx'].values,
            name='adx',
            hovertemplate="%{x:%Y}@%{y:$,.2f}"
        ),
    ]
    
    return {'data':traces,'layout':go.Layout(
        title='ADX',
        xaxis={
            'title':'date',
        },
        yaxis={'title':'value'},
        hovermode="x unified",
    )}

@app.callback(
    Output('mfi','figure'),
    [Input('ticker','value')]
)
def getMFI(value):
    subset=data[data.ticker==value]
    traces=[
        go.Scatter(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['money_flow_index'].values,
            name='MFI',
            hovertemplate="%{x:%Y}@%{y:$,.2f}",
            marker_color='lightgreen'
        ),
    ]
    
    return {'data':traces,'layout':go.Layout(
        title='MFI',
        xaxis={
            'title':'date',
        },
        yaxis={'title':'value'},
        hovermode="x unified",
    )}

@app.callback(
    Output('flow','figure'),
    [Input('ticker','value')]
)
def getFlow(value):
    subset=data[data.ticker==value]
    traces=[
        go.Bar(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['money_flow_gain'].values,
            name='Gain Volume',
            hovertemplate="%{x:%Y}@%{y:$,.2f}",
            marker_color='limegreen'
        ),
        go.Bar(
            x=pd.to_datetime(subset['Date'].values),
            y=subset['money_flow_loss'].values,
            name='Loss Volume',
            hovertemplate="%{x:%Y}@%{y:$,.2f}",
            marker_color='lightsalmon'
        ),
    ]
    
    return {'data':traces,'layout':go.Layout(
        title='Money Flow Volume',
        xaxis={
            'title':'date',
        },
        yaxis={'title':'value'},
        hovermode="x unified",
    )}


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=True)