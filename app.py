import streamlit as st
import pdfplumber
import requests
import time
import re
from bs4 import BeautifulSoup
import json
import nltk

# ==== FIX NLTK DOWNLOAD ISSUE ====
@st.cache_resource
def download_nltk_data():
    nltk.download('punkt_tab', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)

download_nltk_data()  # This runs once and fixes the error forever

from nltk import word_tokenize, ngrams

# ====================== CONFIG ======================
st.set_page_config(page_title="KDP Keyword + Copy Generator", layout="centered")
st.title("🚀 Ultimate Amazon KDP Keyword & Copy Generator")
st.caption("Works with OpenAI (gpt-4o-mini) or Google Gemini 1.5 Flash (completely free)")

# ------------------ API KEY INPUT (user can paste their own) ------------------
api_provider = st.radio("Choose AI provider", ["OpenAI (gpt-4o-mini)", "Google Gemini 1.5 Flash (FREE)"], horizontal=True)

if api_provider == "OpenAI (gpt-4o-mini)":
    openai_key = st.text_input("Enter your OpenAI API key", type="password", help="Get it free at https://platform.openai.com/api-keys")
    gemini_key = None
else:
    gemini_key = st.text_input("Enter your Google Gemini API key (FREE)", type="password", help="Get it instantly at https://aistudio.google.com/app/apikey")
    openai_key = None

if not (openai_key or gemini_key):
    st.info("👆 Paste your API key above to continue (takes 2 seconds)")
    st.stop()

# ------------------ File upload ------------------
uploaded_file = st.file_uploader("Upload your book, planner, journal or ebook (PDF only)", type="pdf")

if uploaded_file:
    with st.spinner("Reading your manuscript..."):
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        words = re.findall(r'\b[a-zA-Z]+\b', full_text.lower())
        st.success(f"✅ Extracted {len(full_text):,} characters • {len(words):,} words")

        # Generate candidate seed phrases
        tokens = word_tokenize(full_text.lower())
        bigrams = [' '.join(g) for g in ngrams(tokens, 2)]
        trigrams = [' '.join(g) for g in ngrams(tokens, 3)]
        fourgrams = [' '.join(g) for g in ngrams(tokens, 4)]
        candidate_seeds = [phrase for phrase in set(bigrams + trigrams + fourgrams) 
                          if 8 < len(phrase) < 60 and phrase.count(' ') <= 3]

    if st.button("🔥 Start Deep Amazon Research + Generate Copy (2–4 minutes)", type="primary"):
        with st.spinner("Scraping Amazon autocomplete for real buyer keywords..."):
            amazon_keywords = set()
            HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

            for seed in candidate_seeds[:45]:
                try:
                    url = f"https://completion.amazon.com/search/complete?search-alias=stripbooks&mkt=1&q={requests.utils.quote(seed)}"
                    r = requests.get(url, headers=HEADERS, timeout=10)
                    if r.status_code == 200:
                        suggestions = r.json()[1]
                        amazon_keywords.update(suggestions)
                except:
                    pass
                time.sleep(0.4)

            amazon_keywords = [k.lower().strip() for k in amazon_keywords if 5 <= len(k) <= 100]
            st.write(f"Found **{len(amazon_keywords)}** real Amazon search suggestions")

        # ------------------ Use selected AI ------------------
        with st.spinner("Selecting the 7 absolute best keywords (high search + low competition)..."):
            if openai_key:
                import openai
                openai.api_key = openai_key
                client_type = "openai"
            else:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                client_type = "gemini"

            prompt_keywords = f"""
You are a 15-year Amazon KDP millionaire expert.
From this book and the Amazon autocomplete suggestions below, choose exactly 7 keywords that have:
• Very high monthly search volume
• Very low competition (<100 exact-match books ideal)
• 100% relevant and not misleading
• Mix of broad + long-tail

Book content sample: {full_text[:14000]}

Amazon suggestions: {", ".join(list(amazon_keywords)[:600])}

Return ONLY a valid JSON array with exactly 7 keywords:
["keyword one", "keyword two", ...]
"""

            if client_type == "openai":
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt_keywords}],
                    temperature=0.2
                )
                best_keywords = json.loads(response.choices[0].message.content.strip())
            else:
                response = model.generate_content(prompt_keywords + "\n\nRespond with valid JSON only.")
                best_keywords = json.loads(response.text.strip("` \njson"))

            if not isinstance(best_keywords, list) or len(best_keywords) != 7:
                best_keywords = best_keywords[:7] if isinstance(best_keywords, list) else ["error"] * 7

        with st.spinner("Writing #1 bestselling title, subtitle & description (20-year copywriter level)..."):
            copy_prompt = f"""
You are a legendary Amazon copywriter who has written dozens of #1 bestsellers.
Write:
1. Magnetic main title (max 80 chars)
2. Benefit-packed subtitle (max 200 chars)
3. High-converting Amazon description (bullet points, bold, emotional, social proof)

Use these 7 keywords naturally: {", ".join(best_keywords)}

Book content: {full_text[:16000]}

Return exactly in this format:
TITLE: ...
SUBTITLE: ...
DESCRIPTION:
...
"""

            if client_type == "openai":
                copy = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": copy_prompt}],
                    temperature=0.7
                ).choices[0].message.content
            else:
                copy = model.generate_content(copy_prompt).text

            # Parse result
            title = copy.split("SUBTITLE:")[0].replace("TITLE:", "").strip()
            subtitle = copy.split("DESCRIPTION:")[0].split("SUBTITLE:")[1].strip() if "SUBTITLE:" in copy else ""
            description = copy.split("DESCRIPTION:")[1].strip() if "DESCRIPTION:" in copy else copy

        # ------------------ FINAL RESULTS ------------------
        st.success("🎉 Your Amazon-ready assets are ready!")
        st.markdown(f"# {title}")
        st.markdown(f"### {subtitle}")
        st.markdown("### 7 Golden Keywords")
        for kw in best_keywords:
            st.code(kw)

        st.markdown("### Amazon Description (copy-paste ready)")
        st.markdown(description.replace("**", "**") if "**" in description else description)

        txt = f"TITLE: {title}\nSUBTITLE: {subtitle}\n\nKEYWORDS:\n" + "\n".join(best_keywords) + "\n\nDESCRIPTION:\n" + description
        st.download_button("📥 Download everything as .txt", txt, "KDP_Assets.txt", "text/plain")
