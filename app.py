import streamlit as st
import pdfplumber
import requests
import time
import re
from bs4 import BeautifulSoup
import openai
from collections import Counter
import json

# ==== CONFIG ====
openai.api_key = st.secrets["OPENAI_API_KEY"]  # We will set this secretly later

# Amazon headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

# ======================
st.set_page_config(page_title="KDP Keyword Goldminer", layout="centered")
st.title("🚀 Amazon KDP Keyword + Copy Generator")
st.caption("Upload your book PDF → Get perfect title, subtitle, description & 7 golden keywords (high search, low competition)")

uploaded_file = st.file_uploader("Upload your book, planner, journal or ebook (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Reading and analyzing your manuscript..."):
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
        
        # Clean and extract words
        words = re.findall(r'\b[a-zA-Z]+\b', full_text.lower())
        word_count = len(words)
        st.success(f"Extracted {len(full_text):,} characters and {word_count:,} words")

        # Get most common meaningful phrases (2-4 words)
        from nltk import ngrams, word_tokenize
        import nltk
        nltk.download('punkt', quiet=True)
        tokens = word_tokenize(full_text.lower())
        bigrams = [' '.join(gram) for gram in ngrams(tokens, 2)]
        trigrams = [' '.join(gram) for gram in ngrams(tokens, 3)]
        fourgrams = [' '.join(gram) for gram in ngrams(tokens, 4)]
        
        candidate_seeds = [w for w in set(bigrams + trigrams + fourgrams) if len(w) > 8 and len(w.split()) <= 4]

    if st.button("🔥 Start Deep Amazon Research (takes 2-4 minutes)", type="primary"):
        with st.spinner("Researching Amazon autocomplete for hundreds of real keywords..."):
            amazon_keywords = set()
            
            # Try many seed keywords from your book
            for seed in candidate_seeds[:40]:  # top 40 seeds
                try:
                    url = f"https://www.amazon.com/s?k={seed.replace(' ', '+')}"
                    r = requests.get(url, headers=HEADERS, timeout=10)
                    soup = BeautifulSoup(r.text, 'html.parser')
                    
                    # Amazon autocomplete via completion.amazon.com (real-time)
                    completion_url = "https://completion.amazon.com/search/complete"
                    params = {
                        "search-alias": "stripbooks",
                        "client": "amazon-search-ui",
                        "q": seed
                    }
                    resp = requests.get(completion_url, params=params, headers=HEADERS, timeout=10)
                    if resp.status_code == 200:
                        suggestions = resp.json()[1]
                        amazon_keywords.update(suggestions)
                except:
                    continue
                time.sleep(0.5)  # Be gentle
                
            amazon_keywords = [k.lower() for k in amazon_keywords if 5 <= len(k) <= 100]
            st.write(f"Found {len(amazon_keywords):,} real Amazon keywords")

        with st.spinner("Finding the 7 golden keywords (high search + low competition)..."):
            # Use OpenAI to rank keywords intelligently
            prompt = f"""
You are a 15-year Amazon KDP expert. From this book content and the list of Amazon-suggested keywords below,
select exactly 7 keywords that have:
- Very high search volume on Amazon
- Very low competition (ideally <50 competing books with that exact phrase in title)
- 100% honest and relevant to the book
- Mix of broad and long-tail

Book is about: {full_text[:12000]}...

Amazon suggested keywords:
{', '.join(list(amazon_keywords)[:500])}

Return ONLY a JSON array of exactly 7 keywords, no explanation:
["keyword one", "keyword two", ...]
"""
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            try:
                best_keywords = json.loads(response.choices[0].message.content.strip())
            except:
                best_keywords = response.choices[0].message.content.strip("[]").replace('"', '').split(",")
                best_keywords = [k.strip() for k in best_keywords][:7]

        with st.spinner("Writing world-class title, subtitle & description by a 20-year copywriter..."):
            copy_prompt = f"""
You are a legendary direct-response copywriter with 20 years writing Amazon #1 bestsellers.

Write:
1. A magnetic main title (max 80 characters)
2. A benefit-rich subtitle (max 200 characters)
3. A high-converting Amazon description (max 4000 characters, use bullet points, bold, emotional triggers)

Book content summary: {full_text[:15000]}

Use these 7 keywords naturally: {', '.join(best_keywords)}

Make it impossible to scroll past. Focus on transformation, pain points, and proof.

Return only:
TITLE: ...
SUBTITLE: ...
DESCRIPTION:
...
"""
            copy = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": copy_prompt}],
                temperature=0.7
            )
            result = copy.choices[0].message.content

            title = result.split("SUBTITLE:")[0].replace("TITLE:", "").strip()
            subtitle = result.split("DESCRIPTION:")[0].split("SUBTITLE:")[1].strip() if "SUBTITLE:" in result else ""
            description = result.split("DESCRIPTION:")[1].strip() if "DESCRIPTION:" in result else result

        st.success("Done! Here are your Amazon-ready assets:")

        st.markdown(f"### 📕 **{title}**")
        st.markdown(f"#### {subtitle}")
        st.markdown("### 7 Golden Keywords")
        for kw in best_keywords:
            st.markdown(f"- `{kw}`")

        st.markdown("### Amazon Description (copy-paste ready)")
        st.markdown(description)

        if st.button("Download as TXT file"):
            txt = f"TITLE: {title}\nSUBTITLE: {subtitle}\n\nKEYWORDS:\n" + "\n".join(best_keywords) + "\n\nDESCRIPTION:\n" + description
            st.download_button("Download now", txt, "kdp_assets.txt")
