import streamlit as st
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
import datetime
import re

st.set_page_config(page_title="競艇AI予想", layout="centered")
st.title("🚤 競艇AI予想")

TRACKS = {f"{i:02d}": name for i, name in enumerate(
    ["桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡", "常滑", "津", "三国", "びわこ", "住之江",
     "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山", "下関", "若松", "芦屋", "福岡", "唐津", "大村"], 1)}

st.markdown("**⚙️ 予算・券種の設定**")
col_cond1, col_cond2 = st.columns(2)
with col_cond1:
    budget = st.number_input("予算 (円)", min_value=100, value=1000, step=100)
with col_cond2:
    bet_type = st.radio("券種", ["3連単", "2連単"])

st.markdown("---")
col_track, col_race = st.columns(2)
with col_track:
    selected_track_name = st.selectbox("対象のレース場", list(TRACKS.values()))
    selected_jcd = [k for k, v in TRACKS.items() if v == selected_track_name][0]
with col_race:
    rno = st.selectbox("レース番号", list(range(1, 13)))

@st.cache_data(ttl=120)
def get_race_data(jcd, rno):
    today = datetime.date.today().strftime('%Y%m%d')
    url_before = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={today}"
    url_race = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={today}"
    
    boats = {}
    weather_info = {"風速": "0m", "波高": "0cm"}
    
    try:
        res_rl = requests.get(url_race, impersonate="chrome110", timeout=15)
        res_rl.encoding = 'utf-8'
        soup_rl = BeautifulSoup(res_rl.text, 'html.parser')
        
        for waku in range(1, 7):
            w_td = soup_rl.find('td', class_=f'is-boatColor{waku}')
            if not w_td: continue
            
            tr = w_td.find_parent('tr')
            tds = tr.find_all('td', recursive=False)
            td_texts = [td.get_text(separator=' ', strip=True) for td in tds]
            
            if len(td_texts) >= 7:
                # 平均ST (例: F1 0.15)
                st_match = re.search(r'0?\.\d{2}', td_texts[3])
                if st_match:
                    st_str = st_match.group()
                    if st_str.startswith('.'): st_str = '0' + st_str
                    avg_st = float(st_str)
                else:
                    avg_st = 0.15
                    
                # 全国勝率
                nat_match = re.findall(r'\d+\.\d+', td_texts[4])
                win_rate = float(nat_match[0]) if nat_match else 5.0
                
                # 当地勝率
                loc_match = re.findall(r'\d+\.\d+', td_texts[5])
                local_win_rate = float(loc_match[0]) if loc_match else 5.0
                
                # モーター2連対率
                mot_match = re.findall(r'\d+\.\d+', td_texts[6])
                motor_rate = float(mot_match[0]) if mot_match else 30.0
                
                boats[waku] = {"勝率": win_rate, "当地勝率": local_win_rate, "モーター": motor_rate, "平均ST": avg_st}
    except Exception:
        pass

    try:
        res_bf = requests.get(url_before, impersonate="chrome110", timeout=15)
        res_bf.encoding = 'utf-8'
        soup_bf = BeautifulSoup(res_bf.text, 'html.parser')
        
        # 気象情報の確実な抽出
        w_titles = soup_bf.find_all(class_='weather1_bodyUnitLabelTitle')
        w_datas = soup_bf.find_all(class_='weather1_bodyUnitLabelData')
        for t, d in zip(w_titles, w_datas):
            if "風速" in t.text: weather_info["風速"] = d.get_text(strip=True)
            if "波高" in t.text: weather_info["波高"] = d.get_text(strip=True)

        valid_times = False
        for waku in range(1, 7):
            w_td = soup_bf.find('td', class_=f'is-boatColor{waku}')
            if not w_td: continue
            
            tr = w_td.find_parent('tr')
            tds = tr.find_all('td', recursive=False)
            td_texts = [td.get_text(separator=' ', strip=True) for td in tds]
            
            if len(td_texts) >= 7:
                tilt = td_texts[5]
                ex_time = td_texts[6]
                
                if waku not in boats: boats[waku] = {"勝率": 5.0, "当地勝率": 5.0, "モーター": 30.0, "平均ST": 0.15}
                boats[waku]["展示"] = ex_time
                boats[waku]["チルト"] = tilt
                
                if ex_time.replace('.','').isdigit():
                    valid_times = True
                        
        if not valid_times:
            return boats, weather_info, "⚠️ 直前情報（展示・チルト）が未公開です。実績データのみで仮計算しています。"
            
        return boats, weather_info, None
    except Exception as e:
        return None, None, f"データ取得エラー: {e}"

