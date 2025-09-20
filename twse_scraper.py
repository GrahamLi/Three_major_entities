import argparse
import logging
import time
import io
import warnings
import csv
from datetime import date, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import pandas as pd
import requests
from urllib3.exceptions import InsecureRequestWarning

# --- 設定日誌 (Logging Configuration) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# --- 常數設定 (Constants) ---
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
ROOT_DIR = Path(__file__).parent
TWSE_DATA_DIR = ROOT_DIR / "data" / "twse_raw"
TPEX_DATA_DIR = ROOT_DIR / "data" / "tpex_raw"
TWSE_SOURCES = {
    "外資": "https://www.twse.com.tw/rwd/zh/fund/TWT38U",
    "投信": "https://www.twse.com.tw/rwd/zh/fund/TWT44U",
    "自營商": "https://www.twse.com.tw/rwd/zh/fund/TWT43U",
}
TPEX_SOURCE_URL = "https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php"

def decode_content(content_bytes: bytes) -> Optional[str]:
    """智慧解碼函式"""
    encodings_to_try = ['utf-8-sig', 'utf-8', 'big5', 'cp950']
    for encoding in encodings_to_try:
        try: return content_bytes.decode(encoding)
        except UnicodeDecodeError: continue
    logging.error("所有編碼嘗試失敗，無法解碼內容。")
    return None

def fetch_data(session: requests.Session, url: str, params: Dict = None, description: str = "") -> Optional[bytes]:
    """通用資料下載函式"""
    logging.info(f"正在下載 {description} 資料...")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureRequestWarning)
            response = session.get(url, params=params, headers=HEADERS, timeout=15, verify=False)
        response.raise_for_status()
        if len(response.content) < 200:
            logging.warning(f"{description} 可能沒有交易資料。")
            return None
        return response.content
    except requests.exceptions.RequestException as e:
        logging.error(f"下載 {description} 資料時發生網路錯誤: {e}")
        return None

def parse_twse_csv(csv_content: str, name: str) -> pd.DataFrame:
    """專門解析三種不同結構TWSE CSV的函式 (最終手動解析標頭版)"""
    try:
        lines = [line for line in csv_content.strip().split('\n') if line.strip()]
        if len(lines) < 2: return pd.DataFrame()
        
        header_row_index = -1
        for i, line in enumerate(lines):
            if '證券代號' in line and '證券名稱' in line:
                header_row_index = i
                break
        if header_row_index == -1: return pd.DataFrame()
        
        df = pd.DataFrame()
        if name == '投信':
            df = pd.read_csv(io.StringIO("\n".join(lines[header_row_index:])), thousands=',')
            df.columns = df.columns.str.strip().str.replace('=', '').str.replace('"', '')
            df = df.rename(columns={'買進股數': '投信_買進股數', '賣出股數': '投信_賣出股數', '買賣超股數': '投信_買賣超股數'})
        elif name in ['外資', '自營商']:
            # --- 核心修正：手動解析雙層標頭 ---
            header_line_1 = list(csv.reader(io.StringIO(lines[header_row_index])))[0]
            header_line_2 = list(csv.reader(io.StringIO(lines[header_row_index + 1])))[0]
            data_rows = [list(csv.reader(io.StringIO(line)))[0] for line in lines[header_row_index + 2:]]

            # 建立正確的雙層標頭
            columns = []
            current_top_level = ""
            for i in range(len(header_line_1)):
                top_level = header_line_1[i].strip().replace('=', '').replace('"', '')
                if top_level: current_top_level = top_level
                sub_level = header_line_2[i].strip().replace('=', '').replace('"', '')
                columns.append((current_top_level, sub_level))
            
            df_multi = pd.DataFrame(data_rows, columns=pd.MultiIndex.from_tuples(columns))
            # --- 手動解析結束 ---
            
            df = pd.DataFrame()
            df['證券代號'] = df_multi[('證券代號', '證券代號')]
            df['證券名稱'] = df_multi[('證券名稱', '證券名稱')]
            
            if name == '外資':
                df['外資_買進股數'] = df_multi[('外資及陸資', '買進股數')]
                df['外資_賣出股數'] = df_multi[('外資及陸資', '賣出股數')]
                df['外資_買賣超股數'] = df_multi[('外資及陸資', '買賣超股數')]
            elif name == '自營商':
                df['自營商_自行買賣_買進股數'] = df_multi[('自營商(自行買賣)', '買進股數')]
                df['自營商_自行買賣_賣出股數'] = df_multi[('自營商(自行買賣)', '賣出股數')]
                df['自營商_自行買賣_買賣超股數'] = df_multi[('自營商(自行買賣)', '買賣超股數')]
                df['自營商_避險_買進股數'] = df_multi[('自營商(避險)', '買進股數')]
                df['自營商_避險_賣出股數'] = df_multi[('自營商(避險)', '賣出股數')]
                df['自營商_避險_買賣超股數'] = df_multi[('自營商(避險)', '買賣超股數')]

        df = df[~df['證券代號'].astype(str).str.contains('計')]
        df = df.dropna(subset=['證券代號'])
        df['證券代號'] = df['證券代號'].astype(str).str.strip()
        # 將所有數值欄位轉為數字
        for col in df.columns:
            if '股數' in str(col):
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

        return df
    except Exception as e:
        logging.error(f"解析 TWSE ({name}) CSV資料時發生失敗: {e}", exc_info=True)
        return pd.DataFrame()

