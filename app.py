import streamlit as st
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
import datetime
import re

st.set_page_config(page_title="独自予想アプリ", layout="centered")
st.title("🚤 総合スコア予測 (AIフォーメーション)")

TRACKS = {
    "01": "桐生", "02": "戸田", "03": "江戸川", "04": "平和島", "05": "多摩川", "06": "浜名湖",
    "07": "蒲郡", "08": "常滑", "09": "津", "10": "三国", "11": "びわこ", "12": "住之江",
    "13": "尼崎", "14": "鳴門", "15": "丸亀", "16": "児島", "17": "宮島", "18": "徳山",
    "19": "下関", "20": "若松", "21": "芦屋", "22": "福岡", "23": "唐津", "24": "大村"
}

@st.cache_data(ttl=300)
def get_real_data(jcd, rno):
    today = datetime.date.today().strftime('%Y%m%d')
    url_before = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={today}"
    url_race = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={today}"
    
    win_rates = {}
    motor_rates = {}
    
    try:
        res_rl = requests.get(url_race, impersonate="chrome110", timeout=15)
        res_rl.encoding = 'utf-8'
        soup_rl = BeautifulSoup(res_rl.text, 'html.parser')
        
        for tbody in soup_rl.find_all('tbody'):
            for waku in range(1, 7):
                if tbody.find('td', class_=f'is-boatColor{waku}'):
                    floats = [float(x) for x in re.findall(r'\d+\.\d+', tbody.text)]
                    if len(floats) >= 5:
                        win_rates[waku] = floats[0]
                        motor_cands = [f for f in floats if 10.0 <= f <= 100.0]
                        motor_rates[waku] = motor_cands[2] if len(motor_cands) > 2 else (motor_cands[-1] if motor_cands else 30.0)
    except Exception:
        pass
        
    try:
        response = requests.get(url_before, impersonate="chrome110", timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.select_one('table.is-w748')
        if not table:
            # 完全にページや表がない場合はエラーとして止める
            return None, "⚠️ 該当レースのページが見つかりません。"

        boats = []
        for tbody in table.find_all('tbody'):
            rows = tbody.find_all('tr')
            if not rows: continue
            
            cols = rows[0].find_all('td')
            if len(cols) > 6:
                waku_text = "".join(filter(str.isdigit, cols[0].text.strip()))
                
                if waku_text in ["1", "2", "3", "4", "5", "6"]:
                    waku = int(waku_text)
                    ex_time = cols[4].text.strip()
                    tilt = cols[5].text.strip()
                    
                    if ex_time.replace('.','').isdigit():
                        time_val = float(ex_time)
                        ex_score = 100 - (time_val - 6.50) * 100
                    else:
                        ex_score = 0
                        
                    w_rate = win_rates.get(waku, 5.0)
                    m_rate = motor_rates.get(waku, 30.0)
                    
                    total_score = int((ex_score * 0.5) + ((w_rate * 10) * 0.3) + (m_rate * 0.2))
                        
                    boats.append({
                        "枠": waku,
                        "総合スコア": total_score,
                        "勝率": w_rate,
                        "モーター": f"{m_rate}%",
                        "展示": ex_time,
                        "チルト": tilt
                    })
                    
        if not boats:
             return None, "⚠️ データ枠が取得できませんでした。"
             
        # 【変更点】展示タイムがない場合でもデータ自体は返しつつ、警告メッセージを添える
        warning_msg = None
        valid_times = [b for b in boats if b["展示"] != ""]
        if len(valid_times) == 0:
             warning_msg = "⚠️ 直前情報（展示・チルト）が未公開です。現在は「勝率」と「モーター」のみで仮計算しています。"
             
        return boats, warning_msg
        
    except Exception as e:
        return None, f"データ取得エラー: {e}"

def color_waku(val):
    colors = {
        1: 'background-color: #FFFFFF; color: #000000; border: 1px solid #CCC; font-weight: bold;',
        2: 'background-color: #000000; color: #FFFFFF; font-weight: bold;',
        3: 'background-color: #FF0000; color: #FFFFFF; font-weight: bold;',
        4: 'background-color: #0000FF; color: #FFFFFF; font-weight: bold;',
        5: 'background-color: #FFFF00; color: #000000; font-weight: bold;',
        6: 'background-color: #008000; color: #FFFFFF; font-weight: bold;'
    }
    return colors.get(val, '')

col1, col2 = st.columns(2)
with col1:
    selected_track_name = st.selectbox("対象のレース場", list(TRACKS.values()))
    selected_jcd = [k for k, v in TRACKS.items() if v == selected_track_name][0]
    
with col2:
    rno = st.selectbox("レース番号", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

if st.button("総合データで予想する"):
    with st.spinner(f"{selected_track_name} {rno}Rの全データを取得・解析中..."):
        real_data, warning_msg = get_real_data(selected_jcd, rno)
        
        # real_dataがNone（完全なエラー）の場合は処理を停止
        if real_data is None:
            st.error(warning_msg)
        else:
            # 警告メッセージがあれば黄色で表示、なければ成功メッセージを表示
            if warning_msg:
                st.warning(warning_msg)
            else:
                st.success("最新データの取得と総合スコア計算が完了しました！")
            
            df = pd.DataFrame(real_data)
            df_sorted = df.sort_values(by="総合スコア", ascending=False)
            
            if len(df_sorted) >= 4:
                t1, t2, t3, t4 = df_sorted.iloc[0:4]['枠'].tolist()
                st.markdown("### 🎯 おすすめフォーメーション (3連単)")
                st.info(f"**【本線】 {t1} - {t2}.{t3}.{t4} - {t2}.{t3}.{t4}** (計6点)")
            
            today_disp = datetime.date.today().strftime('%Y年%m月%d日')
            st.write(f"▼ **{today_disp} {selected_track_name} {rno}R** 直前気配＆総合データ")
            
            if hasattr(df_sorted.style, 'hide'):
                styled_df = df_sorted.style.hide(axis='index').map(color_waku, subset=['枠'])
            else:
                styled_df = df_sorted.style.hide_index().applymap(color_waku, subset=['枠'])
                
            st.table(styled_df)
            
            if any(float(t) >= 0.5 for t in df["チルト"] if str(t).replace('.','').replace('-','').isdigit()):
                 st.error("⚠️ 【波乱アラート】チルトを+0.5以上跳ねている艇がいます！一発まくり警戒！")
