import re, json, math
from urllib.parse import urlparse

# Lightweight keyword heuristics; extend via taxonomy.json
KEYSETS = {
    "Stockholder/Service Centre": [
        r"\bstockholder(s)?\b", r"\bservice\s*centre\b", r"\bcut[\s-]?to[\s-]?length\b",
        r"\bprofil(ing|er)\b", r"\bplate\b", r"\bsections?\b", r"\btube(s)?\b", r"\bcoil(s)?\b",
        r"\bsteel\s(stock|stockist|stockholder)\b"
    ],
    "FinTech/RegTech/WealthTech": [
        r"\b(kyc|know\s+your\s+customer)\b", r"\baml\b", r"\bsanctions?\b", r"\bpep(s)?\b",
        r"\bwealth(tech)?\b", r"\bdfm\b", r"\bmps\b", r"\brobo-?advice\b"
    ],
    "Capital Markets": [
        r"\bprimary\s+issuance\b", r"\bbond\b.*\b(issuance|issue|primary)\b", r"\bfixed\s+income\b",
        r"\bbookbuild(ing)?\b", r"\bsyndicate\b", r"\bRFQ\b", r"\bdealer\s*to\s*client\b"
    ],
    "Brokerage/Advisory": [
        r"\basset\s+finance\b", r"\bbroker(age)?\b", r"\bplacement\s+agent\b", r"\bintroducer\b"
    ],
    "Software/SaaS": [
        r"\bSaaS\b", r"\bAPI\b", r"\bcloud\b", r"\bsubscription\b", r"\bdeveloper\s+docs?\b"
    ],
    "Manufacturing": [
        r"\bmanufactur(er|ing)\b", r"\bfabrication\b", r"\bOEM\b", r"\bISO\s*9001\b"
    ],
    "Distribution/Wholesale": [
        r"\bdistribut(or|ion)\b", r"\bwholesale(r)?\b", r"\bstockist(s)?\b", r"\bauthorised\s+distributor\b"
    ],
    "Industrial Services": [
        r"\basbestos\b", r"\bfire\s*stopp(ing|er)\b", r"\binsulation\b", r"\bmaintenance\b", r"\binstallations?\b"
    ]
}

SUBSECTOR_HINTS = {
    "Stockholder/Service Centre": {
        "Plate": [r"\bplate\b"],
        "Sections": [r"\bsection(s)?\b", r"\bbeam(s)?\b", r"\bcolumn(s)?\b"],
        "Tube/Hollow": [r"\btube(s)?\b", r"\bhollow\s+section(s)?\b"],
        "Coil/Flat": [r"\bcoil(s)?\b", r"\bslit\s+coil\b", r"\bflat\s+product(s)?\b"],
        "Profiling/Cut": [r"\bprofil(ing|er)\b", r"\bcut[\s-]?to[\s-]?length\b"]
    },
    "FinTech/RegTech/WealthTech": {
        "KYC/AML": [r"\b(kyc|know\s+your\s+customer)\b", r"\baml\b", r"\bsanction(s)?\b", r"\bpep(s)?\b"],
        "Wealth Platform": [r"\bwealth\b", r"\bdfm\b", r"\bmps\b"]
    },
    "Capital Markets": {
        "Debt/Fixed Income": [r"\bfixed\s+income\b", r"\bbond\b"],
        "Equities": [r"\bequities\b", r"\bequity\b"]
    }
}

def score_text(text: str):
    text = text or ""
    low = text.lower()
    # Weight title/nav/meta terms slightly higher by naive heuristics
    weights = {}
    for cat, patterns in KEYSETS.items():
        s = 0.0
        for pat in patterns:
            for m in re.finditer(pat, low):
                s += 1.0
                # boost near 'about', 'services', 'products'
                start = max(0, m.start()-30)
                ctx = low[start:m.end()+30]
                if re.search(r"\b(about|services?|products?|solutions?)\b", ctx):
                    s += 0.5
        weights[cat] = s
    
    if not weights:
        return "Unknown", {}, 0.0
        
    # choose best
    best_cat, best_score = max(weights.items(), key=lambda kv: kv[1])
    
    if best_score == 0:
        return "Unknown", weights, 0.0
        
    # confidence = sigmoid over relative margin
    sorted_scores = sorted(weights.values(), reverse=True)
    margin = (sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) > 1 else sorted_scores[0]
    conf = 1 / (1 + math.exp(-margin))
    return best_cat, weights, conf

def choose_subsector(cat: str, text: str):
    text = text or ""
    low = text.lower()
    if cat in SUBSECTOR_HINTS:
        subs = SUBSECTOR_HINTS[cat]
        scores = {sub: 0 for sub in subs}
        for sub, pats in subs.items():
            for pat in pats:
                scores[sub] += len(re.findall(pat, low))
        # take those with non-zero
        ranked = [k for k,v in sorted(scores.items(), key=lambda kv: kv[1], reverse=True) if v>0]
        return ranked[:3]  # top 3 signals
    return []

def classify(employer_homepage_text: str, linkedin_about_text: str = "", homepage_url: str = "", linkedin_url: str = ""):
    text = " ".join([employer_homepage_text or "", linkedin_about_text or ""])
    cat, weights, conf = score_text(text)
    
    if cat == "Unknown":
        return {
            "sector": "Unknown",
            "subsector": "",
            "solution_type": "Unknown",
            "product_focus": "",
            "confidence": 0.0,
            "signals": [],
            "evidence_urls": []
        }
        
    subsecs = choose_subsector(cat, text)
    product_focus = ", ".join(subsecs) if subsecs else ""
    # solution_type is same as the top-level cat for simplicity
    solution = cat
    evidence = [u for u in [homepage_url, linkedin_url] if u]
    # pick top patterns hit for transparency
    top_signals = sorted([(k, v) for k,v in weights.items()], key=lambda kv: kv[1], reverse=True)[:3]
    return {
        "sector": cat,
        "subsector": (subsecs[0] if subsecs else ""),
        "solution_type": solution,
        "product_focus": product_focus,
        "confidence": round(conf, 3),
        "signals": top_signals,
        "evidence_urls": evidence
    }
