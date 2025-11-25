# game.py
import streamlit as st
import random
from itertools import permutations

# ---------- Page config ----------
st.set_page_config(page_title="Digit Guessing Game", page_icon="🎯", layout="centered")

# ---------- Neon CSS (Style 3) ----------
NEON_CSS = """
<style>
:root{
  --bg1:#041024;
  --card:#071433;
  --neon:#00d4ff; /* main neon color - blue cyan */
  --neon-weak: rgba(0,212,255,0.12);
  --muted: #94a3b8;
  --glass: rgba(255,255,255,0.03);
}

/* page background */
.reportview-container, .main {
  background: linear-gradient(180deg, #020617 0%, #041024 100%);
  color: #e6eef6;
}

/* card */
.main-card {
  background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
  padding: 22px;
  border-radius: 14px;
  box-shadow: 0 8px 30px rgba(2,12,27,0.6);
  border: 1px solid rgba(255,255,255,0.02);
}

/* header */
.header {
  font-weight: 800;
  color: #f8fafc;
  font-size: 28px;
  margin-bottom: 2px;
}
.subtitle {
  color: #cfeeff;
  margin-top: 4px;
  margin-bottom: 12px;
  opacity: 0.9;
}

/* neon buttons targeted via title attribute help="neon-btn" */
button[title="neon-btn"], button[title="neon-order"] {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
  border: 2px solid rgba(255,255,255,0.06);
  color: #dff8ff;
  font-size: 20px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 0 12px rgba(0,0,0,0.5), 0 0 0 6px rgba(0,0,0,0.02) inset;
  transition: transform .08s ease, box-shadow .12s ease, background .12s ease;
}

/* Neon glow on hover */
button[title="neon-btn"]:hover, button[title="neon-order"]:hover {
  transform: translateY(-3px);
  box-shadow:
    0 8px 30px rgba(2,12,27,0.7),
    0 0 18px rgba(0,212,255,0.14),
    0 0 60px rgba(0,212,255,0.08);
  border-color: rgba(0,212,255,0.45);
}

/* pressed / active look */
button[title="neon-btn"]:active, button[title="neon-order"]:active {
  transform: translateY(0);
  box-shadow: 0 6px 20px rgba(2,12,27,0.6), 0 0 28px rgba(0,212,255,0.18);
}

/* selected badge (we will display selected value next to buttons) */
.selected-badge {
  display:inline-block;
  min-width:48px;
  padding:8px 10px;
  border-radius:999px;
  background: linear-gradient(90deg, rgba(0,212,255,0.12), rgba(0,212,255,0.06));
  color: #dff8ff;
  border: 1px solid rgba(0,212,255,0.18);
  box-shadow: 0 6px 30px rgba(0,212,255,0.04);
  font-weight:700;
  text-align:center;
}

/* info box & logs */
.info {
  color: #bfefff;
  font-size: 14px;
}
.log {
  background: rgba(255,255,255,0.02);
  padding: 8px;
  border-radius: 8px;
  font-size: 13px;
  color: #dbeeff;
  margin-bottom: 6px;
  border: 1px solid rgba(255,255,255,0.02);
}

/* small text */
.small-muted {
  color: #87b6c6;
  font-size:12px;
}

/* footer */
.footer {
  color: #9ecfe5;
  font-size:13px;
  opacity:0.85;
}
</style>
"""
st.markdown(NEON_CSS, unsafe_allow_html=True)

# ---------- Helper functions ----------
def reset_state():
    st.session_state.update({
        "stage": "intro",        # intro | random_stage | deterministic_stage | det_query | ordering_stage | done | failed_random
        "max_trials": 30,
        "trials": 0,
        "tried": set(),
        "current_guess": None,
        "recovered_guess": None,
        "candidates": [],
        "lo": 0,
        "hi": -1,
        "seed": None,
        "logs": [],
        # selection holders for UI
        "rand_match_selected": None,
        "det_match_selected": None,
        # deterministic specific
        "digit_counts": None,
        "det_digit": 0,
        # ordering stage
        "final_answer": None
    })

def add_log(msg):
    logs = st.session_state.get("logs", [])
    logs.insert(0, msg)
    st.session_state["logs"] = logs[:200]

def generate_random_not_tried():
    tried = st.session_state["tried"]
    if len(tried) >= 10000:
        return None
    while True:
        n = random.randrange(0, 10000)
        if n not in tried:
            return n

def format_guess(n):
    return f"{n:04d}"

