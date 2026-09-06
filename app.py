import streamlit as st
from curl_cffi import requests
from bs4 import BeautifulSoup
import traceback
import datetime

st.set_page_config(page_title="テーブル解析モード", layout="wide")
st.title("🛠️ テーブル完全解析モード")

st.markdown("通信は成功しているため、エラーの原因となったPandasを使用せず、純粋にHTMLのタグ構造を解析します。")

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

if st.button("HTML内の表(テーブル)をすべて探す"):
    today = datetime.date.today().strftime('%Y%m%d')
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={selected_jcd}&hd={today}"
    
    st.info(f"リクエストURL: {url}")
    
    try:
        response = requests.get(url, impersonate="chrome110", timeout=15)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # HTML内にあるすべての <table> タグを探す
        tables = soup.find_all('table')
        
        st.write(f"**HTML内にある <table> タグの数:** {len(tables)} 件")
        
        if len(tables) == 0:
            st.error("HTMLの中に表（table）が一つもありませんでした。")
            with st.expander("▼ HTMLの最後の部分（画面がどう終わっているか確認）"):
                st.text(response.text[-2000:])
        else:
            st.success("🎉 テーブルの取得に成功しました！以下のテーブルがページ内に存在します。")
            
            # 見つかったすべてのテーブルの「クラス名」を表示
            for i, tbl in enumerate(tables):
                cls_list = tbl.get('class', ['クラスなし'])
                cls_name = " ".join(cls_list)
                
                with st.expander(f"テーブル {i+1} (クラス名: {cls_name}) のHTML構造 (最初の500文字)"):
                    st.code(str(tbl)[:500], language='html')
                    
    except Exception as e:
        st.error(f"エラー発生: {type(e).__name__}")
        st.code(traceback.format_exc())
