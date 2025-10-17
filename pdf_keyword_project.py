"""
pdf_keyword_project.py

Usage:
1. Put all charter PDFs in a folder and set PDF_FOLDER below.
2. Activate your virtualenv.
3. python pdf_keyword_project.py

Outputs (saved in PDF_FOLDER):
- keyword_hits.csv        (detailed hits: file, page, category, keyword, snippet)
- charter_summary.csv     (one row per file with descriptive metadata + classification)
"""

import os
import re
import csv
from collections import Counter, defaultdict
import pdfplumber
from tqdm import tqdm
import pandas as pd

# === CONFIG - edit these paths/params ===
PDF_FOLDER = r"C:\Users\Engineer\Documents\pdf_keyword_project\pdfs"
  # <- change this to your folder
OUTPUT_HITS = "keyword_hits.csv"
OUTPUT_SUMMARY = "charter_summary.csv"
CONTEXT_CHARS = 200  # chars before & after match for snippet

# === KEYWORDS (from your specification) ===

CONTROL_KW = [
    "oversight", "monitor", "monitoring", "compliance", "ensure compliance",
    "review performance", "review progress", "risk", "risk management", "risk oversight",
    "accountability", "hold management accountable", "evaluate", "assessment",
    "integrity", "independence", "objectivity", "internal control", "control system",
    "adherence", "ensure alignment", "governance", "supervision"
]

COLLAB_KW = [
    "advise", "advisory", "advisory role", "support", "assist", "help management",
    "guide", "guidance", "strategic direction", "strategic input", "collaboration",
    "partnership", "facilitate", "communication", "coordination", "consult", "counsel",
    "recommend", "propose", "provide input", "expertise", "insight", "best practices",
    "joint", "shared responsibility", "enable", "foster innovation", "enable innovation"
]

# Main function categories and their keyword lists
FUNCTION_KEYWORDS = {
    "R&D Strategy": [
        "r&d", "research and development", "innovation", "innovative capability",
        "technology strategy", "technology roadmap", "product development", "pipeline",
        "portfolio review", "portfolio optimization", "emerging technologies", "digital transformation",
        "competitiveness", "technological leadership", "investment in r&d", "funding",
        "long-term growth"
    ],
    "Legal/Compliance/Risk": [
        "compliance", "regulatory", "legal", "laws", "regulation", "standards",
        "ethics", "ethical conduct", "risk management", "risk oversight", "risk mitigation",
        "audit", "review", "assessment", "health & safety", "product safety",
        "data protection", "data privacy", "cybersecurity", "intellectual property", "patent", "ip protection",
        "reporting", "disclosure", "transparency", "liability", "lawsuit", "prevent"
    ],
    "Product/Project-Specific": [
        "development", "project", "program", "initiative", "product", "drug", "compound",
        "device", "clinical trial", "study", "testing", "preclinical", "phase",
        "regulatory submission", "fda", "ema", "approval process", "milestone",
        "launch", "go-to-market", "commercialization", "research progress", "experimental result"
    ],
    "Sustainability/Ethics": [
        "sustainability", "sustainable technology", "esg", "responsible innovation", "ethical ai",
        "social responsibility", "public impact", "environment", "carbon", "climate",
        "green innovation", "ethical standards", "human rights"
    ],
    "Partnerships/External Collaboration": [
        "partnership", "collaboration", "alliance", "university", "academia", "research institute",
        "joint venture", "consortium", "cooperation", "open innovation", "external engagement",
        "licensing", "technology transfer", "joint research", "stakeholder", "ecosystem", "network"
    ]
}

# Other heuristics
MEETING_FREQ_TERMS = ["monthly", "quarterly", "annually", "annual", "biannually", "semi-annually", "weekly", "as needed", "ad hoc", "bi-monthly"]
CEO_TITLES = ["ceo", "chief executive officer", "cto", "cio", "coo", "chief technology officer", "chief information officer", "chief operating officer"]

# regex patterns
DATE_PATTERNS = [
    r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+\d{4}\b',
    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    r'\b20\d{2}\b'
]

LIST_ITEM_RE = re.compile(r'^\s*(?:\d+[\.\)]|[•\-\u2022\*])\s+', flags=re.MULTILINE)

# utility functions
def normalize(text):
    return " ".join(text.split()).lower()

