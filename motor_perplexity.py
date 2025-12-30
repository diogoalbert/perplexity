import pandas as pd
import re
import os

def clean_val(val_str):
    if pd.isna(val_str): return 0.0
    if isinstance(val_str, (float, int)): return float(val_str)
    s = re.sub(r'[^0-9,\.-]', '', str(val_str))
    if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

def processar_portugal_desmembrado():
    bt_input = 'Relatorio_FIFO_Completo_Contraparte.csv'
    binance_input = 'Binance_Novembro2019-Dezembro2025.csv'
    output_name = 'Relatorio_IRS_Portugal_Lotes_Desmembrados_v2.csv'
    
    inventory = {'BitcoinTrade': {}, 'Binance': {}}
    
    # 1. CARREGAR BITCOINTRADE (Herança)
    df_bt = pd.read_csv(bt_input, sep=';', decimal=',')
    
    for _, row in df_bt.iterrows():
        if row['operação'] in ['Compra', 'Entrada por Transferência', 'Deposit']:
            m = row['Moeda']
            if m not in inventory['BitcoinTrade']: 
                inventory['BitcoinTrade'][m] = []
            inventory['BitcoinTrade'][m].append({
                'qty': abs(float(row['quantidade'])),
                'cost': float(row['Valor (Custo FIFO)']),
                'date': row['Data']
            })
    
    # 2. PROCESSAR BINANCE
    df_bin = pd.read_csv(binance_input)
    df_bin['UTC_Time'] = pd.to_datetime(df_bin['UTC_Time'])
    df_bin['Val_Numeric'] = df_bin['Change'].apply(clean_val)
    df_bin = df_bin.sort_values('UTC_Time')
    
    final_report = []
    
    FIAT_ESTATAL = ['EUR', 'BRL', 'USD']
    STABLECOINS = ['USDT', 'USDC', 'BUSD', 'DAI', 'USDD']
    
    for ts, group in df_bin.groupby('UTC_Time'):
        data_venda = ts.strftime('%Y-%m-%d')
        hora_venda = ts.strftime('%H:%M:%S')
        
        saidas = group[group['Val_Numeric'] < 0]
        entradas = group[group['Val_Numeric'] > 0]
        
        # A) DEPÓSITOS
        for _, ent in entradas.iterrows():
            if e
