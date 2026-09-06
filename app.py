import streamlit as st
import pandas as pd
from curl_cffi import requests
from bs4 import BeautifulSoup
import datetime
import re
import unicodedata

st.set_page_config(page_title="競艇AI予想", layout="centered")
st.title("🚤 競艇AI予想")

TRACKS = {f"{i:02d}": name for i, name in enumerate(
    ["桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖", "蒲郡", "常滑", "津", "三国", "びわこ", "住之江",
     "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山", "下関", "若松", "芦屋", "福岡", "唐津", "大村"], 1)}

# --- UI: 券種・入力モード・金額/点数の設定 ---
st.markdown("**⚙️ 買い目・資金配分の設定**")
bet_type = st.selectbox(
    "券種を選択", 
    ["3連単", "3連複", "2連単", "2連複", "拡連複", "単勝", "複勝"]
)

input_mode = st.radio("入力モード", ["金額で指定 (予算)", "点数で指定"], horizontal=True)

col_cond1, col_cond2 = st.columns(2)
with col_cond1:
    if "金額" in input_mode:
        budget = st.number_input("予算 (円)", min_value=100, value=1000, step=100)
        max_points = None
    else:
        budget = None
        max_points = st.slider("購入点数", 1, 15, 6)

st.markdown("---")
col_track, col_race = st.columns(2)
with col_track:
    selected_track_name = st.selectbox("対象のレース場", list(TRACKS.values()))
    selected_jcd = [k for k, v in TRACKS.items() if v == selected_track_name][0]
with col_race:
    rno = st.selectbox("レース番号", list(range(1, 13)))

@st.cache_data(ttl=60)
def get_race_data(jcd, rno):
    today = datetime.date.today().strftime('%Y%m%d')
    url_before = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={rno}&jcd={jcd}&hd={today}"
    url_race = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={rno}&jcd={jcd}&hd={today}"
    
    boats = {}
    weather = {"風速": "0m", "波高": "0cm"}
    
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
                st_match = re.search(r'0?\.\d{2}', td_texts[3])
                if st_match:
                    st_str = st_match.group()
                    if st_str.startswith('.'): st_str = '0' + st_str
                    avg_st = float(st_str)
                else:
                    avg_st = 0.15
                    
                nat_match = re.findall(r'\d+\.\d+', td_texts[4])
                win_rate = float(nat_match[0]) if nat_match else 5.0
                
                loc_match = re.findall(r'\d+\.\d+', td_texts[5])
                local_win_rate = float(loc_match[0]) if loc_match else 5.0
                
                mot_match = re.findall(r'\d+\.\d+', td_texts[6])
                motor_rate = float(mot_match[0]) if mot_match else 30.0
                
                boats[waku] = {"勝率": win_rate, "当地勝率": local_win_rate, "モーター": motor_rate, "平均ST": avg_st}
    except Exception:
        pass

    try:
        res_bf = requests.get(url_before, impersonate="chrome110", timeout=15)
        res_bf.encoding = 'utf-8'
        soup_bf = BeautifulSoup(res_bf.text, 'html.parser')
        
        soup_text = unicodedata.normalize('NFKC', soup_bf.get_text(separator=' '))
        wind_match = re.search(r'風速\s*(\d+m)', soup_text)
        if wind_match:
            weather["風速"] = wind_match.group(1)
            
        wave_match = re.search(r'波高\s*(\d+cm)', soup_text)
        if wave_match:
            weather["波高"] = wave_match.group(1)

        table = soup_bf.select_one('table.is-w748')
        if not table:
            return boats, weather, "⚠️ 直前情報テーブルが未公開です。実績データのみで仮計算しています。"

        valid_times = False
        for tbody in table.find_all('tbody'):
            rows = tbody.find_all('tr')
            if not rows: continue
            cols = rows[0].find_all('td')
            if len(cols) > 5:
                waku_text = "".join(filter(str.isdigit, cols[0].text.strip()))
                if waku_text in ["1", "2", "3", "4", "5", "6"]:
                    waku = int(waku_text)
                    ex_time = cols[4].text.strip()
                    tilt = cols[5].text.strip()
                    
                    if waku not in boats: 
                        boats[waku] = {"勝率": 5.0, "当地勝率": 5.0, "モーター": 30.0, "平均ST": 0.15}
                    
                    boats[waku]["展示"] = ex_time
                    boats[waku]["チルト"] = tilt
                    
                    if ex_time.replace('.','').isdigit():
                        valid_times = True
                        
        if not valid_times:
            return boats, weather, "⚠️ 直前情報（展示・チルト）がまだ公開されていません。実績データのみで仮計算しています。"
            
        return boats, weather, None
    except Exception as e:
        return boats, weather, f"データ取得エラー: {e}"

