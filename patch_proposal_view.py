#!/usr/bin/env python3
"""Flip the 20 live quiz slices to the proposal-level view (quiz-proposal-v11).

- D.props   <- base64 {item_id: {A: schema, B: schema}} from the audited rewrite run
- D.mp      <- proposal-level picks of 8 judges (luna in, grok out: no proposal run)
- D.items   <- raw A/B text stripped (unused by the new renderer; page shrinks)
- renderer  <- fixed six-section proposal card, subgrid row-aligned across A/B
- version   <- quiz-proposal-v11 (payload + CSV)

Idempotent-ish: refuses to run twice (checks for D.props marker).
Rebuild path: build_quiz.py (v9 template) -> re-apply site functional patches -> this.
"""
import base64, glob, json, re, sys

RUN = "/Users/minglai.yang/Desktop/bolebench/runs/proposal-2026-09-02"
JUDGE_FILES = {
    "claude-opus-5": "pick_claude-opus-5_proposal.jsonl",
    "claude-sonnet-5": "pick_claude-sonnet-5_proposal.jsonl",
    "claude-opus-4-8": "pick_claude-opus-4-8_proposal.jsonl",
    "kimi-k3": "pick_fireworks_ai_kimi-k3_proposal.jsonl",
    "Kimi-K2.6": "pick_azure_ai_Kimi-K2.6_proposal.jsonl",
    "gpt-5.6-sol": "pick_gpt-5.6-sol_proposal.jsonl",
    "gpt-5.6-terra": "pick_gpt-5.6-terra_proposal.jsonl",
    "gpt-5.6-luna": "pick_gpt-5.6-luna_proposal.jsonl",
}

props = {}
for line in open(f"{RUN}/proposals.jsonl"):
    r = json.loads(line)
    if "error" in r:
        continue
    props.setdefault(r["item_id"], {})[r["side"]] = r["proposal"]

mp = {}
for name, fn in JUDGE_FILES.items():
    mp[name] = {}
    for line in open(f"{RUN}/{fn}"):
        r = json.loads(line)
        if "choice" in r:
            mp[name][r["item_id"]] = r["choice"]

CSS_OLD = ".card b{color:var(--acc)} .card.sel{border-color:var(--acc);background:var(--tile);box-shadow:0 0 0 1px var(--acc)}"
CSS_NEW = (CSS_OLD +
    "\n.psec{padding-top:10px}"
    "\n.psec .lab{display:block;font-size:10.5px;letter-spacing:1.2px;text-transform:uppercase;color:var(--ink3);font-weight:600;margin-bottom:3px}"
    "\n.pchips{display:flex;flex-wrap:wrap;gap:5px}"
    "\n.pchip{background:var(--tile);border:1px solid var(--line);border-radius:999px;padding:1px 9px;font-size:12.5px}"
    "\n.pchip.k{opacity:.75}"
    "\n.pnums{border-collapse:collapse;font-size:12.5px}"
    "\n.pnums td{padding:1px 10px 1px 0;border:none}"
    "\n.pnums td:first-child{color:var(--ink3);white-space:nowrap}"
    "\n.pnums code{font-family:ui-monospace,Menlo,monospace;font-size:11.5px;background:var(--tile);border-radius:4px;padding:0 4px}"
    "\n@media(min-width:760px){.card{display:grid;grid-template-rows:subgrid;grid-row:span 7;align-content:start}}")

RENDER_JS = """let PROPS=null;
function chips(a,cls){ return (a&&a.length)? '<div class="pchips">'+a.map(x=>'<span class="pchip'+(cls?' '+cls:'')+'">'+esc(String(x))+'</span>').join('')+'</div>' : '<p class="m">none stated</p>'; }
function prop(p){
  const nums=(p.key_numbers&&p.key_numbers.length)? '<table class="pnums">'+p.key_numbers.map(n=>'<tr><td>'+esc(String(n.name))+'</td><td><code>'+esc(String(n.value))+'</code></td></tr>').join('')+'</table>' : '<p class="m">none stated</p>';
  return '<div class="psec"><span class="lab">Mechanism</span><p>'+esc(String(p.mechanism_one_line||''))+'</p></div>'
    +'<div class="psec"><span class="lab">What changes</span>'+chips(p.what_changes)+'</div>'
    +'<div class="psec"><span class="lab">What stays</span>'+chips(p.what_stays,'k')+'</div>'
    +'<div class="psec"><span class="lab">Key numbers</span>'+nums+'</div>'
    +'<div class="psec"><span class="lab">Risk signals</span><p>'+esc((p.risk_signals||[]).map(String).join(' ')||'none stated')+'</p></div>'
    +'<div class="psec"><span class="lab">Evidence used</span><p>'+esc(String(p.evidence_used||'none stated'))+'</p></div>';
}
"""

