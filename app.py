import streamlit as st
import os
import sys
import json
import pandas as pd
from PIL import Image
import numpy as np
import cv2
import pypdfium2 as pdfium  # For PDF handling

# --- Page Config MUST be the first Streamlit command ---
st.set_page_config(page_title="Scan & Extract", layout="centered", page_icon="📄")

# Disable the model source check to speed up initialization
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# Import PaddleOCR
try:
    from paddleocr import PPStructureV3
except ImportError:
    st.error("PaddleOCR is not installed. Please install it with `pip install paddleocr`.")

# --- Helper Functions ---

@st.cache_resource(show_spinner=False)
def load_engine():
    """
    Loads the engine in the background.
    """
    print("ENGINE: Starting initialization...")
    sys.stdout.flush()
    try:
        # Disable mkldnn for stability
        engine = PPStructureV3(enable_mkldnn=False)
        print("ENGINE: Initialization successful.")
        sys.stdout.flush()
        return engine
    except Exception as e:
        print(f"CRITICAL ENGINE ERROR: {e}")
        sys.stdout.flush()
        return None

@st.cache_data(show_spinner=False)
def process_image_cached(file_bytes, file_type):
    """
    Cached version of the processing logic. 
    Takes bytes and type to ensure cacheability.
    """
    engine = load_engine()
    if not engine:
        return None, None

    try:
        import io
        file_obj = io.BytesIO(file_bytes)
        
        image = None
        if file_type == "application/pdf":
            pdf = pdfium.PdfDocument(file_obj)
            page = pdf[0]
            bitmap = page.render(scale=2)
            image = bitmap.to_pil()
        else:
            image = Image.open(file_obj).convert('RGB')
            
        img_array = np.array(image)
        results = engine.predict(img_array)
        return results, image
    except Exception as e:
        print(f"PROCESSING ERROR: {e}")
        sys.stdout.flush()
        return None, None

# --- Main UI ---

# --- Minimalist CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main {
        background-color: #ffffff;
    }
    h1 {
        font-weight: 600;
        color: #111827;
        text-align: center;
        margin-bottom: 0.5rem !important;
    }
    .subtitle {
        color: #6B7280;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 3rem;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stAppToolbar"] {display: none;}
    
    /* Hide technical connection messages and modals */
    div[data-testid="stStatusWidget"] { display: none !important; }
    .stStatusWidget { display: none !important; }
    div[role="dialog"] { display: none !important; }
    .stConnectionError { display: none !important; }
    
    </style>
    """, unsafe_allow_html=True)

# --- Header ---
# Initialize
engine = load_engine()

if engine is None:
    # On first load, it might take a while. Show a status.
    with st.status("Warming up the scanner... this usually takes a few minutes", expanded=False) as status:
        engine = load_engine()
        if engine:
            status.update(label="Scanner ready!", state="complete", expanded=False)
        else:
            status.update(label="Oops, something went wrong.", state="error")
            st.error("The scanner is currently unavailable. Please try again in a moment.")
            st.stop()

st.markdown("<h1>Scan & Extract</h1>", unsafe_allow_html=True)
st.markdown('<p class="subtitle">Upload any document or image to extract text, tables, and formulas instantly.</p>', unsafe_allow_html=True)

# --- Upload Area ---
uploaded_file = st.file_uploader("Upload document", type=['png', 'jpg', 'jpeg', 'pdf'], label_visibility="collapsed")

if uploaded_file is not None:
    st.write("---")
    
    # Read file once for caching
    file_bytes = uploaded_file.read()
    file_type = uploaded_file.type
    
    with st.spinner("Processing..."):
        results, source_image = process_image_cached(file_bytes, file_type)
        
        if results and len(results) > 0:
            page_res = results[0]
            
            # Display Image First
            st.image(source_image, use_container_width=True, caption="Original Document")
            
            st.markdown("### Results")
            
            # 1. Tables
            table_list = page_res.get('table_res_list', [])
            if table_list:
                for tidx, table in enumerate(table_list):
                    html_table = table.get('pred_html')
                    if html_table:
                        st.markdown(f"**Table {tidx+1}**")
                        st.markdown(html_table, unsafe_allow_html=True)
                        try:
                            df = pd.read_html(html_table)[0]
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(f"Download Table {tidx+1} (CSV)", csv, f"table_{tidx+1}.csv", "text/csv", key=f"dl_{tidx}")
                        except: pass

            # 2. Formulas
            formula_list = page_res.get('formula_res_list', [])
            if formula_list:
                for formula in formula_list:
                    latex = formula.get('rec_formula')
                    if latex:
                        st.latex(latex)
            
            # 3. Text
            parsing_list = page_res.get('parsing_res_list', [])
            if parsing_list:
                full_text = []
                for block in parsing_list:
                    block_str = str(block)
                    if "label:\ttable" in block_str or "label:\tformula" in block_str:
                        continue
                    if "content:\t" in block_str:
                        content = block_str.split("content:\t")[1].split("#################")[0].strip()
                        if content: full_text.append(content)
                
                if full_text:
                    st.markdown("**Extracted Text**")
                    st.text_area("", value="\n\n".join(full_text), height=300)

            # Technical data toggle - Now uses cached data so it's instant
            if st.toggle("Show JSON Output"):
                st.json(page_res)
        else:
            st.error("Could not read this document.")
else:
    # Minimal help text
    st.info("Supported formats: PNG, JPG, PDF")