def parse_tpex_csv(csv_content: str) -> pd.DataFrame:
    """專門解析TPEx CSV的函式"""
    try:
        lines = csv_content.strip().split('\n')
        if len(lines) < 2: return pd.DataFrame()
        header_row_index_list = [i for i, line in enumerate(lines) if '代號' in line and '名稱' in line]
        if not header_row_index_list: return pd.DataFrame()
        header_row_index = header_row_index_list[0]
        df = pd.read_csv(io.StringIO("\n".join(lines[header_row_index:])), thousands=',')
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all')
        df = df[~df['代號'].astype(str).str.contains('計')]
        df = df.dropna(subset=['代號'])
        df = df.rename(columns={'代號': '證券代號', '名稱': '證券名稱'})
        df['證券代號'] = df['證券代號'].astype(str).str.strip()
        columns_to_keep = [
            '證券代號', '證券名稱', '外資及陸資買進股數', '外資及陸資賣出股數', '外資及陸資買賣超股數',
            '投信買進股數', '投信賣出股數', '投信買賣超股數', '自營商(自行買賣)買進股數', '自營商(自行買賣)賣出股數',
            '自營商(自行買賣)買賣超股數', '自營商(避險)買進股數', '自營商(避險)賣出股數', '自營商(避險)買賣超股數',
        ]
        final_columns_to_select = []
        rename_map_suffix = {}
        for col_base in columns_to_keep:
            if col_base in df.columns: final_columns_to_select.append(col_base)
            elif f"{col_base}(股)" in df.columns:
                rename_map_suffix[f"{col_base}(股)"] = col_base
                final_columns_to_select.append(f"{col_base}(股)")
        return df[final_columns_to_select].rename(columns=rename_map_suffix)
    except Exception as e:
        logging.error(f"解析 TPEX CSV資料時發生失敗: {e}", exc_info=True)
        return pd.DataFrame()

