#!/usr/bin/env python3
"""Render the daily email (HTML + plain text) from data/recommendations.json,
data/listings.json and data/changes.json. Fixed layout so every morning looks
the same; Claude only supplies the judgement in recommendations.json.

Writes data/email.html and data/email.txt and prints the subject line.
"""
import datetime
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
CFG = json.load(open(ROOT / "config.json", encoding="utf-8"))


def load(name, default):
    try:
        return json.load(open(DATA / name, encoding="utf-8"))
    except Exception:
        return default


R = load("recommendations.json", {})
L = load("listings.json", {"stats": {}, "listings": []})
C = load("changes.json", {"new": [], "gone": [], "price_changes": []})
S = L.get("stats", {})
by_id = {}
for _l in L.get("listings", []):
    by_id[_l["id"]] = _l
    for _a in _l.get("alt_ids", []):
        by_id[_a] = _l
date = R.get("date") or S.get("date") or datetime.date.today().isoformat()
site = CFG["site_url"]
doc = CFG["doc_url"]

def kr(n):
    return "–" if n is None else f"{int(n):,}".replace(",", " ") + " kr"

def e(s):
    return html.escape(str(s if s is not None else ""))

picks = R.get("top", R.get("top3", []))
n_cuts = S.get("price_cuts", 0)
subject = f"{CFG.get('profile_title', 'Gård-radar')} {date}: {S.get('matched', '?')} träffar, {S.get('new', '?')} nya, {n_cuts} prissänkningar"

# ---------- criteria box (what the judgement is based on) ----------
criteria_surv = [
    "Hem för två: beboeligt hus utan renovering, helst enplan eller sovrum och badrum på entréplan, fiber, vårdcentral inom 25 min och mataffär inom 15",
    "Självförsörjning: egen brunn, odlingsbar mark, plats för höns och gärna får, ved från egen skog, vedeldning plus värmepump",
    "Plats för hela familjen: andra bostad, flygel eller minst fem rum",
    "Max 60 minuter från Göteborg, grannar inom synhåll, levande bygd",
]
criteria_fin = [
    "Nära Göteborg håller huset värdet bäst i landet och går alltid att sälja",
    "Pris per hektar under medianen bland träffarna",
    "Skog och åker i södra Sverige nära rekordnivå, färre affärer ger förhandlingsläge",
    "Inte mer skog eller byggnader än Mina och Parviz kan sköta",
]