def calculate_score(boats, weather):
    results = []
    wind_match = re.search(r'\d+', weather.get("風速", "0m"))
    wind_speed = int(wind_match.group()) if wind_match else 0
    
    for waku, data in boats.items():
        ex_time = data.get("展示", "")
        time_val = float(ex_time) if ex_time.replace('.','').isdigit() else 6.80
        
        ex_score = 100 - (time_val - 6.50) * 100
        st_score = (0.20 - data["平均ST"]) * 100
        
        total_score = (ex_score * 0.4) + (data["勝率"] * 10 * 0.2) + (data["当地勝率"] * 10 * 0.1) + (data["モーター"] * 0.2) + st_score
        if waku == 1: total_score += 15 - (wind_speed * 2) 
        
        results.append({
            "枠": waku, "総合スコア": int(total_score), 
            "展示": ex_time, "チルト": data.get("チルト", ""),
            "勝率": f"{data['勝率']:.2f}", "モーター": f"{data['モーター']:.1f}%", "平均ST": f"{data['平均ST']:.2f}"
        })
    return sorted(results, key=lambda x: x["総合スコア"], reverse=True)

def color_waku(val):
    colors = {1: '#FFF; color: #000; border: 1px solid #CCC', 2: '#000; color: #FFF', 3: '#F00; color: #FFF', 
              4: '#00F; color: #FFF', 5: '#FF0; color: #000', 6: '#080; color: #FFF'}
    return f'background-color: {colors.get(val, "")}; font-weight: bold; text-align: center;'

if st.button("予想＆資金配分を計算する"):
    with st.spinner("データ収集と期待値スコアを計算中..."):
        raw_boats, weather, warning_msg = get_race_data(selected_jcd, rno)
        
        if raw_boats is None:
            st.error(warning_msg)
        else:
            if warning_msg: st.warning(warning_msg)
            
            df_scored = calculate_score(raw_boats, weather)
            df = pd.DataFrame(df_scored)
            top_waku = [row["枠"] for row in df_scored[:4]]
            
            st.markdown("### 🐱 おすすめフォーメーションと資金配分")
            # ※現在はロジック確認用のダミーオッズ。実用化でリアルオッズを取得・計算します。
            mock_odds = {f"{top_waku[0]}-{top_waku[1]}-{top_waku[2]}": 15.5, f"{top_waku[0]}-{top_waku[2]}-{top_waku[1]}": 22.0,
                         f"{top_waku[0]}-{top_waku[1]}-{top_waku[3]}": 8.2,  f"{top_waku[0]}-{top_waku[3]}-{top_waku[1]}": 12.0}
            
            if bet_type == "3連単":
                st.info(f"**【抽出目】 {top_waku[0]} - {top_waku[1]}.{top_waku[2]}.{top_waku[3]} - {top_waku[1]}.{top_waku[2]}.{top_waku[3]}**")
                
                total_prob = sum(1/odds for odds in mock_odds.values())
                if total_prob >= 1.0:
                    st.error("⚠️ この買い目は合成オッズが1.0を切るためトリガミになります。見送りを推奨します。")
                else:
                    st.success(f"✅ 合成オッズ: {1/total_prob:.2f}倍 (ガミりません)")
                    st.write(f"**{budget}円** の推奨資金配分 (利益均等化):")
                    for formation, odds in mock_odds.items():
                        allocation = int((budget * (1/odds) / total_prob) / 100) * 100
                        if allocation == 0: allocation = 100
                        st.write(f"・ {formation} : **{allocation}円** (オッズ {odds}倍 / 的中時約 {int(allocation*odds)}円)")

            st.write(f"▼ **{selected_track_name} {rno}R** 予想スコア")
            if hasattr(df.style, 'hide'):
                styled_df = df[["枠", "総合スコア", "展示", "チルト"]].style.hide(axis='index').map(color_waku, subset=['枠'])
            else:
                styled_df = df[["枠", "総合スコア", "展示", "チルト"]].style.hide_index().applymap(color_waku, subset=['枠'])
            st.table(styled_df)
            
            with st.expander("📊 スコア計算に使用した詳細データ"):
                st.write(f"**気象条件:** 風速 {weather['風速']} / 波高 {weather['波高']}")
                if hasattr(df.style, 'hide'):
                    styled_details = df[["枠", "勝率", "平均ST", "モーター"]].style.hide(axis='index').map(color_waku, subset=['枠'])
                else:
                    styled_details = df[["枠", "勝率", "平均ST", "モーター"]].style.hide_index().applymap(color_waku, subset=['枠'])
                st.table(styled_details)
