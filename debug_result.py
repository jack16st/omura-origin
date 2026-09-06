import datetime
import unicodedata
from bs4 import BeautifulSoup
from curl_cffi import requests

# テストとして、本日の桐生 1R の結果ページにアクセスしてみる
jcd = "01"  # 桐生
rno = 1
today = datetime.date.today().strftime('%Y%m%d')
url_result = f"https://www.boatrace.jp/owpc/pc/race/raceresult?rno={rno}&jcd={jcd}&hd={today}"

print(f"Fetching URL: {url_result}")

try:
    res = requests.get(url_result, impersonate="chrome110", timeout=10)
    res.encoding = 'utf-8'
    print(f"Status Code: {res.status_code}")
    
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # ページ内のすべてのテーブル要素を走査して、文字がどう入っているか出力
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables on the page.\n")
    
    for i, table in enumerate(tables):
        text = unicodedata.normalize('NFKC', table.get_text(separator=' ', strip=True))
        if '3連単' in text or '払戻' in text or '単勝' in text:
            print(f"--- Table {i} contains target data ---")
            print(text[:600]) # 最初の600文字を表示
            print("-" * 50)
            
            # 行ごとの詳細
            for tr in table.find_all('tr'):
                row_text = unicodedata.normalize('NFKC', tr.get_text(separator=' | ', strip=True))
                if any(k in row_text for k in ['3連単', '2連単', '単勝', '複勝']):
                    print(f"ROW: {row_text}")

except Exception as e:
    print(f"Error occurred: {e}")
