import numpy as np
import pandas as pd
from pandas_datareader import data as web
import yfinance as yfin


def main(ticker):

    try:
        yfin.pdr_override()
        data=web.DataReader(
            ticker,start='2022-01-01'
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
    except Exception as e:
        return None, e