def generate_candidates_from_multiset(guess_str):
    digits = list(guess_str)
    perms = set(permutations(digits, 4))
    perm_ints = sorted(int(''.join(p)) for p in perms)
    return perm_ints

# ---------- Initialize ----------
if "stage" not in st.session_state:
    reset_state()

# ---------- Sidebar ----------
with st.sidebar:
    st.title("🎯 Game Options")
    st.markdown("Use these settings before starting a new game.")
    max_trials = st.number_input("Max random trials", min_value=1, max_value=1000, value=30, step=1)
    seed_text = st.text_input("Random seed (optional)", value="")
    strategy = st.radio("Digit detection strategy", options=["Random-guess until 4 (your idea)", "Deterministic 10-digit queries (guaranteed)"], index=0)
    st.markdown("---")
    if st.button("Reset game", key="reset_btn"):
        reset_state()
        st.rerun()

st.session_state["max_trials"] = int(max_trials)
st.session_state["seed"] = int(seed_text) if seed_text.strip().lstrip('-').isdigit() else None

# ---------- Main UI ----------
st.markdown('<div class="main-card">', unsafe_allow_html=True)
st.markdown('<div class="header">🎯 Four-digit Mind Reader</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Think of a 4-digit number (0000–9999). I will try to discover it — duplicates allowed.</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3,1])
with col1:
    st.markdown("### How the game flows")
    st.markdown("""
- **Stage 1 (digit discovery):** I will make guesses and you tell me how many digits (value only) match your secret number (0–4).  
- When you respond **4**, I know the multiset of the four digits.  
- **Stage 2 (ordering):** I will try orderings and you respond `<`, `>`, `=` comparing your secret number to my guess.  
- The random stage has a **limit** (set in the sidebar).  
""")
with col2:
    st.markdown("### Info")
    st.markdown(f"- Strategy: **{'Random' if strategy.startswith('Random') else 'Deterministic'}**")
    st.markdown(f"- Max random trials: **{st.session_state['max_trials']}**")
    if st.session_state["seed"] is not None:
        st.markdown(f"- Seed: `{st.session_state['seed']}`")
    st.markdown("---")
    st.markdown("⚠️ Keep answers consistent (don't change the secret mid-game).", unsafe_allow_html=True)

st.markdown("----")

# ---------- Start / Intro ----------
if st.session_state["stage"] == "intro":
    st.markdown("#### Ready? Start the game")
    start_col1, start_col2 = st.columns([2,1])
    with start_col1:
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
            add_log("Game started.")
            if strategy.startswith("Random"):
                st.session_state["stage"] = "random_stage"
            else:
                st.session_state["stage"] = "deterministic_stage"
            st.rerun()
    with start_col2:
        st.button("Instructions ❓", key="instr")

# ---------- Deterministic 10-query mode ----------
if st.session_state["stage"] == "deterministic_stage":
    st.markdown("### Deterministic digit detection (10 queries)")
    st.markdown("I will ask *exactly* for each digit `dddd` how many matches the secret has. This always recovers the multiset of digits in 10 replies (0–4 each).")
    if st.button("Begin 10 queries", key="start_det"):
        st.session_state["digit_counts"] = {str(d): None for d in range(10)}
        st.session_state["det_digit"] = 0
        st.session_state["stage"] = "det_query"
        st.rerun()

# ---------- Deterministic query UI (0-4 neon buttons) ----------
if st.session_state.get("stage") == "det_query":
    i = st.session_state["det_digit"]
    d = str(i)
    guess = d * 4
    st.markdown(f"**Query {i+1}/10** — If I show **{guess}**, how many digits (value-only) match?")

    # buttons row
    cols = st.columns(5)
    for idx, col in enumerate(cols):
        with col:
            # each numeric button uses help="neon-btn" so CSS matches
            if st.button(f"{idx}", key=f"det_m_{idx}", help="neon-btn"):
                st.session_state["det_match_selected"] = idx

    # display selected
    sel = st.session_state.get("det_match_selected")
    st.markdown(f"**Selected:** " + (f"<span class='selected-badge'>{sel}</span>" if sel is not None else "<span class='small-muted'>None</span>"), unsafe_allow_html=True)

    # submit
    if st.button("Submit answer", key=f"det_submit"):
        if sel is None:
            st.warning("Please select 0–4 before submitting.")
        else:
            st.session_state["digit_counts"][d] = int(sel)
            add_log(f"Q {i+1}: {guess} → {sel}")
            st.session_state["det_match_selected"] = None
            st.session_state["det_digit"] += 1
            if st.session_state["det_digit"] >= 10:
                # reconstruct
                counts = st.session_state["digit_counts"]
                digits = []
                total = 0
                for dig, cnt in counts.items():
                    digits.extend([dig]*cnt)
                    total += cnt
                if total != 4:
                    st.error(f"The total count of digits is {total}, but should be 4. Check your answers or restart.")
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

# ---------- Random-guess stage (neon buttons replacing slider) ----------
if st.session_state["stage"] == "random_stage":
    st.markdown("### Stage 1 — Random guesses (value-only matches)")
    st.markdown("I will show a 4-digit guess and you tell me how many digits (value-only) match your secret. If you reply `4`, I will recover the digits' multiset.")
    trials = st.session_state["trials"]
    max_trials = st.session_state["max_trials"]
    st.progress(min(1.0, trials / max_trials))
    st.markdown(f"**Trials:** {trials} / {max_trials}")

    # choose new guess if needed
    if st.session_state["current_guess"] is None:
        n = generate_random_not_tried()
        if n is None:
            st.error("All 10000 numbers tried (rare). Reset to start over.")
        else:
            st.session_state["current_guess"] = format_guess(n)
            st.session_state["tried"].add(n)
            st.session_state["trials"] += 1

    guess_str = st.session_state["current_guess"]
    st.markdown(f"## My guess:  **{guess_str}**")

    # neon buttons for match count
    st.markdown("**How many digits match? (value-only)**")
    cols = st.columns(5)
    for idx, col in enumerate(cols):
        with col:
            if st.button(f"{idx}", key=f"rand_m_{idx}", help="neon-btn"):
                st.session_state["rand_match_selected"] = idx

    # show selected
    sel = st.session_state.get("rand_match_selected")
    st.markdown(f"**Selected:** " + (f"<span class='selected-badge'>{sel}</span>" if sel is not None else "<span class='small-muted'>None</span>"), unsafe_allow_html=True)

    col_a, col_b = st.columns([2,1])
    with col_a:
        if st.button("Submit match count ✓", key=f"rand_submit"):
            if sel is None:
                st.warning("Please select 0–4 before submitting.")
            else:
                add_log(f"Guess #{st.session_state['trials']}: {guess_str} → matches {sel}")
                if sel == 4:
                    st.session_state["recovered_guess"] = guess_str
                    st.session_state["candidates"] = generate_candidates_from_multiset(guess_str)
                    st.session_state["lo"] = 0
                    st.session_state["hi"] = len(st.session_state["candidates"]) - 1
                    st.session_state["stage"] = "ordering_stage"
                    add_log(f"Recovered digits: {guess_str} (multiset)")
                    st.session_state["rand_match_selected"] = None
                    st.rerun()
                else:
                    st.session_state["current_guess"] = None
                    st.session_state["rand_match_selected"] = None
                    if st.session_state["trials"] >= st.session_state["max_trials"]:
                        st.warning("Reached max trials without collecting a '4'. You can restart, or switch to deterministic method.")
                        st.session_state["stage"] = "failed_random"
                    st.rerun()
    with col_b:
        if st.button("Skip → new random guess", key=f"rand_skip"):
            add_log(f"Skipped guess {guess_str}")
            st.session_state["current_guess"] = None
            st.session_state["rand_match_selected"] = None
            if st.session_state["trials"] >= st.session_state["max_trials"]:
                st.warning("Reached max trials.")
                st.session_state["stage"] = "failed_random"
            st.rerun()

    st.markdown("#### Recent logs")
    for l in st.session_state["logs"][:6]:
        st.markdown(f"<div class='log'>{l}</div>", unsafe_allow_html=True)

# ---------- Failed random fallback ----------
if st.session_state["stage"] == "failed_random":
    st.error("Random stage failed to reach a match=4 within trial limit.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Switch to deterministic 10-query method now"):
            st.session_state["stage"] = "deterministic_stage"
            st.rerun()
    with col2:
        if st.button("Restart (random)"):
            reset_state()
            st.rerun()

# ---------- Ordering stage (neon < > = buttons) ----------
if st.session_state["stage"] == "ordering_stage":
    candidates = st.session_state["candidates"]
    lo = st.session_state["lo"]
    hi = st.session_state["hi"]
    st.markdown("### Stage 2 — Find exact ordering (comparison feedback)")
    st.markdown(f"Recovered digits (multiset): **{st.session_state['recovered_guess']}**")
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

