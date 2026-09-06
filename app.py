import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime

st.set_page_config(page_title="独自予想アプリ", layout="centered")
st.title("🚤 独自スコア予測 (リアルタイム)")

# 負荷対策：取得したデータを300秒（5分）記憶する
@st.cache_data(ttl=300)
def get_real_data(jcd, rno):
    # 今日の日付を自動取得
    today = datetime.date.today().strftime('%Y%m%d')
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={today}"
    
    try:
        response = requests.get(url, timeout=5)
        response.encoding = 'utf-8'
        
        # 自己テスト1: 正常に通信できたか
        if response.status_code != 200:
            return None, "公式サイトにアクセスできませんでした。"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table_rows = soup.select('.is-tableFixed__3rdadd tbody')
        
        # 自己テスト2: 展示データがすでに公開されているか
        if not table_rows or len(table_rows) < 6:
            return None, "まだ展示データが公開されていないか、対象のレースがありません。"

        boats = []
        for i in range(6):
            row = table_rows[i].find_all('tr')[0]
            cols = row.find_all('td')
            if len(cols) > 6:
                ex_time = cols[6].text.strip()
                tilt = cols[5].text.strip()
                
                # 自己テスト3: タイムが数字として取得できているか（欠場対策）
                if ex_time.replace('.','').isdigit():
                    time_val = float(ex_time)
                    # 簡易スコア計算（タイムが早いほど高得点になる仮の計算式）
                    score = int(100 - (time_val - 6.50) * 100)
                else:
                    score = 0
                    
                boats.append({
                    "枠": i + 1,
                    "スコア": score,
                    "展示": ex_time,
                    "チルト": tilt
                })
        return boats, None
        
    except Exception as e:
        return None, f"データ取得エラー: {e}"

# 画面の表示レイアウト
rno = st.selectbox("大村の対象レース（本日のレース）", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

if st.button("最新データで予想する"):
    with st.spinner("公式サイトから直前情報を取得中..."):
        # 大村(24)の指定レースを取得
        real_data, error_msg = get_real_data("24", rno)
        
        if error_msg:
            st.error(error_msg)
        else:
            df = pd.DataFrame(real_data)
            df_sorted = df.sort_values(by="スコア", ascending=False)
            
            st.success("最新データの取得とスコア計算が完了しました！")
            st.write("▼ 直前気配＆独自スコア")
            st.dataframe(df_sorted[["枠", "スコア", "展示", "チルト"]], hide_index=True, use_container_width=True)
            
            # 波乱アラート（チルトを0.5以上跳ねている艇がいれば警告）
            if any(float(t) >= 0.5 for t in df["チルト"] if t.replace('.','').replace('-','').isdigit()):
                 st.error("⚠️ 【波乱アラート】チルトを+0.5以上跳ねている艇がいます！一発まくり警戒！")
