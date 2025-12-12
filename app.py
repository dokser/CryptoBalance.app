import streamlit as st
import requests
import datetime
from fpdf import FPDF
import cv2
import numpy as np
from PIL import Image

# --- Configuration ---
st.set_page_config(page_title="CryptoBalance Forensic", page_icon="🕵️‍♂️", layout="centered")

# --- Initialize Session State ---
if 'wallet_address' not in st.session_state:
    st.session_state.wallet_address = ""

# --- Helper Functions ---
def clear_text():
    st.session_state.wallet_address = ""

def decode_qr(image_buffer):
    try:
        # Convert the file/buffer to an opencv image
        file_bytes = np.asarray(bytearray(image_buffer.read()), dtype=np.uint8)
        opencv_image = cv2.imdecode(file_bytes, 1)
        
        # Initialize the QRCode detector
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(opencv_image)
        
        if data:
            return data
        return None
    except Exception as e:
        return None

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
             return -1 

        nodes = ["https://eth.llamarpc.com", "https://rpc.ankr.com/eth", "https://cloudflare-eth.com"]
        payload = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [address, "latest"], "id": 1}
        
        for node in nodes:
            try:
                resp = requests.post(node, json=payload, headers=headers, timeout=5)
                data = resp.json()
                if 'result' in data:
                    return int(data['result'], 16) / 10**18
            except: continue
        return None

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
    return pdf.output(dest='S').encode('latin-1')

# --- UI Layout ---
st.title("🕵️‍♂️ CryptoBalance Scanner")

# 1. Sidebar
with st.sidebar:
    st.header("📋 Investigator Details")
    st.caption("Optional - For Report Only")
    input_name = st.text_input("Full Name")
    input_id = st.text_input("ID Number")
    input_unit = st.text_input("Unit")
    
    full_name = input_name if input_name.strip() else "Guest"
    id_number = input_id if input_id.strip() else "N/A"
    unit = input_unit if input_unit.strip() else "N/A"

    if input_name:
        st.success(f"User: {full_name}")

# 2. Coin Selection
coin_type = st.selectbox("Select Cryptocurrency", 
    ['Bitcoin (BTC)', 'Ethereum (ETH)', 'Tron (TRX)', 'Litecoin (LTC)', 'Dogecoin (DOGE)'])

# 3. QR Options (Tabs for cleaner UI)
st.write("---")
st.subheader("📷 Address Input Options")
tab1, tab2 = st.tabs(["📤 Upload Image", "🎥 Live Camera"])

# Option A: Upload File (Easier & No Permissions needed)
with tab1:
    uploaded_file = st.file_uploader("Upload QR Code Image", type=['png', 'jpg', 'jpeg'])
    if uploaded_file is not None:
        qr_data = decode_qr(uploaded_file)
        if qr_data:
            st.session_state.wallet_address = qr_data
            st.success(f"QR Decoded from File: {qr_data}")
        else:
            st.error("Could not read QR code from image.")

# Option B: Live Camera (Requires Permission)
with tab2:
    st.caption("Requires browser camera permission")
    camera_image = st.camera_input("Scan QR")
    if camera_image is not None:
        qr_data = decode_qr(camera_image)
        if qr_data:
            st.session_state.wallet_address = qr_data
            st.success(f"QR Decoded from Camera: {qr_data}")

# 4. Wallet Address Input + Clear
col_input, col_clear = st.columns([5, 1])
with col_input:
    address = st.text_input("Wallet Address", key="wallet_address")
with col_clear:
    st.write("") 
    st.write("") 
    if st.button("❌", help="Clear Address"):
        clear_text()
        st.experimental_rerun()

# 5. Scan Action
if st.button("🔎 Scan Blockchain", type="primary", use_container_width=True):
    if not address:
        st.error("Please enter a wallet address.")
    else:
        with st.spinner('Connecting to Blockchain Nodes...'):
            price = get_price(coin_type)
            balance = get_balance(coin_type, address.strip())
            
            if balance == -1:
                st.error("Invalid Address Format.")
            elif balance is None or price is None:
                st.error("Connection Error or API Limit. Try again.")
            else:
                total_usd = balance * price
                
                st.markdown("---")
                c1, c2 = st.columns(2)
                c1.metric("Balance", f"{balance:.8f}", coin_type.split('(')[1][:-1])
                c2.metric("Value (USD)", f"${total_usd:,.2f}")
                
                scan_data = {
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "coin": coin_type,
                    "address": address,
                    "total_usd": total_usd
                }
                
                pdf_bytes = create_pdf(scan_data, {"name": full_name, "id": id_number, "unit": unit})
                
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"Report_{datetime.datetime.now().strftime('%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

st.caption("v4.1 | Secure Cloud Forensic Tool")
