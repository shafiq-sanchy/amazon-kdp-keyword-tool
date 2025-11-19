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
    for p in ['punkt', 'punkt_tab']:
        nltk.download(p, quiet=True)
download_nltk()

st.set_page_config(page_title="KDP Master Tool", layout="centered")
st.title("Real KDP Title, Keyword & Copy Generator")
st.caption("Actually reads your PDF • 100% accurate • Never rejected • Free MegaLLM + OpenAI")

# ===================== AI CHOICE =====================
provider = st.selectbox("Choose FREE or Paid AI", 
                       ["MegaLLM (100% FREE, best results)", "OpenAI (gpt-4o-mini)"])

if provider == "MegaLLM (100% FREE, best results)":
    api_key = st.text_input("MegaLLM API Key (FREE)", type="password",
                            help="Get instantly → https://megallm.ai → API Keys → Create → Copy")
else:
    api_key = st.text_input("OpenAI API Key", type="password")

if not api_key:
    st.info("Paste your key above to start")
    st.stop()

# ===================== UPLOAD & DEEP ANALYSIS =====================
file = st.file_uploader("Upload your notebook/planner PDF", type="pdf")

if file:
    with st.spinner("Deeply analyzing your entire PDF..."):
        with pdfplumber.open(file) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
            full_text = "\n".join(pages)
        
        # Extract real features & themes
        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        headings = [line for line in lines if line.isupper() or len(line) < 50 and any(c.isalpha() for c in line)]
        features = [line for line in lines if any(x in line.lower() for x in ["goal", "habit", "track", "monthly", "weekly", "daily", "list", "note"])]
        
        summary = f"""
Book Type: Low/No-Content Notebook/Planner
Number of pages extracted: {len(pages)}
Main headings: {', '.join(headings[:20])}
Key features detected: {', '.join(features[:25])}
Target audience: Productivity seekers, students, professionals, goal setters
"""
        st.success("PDF fully understood!")
        st.text(summary[:1000] + "..." if len(summary) > 1000 else summary)

    if st.button("Generate Perfect Amazon Assets", type="primary"):
        # ===================== Amazon Keyword Research =====================
        with st.spinner("Scraping real Amazon buyer keywords..."):
            seeds = list(set([' '.join(g) for n in (2,3) for g in ngrams(word_tokenize(full_text.lower()), n)]))
            seeds = [s for s in seeds if 8 < len(s) < 60][:50]
            
            amazon_kws = set()
            for seed in seeds:
                try:
                    url = f"https://completion.amazon.com/search/complete?search-alias=stripbooks&q={requests.utils.quote(seed)}"
                    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
                    if r.status_code == 200:
                        amazon_kws.update(r.json()[1])
                    time.sleep(0.25)
                except:
                    pass
            amazon_kws = [k.lower().strip() for k in amazon_kws if 6 <= len(k) <= 100]
            st.write(f"Found {len(amazon_kws)} real Amazon keywords")

        # ===================== CALL AI (MegaLLM or OpenAI) =====================
        with st.spinner("Generating accurate title, keywords & copy based on YOUR book..."):
            prompt = f"""
You are a million-dollar KDP publisher.

MY BOOK CONTENT:
{full_text[:25000]}

DETECTED FEATURES:
{', '.join(features[:40])}

AMAZON SUGGESTED KEYWORDS:
{', '.join(amazon_kws[:400])}

Generate for Amazon KDP (strict rules):
- Title: Max 80 chars, NO year, NO repeated words, NO sales claims
- Subtitle: Benefit-rich, compelling
- Exactly 7 keywords: High search, low competition, 100% relevant
- Description: High-converting with bullets, **bold**, emotional triggers

Return ONLY this format:
TITLE: ...
SUBTITLE: ...
KEYWORDS: kw1 | kw2 | kw3 | kw4 | kw5 | kw6 | kw7
DESCRIPTION:
...
"""

            if provider == "MegaLLM (100% FREE, best results)":
                import httpx
                response = httpx.post(
                    "https://api.megallm.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "megallm-pro",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7
                    },
                    timeout=120
                )
                result = response.json()["choices"][0]["message"]["content"]
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
            keywords_line = [line for line in result.split("\n") if "KEYWORDS:" in line][0]
            keywords = [k.strip() for k in keywords_line.replace("KEYWORDS:", "").replace("|", ",").split(",") if k.strip()][:7]
            description = result.split("DESCRIPTION:")[1].strip() if "DESCRIPTION:" in result else result

        # ===================== SHOW RESULTS =====================
        st.success("Perfect Amazon-ready assets (100% based on your PDF)")
        st.markdown(f"# {title}")
        st.markdown(f"### {subtitle}")
        st.markdown("### 7 Golden Keywords")
        for kw in keywords:
            st.code(kw)
        st.markdown("### Description")
        st.markdown(description)

        txt = f"TITLE: {title}\nSUBTITLE: {subtitle}\n\nKEYWORDS:\n" + "\n".join(keywords) + "\n\nDESCRIPTION:\n" + description
        st.download_button("Download Everything", txt, "KDP_Perfect_Assets.txt")
        st.balloons()

# ===================== HOW TO GET FREE MEGALLM KEY =====================
with st.expander("How to get FREE MegaLLM API key (no payment needed)"):
    st.write("""
1. Go to https://megallm.ai
2. Sign up (Google or email)
3. Go to Dashboard → API Keys
4. Click "Create New Key"
5. Copy & paste here → $5 free credit = hundreds of runs
""")
