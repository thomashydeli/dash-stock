import os
import pickle
import numpy as np
import pandas as pd
from pytz import timezone
from datetime import datetime, timedelta
from plotly import graph_objects as go
from plotly.subplots import make_subplots

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import base64
import json

from utils.data import get_data

import threading

data_lock=threading.Lock()
data, decisions=get_data()
data_store={'data': data, 'decisions': decisions}
def fetch_and_store_data(ticker):
    data, decisions = get_data(ticker)
    return data, decisions


app=dash.Dash()
app_layout=[]
app_layout.append(
    html.Link(rel='stylesheet', href='/assets/style.css')
)
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
app_layout.append(dcc.Store(id='data-store'))
app_layout.append(
    html.Div(
        dcc.Input(id='ticker', type='text', value='VOO', placeholder="Enter a stock ticker:"),
        style={'width': '20%', 'padding-left': '40px'}
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

app.layout = html.Div(
    app_layout,
    style={'backgroundColor': '#f5f5f5'}
)


# callback functions:
# @app.callback(
#     Output('data-store', 'data'),
#     [Input('ticker', 'value')]
# )
# def update_global_data(ticker):
#     with data_lock:
#         fetch_and_store_data(ticker)
#     data_store={'data': data, 'decisions': decisions}
#     print(data_store)
#     return data_store


@app.callback(
    Output('data-store', 'data'),
    [Input('ticker', 'value')]
)
def update_global_data(ticker):
    with data_lock:
        global data, decisions, data_store
        data, decisions = fetch_and_store_data(ticker)
        data_store = {'data': data, 'decisions': decisions}
    return data_store

@app.callback(
    Output('title','children'),
    [Input('ticker','value')]
)
def getTitle(value):
    title=f'Technical Analysis for {value}'
    return title


@app.callback(
    Output('subtitle', 'children'),
    [Input('ticker', 'value')]  # Added the data-store input here
)
def getSubtitle(value):  # Added store_data parameter here
    with data_lock:
        print(data_store)
        decisions = data_store['decisions']
        decision = f'suggestion: {decisions[value]}'
    return decision

@app.callback(
    Output('bollinger','figure'),
    [Input('ticker','value')]
)
def getBollingerBand(value):
    with data_lock:
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
    with data_lock:
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
    with data_lock:
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
    with data_lock:
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
    app.run_server(host='0.0.0.0', port=8050, debug=False)