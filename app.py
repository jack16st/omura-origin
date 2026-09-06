import streamlit as st
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
import datetime

st.set_page_config(page_title="独自予想アプリ", layout="centered")
st.title("🚤 独自スコア予測 (リアルタイム)")

TRACKS = {
    "01": "桐生", "02": "戸田", "03": "江戸川", "04": "平和島", "05": "多摩川", "06": "浜名湖",
    "07": "蒲郡", "08": "常滑", "09": "津", "10": "三国", "11": "びわこ", "12": "住之江",
    "13": "尼崎", "14": "鳴門", "15": "丸亀", "16": "児島", "17": "宮島", "18": "徳山",
    "19": "下関", "20": "若松", "21": "芦屋", "22": "福岡", "23": "唐津", "24": "大村"
}

@st.cache_data(ttl=300)
def get_real_data(jcd, rno):
    today = datetime.date.today().strftime('%Y%m%d')
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={today}"
    
    try:
        # Chrome完全偽装通信
        response = requests.get(url, impersonate="chrome110", timeout=15)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 判明した正しいテーブル名「is-w748」を狙い撃ち
        table = soup.select_one('table.is-w748')
        
        if not table:
            return None, "まだ展示データが公開されていないか、対象のレースがありません。"

        boats = []
        tbodies = table.find_all('tbody')
        
        for tbody in tbodies:
            rows = tbody.find_all('tr')
            if not rows: continue
            
            cols = rows[0].find_all('td')
            
            if len(cols) > 6:
                waku_text = "".join(filter(str.isdigit, cols[0].text.strip()))
                
                if waku_text in ["1", "2", "3", "4", "5", "6"]:
                    waku = int(waku_text)
                    # 列番号を修正：展示タイムは4番目、チルトは5番目
                    ex_time = cols[4].text.strip()
                    tilt = cols[5].text.strip()
                    
                    if ex_time.replace('.','').isdigit():
                        time_val = float(ex_time)
                        # 仮の計算：タイムが早い（6.50に近い）ほど高得点になるロジック
                        score = int(100 - (time_val - 6.50) * 100)
                    else:
                        score = 0
                        
                    boats.append({"枠": waku, "スコア": score, "展示": ex_time, "チルト": tilt})
                    
        if not boats:
             return None, "テーブルは発見しましたが、タイムデータを抽出できませんでした。"
             
        return boats, None
        
    except Exception as e:
        return None, f"データ取得エラー: {e}"

col1, col2 = st.columns(2)
with col1:
    selected_track_name = st.selectbox("対象のレース場", list(TRACKS.values()))
    selected_jcd = [k for k, v in TRACKS.items() if v == selected_track_name][0]
    
with col2:
    rno = st.selectbox("レース番号", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

if st.button("最新データで予想する"):
    with st.spinner(f"{selected_track_name} {rno}Rの直前情報を取得中..."):
        real_data, error_msg = get_real_data(selected_jcd, rno)
        
        if error_msg:
            st.error(error_msg)
        else:
            df = pd.DataFrame(real_data)
            df_sorted = df.sort_values(by="スコア", ascending=False)
            
            st.success("最新データの取得とスコア計算が完了しました！")
            st.write("▼ 直前気配＆独自スコア")
            st.dataframe(df_sorted[["枠", "スコア", "展示", "チルト"]], hide_index=True, use_container_width=True)
            
            if any(float(t) >= 0.5 for t in df["チルト"] if t.replace('.','').replace('-','').isdigit()):
                 st.error("⚠️ 【波乱アラート】チルトを+0.5以上跳ねている艇がいます！一発まくり警戒！")
