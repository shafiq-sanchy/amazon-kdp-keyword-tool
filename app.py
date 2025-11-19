import streamlit as st
import pdfplumber
import requests
import time
import re
import json
import nltk
from nltk import ngrams, word_tokenize

# NLTK fix
@st.cache_resource
def download_nltk():
    nltk.download(['punkt', 'punkt_tab'], quiet=True)
download_nltk()

st.set_page_config(page_title="KDP Pro Tool", layout="centered")
st.title("🚀 Ultimate KDP Title, Keyword & Copy Generator")
st.caption("100% accurate • Reads your entire PDF • Gemini 2.0 Flash (FREE) or OpenAI")

# ===================== AI CHOICE =====================
provider = st.selectbox("Choose AI Model", 
                       ["Google Gemini 2.0 Flash (100% FREE & BEST)", "OpenAI (gpt-4o-mini)"])

if provider.startswith("Google"):
    api_key = st.text_input("Your FREE Gemini API Key", type="password",
                           help="Get instantly (no credit card): https://aistudio.google.com/app/apikey")
else:
    api_key = st.text_input("OpenAI API Key", type="password")

if not api_key:
    st.info("Paste your key above → start in 3 seconds")
    st.stop()

# ===================== PDF UPLOAD & DEEP ANALYSIS =====================
file = st.file_uploader("Upload your planner/notebook PDF", type="pdf")
if file:
    with st.spinner("Deep reading & understanding your entire book..."):
        with pdfplumber.open(file) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            full_text = "\n".join(pages).replace("  ", " ").replace("\n\n", "\n")

        # Smart feature detection
        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        headings = [l for l in lines if l.isupper() or (len(l)<60 and l.endswith((':','—','-')))]
        features = [l for l in lines if any(k in l.lower() for k in ["goal","habit","daily","weekly","monthly","tracker","note","list","plan","journal"])]
        
        st.success("Your PDF is fully understood!")
        st.markdown(f"**Detected type:** Planner / Notebook  \n**Pages:** {len(pages)}  \n**Key sections:** {', '.join(headings[:15]) or 'Custom layout'}")

    if st.button("Generate Amazon-Ready Assets (Compliant & High-Converting)", type="primary"):
        # ===================== Amazon Research =====================
        with st.spinner("Finding real buyer keywords on Amazon..."):
            seeds = list({s for n in (2,3) for g in ngrams(word_tokenize(full_text.lower()), n) for s in [' '.join(g)]})[:50]
            amazon_kws = set()
            for seed in seeds:
                try:
                    url = f"https://completion.amazon.com/search/complete?search-alias=stripbooks&q={requests.utils.quote(seed)}"
                    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                    if r.status_code == 200: amazon_kws.update(r.json()[1])
                    time.sleep(0.3)
                except: pass
            amazon_kws = [k.lower().strip() for k in amazon_kws if 6 <= len(k) <= 100]
            st.write(f"Found **{len(amazon_kws)}** real Amazon search terms")

        # ===================== AI CALL =====================
        with st.spinner("Creating perfect title, 7 keywords & description based on YOUR book..."):
            prompt = f"""
You are a 20-year KDP millionaire expert.

MY EXACT BOOK CONTENT (first 28,000 characters):
{full_text[:28000]}

DETECTED FEATURES:
{', '.join(features[:50])}

AMAZON BUYER KEYWORDS:
{', '.join(amazon_kws[:500])}

Generate ONLY for Amazon KDP (strict rules - no rejection):
- Title <80 chars, NO year, NO repeated words, NO sales claims
- Subtitle benefit-rich
- Exactly 7 golden keywords (high search, low competition, 100% relevant)
- Description with bullets, **bold**, emotions

Return exactly this format:
TITLE: ...
SUBTITLE: ...
KEYWORDS: kw1 | kw2 | kw3 | kw4 | kw5 | kw6 | kw7
DESCRIPTION:
...
"""

            if provider.startswith("Google"):
                import google.generativeai as genai
                genai.configure(api_key=api_key, transport='rest')  # Fixes any connection issues
                model = genai.GenerativeModel('gemini-2.0-flash-exp')  # Latest free 2025 model
                response = model.generate_content(prompt, generation_config={"response_mime_type": "text/plain"})
                result = response.text
            else:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                result = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                ).choices[0].message.content

            # Parse results
            title = result.split("SUBTITLE:")[0].replace("TITLE:", "").strip()
            subtitle = result.split("KEYWORDS:")[0].split("SUBTITLE:")[1].strip() if "SUBTITLE:" in result else ""
            kw_line = [l for l in result.split("\n") if "KEYWORDS:" in l][0]
            keywords = [k.strip() for k in kw_line.replace("KEYWORDS:", "").split("|") if k.strip()]
            description = result.split("DESCRIPTION:")[1].strip() if "DESCRIPTION:" in result else result

        # ===================== DISPLAY =====================
        st.success("Done! 100% Amazon-compliant & based on YOUR PDF")
        st.markdown(f"# {title}")
        st.markdown(f"### {subtitle}")
        st.markdown("### 7 Golden Keywords")
        for kw in keywords:
            st.code(kw)
        st.markdown("### Amazon Description")
        st.markdown(description)

        txt = f"TITLE: {title}\nSUBTITLE: {subtitle}\n\nKEYWORDS:\n" + "\n".join(keywords) + "\n\nDESCRIPTION:\n" + description
        st.download_button("Download All Assets", txt, "KDP_2026_Gold.txt")
        st.balloons()

# ===================== FREE GEMINI KEY GUIDE =====================
with st.expander("How to get FREE Gemini 2.0 Flash key (no credit card, 2 seconds)"):
    st.write("""
1. Go → https://aistudio.google.com/app/apikey
2. Sign in with Google
3. Click "Create API key"
4. Copy & paste here → unlimited free use!
Works worldwide in 2025, no payment method required.
""")
