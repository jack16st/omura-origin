import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
import traceback

# デバッグ用に画面を広く使います
st.set_page_config(page_title="デバッグモード: 独自予想アプリ", layout="wide")
st.title("🛠️ 通信デバッグモード")

st.markdown("曖昧なエラーメッセージを排除し、サーバーから実際に返ってきた**生のステータスとHTMLの中身**をそのまま画面に出力して原因を特定します。")

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

if st.button("生データとエラーを完全に確認する"):
    today = datetime.date.today().strftime('%Y%m%d')
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={selected_jcd}&hd={today}"
    
    st.info(f"🌐 リクエストURL:\n{url}")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # アクセス実行
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        # 1. ステータスコードの表示（200なら正常、403なら拒否）
        if response.status_code == 200:
            st.success(f"HTTPステータスコード: {response.status_code} (通信は成功しています)")
        else:
            st.error(f"HTTPステータスコード: {response.status_code} (エラーが返ってきています)")
            
        # 2. サーバーから返ってきたレスポンスヘッダーのダンプ
        with st.expander("レスポンスヘッダーの中身 (詳細)"):
            st.json(dict(response.headers))
            
        # 3. HTMLそのもののダンプ
        with st.expander("取得したHTMLの中身 (最初の2000文字)"):
            html_content = response.text
            if len(html_content) == 0:
                st.warning("⚠️ HTMLの中身が完全に空っぽ（0文字）で返ってきました！")
            else:
                st.text(html_content[:2000])

        # 4. 解析テスト（HTML構造が変わっているかどうかの確認）
        soup = BeautifulSoup(response.text, 'html.parser')
        table_rows = soup.select('.is-tableFixed__3rdadd tbody')
        st.write(f"🔍 解析対象のテーブル (`.is-tableFixed__3rdadd tbody`) の検索結果: **{len(table_rows)} 件見つかりました**")
        
        if len(table_rows) > 0:
            with st.expander("テーブル要素のHTML構造"):
                st.code(str(table_rows[0])[:1000], language='html')
                
    except requests.exceptions.Timeout:
        st.error("❌ タイムアウトエラーが発生しました。ボートレース公式サイトがアクセスを無視（ドロップ）しています。")
        st.code(traceback.format_exc())
    except Exception as e:
        st.error(f"❌ プログラムの処理中に予期せぬ例外が発生しました: {type(e).__name__}")
        st.code(traceback.format_exc())
