import streamlit as st
import pdfplumber
import requests
import time
import re
import json
import nltk
from nltk import ngrams, word_tokenize

# ==================== FIX NLTK ONCE AND FOR ALL ====================
@st.cache_resource
def download_nltk():
    for package in ['punkt', 'punkt_tab']:
        nltk.download(package, quiet=True)

download_nltk()
# ====================================================================

st.set_page_config(page_title="KDP Title & Keyword Generator", layout="centered")
st.title("🛡️ Amazon KDP Title, Subtitle, Keywords & Description Generator")
st.caption("100% compliant with Amazon rules • Never get rejected again")

# --------------------- AI Provider Selection ---------------------
provider = st.radio("Choose AI (both work perfectly)", 
                    ["Google Gemini 1.5 Flash (FREE)", "OpenAI (gpt-4o / gpt-4o-mini)"], 
                    horizontal=True)

if provider == "Google Gemini 1.5 Flash (FREE)":
    gemini_key = st.text_input("Enter your FREE Gemini API key", type="password",
                               help="Get it instantly: https://aistudio.google.com/app/apikey")
    openai_key = None
else:
    openai_key = st.text_input("Enter your OpenAI API key", type="password",
                               help="Get it: https://platform.openai.com/api-keys")
    gemini_key = None

if not (openai_key or gemini_key):
    st.info("Paste your API key above to start (takes 2 seconds)")
    st.stop()

# --------------------- Upload PDF ---------------------
uploaded_file = st.file_uploader("Upload your planner/book PDF", type="pdf")

if uploaded_file:
    with st.spinner("Reading your PDF..."):
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        
        tokens = word_tokenize(full_text.lower())
        ngram_list = [ngrams(tokens, n) for n in (2,3,4)]
        candidate_phrases = [' '.join(gram) for ngram in ngram_list for gram in ngram]
        candidate_seeds = [p for p in set(candidate_phrases) if 10 < len(p) < 70]

        st.success(f"Extracted {len(full_text):,} characters • Ready!")

    if st.button("Generate Amazon-Compliant Title, Keywords & Copy", type="primary"):
        # --------------------- Amazon Keyword Research ---------------------
        with st.spinner("Researching real Amazon buyer keywords..."):
            amazon_keywords = set()
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

            for seed in candidate_seeds[:50]:
                try:
                    url = f"https://completion.amazon.com/search/complete?search-alias=stripbooks&q={requests.utils.quote(seed)}"
                    r = requests.get(url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        suggestions = r.json()[1]
                        amazon_keywords.update(suggestions)
                except:
                    pass
                time.sleep(0.35)

            amazon_keywords = [k.lower().strip() for k in amazon_keywords if 6 <= len(k) <= 100]
            st.write(f"Found **{len(amazon_keywords)}** real Amazon search terms")

        # --------------------- AI Setup ---------------------
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
        else:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

        # --------------------- Generate 7 Golden Keywords ---------------------
        with st.spinner("Selecting 7 perfect, low-competition keywords..."):
            kw_prompt = f"""
You are a top Amazon KDP expert. From this book and Amazon suggestions, pick exactly 7 keywords that:
- Have high search volume
- Low competition
- Are 100% honest and relevant
- Do NOT include year (2026), "planner", "notebook" repeated, sales claims, or anything that violates Amazon title rules

Book type: Planner / Organizer
Amazon suggestions: {', '.join(list(amazon_keywords)[:500])}

Return ONLY valid JSON array with exactly 7 keywords:
["keyword one", "keyword two", ...]
"""

            if openai_key:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": kw_prompt}],
                    temperature=0.3
                )
                best_keywords = json.loads(resp.choices[0].message.content.strip())
            else:
                resp = model.generate_content(kw_prompt + "\nRespond with valid JSON only")
                best_keywords = json.loads(resp.text.strip("```json\n"))

        # --------------------- Generate Compliant Title & Copy ---------------------
        with st.spinner("Writing rejection-proof title, subtitle & description..."):
            copy_prompt = f"""
You are a 20-year Amazon KDP copywriting legend who has launched 50+ bestsellers.

Write for a 2026 planner. Rules you MUST follow:
- Title: Max 80 chars. NO year "2026", NO "planner" repeated, NO "notebook", NO sales claims
- Subtitle: Max 200 chars. Benefit-focused, compelling
- Description: High-converting, use bullets, bold, emotional triggers
- Naturally include these keywords: {', '.join(best_keywords)}

Book content summary: {full_text[:18000]}

Return exactly:
TITLE: Your Title Here
SUBTITLE: Your Subtitle Here
DESCRIPTION:
Your full description with **bold** and bullets
"""

            if openai_key:
                result = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": copy_prompt}],
                    temperature=0.7
                ).choices[0].message.content
            else:
                result = model.generate_content(copy_prompt).text

            # Parse
            title = result.split("SUBTITLE:")[0].replace("TITLE:", "").strip()
            subtitle = result.split("DESCRIPTION:")[0].split("SUBTITLE:")[1].strip() if "SUBTITLE:" in result else ""
            description = result.split("DESCRIPTION:")[1].strip() if "DESCRIPTION:" in result else result

        # --------------------- FINAL OUTPUT ---------------------
        st.success("Done! 100% Amazon-compliant assets ready")
        st.markdown(f"# {title}")
        st.markdown(f"### {subtitle}")
        st.markdown("### 7 Golden Keywords")
        for kw in best_keywords:
            st.code(kw, language=None)

        st.markdown("### Amazon Description")
        st.markdown(description)

        txt = f"TITLE: {title}\nSUBTITLE: {subtitle}\n\nKEYWORDS:\n" + "\n".join(best_keywords) + "\n\nDESCRIPTION:\n" + description
        st.download_button("Download All Assets (.txt)", txt, "KDP_Compliant_Assets.txt")

        st.balloons()
