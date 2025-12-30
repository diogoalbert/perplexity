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

def processar_portugal_persistente():
    binance_input = 'Binance_Novembro2019-Dezembro2025.csv'
    bt_input = 'Relatorio_FIFO_Completo_Contraparte.csv'
    output_name = 'RELATORIO_FINAL_IRS_2018_2025.csv'

    # 1. Carregar e Limpar Dados
    df = pd.read_csv(binance_input)
    df['UTC_Time'] = pd.to_datetime(df['UTC_Time'])
    df['Val_Numeric'] = df['Change'].apply(clean_val)
    # Tolerância de 5 segundos para agrupar operações que a Binance separa
    df['Time_Group'] = df['UTC_Time'].dt.round('5s') 
    df = df.sort_values('UTC_Time')

    inventory = {}
    final_report = []
    FIAT_ESTATAL = ['EUR', 'BRL', 'USD']

    # --- INVENTÁRIO INICIAL (BT) ---
    if os.path.exists(bt_input):
        df_bt = pd.read_csv(bt_input, sep=';', decimal=',')
        for _, row in df_bt.iterrows():
            m = row['Moeda']
            if m not in inventory: inventory[m] = []
            inventory[m].append({'qty': abs(float(row['quantidade'])), 'cost': float(row['Valor (Custo FIFO)']), 'date': row['Data']})

    # --- PROCESSAMENTO ---
    print("Processando todas as transações até 2025...")

    for tg, group in df.groupby('Time_Group'):
        data_venda = tg.strftime('%Y-%m-%d')
        entradas = group[group['Val_Numeric'] > 0]
        saidas = group[group['Val_Numeric'] < 0]

        # 1. ENTRADAS (Alimentar Inventário)
        for _, ent in entradas.iterrows():
            m = ent['Coin']
            if m in FIAT_ESTATAL: continue
            if m not in inventory: inventory[m] = []
            
            # Custo zero por padrão (será atualizado se for Swap abaixo)
            inventory[m].append({'qty': ent['Val_Numeric'], 'cost': 0.0, 'date': data_venda})

        # 2. SAÍDAS (Vendas ou Swaps)
        for _, s in saidas.iterrows():
            if 'Fee' in s['Operation']: continue
            moeda_sai = s['Coin']
            qtd_sai = abs(s['Val_Numeric'])
            
            # Identificar se houve entrada de moeda fiduciária (Venda para Fiat)
            fiat_entry = entradas[entradas['Coin'].isin(FIAT_ESTATAL)]
            
            if not fiat_entry.empty:
                valor_fiat_total = abs(fiat_entry['Val_Numeric'].sum())
                
                # FORÇAR LOTE: Se não houver no inventário, cria um para não ignorar a venda
                if moeda_sai not in inventory or not inventory[moeda_sai]:
                    inventory[moeda_sai] = [{'qty': 1000000.0, 'cost': 0.0, 'date': 'DATA_NAO_RASTREADA'}]

                qtd_restante = qtd_sai
                while qtd_restante > 1e-10 and inventory[moeda_sai]:
                    lote = inventory[moeda_sai][0]
                    vender = min(lote['qty'], qtd_restante)
                    
                    prop = vender / qtd_sai
                    custo_lote = (lote['cost'] / lote['qty']) * vender if lote['qty'] > 0 else 0
                    
                    final_report.append({
                        'Data_Venda': data_venda,
                        'Moeda': moeda_sai,
                        'Quantidade': round(vender, 8),
                        'Data_Aquisição': lote['date'],
                        'Custo_Aquisição': round(custo_lote, 2),
                        'Valor_Venda': round(valor_fiat_total * prop, 2),
                        'Status': 'OK' if lote['date'] != 'DATA_NAO_RASTREADA' else 'VERIFICAR_ORIGEM'
                    })
                    
                    if lote['qty'] <= qtd_restante:
                        qtd_restante -= lote['qty']
                        inventory[moeda_sai].pop(0)
                    else:
                        lote['qty'] -= vender
                        lote['cost'] -= custo_lote
                        qtd_restante = 0
            else:
                # SWAP: Herança de Custo para manter a linha do tempo viva
                if moeda_sai in inventory and inventory[moeda_sai]:
                    lote_velho = inventory[moeda_sai].pop(0)
                    for _, e in entradas.iterrows():
                        m_ent = e['Coin']
                        if m_ent not in inventory: inventory[m_ent] = []
                        inventory[m_ent].append({'qty': e['Val_Numeric'], 'cost': lote_velho['cost'], 'date': lote_velho['date']})

    pd.DataFrame(final_report).to_csv(output_name, sep=';', index=False, decimal=',')
    print(f"Relatório final gerado com {len(final_report)} linhas.")

if __name__ == "__main__":
    processar_portugal_persistente()