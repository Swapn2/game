# game.py
import streamlit as st
import random
from itertools import permutations
from collections import defaultdict
import math

# ---------- Page config ----------
st.set_page_config(page_title="Digit Guessing Game (logical solver)", page_icon="🎯", layout="centered")

# ---------- Neon CSS (kept similar to prior) ----------
NEON_CSS = """
<style>
:root{ --neon:#00d4ff; }
.reportview-container, .main { background: linear-gradient(180deg, #020617 0%, #041024 100%); color: #e6eef6; }
.main-card { background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02)); padding: 22px; border-radius: 14px; box-shadow: 0 8px 30px rgba(2,12,27,0.6); border: 1px solid rgba(255,255,255,0.02); }
.header { font-weight: 800; color: #f8fafc; font-size: 28px; margin-bottom: 2px; }
.subtitle { color: #cfeeff; margin-top: 4px; margin-bottom: 12px; opacity: 0.9; }
button[title="neon-btn"], button[title="neon-order"] { width:64px;height:64px;border-radius:50%; background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01)); border:2px solid rgba(255,255,255,0.06); color:#dff8ff; font-size:20px; font-weight:700; cursor:pointer; transition:transform .08s ease,box-shadow .12s ease; }
button[title="neon-btn"]:hover, button[title="neon-order"]:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(2,12,27,0.7), 0 0 18px rgba(0,212,255,0.14), 0 0 60px rgba(0,212,255,0.08); border-color: rgba(0,212,255,0.45); }
.selected-badge { display:inline-block; min-width:48px; padding:8px 10px; border-radius:999px; background: linear-gradient(90deg, rgba(0,212,255,0.12), rgba(0,212,255,0.06)); color: #dff8ff; border: 1px solid rgba(0,212,255,0.18); font-weight:700; text-align:center; }
.log { background: rgba(255,255,255,0.02); padding: 8px; border-radius: 8px; font-size: 13px; color: #dbeeff; margin-bottom: 6px; border: 1px solid rgba(255,255,255,0.02); }
.small-muted { color: #87b6c6; font-size:12px; }
</style>
"""
st.markdown(NEON_CSS, unsafe_allow_html=True)

# ---------- Helper functions ----------
def reset_state():
    st.session_state.update({
        "stage": "intro",
        "max_trials": 30,
        "trials": 0,
        "tried": set(),
        "current_guess": None,
        "recovered_guess": None,
        "candidates": UNIQUE_POOL.copy(),
        "lo": 0, "hi": -1,
        "seed": None, "logs": [],
        "rand_match_selected": None, "det_match_selected": None,
        "digit_counts": None, "det_digit": 0,
        "final_answer": None
    })

def add_log(msg):
    logs = st.session_state.get("logs", [])
    logs.insert(0, msg)
    st.session_state["logs"] = logs[:300]

def all_unique_4digit_numbers():
    nums = []
    for n in range(10000):
        s = f"{n:04d}"
        if len(set(s)) == 4:
            nums.append(n)
    return nums

UNIQUE_POOL = all_unique_4digit_numbers()  # 5040 elements

def format_guess(n): return f"{n:04d}"

def common_digit_count(a_str, b_str):
    # counts number of value-matches ignoring position (multiset intersection) but digits unique so just set intersection
    return len(set(a_str) & set(b_str))

def filter_candidates_by_feedback(candidates, guess_str, reported_matches):
    # keep only candidates that would yield reported_matches for the guess
    new = [c for c in candidates if common_digit_count(format_guess(c), guess_str) == reported_matches]
    return new

def choose_best_guess(candidates, pool, sample_limit=600):
    """
    Choose a guess from `pool` (list of ints) that best partitions `candidates`.
    If pool is large, sample sample_limit candidates from pool.
    Score = sum(size^2 across match-count buckets) (lower is better).
    """
    n_cand = len(candidates)
    if n_cand == 0:
        return None
    eval_pool = pool if len(pool) <= 1000 else random.sample(pool, min(sample_limit, len(pool)))
    best_score = math.inf
    best_guess = None
    cand_strs = [format_guess(c) for c in candidates]
    for g in eval_pool:
        g_str = format_guess(g)
        # bucket counts for match = 0..4
        counts = [0]*5
        for cs in cand_strs:
            m = len(set(cs) & set(g_str))
            counts[m] += 1
        # score: sum squares (penalize unbalanced large buckets)
        score = sum(c*c for c in counts)
        if score < best_score:
            best_score = score
            best_guess = g
    # if best_guess is None pick random from candidates
    if best_guess is None:
        return random.choice(candidates)
    return best_guess

