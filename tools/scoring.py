
import re
HOSPITALITY_KEYWORDS=[r"hospitality",r"catering",r"professional cookery",r"kitchen",r"chef",r"restaurant",r"barista",r"food"]
SEND_KEYWORDS=[r"ehcp",r"ehc plan",r"send",r"inclusive learning",r"foundation learning",r"high needs",r"additional learning support",r"reasonable adjustments",r"autism",r"adhd",r"quiet",r"sensory"]

def keyword_hits(text: str, patterns) -> int:
    if not text: return 0
    t=text.lower(); hits=0
    for p in patterns:
        if re.search(p,t): hits+=1
    return hits

def normalize(v: float, m: float) -> float:
    if m<=0: return 0.0
    return max(0.0, min(1.0, v/m))

def blended_score(distance_miles: float, radius_miles: float, aspiration_hits: int, send_hits: int, cfg):
    d_comp = 1.0 - (distance_miles / max(radius_miles, 0.0001))
    d_comp = max(0.0, min(1.0, d_comp))
    a_comp = normalize(aspiration_hits, 10)
    s_comp = normalize(send_hits, 10)
    score = cfg.w_distance*d_comp + cfg.w_aspiration*a_comp + cfg.w_send_fit*s_comp
    return score, d_comp, a_comp, s_comp
