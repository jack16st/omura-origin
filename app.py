import streamlit as st
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
import datetime
import re
import unicodedata

st.set_page_config(page_title="競艇AI予想 デバッグモード", layout="centered")
st.title("🚤 競艇AI予想 [デバッグ画面]")

TRACKS = {f"{i:02d}": name for i, name in enumerate(
    ["桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡", "常滑", "津", "三国", "びわこ", "住之江",
     "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山", "下関", "若松", "芦屋", "福岡", "唐津", "大村"], 1)}

st.markdown("### 🔍 払戻金データの直接確認ツール")
col_track, col_race = st.columns(2)
with col_track:
    selected_track_name = st.selectbox("対象のレース場", list(TRACKS.values()), index=0) # デフォルト桐生
    selected_jcd = [k for k, v in TRACKS.items() if v == selected_track_name][0]
with col_race:
    rno = st.selectbox("レース番号", list(range(1, 13)), index=0) # デフォルト1R

if st.button("公式から結果ページのHTMLを取得して解析する"):
    with st.spinner("データを取得中..."):
        today = datetime.date.today().strftime('%Y%m%d')
        url_result = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={rno}&jcd={selected_jcd}&hd={today}"
        
        st.write(f"**アクセスURL:** `{url_result}`")
        
        try:
            res = requests.get(url_result, impersonate="chrome110", timeout=10)
            res.encoding = 'utf-8'
            st.write(f"**ステータスコード:** `{res.status_code}`")
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                st.markdown("#### 1. ページ内の全テーブル（`table`）の生テキスト抽出結果")
                tables = soup.find_all('table')
                st.write(f"見つかったテーブルの数: {len(tables)} 個")
                
                found_data = False
                for i, table in enumerate(tables):
                    t_text = unicodedata.normalize('NFKC', table.get_text(separator=' | ', strip=True))
                    if '3連単' in t_text or '払戻' in t_text or '単勝' in t_text:
                        found_data = True
                        st.markdown(f"**--- テーブル [{i}] ---**")
                        st.text(t_text[:1500]) # 最初の1500文字を表示
                
                if not found_data:
                    st.warning("⚠️ 3連単や払戻金というキーワードが含まれるテーブルが見つかりませんでした。ページ構造が変わっているか、まだ未確定の可能性があります。")
                    
                st.markdown("#### 2. 行（`tr`）ごとの詳細データ（キーワードマッチ）")
                rows_found = 0
                for tr in soup.find_all('tr'):
                    row_text = unicodedata.normalize('NFKC', tr.get_text(separator=' | ', strip=True))
                    if any(k in row_text for k in ['3連単', '3連複', '2連単', '2連複', '拡連複', '単勝', '複勝']):
                        rows_found += 1
                        st.code(row_text)
                
                if rows_found == 0:
                    st.warning("⚠️ 券種キーワードに一致する行（tr）が1件もありませんでした。")
                    
            else:
                st.error(f"ページの取得に失敗しました。ステータスコード: {res.status_code}")
                
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
