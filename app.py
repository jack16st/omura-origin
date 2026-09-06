import streamlit as st
import pandas as pd

# スマホ画面に最適化した設定
st.set_page_config(page_title="独自予想アプリ", layout="centered")

# アプリのタイトルとレース選択
st.title("🚤 独自スコア予測")
race_select = st.selectbox("対象レース", ["桐生 1R (締切 15:25)", "戸田 12R (締切 16:30)"])

# 波乱アラート機能（システムが危険を検知した時だけ表示）
st.error("⚠️ 【波乱アラート】イン最弱水面 × 1号艇F持ち。4コースのまくり警戒！")

# データの準備（画面確認用のサンプルデータ）
data = {
    "枠": [1, 2, 3, 4, 5, 6],
    "スコア": [45, 52, 60, 88, 40, 35],
    "展示": [6.82, 6.78, 6.75, 6.69, 6.80, 6.85],
    "チルト": ["-0.5", "-0.5", "0.0", "+0.5", "-0.5", "-0.5"]
}
df = pd.DataFrame(data)

# スコアが高い順（期待値順）に自動で並び替えて表示
df_sorted = df.sort_values(by="スコア", ascending=False)

st.write("▼ 直前気配＆独自スコア")
# スマホの横幅にぴったり合わせる設定 (use_container_width)
st.dataframe(df_sorted, hide_index=True, use_container_width=True)

# スコアに基づいた買い目の自動出力
st.success("🎯 推奨買い目（3連単）\n\n【本線】 4 - 3 - 12\n\n【抑え】 4 - 12 - 3")
