import pandas as pd
from utils.statistics import main

def get_data(ticker='VOO'):
    tickers=[ticker]
    decisions={}

    data=[]
    for ticker in tickers:
        d, di=main(ticker)
        data.append(d)
        decisions[ticker]=di
    data=pd.concat(data)
    return data, decisions