# ---------- Initialize ----------
if "stage" not in st.session_state:
    # default candidates = full pool
    st.session_state["candidates"] = UNIQUE_POOL.copy()
    reset_state()

# ---------- Sidebar ----------
with st.sidebar:
    st.title("🎯 Options")
    st.markdown("Solver mode: logical filtering of candidates (unique digits enforced).")
    max_trials = st.number_input("Max random trials", min_value=1, max_value=1000, value=30, step=1)
    seed_text = st.text_input("Random seed (optional)", value="")
    strategy = st.radio("Digit detection strategy", options=["Solver-driven (recommended)", "Deterministic 10-digit queries (guaranteed)"], index=0)
    st.markdown("---")
    if st.button("Reset game", key="reset_btn"):
        reset_state()
        st.rerun()

st.session_state["max_trials"] = int(max_trials)
st.session_state["seed"] = int(seed_text) if seed_text.strip().lstrip('-').isdigit() else None

# ---------- Header ----------
st.markdown('<div class="main-card">', unsafe_allow_html=True)
st.markdown('<div class="header">🎯 Logical Four-digit Mind Reader</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Think of a 4-digit number with unique digits (e.g. 0123). I will reason to discover it.</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3,1])
with col1:
    st.markdown("### How this solver works (short)")
    st.markdown("""
- I maintain a pool of all possible 4-digit numbers with unique digits (5040 possibilities).
- After each guess you tell me how many digits match (0–4). I filter the pool to only numbers consistent with that response.
- I choose the next guess to best split remaining possibilities (minimize expected remaining candidates).
- When the pool is small, decisions are exhaustive; when large, I sample to stay fast.
""")
with col2:
    st.markdown("### Info")
    st.markdown(f"- Strategy: **{'Solver' if strategy.startswith('Solver') else 'Deterministic'}**")
    st.markdown(f"- Pool size: **{len(st.session_state['candidates'])}**")
st.markdown("----")

# ---------- Intro / Start ----------
if st.session_state["stage"] == "intro":
    st.markdown("#### Ready? Start the game")
    c1, c2 = st.columns([2,1])
    with c1:
        if st.button("Start Game ▶️", key="start"):
            if st.session_state["seed"] is not None:
                try:
                    random.seed(st.session_state["seed"])
                except:
                    pass
            st.session_state["trials"] = 0
            st.session_state["tried"] = set()
            st.session_state["logs"] = []
            st.session_state["rand_match_selected"] = None
            st.session_state["det_match_selected"] = None
            st.session_state["candidates"] = UNIQUE_POOL.copy()
            add_log("Game started (solver-driven).")
            if strategy.startswith("Solver"):
                st.session_state["stage"] = "solver_stage"
            else:
                st.session_state["stage"] = "deterministic_stage"
            st.rerun()
    with c2:
        st.button("Instructions ❓", key="instr")

# ---------- Deterministic 10-query (unchanged) ----------
if st.session_state["stage"] == "deterministic_stage":
    st.markdown("### Deterministic digit detection (10 queries, 0/1 answers)")
    st.markdown("For each digit 0..9 tell me whether it appears (0/1). Exactly four digits must be '1'.")
    if st.button("Begin 10 queries", key="start_det"):
        st.session_state["digit_counts"] = {str(d): None for d in range(10)}
        st.session_state["det_digit"] = 0
        st.session_state["stage"] = "det_query"
        st.rerun()

if st.session_state.get("stage") == "det_query":
    i = st.session_state["det_digit"]
    d = str(i)
    st.markdown(f"**Query {i+1}/10** — Does digit **{d}** appear in your secret?")

    c0, c1 = st.columns([1,1])
    with c0:
        if st.button("0", key=f"det_no_{i}", help="neon-btn"):
            st.session_state["det_match_selected"] = 0
    with c1:
        if st.button("1", key=f"det_yes_{i}", help="neon-btn"):
            st.session_state["det_match_selected"] = 1

    sel = st.session_state.get("det_match_selected")
    st.markdown(f"**Selected:** " + (f"<span class='selected-badge'>{sel}</span>" if sel is not None else "<span class='small-muted'>None</span>"), unsafe_allow_html=True)

    if st.button("Submit answer", key=f"det_submit"):
        if sel is None:
            st.warning("Select 0 or 1.")
        else:
            st.session_state["digit_counts"][d] = int(sel)
            add_log(f"Q {i+1}: digit {d} → {sel}")
            st.session_state["det_match_selected"] = None
            st.session_state["det_digit"] += 1
            if st.session_state["det_digit"] >= 10:
                counts = st.session_state["digit_counts"]
                digits = []
                total = 0
                for dig, cnt in counts.items():
                    if cnt is None:
                        st.error("All 10 queries must be answered.")
                        break
                    if cnt not in (0,1):
                        st.error("Each answer must be 0 or 1.")
                        break
                    if cnt == 1:
                        digits.append(dig)
                        total += 1
                else:
                    if total != 4:
                        st.error(f"You marked {total} digits present; exactly 4 must be present. Please restart and answer carefully.")
                    else:
                        recovered = ''.join(digits)
                        st.session_state["recovered_guess"] = recovered
                        st.session_state["candidates"] = generate_candidates_from_multiset(recovered)
                        st.session_state["lo"] = 0
                        st.session_state["hi"] = len(st.session_state["candidates"]) - 1
                        st.session_state["stage"] = "ordering_stage"
                        add_log(f"Digits recovered deterministically: {recovered}")
            st.rerun()

    st.markdown("#### Logs")
    for l in st.session_state["logs"][:10]:
        st.markdown(f"<div class='log'>{l}</div>", unsafe_allow_html=True)

# ---------- Solver-driven stage (replacement for random stage) ----------
if st.session_state["stage"] == "solver_stage":
    st.markdown("### Solver stage — I pick a logical guess")
    st.markdown("I will choose a guess to efficiently narrow the candidate pool. Tell me how many digits match (0–4).")
    trials = st.session_state["trials"]
    max_trials = st.session_state["max_trials"]
    st.progress(min(1.0, trials / max_trials))
    st.markdown(f"**Trials:** {trials} / {max_trials}")
    st.markdown(f"**Candidates remaining:** {len(st.session_state['candidates'])}")

    # decide next guess intelligently
    candidates = st.session_state["candidates"]
    pool_for_guess = candidates  # we can also consider entire UNIQUE_POOL but we restrict to candidates for simplicity
    if len(candidates) == 0:
        st.error("No candidates left — inconsistent answers or secret changed. Restart.")
    else:
        # choose best guess
        guess_int = None
        # if only one candidate left, pick it
        if len(candidates) == 1:
            guess_int = candidates[0]
        else:
            # choose best candidate (exhaustive if small, sample if large)
            guess_int = choose_best_guess(candidates, pool_for_guess, sample_limit=600)

        # set current guess if not set this round
        if st.session_state["current_guess"] is None or st.session_state["current_guess"] != format_guess(guess_int):
            st.session_state["current_guess"] = format_guess(guess_int)
            # note: do not add to tried until user submits (but we count trial when user sees and answers)
            # increment trials now to reflect an attempt shown
            st.session_state["trials"] += 1

        guess_str = st.session_state["current_guess"]
        st.markdown(f"## My guess:  **{guess_str}**")

        # neon buttons for match count 0..4
        st.markdown("**How many digits match? (value-only)**")
        cols = st.columns(5)
        for idx, col in enumerate(cols):
            with col:
                if st.button(f"{idx}", key=f"solver_m_{idx}", help="neon-btn"):
                    st.session_state["rand_match_selected"] = idx

        sel = st.session_state.get("rand_match_selected")
        st.markdown(f"**Selected:** " + (f"<span class='selected-badge'>{sel}</span>" if sel is not None else "<span class='small-muted'>None</span>"), unsafe_allow_html=True)

        c1, c2 = st.columns([2,1])
        with c1:
            if st.button("Submit match count ✓", key=f"solver_submit"):
                if sel is None:
                    st.warning("Please select 0–4 before submitting.")
                else:
                    add_log(f"Guess #{st.session_state['trials']}: {guess_str} → matches {sel}")
                    # filter candidates
                    new_cands = filter_candidates_by_feedback(st.session_state["candidates"], guess_str, sel)
                    st.session_state["candidates"] = new_cands
                    st.session_state["tried"].add(int(guess_str))
                    st.session_state["rand_match_selected"] = None
                    # if match==4 we recovered digits (unique)
                    if sel == 4:
                        st.session_state["recovered_guess"] = guess_str
                        st.session_state["candidates"] = generate_candidates_from_multiset_unique(guess_str)
                        st.session_state["lo"] = 0
                        st.session_state["hi"] = len(st.session_state["candidates"]) - 1
                        st.session_state["stage"] = "ordering_stage"
                        add_log(f"Recovered digits: {guess_str} (unique multiset)")
                        st.rerun()
                    else:
                        # check trial limit
                        if st.session_state["trials"] >= st.session_state["max_trials"]:
                            st.warning("Reached max trials without collecting a '4'. You can restart, or switch to deterministic method.")
                            st.session_state["stage"] = "failed_random"
                            st.rerun()
                        # continue with updated candidate pool — next rerun will choose next guess
                        st.session_state["current_guess"] = None
                        st.rerun()
        with c2:
            if st.button("Skip → new logical guess", key=f"solver_skip"):
                add_log(f"Skipped guess {guess_str}")
                st.session_state["current_guess"] = None
                st.session_state["rand_match_selected"] = None
                st.rerun()

    st.markdown("#### Recent logs")
    for l in st.session_state["logs"][:8]:
        st.markdown(f"<div class='log'>{l}</div>", unsafe_allow_html=True)

# ---------- Failed random fallback ----------
if st.session_state["stage"] == "failed_random":
    st.error("Solver stage failed to find match=4 within trial limit.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Switch to deterministic 10-query method now"):
            st.session_state["stage"] = "deterministic_stage"
            st.rerun()
    with col2:
        if st.button("Restart (solver)"):
            reset_state()
            st.rerun()

# ---------- Ordering stage (binary search over permutations) ----------
if st.session_state["stage"] == "ordering_stage":
    candidates = st.session_state["candidates"]
    lo = st.session_state["lo"]; hi = st.session_state["hi"]
    st.markdown("### Stage 2 — Find exact ordering (comparison feedback)")
    st.markdown(f"Recovered digits (set): **{st.session_state['recovered_guess']}**")
    st.markdown(f"Possible arrangements: **{len(candidates)}**")
    sample_str = ', '.join(f"{c:04d}" for c in candidates[:10]) + (", ..." if len(candidates) > 10 else "")
    st.markdown(f"**Sample orderings:** {sample_str}")

    if lo > hi:
        st.error("Inconsistent comparison answers — no candidate remains. You may have changed the secret. Restart to try again.")
    else:
        mid = (lo + hi) // 2
        guess_val = candidates[mid]
        st.markdown(f"## My ordering guess: **{guess_val:04d}**")

        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            if st.button("❮", key="order_lt", help="neon-order"):
                st.session_state["hi"] = mid - 1
                add_log(f"Ordering guess {guess_val:04d} → user said '<'")
                st.rerun()
            st.markdown("<div class='small-muted'>Secret is smaller</div>", unsafe_allow_html=True)
        with c2:
            if st.button("✔", key="order_eq", help="neon-order"):
                add_log(f"Ordering found: {guess_val:04d}")
                st.session_state["stage"] = "done"
                st.session_state["final_answer"] = guess_val
                st.rerun()
            st.markdown("<div class='small-muted'>Equal</div>", unsafe_allow_html=True)
        with c3:
            if st.button("❯", key="order_gt", help="neon-order"):
                st.session_state["lo"] = mid + 1
                add_log(f"Ordering guess {guess_val:04d} → user said '>'")
                st.rerun()
            st.markdown("<div class='small-muted'>Secret is greater</div>", unsafe_allow_html=True)

    st.markdown("#### Logs")
    for l in st.session_state["logs"][:10]:
        st.markdown(f"<div class='log'>{l}</div>", unsafe_allow_html=True)

# ---------- Done ----------
if st.session_state["stage"] == "done":
    final = st.session_state.get("final_answer")
    st.success(f"🎉 I found it! Your number is **{final:04d}**")
    st.balloons()
    if st.button("Play again"):
        reset_state()
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("----")
st.markdown("#### Debug & recent activity")
with st.expander("Show logs"):
    for l in st.session_state["logs"]:
        st.write(l)