def merge_dataframes(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """智慧合併多個DataFrame"""
    if not dfs: return pd.DataFrame()
    valid_dfs = [df for df in dfs if '證券代號' in df.columns and '證券名稱' in df.columns]
    if not valid_dfs: return pd.DataFrame()
    merged_df = valid_dfs[0]
    for df in valid_dfs[1:]:
        merged_df = pd.merge(merged_df, df, on=['證券代號', '證券名稱'], how='outer')
    for col in merged_df.columns:
        if '股數' in str(col): merged_df[col] = merged_df[col].fillna(0)
    return merged_df

def update_accumulation_file(stock_id: str, new_data_df: pd.DataFrame, stock_dir: Path):
    """高效更新個股的累加匯總CSV檔"""
    accumulation_file = stock_dir / f"{stock_id}.csv"
    try:
        if accumulation_file.exists():
            existing_df = pd.read_csv(accumulation_file, parse_dates=['日期'])
            combined_df = pd.concat([existing_df, new_data_df], ignore_index=True)
        else:
            combined_df = new_data_df
        combined_df = combined_df.drop_duplicates(subset=['日期'], keep='last').sort_values(by='日期').reset_index(drop=True)
        combined_df.to_csv(accumulation_file, index=False, encoding='utf-8-sig')
        logging.info(f"已更新 {stock_id} 的累加匯總檔。")
    except Exception as e:
        logging.error(f"更新 {stock_id} 累加檔案時發生錯誤: {e}")

def process_day(target_date: date, stock_map: Dict[str, str]):
    """處理單一日期的完整流程"""
    date_str_twse = target_date.strftime('%Y%m%d')
    date_str_tpex = f"{target_date.year - 1911}/{target_date.month:02d}/{target_date.day:02d}"
    twse_market_df, tpex_market_df = pd.DataFrame(), pd.DataFrame()
    with requests.Session() as session:
        twse_dfs = []
        params_twse = {'date': date_str_twse, 'response': 'csv'}
        for name, url in TWSE_SOURCES.items():
            content_bytes = fetch_data(session, url, params=params_twse, description=f"TWSE {name} {target_date}")
            if content_bytes and (content_str := decode_content(content_bytes)):
                df = parse_twse_csv(content_str, name)
                if not df.empty: twse_dfs.append(df)
            time.sleep(0.5)
        if twse_dfs:
            twse_market_df = merge_dataframes(twse_dfs)
            if not twse_market_df.empty:
                twse_market_df['日期'] = pd.to_datetime(target_date)

        params_tpex = {'d': date_str_tpex, 't': 'D', 'o': 'csv'}
        content_bytes = fetch_data(session, TPEX_SOURCE_URL, params=params_tpex, description=f"TPEX {target_date}")
        if content_bytes and (content_str := decode_content(content_bytes)):
            tpex_market_df = parse_tpex_csv(content_str)
            if not tpex_market_df.empty:
                tpex_market_df['日期'] = pd.to_datetime(target_date)
                for col in tpex_market_df.columns:
                    if '股數' in str(col): tpex_market_df[col] = pd.to_numeric(tpex_market_df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    if twse_market_df.empty and tpex_market_df.empty:
        logging.warning(f"{target_date} 無法獲取任何市場資料。")
        return
    for stock_id, market_type in stock_map.items():
        base_dir = TWSE_DATA_DIR if market_type == '上市' else TPEX_DATA_DIR
        market_df = twse_market_df if market_type == '上市' else tpex_market_df
        if market_df.empty: continue
        stock_df = market_df[market_df['證券代號'] == stock_id].copy()
        if stock_df.empty: continue
        stock_dir = base_dir / stock_id
        daily_file = stock_dir / f"{target_date.strftime('%Y-%m-%d')}.csv"
        if daily_file.exists():
            logging.info(f"資料已存在，跳過: {daily_file}")
            continue
        try:
            stock_dir.mkdir(parents=True, exist_ok=True)
            stock_df.to_csv(daily_file, index=False, encoding='utf-8-sig')
            logging.info(f"已儲存新資料: {daily_file}")
            update_accumulation_file(stock_id, stock_df, stock_dir)
        except OSError as e:
            logging.error(f"儲存檔案 {daily_file} 時發生系統錯誤: {e}")

def main():
    """主執行函式"""
    parser = argparse.ArgumentParser(description="台灣股市三大法人買賣超資料爬蟲 (上市+上櫃)")
    parser.add_argument("--days", type=int, default=1, help="指定從今天往前抓取的天數。預設為 1。")
    args = parser.parse_args()
    stock_list_file = ROOT_DIR / "stock_list.csv"
    if not stock_list_file.exists():
        logging.critical(f"錯誤: 找不到股票清單檔案 {stock_list_file}，請建立它。")
        return
    try:
        header_row_index = None
        with open(stock_list_file, 'r', encoding='utf-8-sig') as f:
            for i, line in enumerate(f):
                if 'stock_code' in line and '上市上櫃' in line:
                    header_row_index = i
                    break
        if header_row_index is None:
            logging.critical(f"錯誤: 在 {stock_list_file} 中找不到包含 'stock_code' 和 '上市上櫃' 的標頭行。")
            return
        logging.info(f"在 {stock_list_file} 的第 {header_row_index + 1} 行找到標頭。")
        stock_df = pd.read_csv(stock_list_file, header=header_row_index, dtype=str)
        stock_df.dropna(how='all', inplace=True)
        stock_map = dict(zip(stock_df['stock_code'], stock_df['上市上櫃']))
        logging.info(f"讀取到 {len(stock_map)} 支目標股票。")
    except Exception as e:
        logging.critical(f"讀取 stock_list.csv 失敗。請檢查檔案內容與格式。錯誤: {e}")
        return
    target_dates = [date.today() - timedelta(days=i) for i in range(args.days)]
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_day, dt, stock_map) for dt in target_dates]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logging.error(f"執行每日任務時發生未預期錯誤: {e}", exc_info=True)
    logging.info("所有任務執行完畢。")

if __name__ == "__main__":
    main()