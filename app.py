import streamlit as st
import os
import sys
import json
import pandas as pd
from PIL import Image
import numpy as np
import cv2
import pypdfium2 as pdfium
import io

# --- Page Config MUST be the first Streamlit command ---
st.set_page_config(page_title="Scan & Extract", layout="centered", page_icon="📄")

# Disable the model source check to speed up initialization
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #ffffff; }
    h1 { font-weight: 600; color: #111827; text-align: center; margin-bottom: 0.5rem !important; }
    .subtitle { color: #6B7280; text-align: center; font-size: 1.1rem; margin-bottom: 3rem; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stAppToolbar"] {display: none;}
    div[data-testid="stStatusWidget"] { display: none !important; }
    .stStatusWidget { display: none !important; }
    div[role="dialog"] { display: none !important; }
    .stConnectionError { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- Engine ---
@st.cache_resource(show_spinner=False)
def load_engine():
    try:
        from paddleocr import PPStructureV3
        engine = PPStructureV3(enable_mkldnn=False)
        return engine, None
    except Exception as e:
        return None, str(e)

# Initialize Engine
if 'engine' not in st.session_state:
    st.session_state.engine = None

if st.session_state.engine is None:
    with st.status("Warming up the scanner... this usually takes a few minutes", expanded=False) as status:
        engine, err = load_engine()
        if engine:
            st.session_state.engine = engine
            status.update(label="Scanner ready!", state="complete", expanded=False)
        else:
            status.update(label="Initialization failed", state="error")
            st.error(f"Scanner error: {err}")
            st.stop()

engine = st.session_state.engine

# --- UI Header ---
st.markdown("<h1>Scan & Extract</h1>", unsafe_allow_html=True)
st.markdown('<p class="subtitle">Upload any document or image to extract text, tables, and formulas instantly.</p>', unsafe_allow_html=True)

# --- Logic ---
uploaded_file = st.file_uploader("Upload document", type=['png', 'jpg', 'jpeg', 'pdf'], label_visibility="collapsed")

if uploaded_file:
    # Use session state to store results so toggles don't re-run the heavy OCR
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    
    if "last_file_id" not in st.session_state or st.session_state.last_file_id != file_id:
        st.session_state.results = None
        st.session_state.source_image = None
        st.session_state.last_file_id = file_id

    if st.session_state.results is None:
        with st.spinner("Processing... this may take a few minutes"):
            try:
                file_bytes = uploaded_file.read()
                file_type = uploaded_file.type
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
                raw_results = engine.predict(img_array)
                
                st.session_state.results = raw_results
                st.session_state.source_image = image
            except Exception as e:
                st.error(f"Error during processing: {e}")
                st.stop()

    # --- Display Results ---
    results = st.session_state.results
    source_image = st.session_state.source_image

    if results and len(results) > 0:
        page_res = results[0]
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

        # JSON Toggle - Uses session state, so it's instant
        if st.toggle("Show JSON Output"):
            st.json(page_res)
    else:
        st.error("Could not extract any data from this document.")
else:
    st.info("Supported formats: PNG, JPG, PDF")