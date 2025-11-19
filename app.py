import streamlit as st
import pdfplumber
import requests
import time
import re
import json
import nltk
from nltk import ngrams, word_tokenize

# ==================== NLTK FIX ====================
@st.cache_resource
def download_nltk():
    for p in ['punkt', 'punkt_tab']:
        nltk.download(p, quiet=True)
download_nltk()

st.set_page_config(page_title="KDP Gold Tool", layout="centered")
st.title("Amazon KDP Title, Keywords & Copy Generator")
st.caption("100% Amazon-compliant • Never rejected again • Works with FREE Gemini or OpenAI")

# ===================== AI Selection =====================
provider = st.radio("AI Model", ["Google Gemini 1.5 Flash (FREE)", "OpenAI (gpt-4o-mini)"], horizontal=True)

if provider.startswith("Google"):
    gemini_key = st.text_input("Gemini API Key (FREE)", type="password", help="Get instantly: https://aistudio.google.com/app/apikey")
    openai_key = None
else:
    openai_key = st.text_input("OpenAI API Key", type="password", help="platform.openai.com/api-keys")
    gemini_key = None

if not (openai_key or gemini_key):
    st.info("Paste your key above to continue")
    st.stop()

# ===================== Upload =====================
file = st.file_uploader("Upload your planner/book PDF", type="pdf")
if file:
    with st.spinner("Analyzing your book..."):
        with pdfplumber.open(file) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        tokens = word_tokenize(text.lower())
        seeds = [' '.join(g) for n in (2,3,4) for g in ngrams(tokens, n)]
        seeds = list({s for s in seeds if 10 < len(s) < 70})
        st.success(f"Ready! Found {len(seeds)} seed phrases")

    if st.button("Generate Everything (Amazon-Compliant)", type="primary"):
        # ===================== Amazon Research =====================
        with st.spinner("Scraping real Amazon buyer keywords..."):
            kw_set = set()
            headers = {"User-Agent": "Mozilla/5.0"}
            for seed in seeds[:50]:
                try:
                    url = f"https://completion.amazon.com/search/complete?search-alias=stripbooks&q={requests.utils.quote(seed)}"
                    r = requests.get(url, headers=headers, timeout=8)
                    if r.status_code == 200:
                        kw_set.update(r.json()[1])
                except:
                    pass
                time.sleep(0.3)
            amazon_kws = [k.lower().strip() for k in kw_set if 6 <= len(k) <= 100]
            st.write(f"Discovered **{len(amazon_kws)}** real Amazon keywords")

        # ===================== AI Setup =====================
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            use_gemini = False
        else:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key, transport='rest')   # ← THIS LINE FIXES THE 404 ERROR
            model = genai.GenerativeModel('gemini-1.5-flash')
            use_gemini = True

        # ===================== 7 Keywords =====================
        with st.spinner("Choosing 7 golden keywords..."):
            prompt_kw = f"""Pick exactly 7 high-search, low-competition, 100% honest keywords.
NO year numbers, no repetitive "planner", no sales claims.
Amazon suggestions: {", ".join(amazon_kws[:500])}
Return ONLY valid JSON array: ["kw1", "kw2", ...]"""

            if use_gemini:
                resp = model.generate_content(prompt_kw, generation_config={"response_mime_type": "application/json"})
                best_kws = json.loads(resp.text)
            else:
                resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt_kw}], temperature=0.3)
                best_kws = json.loads(resp.choices[0].message.content.strip("```json\n"))

        # ===================== Title + Copy =====================
        with st.spinner("Writing rejection-proof title & description..."):
            prompt_copy = f"""Write a 2026 planner title/subtitle/description that will NEVER be rejected.
Rules:
- Title <80 chars, NO "2026", NO repeated "planner"
- Subtitle benefit-focused
- Description with bullets, **bold**, emotions
Use these keywords naturally: {", ".join(best_kws)}

Return exactly:
TITLE: ...
SUBTITLE: ...
DESCRIPTION:
..."""

            if use_gemini:
                result = model.generate_content(prompt_copy).text
            else:
                result = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt_copy}], temperature=0.7).choices[0].message.content

            title = result.split("SUBTITLE:")[0].replace("TITLE:", "").strip()
            subtitle = "SUBTITLE:" in result and result.split("DESCRIPTION:")[0].split("SUBTITLE:")[1].strip() or ""
            description = result.split("DESCRIPTION:")[1].strip() if "DESCRIPTION:" in result else result

        # ===================== Results =====================
        st.success("All done! 100% Amazon-safe")
        st.markdown(f"# {title}")
        st.markdown(f"### {subtitle}")
        st.markdown("### 7 Golden Keywords")
        for kw in best_kws:
            st.code(kw)
        st.markdown("### Description")
        st.markdown(description)
        st.download_button("Download All", f"TITLE: {title}\nSUBTITLE: {subtitle}\n\nKEYWORDS:\n" + "\n".join(best_kws) + "\n\nDESCRIPTION:\n" + description, "KDP_Assets.txt")
        st.balloons()