def find_snippets(text, keyword, context_chars=CONTEXT_CHARS):
    """Return list of snippet strings for occurrences of keyword in text."""
    snippets = []
    text_lower = text.lower()
    kw_lower = keyword.lower()
    start = 0
    while True:
        idx = text_lower.find(kw_lower, start)
        if idx == -1:
            break
        s = max(0, idx - context_chars)
        e = min(len(text), idx + len(kw_lower) + context_chars)
        snippet = text[s:e].replace("\n", " ").strip()
        snippets.append(snippet)
        start = idx + len(kw_lower)
    return snippets

def find_first_regex(text, patterns):
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(0)
    return ""

def count_list_items(text):
    # Count lines that look like list items
    return len(re.findall(LIST_ITEM_RE, text))

def find_members_count(text):
    # Look for patterns like "consists of X members" or "X members"
    patterns = [
        r'consist(?:s|ing)? of\s+(\d{1,3})\s+members',
        r'composed of\s+(\d{1,3})\s+members',
        r'(\d{1,3})\s+members\b',
        r'(\d{1,3})\s+member(s)?\b'
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None

def find_meeting_frequency(text):
    for term in MEETING_FREQ_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', text, flags=re.IGNORECASE):
            return term
    # also look for "meets X times per year" type
    m = re.search(r'meet(?:s|ing)?\s+(?:approximately\s+)?(\d{1,2})\s+times\s+per\s+year', text, flags=re.IGNORECASE)
    if m:
        return f"{m.group(1)} times/year"
    return ""

def find_reporting_line(text):
    m = re.search(r'reports? to (the )?([A-Z][A-Za-z &-]{2,100})', text, flags=re.IGNORECASE)
    if m:
        return m.group(2).strip()
    return ""

def find_authorities(text):
    auth = []
    if re.search(r'\b(hir|retain|engage)\b .* (consultant|expert|advisor|external)', text, flags=re.IGNORECASE):
        auth.append("authority_to_hire_external_experts")
    if re.search(r'\b(approve|authorize)\b .* budget', text, flags=re.IGNORECASE):
        auth.append("authority_to_approve_budgets")
    if re.search(r'\b(approve|authorize)\b .* (projects|programs|spending)', text, flags=re.IGNORECASE):
        auth.append("authority_to_approve_projects")
    return auth

def detect_expertise_tags(text):
    tags = set()
    if re.search(r'\b(scientif|scientist|scientific)\b', text, re.IGNORECASE):
        tags.add("scientific")
    if re.search(r'\b(technolog|technical|engineer)\b', text, re.IGNORECASE):
        tags.add("technological")
    if re.search(r'\b(legal|law|counsel|attorney)\b', text, re.IGNORECASE):
        tags.add("legal")
    if re.search(r'\b(financ|accounting|audit)\b', text, re.IGNORECASE):
        tags.add("financial")
    return list(tags)

def find_ceo_participation(text):
    for title in CEO_TITLES:
        if re.search(r'\b' + re.escape(title) + r'\b', text, flags=re.IGNORECASE):
            return True
    return False

# === PROCESS PDFs ===
hits_rows = []
summary_rows = []

pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")]
for fname in tqdm(pdf_files, desc="Processing PDFs"):
    path = os.path.join(PDF_FOLDER, fname)
    full_text = ""
    page_texts = []
    num_pages = 0
    try:
        with pdfplumber.open(path) as pdf:
            num_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages, start=1):
                ptext = page.extract_text() or ""
                page_texts.append((i, ptext))
                full_text += ptext + "\n"
    except Exception as e:
        print(f"Error opening {fname}: {e}")
        continue

    if not full_text.strip():
        # empty extraction - skip with a minimal summary
        summary_rows.append({
            "file": fname,
            "num_pages": num_pages,
            "word_count": 0,
            "num_listed_functions_est": 0,
            "members_count_est": "",
            "expertise_tags": "",
            "ceo_participation": False,
            "meeting_frequency": "",
            "last_review_date": "",
            "authorities": "",
            "self_evaluation": False,
            "control_count": 0,
            "collab_count": 0,
            "orientation": "no_text_extracted",
            "top_functions": ""
        })
        continue

    norm_text = normalize(full_text)
    word_count = len(norm_text.split())

    # count list items (heuristic)
    num_list_items = count_list_items(full_text)

    members_count = find_members_count(full_text) or ""

    expertise_tags = detect_expertise_tags(full_text)
    ceo_part = find_ceo_participation(full_text)
    meeting_freq = find_meeting_frequency(full_text)
    reporting_line = find_reporting_line(full_text)
    last_review = find_first_regex(full_text, DATE_PATTERNS)
    authorities = find_authorities(full_text)
    self_eval = bool(re.search(r'self-?evaluation|evaluation of the committee|committee evaluation', full_text, flags=re.IGNORECASE))

    # search keywords page-by-page so we can capture page numbers
    control_counter = 0
    collab_counter = 0
    function_counters = Counter()

    # prepare combined function keyword -> category mapping for quicker lookup
    flat_func_map = {}
    for cat, kws in FUNCTION_KEYWORDS.items():
        for k in kws:
            flat_func_map[k.lower()] = cat

    # keyword lists to lookup for hits (include control, collab, and function keywords)
    search_kws = set([k.lower() for k in CONTROL_KW + COLLAB_KW])
    for k in flat_func_map.keys():
        search_kws.add(k)

    # page by page search
    for (pnum, ptext) in page_texts:
        if not ptext:
            continue
        ptext_norm = ptext.lower()
        for kw in search_kws:
            # simple substring search (case-insensitive)
            start = 0
            while True:
                idx = ptext_norm.find(kw, start)
                if idx == -1:
                    break
                s = max(0, idx - CONTEXT_CHARS)
                e = min(len(ptext), idx + len(kw) + CONTEXT_CHARS)
                snippet = ptext[s:e].replace("\n", " ").strip()
                # determine category for this keyword
                cat = ""
                if kw in [w.lower() for w in CONTROL_KW]:
                    cat = "Control"
                    control_counter += 1
                elif kw in [w.lower() for w in COLLAB_KW]:
                    cat = "Collaboration"
                    collab_counter += 1
                else:
                    # function category
                    cat = flat_func_map.get(kw, "Function")
                    function_counters[cat] += 1

                hits_rows.append({
                    "file": fname,
                    "page": pnum,
                    "category": cat,
                    "keyword": kw,
                    "snippet": snippet
                })
                start = idx + len(kw)

    # Decide orientation
    orientation = "none"
    if control_counter == 0 and collab_counter == 0:
        orientation = "no_orientation_keywords"
    elif control_counter > collab_counter:
        orientation = "Control"
    elif collab_counter > control_counter:
        orientation = "Collaboration"
    else:
        orientation = "Mixed/Equal"

    # Top function categories (sort by counts)
    top_funcs = [f"{cat} ({count})" for cat, count in function_counters.most_common() if count > 0]
    top_funcs_str = "; ".join(top_funcs)

    summary_rows.append({
        "file": fname,
        "num_pages": num_pages,
        "word_count": word_count,
        "num_listed_functions_est": num_list_items,
        "members_count_est": members_count,
        "expertise_tags": "|".join(expertise_tags),
        "ceo_participation": ceo_part,
        "meeting_frequency": meeting_freq,
        "reporting_line": reporting_line,
        "last_review_date": last_review,
        "authorities": "|".join(authorities),
        "self_evaluation": self_eval,
        "control_count": control_counter,
        "collab_count": collab_counter,
        "orientation": orientation,
        "top_functions": top_funcs_str
    })


# === SAVE OUTPUTS ===
hits_df = pd.DataFrame(hits_rows, columns=["file", "page", "category", "keyword", "snippet"])
summary_df = pd.DataFrame(summary_rows, columns=[
    "file", "num_pages", "word_count", "num_listed_functions_est", "members_count_est",
    "expertise_tags", "ceo_participation", "meeting_frequency", "reporting_line",
    "last_review_date", "authorities", "self_evaluation", "control_count", "collab_count",
    "orientation", "top_functions"
])

out_hits = os.path.join(PDF_FOLDER, OUTPUT_HITS)
out_summary = os.path.join(PDF_FOLDER, OUTPUT_SUMMARY)
hits_df.to_csv(out_hits, index=False, quoting=csv.QUOTE_ALL)
summary_df.to_csv(out_summary, index=False, quoting=csv.QUOTE_ALL)

print("Done.")
print("Hits saved to:", out_hits)
print("Summary saved to:", out_summary)