OLD_FA = "  const fa=fmt(it[canonOf('A')]), fb=fmt(it[canonOf('B')]);\n"
OLD_CARDS = """  document.getElementById('cardA').innerHTML='<b>Attempt A &mdash; what it changes</b>'+fa.body;
  document.getElementById('cardB').innerHTML='<b>Attempt B &mdash; what it changes</b>'+fb.body;
"""
NEW_CARDS = """  if(!PROPS) PROPS=JSON.parse(atob(D.props));
  const P=PROPS[id];
  document.getElementById('cardA').innerHTML='<b>Attempt A &mdash; what it changes</b>'+prop(P[canonOf('A')]);
  document.getElementById('cardB').innerHTML='<b>Attempt B &mdash; what it changes</b>'+prop(P[canonOf('B')]);
"""

OLD_CTX = ("Long descriptions end at a fixed character budget &mdash; the model judges saw exactly "
           "the same cut text.")
NEW_CTX = ("Each attempt is shown as a proposal card, normalized from its blinded description by one fixed "
           "editor model; the model judges you are compared against answered on exactly this same document.")

OLD_VER = "v:'quiz-poolv2-v9'+(D.slice?'-slice'+D.slice:'')"
NEW_VER = "v:'quiz-proposal-v11'+(D.slice?'-slice'+D.slice:'')"

OLD_NOTE = "Judge the attempts from mechanism alone."
NEW_NOTE = ("Judge the attempts from mechanism alone. Both attempts appear in the same normalized proposal "
            "format; the frontier models on your results board judged exactly the same documents.")

n_ok = 0
for f in sorted(glob.glob("/Users/minglai.yang/Desktop/bolebench-site/bole-quiz-*.html")):
    s = open(f).read()
    if '"props"' in s.split("const D = ")[1][:200000]:
        print(f"{f}: already patched, skipping"); continue
    i = s.find("const D = ")
    d, end = json.JSONDecoder().raw_decode(s[i + len("const D = "):])
    assert set(d["pool"]) <= set(props), f"{f}: missing proposals"
    for j, pk in mp.items():
        assert set(d["pool"]) <= set(pk), f"{f}: judge {j} missing picks"
    slice_props = {iid: props[iid] for iid in d["pool"]}
    slice_mp = {j: {iid: pk[iid] for iid in d["pool"]} for j, pk in mp.items()}
    d["props"] = base64.b64encode(json.dumps(slice_props, separators=(",", ":")).encode()).decode()
    d["mp"] = base64.b64encode(json.dumps(slice_mp, separators=(",", ":")).encode()).decode()
    for iid in list(d["items"]):
        d["items"][iid].pop("A", None); d["items"][iid].pop("B", None)
    new_d = json.dumps(d, separators=(",", ":"))
    s = s[:i] + "const D = " + new_d + s[i + len("const D = ") + end:]
    for old, new in [(CSS_OLD, CSS_NEW), (OLD_FA, ""), (OLD_CARDS, NEW_CARDS),
                     (OLD_CTX, NEW_CTX), (OLD_VER, NEW_VER), (OLD_NOTE, NEW_NOTE)]:
        assert old in s, f"{f}: anchor missing: {old[:60]}"
        s = s.replace(old, new)
    s = s.replace("function show(){", RENDER_JS + "function show(){", 1)
    open(f, "w").write(s)
    n_ok += 1
print(f"patched {n_ok}/20 slices -> quiz-proposal-v11")