@st.cache_data(ttl=30)
def get_realtime_odds(jcd, rno, bet_type, target_combos):
    today = datetime.date.today().strftime('%Y%m%d')
    endpoint_map = {
        "3連単": "odds3t",
        "3連複": "odds3f",
        "2連単": "odds2t",
        "2連複": "odds2f",
        "単勝": "oddst",
        "複勝": "oddst",
        "拡連複": "odds3f"
    }
    endpoint = endpoint_map.get(bet_type, "odds3t")
    url_odds = f"https://www.boatrace.jp/owpc/pc/race/{endpoint}?rno={rno}&jcd={jcd}&hd={today}"
    
    odds_dict = {}
    try:
        res = requests.get(url_odds, impersonate="chrome110", timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        page_text = unicodedata.normalize('NFKC', soup.get_text(separator=' ', strip=True))
        
        for combo in target_combos:
            search_combo = combo.replace('-', '[-―]').replace('=', '[=＝]')
            pattern = rf'{search_combo}\s+([\d.]+)'
            match = re.search(pattern, page_text)
            if match:
                odds_dict[combo] = float(match.group(1))
            else:
                odds_dict[combo] = 15.0
    except Exception:
        for combo in target_combos:
            odds_dict[combo] = 15.0
            
    return odds_dict

@st.cache_data(ttl=60)
def get_race_result(jcd, rno):
    today = datetime.date.today().strftime('%Y%m%d')
    url_result = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={rno}&jcd={jcd}&hd={today}"
    try:
        res = requests.get(url_result, impersonate="chrome110", timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        result_list = []
        target_types = ['3連単', '3連複', '2連単', '2連複', '拡連複', '単勝', '複勝']
        
        for tr in soup.find_all('tr'):
            row_text = unicodedata.normalize('NFKC', tr.get_text(separator=' | ', strip=True))
            for bet in target_types:
                if bet in row_text and not any(r['券種'] == bet for r in result_list):
                    cells = [unicodedata.normalize('NFKC', td.get_text(strip=True)) for td in tr.find_all(['th', 'td'])]
                    combo = "---"
                    money = "---"
                    
                    for c in cells:
                        if re.match(r'^[1-6][\-\,=][1-6]', c) or re.match(r'^[1-6]$', c) or re.match(r'^[1-6][\-\,=][1-6][\-\,=][1-6]$', c):
                            if combo == "---":
                                combo = c
                        if '¥' in c or '￥' in c or ('円' in c and any(char.isdigit() for char in c)):
                            money = c if c.startswith('¥') or c.startswith('￥') or '円' in c else f"¥{c}"
                            if not money.endswith('円') and not '¥' in money and not '￥' in money:
                                money += "円"
                                
                    if combo == "---":
                        match_combo = re.search(r'([1-6](?:[\-\,=][1-6])*)', row_text.replace(' ', ''))
                        if match_combo:
                            combo = match_combo.group(1)
                    if money == "---":
                        match_money = re.search(r'([¥￥][\d,]+円?)', row_text)
                        if match_money:
                            money = match_money.group(1)
                            
                    if combo != "---" and money != "---":
                        result_list.append({
                            "券種": bet,
                            "結果 (組番)": combo,
                            "払戻金": money
                        })
                            
        return result_list if result_list else None
    except Exception:
        return None

def calculate_score(boats, weather):
    results = []
    wind_match = re.search(r'\d+', weather.get("風速", "0m"))
    wind_speed = int(wind_match.group()) if wind_match else 0
    
    for waku, data in boats.items():
        ex_time = data.get("展示", "")
        time_val = float(ex_time) if ex_time.replace('.','').isdigit() else 6.80
        
        ex_score = 100 - (time_val - 6.50) * 100
        st_score = (0.20 - data["平均ST"]) * 100
        
        win_val = data.get("勝率", 5.0)
        total_score = (ex_score * 0.4) + (win_val * 10 * 0.2) + (data["当地勝率"] * 10 * 0.1) + (data["モーター"] * 0.2) + st_score
        if waku == 1: total_score += 15 - (wind_speed * 2) 
        
        results.append({
            "枠": waku, "総合スコア": int(total_score), 
            "展示": ex_time, "チルト": data.get("チルト", ""),
            "勝率": f"{win_val:.2f}", "モーター": f"{data['モーター']:.1f}%", "平均ST": f"{data['平均ST']:.2f}"
        })
    return sorted(results, key=lambda x: x["総合スコア"], reverse=True)

def color_waku(val):
    colors = {1: '#FFF; color: #000; border: 1px solid #CCC', 2: '#000; color: #FFF', 3: '#F00; color: #FFF', 
              4: '#00F; color: #FFF', 5: '#FF0; color: #000', 6: '#080; color: #FFF'}
    return f'background-color: {colors.get(val, "")}; font-weight: bold; text-align: center;'

if st.button("予想＆資金配分を計算する"):
    with st.spinner("データ収集とリアルタイムオッズを計算中..."):
        raw_boats, weather, warning_msg = get_race_data(selected_jcd, rno)
        
        if not raw_boats:
            st.error(warning_msg or "データが取得できませんでした。")
        else:
            if warning_msg: st.warning(warning_msg)
            
            df_scored = calculate_score(raw_boats, weather)
            df = pd.DataFrame(df_scored)
            top_waku = [row["枠"] for row in df_scored[:4]]
            
            st.markdown(f"### 🐱 おすすめフォーメーション ({bet_type})")
            
            if bet_type == "3連単":
                formation_combos = [
                    f"{top_waku[0]}-{top_waku[1]}-{top_waku[2]}",
                    f"{top_waku[0]}-{top_waku[2]}-{top_waku[1]}",
                    f"{top_waku[0]}-{top_waku[1]}-{top_waku[3]}",
                    f"{top_waku[0]}-{top_waku[3]}-{top_waku[1]}"
                ]
                formation_text = f"{top_waku[0]} - {top_waku[1]}.{top_waku[2]}.{top_waku[3]} - {top_waku[1]}.{top_waku[2]}.{top_waku[3]}"
            elif bet_type == "2連単":
                formation_combos = [
                    f"{top_waku[0]}-{top_waku[1]}",
                    f"{top_waku[0]}-{top_waku[2]}",
                    f"{top_waku[0]}-{top_waku[3]}"
                ]
                formation_text = f"{top_waku[0]} - {top_waku[1]}.{top_waku[2]}.{top_waku[3]}"
            elif bet_type == "単勝":
                formation_combos = [f"{top_waku[0]}"]
                formation_text = f"{top_waku[0]}"
            else:
                formation_combos = [
                    f"{top_waku[0]}={top_waku[1]}",
                    f"{top_waku[0]}={top_waku[2]}"
                ]
                formation_text = f"{top_waku[0]} 軸ながし等"

            real_odds = get_realtime_odds(selected_jcd, rno, bet_type, formation_combos)

            st.info(f"**【本線】 {formation_text}**")
            
            allocations = {}
            total_invest = 0
            
            if "金額" in input_mode:
                total_prob = sum(1/odds for odds in real_odds.values())
                if total_prob >= 1.0:
                    st.error("⚠️ この買い目は合成オッズが1.0を切るためトリガミになります。見送りを推奨します。")
                else:
                    st.success(f"✅ リアルタイム合成オッズ: {1/total_prob:.2f}倍 (ガミりません)")
                    st.write(f"**{budget}円** の推奨資金配分 (利益均等化):")
                    for formation, odds in real_odds.items():
                        allocation = int((budget * (1/odds) / total_prob) / 100) * 100
                        if allocation == 0: allocation = 100
                        allocations[formation] = allocation
                        total_invest += allocation
                        st.write(f"・ **{formation}** : **{allocation}円** (リアルタイムオッズ: **{odds}倍** / 的中時約 {int(allocation*odds)}円)")
            else:
                st.write(f"🎯 指定点数 ({max_points}点) での均等買いモードです。")
                each_budget = int((1000 / max_points) / 100) * 100
                for formation, odds in real_odds.items():
                    allocations[formation] = max(100, each_budget)
                    total_invest += max(100, each_budget)
                    st.write(f"・ **{formation}** : 約 **{max(100, each_budget)}円** (リアルタイムオッズ: **{odds}倍**) ")

            st.write(f"▼ **{selected_track_name} {rno}R** 予想スコア")
            if hasattr(df.style, 'hide'):
                styled_df = df[["枠", "総合スコア", "展示", "チルト"]].style.hide(axis='index').map(color_waku, subset=['枠'])
            else:
                styled_df = df[["枠", "総合スコア", "展示", "チルト"]].style.hide_index().applymap(color_waku, subset=['枠'])
            st.table(styled_df)
            
            with st.expander("📊 スコア計算に使用した詳細データ & 買い目オッズ一覧"):
                st.write(f"**気象条件:** 風速 {weather['風速']} / 波高 {weather['波高']}")
                st.markdown("**【選択した買い目のリアルタイムオッズ一覧】**")
                for form, od in real_odds.items():
                    st.write(f"- {form}: **{od}倍**")
                st.markdown("---")
                if hasattr(df.style, 'hide'):
                    styled_details = df[["枠", "勝率", "平均ST", "モーター"]].style.hide(axis='index').map(color_waku, subset=['枠'])
                else:
                    styled_details = df[["枠", "勝率", "平均ST", "モーター"]].style.hide_index().applymap(color_waku, subset=['枠'])
                st.table(styled_details)

            # --- 確定結果テーブル & 的中・収支判定表示 ---
            race_result = get_race_result(selected_jcd, rno)
            if race_result:
                st.markdown("---")
                st.markdown("### 🏁 レース確定結果 & 的中判定")
                
                # 的中判定ロジック
                # 該当券種の正式な結果組番を取得
                actual_result_combo = None
                actual_payout_money = 0
                
                for res in race_result:
                    if res["券種"] == bet_type:
                        actual_result_combo = res["結果 (組番)"].replace('=', '-')
                        money_str = re.sub(r'[^\d]', '', res["払戻金"])
                        actual_payout_money = int(money_str) if money_str.isdigit() else 0
                        break
                
                hit_found = False
                total_return = 0
                
                for form, alloc in allocations.items():
                    # フォーメーションの表記揺れ（2-4-5 と 2-4-5 など）を正規化して比較
                    norm_form = form.replace('=', '-')
                    if actual_result_combo and norm_form == actual_result_combo:
                        hit_found = True
                        # 100円あたりの払戻金 × (投資額 / 100)
                        return_amount = int(actual_payout_money * (alloc / 100))
                        total_return += return_amount

                if hit_found:
                    profit = total_return - total_invest
                    recovery_rate = int((total_return / total_invest) * 100) if total_invest > 0 else 0
                    st.success(f"🎉 **的中！** （確定結果: **{actual_result_combo}**）")
                    st.metric(label="払戻金合計 / 収支", value=f"¥{total_return:,}", delta=f"¥{profit:,} (回収率: {recovery_rate}%)")
                else:
                    if actual_result_combo:
                        st.error(f"残念… ハズレです。（確定結果: **{actual_result_combo}**）")
                        st.metric(label="収支", value=f"¥-{total_invest:,}", delta="回収率: 0%")
                    else:
                        st.info("ℹ️ 結果は公開されていますが、該当券種の結果照合中です。")

                df_res = pd.DataFrame(race_result)
                if hasattr(df_res.style, 'hide'):
                    st.table(df_res.style.hide(axis='index'))
                else:
                    st.table(df_res.style.hide_index())
            else:
                st.info("ℹ️ まだレース結果が確定していないか、データが取得できませんでした。")
