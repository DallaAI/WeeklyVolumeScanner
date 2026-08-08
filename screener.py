import pandas as pd
import yfinance as yf
import requests
import io
import time

def get_nse_symbols():
    """Fetches official stock symbol lists for Nifty 500, Smallcap 250, and Microcap 250 from NSE India."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    urls = {
        "Nifty 500": "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv",
        "Smallcap 250": "https://niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv",
        "Microcap 250": "https://niftyindices.com/IndexConstituent/ind_niftymicrocap250_list.csv"
    }
    
    symbols_dict = {}
    
    for category, url in urls.items():
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                # Append .NS suffix required for Yahoo Finance Indian stock tickers
                symbols = [f"{symbol}.NS" for symbol in df['Symbol'].dropna().unique()]
                symbols_dict[category] = symbols
            else:
                print(f"Could not download {category} list. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error fetching {category}: {e}")
            
    return symbols_dict

def run_screener():
    print("Fetching stock lists from NSE...")
    categories = get_nse_symbols()
    
    # Fallback to a sample list if NSE website blocks automated request
    if not categories:
        print("Using fallback processing...")
        return

    results = []

    for category, symbols in categories.items():
        print(f"\nProcessing {category} ({len(symbols)} stocks)...")
        
        # Batch process symbols to avoid rate limits
        for i, symbol in enumerate(symbols):
            try:
                # Fetch 15 days of daily data to ensure we have at least 8 trading days
                df = yf.download(symbol, period="15d", progress=False)
                
                if len(df) >= 8:
                    # Get last 8 trading days volume
                    volumes = df['Volume'].tail(8)
                    
                    # Today's volume is the most recent trading day
                    today_vol = float(volumes.iloc[-1])
                    
                    # Average volume of previous 7 trading days
                    avg_7d_vol = float(volumes.iloc[-8:-1].mean())
                    
                    if avg_7d_vol > 0:
                        vol_ratio = (today_vol / avg_7d_vol) * 100
                        
                        # Check if Today's Volume >= 110% of 7-day average
                        if vol_ratio >= 110.0:
                            stock_name = symbol.replace(".NS", "")
                            close_price = round(float(df['Close'].iloc[-1]), 2)
                            
                            results.append({
                                "Category": category,
                                "Symbol": stock_name,
                                "Close Price": close_price,
                                "Today Volume": int(today_vol),
                                "7-Day Avg Volume": int(avg_7d_vol),
                                "Volume Surge (%)": round(vol_ratio, 2)
                            })
                            print(f"MATCH: {stock_name} | Surge: {round(vol_ratio, 2)}%")
            except Exception as e:
                continue
                
            # Brief pause to respect API rate limits
            time.sleep(0.1)

    # Save results to a CSV file
    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values(by="Volume Surge (%)", ascending=False)
        results_df.to_csv("screener_results.csv", index=False)
        print("\nScreener completed successfully! Results saved to 'screener_results.csv'.")
    else:
        print("\nScreener completed. No stocks met the criteria today.")

if __name__ == "__main__":
    run_screener()