# ---------- HTML ----------
css = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:14px;color:#1f2a1f;line-height:1.45;margin:0;padding:0;background:#f6f4ee}
.wrap{max-width:900px;margin:0 auto;padding:18px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:22px 0 8px;border-bottom:1px solid #ddd;padding-bottom:4px}
.sub{color:#666;margin-bottom:12px}
.kpis td{padding:8px 12px;background:#fff;border:1px solid #e3e0d6;border-radius:8px;text-align:center}
.kpis b{font-size:20px;display:block}
.crit{display:table;width:100%}.crit td{vertical-align:top;width:50%;padding:0 8px 0 0}
ul{margin:4px 0 0 18px;padding:0}li{margin:2px 0}
table.t{border-collapse:collapse;width:100%;background:#fff;table-layout:fixed}
table.t th{background:#2f6b3a;color:#fff;text-align:left;padding:8px;font-size:12px;vertical-align:top}
table.t td{border-bottom:1px solid #e3e0d6;padding:8px;vertical-align:top;font-size:13px}
table.t tr:nth-child(even) td{background:#fafaf7}
.rank{font-size:20px;font-weight:700;color:#2f6b3a;text-align:center}
.rec{font-weight:700}.rec.go{color:#2f6b3a}.rec.watch{color:#b5541c}.rec.skip{color:#888}
.small{font-size:12px;color:#666}
a{color:#2f6b3a}
"""

def rec_class(txt):
    t = (txt or "").lower()
    if t.startswith(("boka", "book")) or "boka visning" in t:
        return "go"
    if t.startswith(("fråga", "bevaka", "ask", "watch", "wait")) or "vänta" in t:
        return "watch"
    if t.startswith(("hoppa", "skip")):
        return "skip"
    return "watch"

rows = []
for i, p in enumerate(picks, 1):
    l = by_id.get(p.get("id"), {})
    title = p.get("title") or l.get("title", "")
    url = p.get("url") or l.get("url", "")
    facts = " · ".join(x for x in [
        f"{e(p.get('kommun') or l.get('kommun'))} ({e(l.get('region', ''))})",
        kr(p.get("price") or l.get("price")),
        f"{p.get('land_ha') or l.get('land_ha') or '?'} ha",
        f"{l.get('living_m2')} m²" if l.get("living_m2") else "",
        f"byggår {l.get('build_year')}" if l.get("build_year") else "",
        f"{l.get('drive_h')} h från Göteborg" if l.get("drive_h") else "",
        f"score {p.get('score') or l.get('score')}",
    ] if x)
    rows.append(f"""
<tr>
 <td class="rank">{i}</td>
 <td><a href="{e(url)}"><b>{e(title)}</b></a><br><span class="small">{facts}</span>
     {('<br><span class="small"><b>Underhåll:</b> ' + e(p.get('maintenance')) + '</span>') if p.get('maintenance') else ''}</td>
 <td>{e(p.get('home_why') or p.get('prepping_why') or p.get('why'))}</td>
 <td>{e(p.get('safehouse_why'))}</td>
 <td>{e(p.get('invest_why'))}</td>
 <td>{e(p.get('rank_why'))}</td>
 <td class="rec {rec_class(p.get('recommendation'))}">{e(p.get('recommendation'))}</td>
</tr>""")

changes_html = ""
if C.get("first_run"):
    changes_html = "<p>Första körningen: allt räknas som nytt.</p>"
else:
    items = []
    for x in (C.get("new") or [])[:10]:
        items.append(f"<li><b>Nytt</b>: <a href=\"{e(x['url'])}\">{e(x['title'])}</a>, {e(x['kommun'])}, {kr(x['price'])}, score {x.get('score')}</li>")
    for x in (C.get("price_changes") or [])[:10]:
        arrow = "sänkt" if x["new"] < x["old"] else "höjt"
        items.append(f"<li><b>Pris {arrow}</b>: <a href=\"{e(x['url'])}\">{e(x['title'])}</a>, {kr(x['old'])} to {kr(x['new'])}</li>")
    for x in (C.get("gone") or [])[:10]:
        items.append(f"<li><b>Borta</b>: {e(x.get('title'))}, {e(x.get('kommun'))}, {kr(x.get('price'))}</li>")
    changes_html = "<ul>" + "".join(items) + "</ul>" if items else "<p>Inga förändringar sedan förra veckan.</p>"

dropped_html = ""
if R.get("dropped"):
    dropped_html = "<p class=\"small\"><b>Lämnade listan:</b> " + "; ".join(f"{e(d.get('title'))} ({e(d.get('why'))})" for d in R["dropped"]) + "</p>"
watch_html = ""
if R.get("watch"):
    watch_html = ("<p class=\"small\"><b>Bevakas:</b> " +
                  "; ".join(f"{e(w.get('title'))} ({e(w.get('note'))})" for w in R["watch"]) + "</p>")
crit_changes_html = ""
if R.get("criteria_changes"):
    crit_changes_html = "<p class=\"small\"><b>Kriterier uppdaterade från plandokumentet:</b> " + "; ".join(e(x) for x in R["criteria_changes"]) + "</p>"

region_rows = "".join(
    f"<tr><td>{e(k)}</td><td>{v['count']}</td><td>{v.get('new', 0)}</td><td>{kr(v.get('median_price'))}</td></tr>"
    for k, v in sorted((S.get("by_region") or {}).items(), key=lambda kv: -kv[1]["count"]))

html_out = f"""<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="wrap">
<h1>{e(CFG.get("profile_title", "Gård-radar"))} {e(date)}</h1>
<div class="sub">{S.get('matched', '?')} träffar · {S.get('new', 0)} nya · {S.get('gone', 0)} borta · {n_cuts} prissänkningar · medianpris {kr(S.get('median_price'))} · median {kr(S.get('median_price_per_ha'))} per ha</div>

<h2>Läget i korthet</h2>
<p>{e(R.get('market_summary') or 'Ingen bedömning skriven i dag.')}</p>

<h2>Veckans förslag</h2>
<table class="t">
<tr><th style="width:3%">#</th><th style="width:17%">Objekt</th><th style="width:20%">Hem för Mina och Parviz</th><th style="width:20%">Safe house för familjen</th><th style="width:15%">Ekonomi</th><th style="width:12%">Varför denna plats</th><th style="width:13%">Rekommendation</th></tr>
{''.join(rows) if rows else '<tr><td colspan="7">Inget objekt klarade ribban i dag.</td></tr>'}
</table>
{dropped_html}
{crit_changes_html}
{watch_html}

<h2>Vad förslagen bedöms på</h2>
<div class="crit"><table width="100%"><tr>
<td><b>Hem och trygghet</b><ul>{''.join(f'<li>{e(x)}</li>' for x in criteria_surv)}</ul></td>
<td><b>Ekonomi</b><ul>{''.join(f'<li>{e(x)}</li>' for x in criteria_fin)}</ul></td>
</tr></table></div>
<p class="small">Fullständiga kriterier och vikter: <a href="{e(doc)}">plandokumentet</a>, avsnitt 5, 6 och 8. Ändra i dokumentet så följer morgondagens körning med.</p>

<h2>Marknad per område</h2>
<table class="t"><tr><th>Område</th><th>Träffar</th><th>Nya</th><th>Medianpris</th></tr>{region_rows}</table>

<h2>Förändringar sedan förra veckan</h2>
{changes_html}

<p><a href="{e(site)}"><b>Öppna radarsajten</b></a> (alla {S.get('matched', '?')} träffar, filter, poäng) · <a href="{e(doc)}">Plandokumentet</a></p>
<p class="small">Källor: Hemnet och Booli, skannat {e(L.get('generated', ''))}. Poängen är en nyckelordsbaserad förpoäng; urvalet och motiveringarna är Claudes bedömning. Kontrollera allt på visningen.</p>
</div></body></html>"""

# ---------- plain text fallback ----------
lines = [f"{CFG.get('profile_title', 'GÅRD-RADAR').upper()} {date}", subject.split(': ', 1)[1] if ': ' in subject else "", "",
         "LÄGET I KORTHET", R.get("market_summary") or "Ingen bedömning skriven i dag.", "", "VECKANS FÖRSLAG"]
for i, p in enumerate(picks, 1):
    l = by_id.get(p.get("id"), {})
    lines += [f"{i}. {p.get('title') or l.get('title')}, {p.get('kommun') or l.get('kommun')}, {kr(p.get('price') or l.get('price'))}, {p.get('land_ha') or l.get('land_ha') or '?'} ha",
              f"   Hem: {p.get('home_why') or p.get('prepping_why') or p.get('why') or ''}",
              f"   Safe house: {p.get('safehouse_why') or ''}",
              f"   Ekonomi: {p.get('invest_why') or ''}",
              f"   Varför denna plats: {p.get('rank_why') or ''}",
              f"   Underhåll: {p.get('maintenance') or ''}",
              f"   Rekommendation: {p.get('recommendation') or ''}",
              f"   {p.get('url') or l.get('url') or ''}", ""]
if R.get("dropped"):
    lines += ["Lämnade listan: " + "; ".join(f"{d.get('title')} ({d.get('why')})" for d in R["dropped"]), ""]
if R.get("watch"):
    lines += ["BEVAKAS: " + "; ".join(f"{w.get('title')} ({w.get('note')})" for w in R["watch"]), ""]
lines += ["BEDÖMS PÅ", "Hem och trygghet: " + "; ".join(criteria_surv), "Ekonomi: " + "; ".join(criteria_fin), "",
          "FÖRÄNDRINGAR", f"Nya {S.get('new', 0)}, borta {S.get('gone', 0)}, prissänkningar {n_cuts}.", "",
          f"Sajt: {site}", f"Plandokument: {doc}"]
text_out = "\n".join(lines)

(DATA / "email.html").write_text(html_out, encoding="utf-8")
(DATA / "email.txt").write_text(text_out, encoding="utf-8")
print(subject)
print(f"html {len(html_out)} chars -> {DATA/'email.html'}; text {len(text_out)} chars -> {DATA/'email.txt'}")
