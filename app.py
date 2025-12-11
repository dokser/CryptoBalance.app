import streamlit as st
import requests
import datetime
from fpdf import FPDF
import io

# --- Configuration ---
st.set_page_config(page_title="CryptoBalance Forensic", page_icon="🕵️‍♂️", layout="centered")

# --- Custom CSS for Hebrew Support (RTL) & UI Tweaks ---
st.markdown("""
    <style>
    .stTextInput > label {font-size:110%; font-weight:bold;}
    .stSelectbox > label {font-size:110%; font-weight:bold;}
    /* Simple RTL alignment */
    .element-container {direction: ltr;} 
    </style>
    """, unsafe_allow_html=True)

# --- Logic Functions (Robust & Anti-Blocking) ---
def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

def get_price(coin_str):
    ids = {'Bitcoin (BTC)': 'bitcoin', 'Ethereum (ETH)': 'ethereum', 'Tron (TRX)': 'tron', 
           'Litecoin (LTC)': 'litecoin', 'Dogecoin (DOGE)': 'dogecoin'}
    coin_id = ids.get(coin_str)
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        return requests.get(url, headers=get_headers(), timeout=10).json()[coin_id]['usd']
    except:
        return None

def get_balance(coin_str, address):
    headers = get_headers()
    
    if 'Bitcoin' in coin_str:
        url = f"https://blockchain.info/q/addressbalance/{address}"
        try:
            return float(requests.get(url, headers=headers).text) / 100000000
        except: return None
        
    elif 'Ethereum' in coin_str:
        if not address.startswith('0x') or len(address) != 42:
             return -1 # Invalid format indicator

        # Multi-node fallback
        nodes = [
            "https://eth.llamarpc.com",
            "https://rpc.ankr.com/eth",
            "https://cloudflare-eth.com"
        ]
        payload = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [address, "latest"], "id": 1}
        
        for node in nodes:
            try:
                resp = requests.post(node, json=payload, headers=headers, timeout=5)
                data = resp.json()
                if 'result' in data:
                    return int(data['result'], 16) / 10**18
            except: continue
        return None # Failed

    elif 'Tron' in coin_str:
        url = f"https://apilist.tronscan.org/api/account?address={address}"
        try:
            data = requests.get(url, headers=headers).json()
            if 'balances' in data:
                for t in data['balances']:
                    if t['tokenName'] == 'trx': return float(t['balance']) / 1000000
                return 0.0
            elif 'balance' in data: return float(data['balance']) / 1000000
        except: return None

    elif 'Litecoin' in coin_str or 'Dogecoin' in coin_str:
        c = 'ltc' if 'Litecoin' in coin_str else 'doge'
        url = f"https://api.blockcypher.com/v1/{c}/main/addrs/{address}/balance"
        try:
            return requests.get(url, headers=headers).json()['balance'] / 100000000
        except: return None
        
    return None

def create_pdf(data, user_info):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "CryptoBalance Report", ln=1, align='C')
    pdf.line(10, 22, 200, 22)
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(190, 10, f"Investigator: {user_info['name']}", ln=1)
    pdf.cell(190, 10, f"ID Number: {user_info['id']}", ln=1)
    pdf.cell(190, 10, f"Unit: {user_info['unit']}", ln=1)
    pdf.ln(5)
    
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(190, 10, " Scan Results", ln=1, fill=True)
    pdf.ln(2)
    
    pdf.cell(190, 8, f"Time: {data['time']}", ln=1)
    pdf.cell(190, 8, f"Coin: {data['coin']}", ln=1)
    pdf.cell(190, 8, f"Address: {data['address']}", ln=1)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, f"Total Value: ${data['total_usd']:,.2f}", ln=1)
    
    # Return as bytes for download
    return pdf.output(dest='S').encode('latin-1')

# --- UI Structure ---
st.title("🕵️‍♂️ CryptoBalance Scanner")
st.markdown("### Forensic Blockchain Tool")

# Sidebar for Login (Optional)
with st.sidebar:
    st.header("Investigator Details")
    st.markdown("*(Optional - Leave empty to skip)*")
    
    input_name = st.text_input("Full Name")
    input_id = st.text_input("ID Number")
    input_unit = st.text_input("Unit")
    
    # Logic: If empty, use defaults
    full_name = input_name if input_name.strip() else "Guest"
    id_number = input_id if input_id.strip() else "N/A"
    unit = input_unit if input_unit.strip() else "N/A"

    if input_name:
        st.success(f"Active: {full_name}")
    else:
        st.info("Running as Guest")

# Main Scanner Area
col1, col2 = st.columns([3, 1])
with col1:
    coin_type = st.selectbox("Select Cryptocurrency", 
        ['Bitcoin (BTC)', 'Ethereum (ETH)', 'Tron (TRX)', 'Litecoin (LTC)', 'Dogecoin (DOGE)'])

address = st.text_input("Wallet Address (Paste here)")

if st.button("🔎 Scan Blockchain", type="primary"):
    if not address:
        st.error("Please enter a wallet address.")
    else:
        with st.spinner('Connecting to Blockchain Nodes...'):
            # Run Logic
            price = get_price(coin_type)
            balance = get_balance(coin_type, address.strip())
            
            if balance == -1:
                st.error("Invalid Address Format.")
            elif balance is None or price is None:
                st.error("Connection Error or API Limit. Try again.")
            else:
                total_usd = balance * price
                
                # Display Results
                st.markdown("---")
                c1, c2 = st.columns(2)
                c1.metric("Balance", f"{balance:.8f}", coin_type.split('(')[1][:-1])
                c2.metric("Value (USD)", f"${total_usd:,.2f}")
                
                # Prepare Data for Report
                scan_data = {
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "coin": coin_type,
                    "address": address,
                    "total_usd": total_usd
                }
                
                # Generate PDF (Always available now)
                pdf_bytes = create_pdf(scan_data, {"name": full_name, "id": id_number, "unit": unit})
                
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"Report_{datetime.datetime.now().strftime('%H%M')}.pdf",
                    mime="application/pdf"
                )

st.markdown("---")
st.caption("Secure Forensic Tool | Runs on Cloud | No Logs Saved")
