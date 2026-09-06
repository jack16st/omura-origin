import streamlit as st
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
import traceback
import datetime

st.set_page_config(page_title="完全デバッグモード", layout="wide")
st.title("🛠️ 完全デバッグモード (通信偽装版)")

st.write("独自のメッセージを一切排除し、サーバーの応答をそのまま出力します。")

TRACKS = {
    "01": "桐生", "02": "戸田", "03": "江戸川", "04": "平和島", "05": "多摩川", "06": "浜名湖",
    "07": "蒲郡", "08": "常滑", "09": "津", "10": "三国", "11": "びわこ", "12": "住之江",
    "13": "尼崎", "14": "鳴門", "15": "丸亀", "16": "児島", "17": "宮島", "18": "徳山",
    "19": "下関", "20": "若松", "21": "芦屋", "22": "福岡", "23": "唐津", "24": "大村"
}

col1, col2 = st.columns(2)
with col1:
    selected_track_name = st.selectbox("対象のレース場", list(TRACKS.values()))
    selected_jcd = [k for k, v in TRACKS.items() if v == selected_track_name][0]
with col2:
    rno = st.selectbox("レース番号", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

if st.button("生データを完全に解析する"):
    today = datetime.date.today().strftime('%Y%m%d')
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={selected_jcd}&hd={today}"
    
    st.info(f"リクエストURL:\n{url}")
    
    try:
        # Chromeの通信を完全に偽装してアクセス
        response = requests.get(url, impersonate="chrome110", timeout=15)
        response.encoding = 'utf-8'
        
        st.write(f"**HTTPステータスコード:** {response.status_code}")
        
        with st.expander("取得したHTMLの中身 (最初の2000文字)", expanded=True):
            if len(response.text) == 0:
                st.warning("HTMLが0文字です。")
            else:
                st.text(response.text[:2000])

        soup = BeautifulSoup(response.text, 'html.parser')
        table_rows = soup.select('.is-tableFixed__3rdadd tbody')
        
        st.write(f"**特定のテーブル (`.is-tableFixed__3rdadd tbody`) の検索結果:** {len(table_rows)} 件")
        
        st.write("**▼ Pandasによる全テーブル強制抽出テスト**")
        try:
            tables = pd.read_html(response.text)
            st.success(f"{len(tables)} 個のテーブルデータを発見しました。")
            for i, df in enumerate(tables):
                with st.expander(f"テーブル {i+1}"):
                    st.dataframe(df)
        except ValueError:
            st.error("HTML内に <table> タグが一つも存在しません。")
            
    except Exception as e:
        st.error(f"通信または処理中にエラーが発生しました: {type(e).__name__}")
        st.code(traceback.format_exc())
