#!/usr/bin/env python3
"""Chem Builder (EA FC 27) -- local tool. Standard library only.

  python chem_builder.py --app        open as a desktop app (own window, needs: pip install pywebview==6.2.1)
  python chem_builder.py              start the app in your web browser at http://127.0.0.1:8765
  python chem_builder.py --sync       refresh cards.json from FUT.GG first (then start)
  python chem_builder.py --sync-only  refresh and exit
  options: --min-rating 75  --port 8765  --no-browser  --stay (don't stop when the last app tab closes)

Started with pythonw (what start.bat does) there is no console window: output goes to chem_builder.log,
the app stops by itself shortly after its last browser tab is closed, and starting it again while it is
already running just opens the page.

Card data comes from FUT.GG's public JSON feed (the same one its own player list uses).
It is fetched politely (one request every ~0.4 s) and cached in cards.json next to this file.
"""
import argparse
import json
import os
import re
import socket
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import chem_engine as eng

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = getattr(sys, "frozen", False)                       # running as ChemBuilder.exe (PyInstaller)
BUNDLE = getattr(sys, "_MEIPASS", HERE)                       # where ui.html / the shipped cards.json live
DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"),
                        "ChemBuilder" if os.environ.get("APPDATA") else ".chembuilder")
CACHE = os.path.join(DATA_DIR if FROZEN else HERE, "cards.json")   # the .exe keeps updatable card data in AppData
UI = os.path.join(BUNDLE, "ui.html")
STATE_FILE = os.path.join(DATA_DIR, "state.json")             # saved squads, blacklist, preferences, settings
API = "https://www.fut.gg/api/fut/players/v2/27/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
LOG = os.path.join(DATA_DIR if FROZEN else HERE, "chem_builder.log")
PSEUDO_CLUBS = {"ICON", "HERO", "HALL OF FUT"}

STATE = {"cards": [], "meta": {}, "by_slug": {}, "by_bp": {}, "sync": {"running": False, "msg": "", "done": 0, "total": 0}}

# ------------------------------------------------------------------ formations
# FC 27 Ultimate Team formations, copied from FUT.GG's squad-builder data (8 Oct 2026). The list matches
# FIFPlay's FC 27 Ultimate Team list, plus 4-4-1-1, which FIFPlay leaves out but FUT.GG's tactics stats
# show pros using. Slots are FUT.GG "unique position" ids in FUT.GG's positionIdx order, so slot k of a
# FUT.GG squad is slot k here. FC 25+ has no LWB/RWB/CF: 5-back formations use RB/LB.
UNIQUE_POS = {0: "GK", 3: "RB", 4: "CB", 5: "CB", 6: "CB", 7: "LB", 9: "CDM", 10: "CDM", 11: "CDM",
              12: "RM", 13: "CM", 14: "CM", 15: "CM", 16: "LM", 17: "CAM", 18: "CAM", 19: "CAM",
              23: "RW", 24: "ST", 25: "ST", 26: "ST", 27: "LW"}
FORMATION_DATA = [  # (FUT.GG formation id, name, unique position ids)
    (22, "3-1-4-2", (0, 4, 5, 6, 10, 12, 13, 15, 16, 24, 26)),
    (23, "3-4-1-2", (0, 4, 5, 6, 12, 13, 15, 16, 18, 24, 26)),
    (24, "3-4-2-1", (0, 4, 5, 6, 12, 13, 15, 16, 17, 19, 25)),
    (25, "3-4-3", (0, 4, 5, 6, 12, 13, 15, 16, 23, 25, 27)),
    (27, "3-5-2", (0, 4, 5, 6, 9, 11, 12, 16, 18, 24, 26)),
    (14, "4-1-2-1-2", (0, 3, 4, 6, 7, 10, 12, 16, 18, 24, 26)),
    (15, "4-1-2-1-2 (2)", (0, 3, 4, 6, 7, 10, 13, 15, 18, 24, 26)),
    (1, "4-1-3-2", (0, 3, 4, 6, 7, 10, 12, 14, 16, 24, 26)),
    (2, "4-1-4-1", (0, 3, 4, 6, 7, 10, 12, 13, 15, 16, 25)),
    (36, "4-2-1-3", (0, 3, 4, 6, 7, 9, 11, 18, 23, 25, 27)),
    (13, "4-2-2-2", (0, 3, 4, 6, 7, 9, 11, 17, 19, 24, 26)),
    (3, "4-2-3-1", (0, 3, 4, 6, 7, 9, 11, 17, 18, 19, 25)),
    (4, "4-2-3-1 (2)", (0, 3, 4, 6, 7, 9, 11, 12, 16, 18, 25)),
    (5, "4-2-4", (0, 3, 4, 6, 7, 13, 15, 23, 24, 26, 27)),
    (6, "4-3-1-2", (0, 3, 4, 6, 7, 13, 14, 15, 18, 24, 26)),
    (7, "4-3-2-1", (0, 3, 4, 6, 7, 13, 14, 15, 17, 19, 25)),
    (8, "4-3-3", (0, 3, 4, 6, 7, 13, 14, 15, 23, 25, 27)),
    (9, "4-3-3 (2)", (0, 3, 4, 6, 7, 10, 13, 15, 23, 25, 27)),
    (10, "4-3-3 (3)", (0, 3, 4, 6, 7, 9, 11, 14, 23, 25, 27)),
    (11, "4-3-3 (4)", (0, 3, 4, 6, 7, 13, 15, 18, 23, 25, 27)),
    (18, "4-4-1-1", (0, 3, 4, 6, 7, 12, 13, 15, 16, 18, 25)),
    (16, "4-4-2", (0, 3, 4, 6, 7, 12, 13, 15, 16, 24, 26)),
    (17, "4-4-2 (2)", (0, 3, 4, 6, 7, 9, 11, 12, 16, 24, 26)),
    (21, "4-5-1", (0, 3, 4, 6, 7, 12, 14, 16, 17, 19, 25)),
    (20, "4-5-1 (2)", (0, 3, 4, 6, 7, 12, 13, 14, 15, 16, 25)),
    (29, "5-2-1-2", (0, 3, 4, 5, 6, 7, 13, 15, 18, 24, 26)),
    (30, "5-2-3", (0, 3, 4, 5, 6, 7, 13, 15, 23, 25, 27)),
    (31, "5-3-2", (0, 3, 4, 5, 6, 7, 10, 13, 15, 24, 26)),
    (33, "5-4-1", (0, 3, 4, 5, 6, 7, 12, 13, 15, 16, 25)),
]
FORMATIONS = {name: {"name": name, "fgg": fid, "uids": list(u), "slots": [UNIQUE_POS[x] for x in u]}
              for fid, name, u in FORMATION_DATA}
FORMATION_BY_FGG = {fid: name for fid, name, _ in FORMATION_DATA}


# ------------------------------------------------------------------ data

def fold(s):
    return "".join(ch for ch in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(ch)).lower()


def normalize_card(r):
    uc = r.get("uniqueClub") or {}
    club = r.get("club") or None
    club_name = (club or {}).get("name") or ""
    pseudo = bool(uc.get("isIconClub")) or club_name in PSEUDO_CLUBS or uc.get("name") in PSEUDO_CLUBS
    ck, cn = None, None
    if club and not pseudo:
        ids = [x for x in (uc.get("eaId"), uc.get("siblingClubEaId"), uc.get("sisterClubEaId")) if x]
        ck = str(min(ids)) if ids else str(club.get("eaId"))
        cn = club_name
    rarity = r.get("rarityName") or ""
    ty = "icon" if r.get("isIcon") else "hero" if r.get("isHero") else \
        "hof" if ("Hall of FUT" in rarity or club_name == "HALL OF FUT") else ""
    nat, lg = r.get("nation") or {}, r.get("league") or {}
    return {
        "s": r["slug"], "n": r.get("cardName") or r.get("commonName") or r.get("lastName"),
        "fn": " ".join(x for x in (r.get("firstName"), r.get("lastName"), r.get("nickname")) if x),
        "ov": r["overall"], "rt": rarity, "g": r.get("gender") or 1,
        "p": r.get("position"), "a": list(r.get("alternativePositions") or []),
        "ni": nat.get("eaId"), "nn": nat.get("name"), "li": lg.get("eaId"), "ln": lg.get("name"),
        "ck": ck, "cn": cn, "ty": ty, "bp": r.get("basePlayerEaId") or r.get("eaId"),
        "gg": r.get("playerScore") or None,  # FUT.GG score; display only, never used for ranking (empty in FC 27 feed so far)
        "fc": bool(r.get("isFullChemistry")),
        "xc": int(r.get("extraClubChemistry") or 0), "xl": int(r.get("extraLeagueChemistry") or 0),
        "xn": int(r.get("extraNationChemistry") or 0),
        "xsl": bool(r.get("extraSquadLeagueChemistry")), "xsn": bool(r.get("extraSquadNationChemistry")),
        "fs": face_stats(r),
        "ps": [int(x) for x in r.get("playStyleEaIds") or []],      # PlayStyles (ids, see PLAYSTYLES)
        "pp": [int(x) for x in r.get("playStylePlusEaIds") or []],  # PlayStyle+ (ids)
    }


# PlayStyle ids used by FUT.GG's feed -> FC 27 display names (from FUT.GG's site code, Oct 2026;
# "Rush Out" is shown in FC 27 as "1v1 Close Down").
PLAYSTYLES = {0: "Finesse Shot", 1: "Chip Shot", 2: "Power Shot", 3: "Dead Ball", 4: "Power Header", 5: "Incisive Pass",
              6: "Pinged Pass", 7: "Long Ball", 8: "Tiki Taka", 9: "Whipped Pass", 10: "Jockey", 11: "Block",
              12: "Intercept", 13: "Anticipate", 14: "Slide Tackle", 15: "Bruiser", 16: "Technical", 17: "Rapid",
              18: "Flair", 19: "First Touch", 20: "Trickster", 21: "Press Proven", 22: "Quick Step", 23: "Relentless",
              24: "Trivela", 25: "Acrobatic", 26: "Long Throw", 27: "Aerial", 28: "Far Throw", 29: "Footwork",
              30: "Cross Claimer", 31: "1v1 Close Down", 32: "Far Reach", 33: "Deflector", 34: "Low Driven Shot",
              35: "Aerial Fortress", 36: "Enforcer", 37: "Gamechanger", 38: "Inventive", 39: "Precision Header"}
GK_PLAYSTYLES = {28, 29, 30, 31, 32, 33}


OUTFIELD_FACE = ("facePace", "faceShooting", "facePassing", "faceDribbling", "faceDefending", "facePhysicality")
GK_FACE = ("gkFaceDiving", "gkFaceHandling", "gkFaceKicking", "gkFaceReflexes", "gkFaceSpeed", "gkFacePositioning")


def face_stats(r):
    """The six numbers printed on the card: PAC SHO PAS DRI DEF PHY, or DIV HAN KIC REF SPE POS for keepers."""
    v2 = r.get("faceStatsV2") or {}
    keys = GK_FACE if r.get("position") == "GK" else OUTFIELD_FACE
    vals = [v2.get(k) for k in keys]
    return [int(x) for x in vals] if all(isinstance(x, (int, float)) and x > 0 for x in vals) else None


def explain_error(e):
    """Turn a urllib/ssl/socket exception into something that names the actual cause."""
    import ssl
    if isinstance(e, urllib.error.HTTPError):
        if e.code == 403 and (e.headers or {}).get("cf-mitigated") == "challenge":
            return ("HTTP 403 - FUT.GG puts this data behind a Cloudflare browser check that only a real browser "
                    "can pass, so programs (this app included) can't read it. Not a problem on your PC or network.")
        hint = {403: "blocked by FUT.GG or a firewall", 429: "rate limited - wait a minute and retry",
                404: "endpoint not found (FUT.GG may have changed its feed)"}.get(e.code, "")
        return f"HTTP {e.code} {e.reason}" + (f" - {hint}" if hint else "")
    r = getattr(e, "reason", e)
    if isinstance(r, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(r):
        return "TLS certificate check failed - a firewall/antivirus doing HTTPS inspection is the usual cause (" + str(r) + ")"
    if isinstance(r, socket.gaierror):
        return "DNS lookup failed - no internet, DNS filter, or fut.gg blocked (" + str(r) + ")"
    if isinstance(r, (socket.timeout, TimeoutError)):
        return "timed out - network or firewall dropping the connection"
    return f"{type(r).__name__}: {r}"


def fetch_json(url, tries=4):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                break  # 403/404 will not fix themselves on retry
            time.sleep(3 * (k + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"{explain_error(last)}  [{url}]")


def diagnose():
    """Step-by-step connection test shown by the app and by --check."""
    steps = []
    steps.append({"step": "cards.json", "ok": bool(STATE["cards"]),
                  "detail": f"{CACHE} - {len(STATE['cards'])} cards loaded" if STATE["cards"] else f"not found or empty at {CACHE}"})
    try:
        socket.getaddrinfo("www.fut.gg", 443)
        steps.append({"step": "DNS www.fut.gg", "ok": True, "detail": "resolved"})
    except Exception as e:  # noqa: BLE001
        steps.append({"step": "DNS www.fut.gg", "ok": False, "detail": explain_error(e)})
        return steps
    try:
        t = time.time()
        d = fetch_json(f"{API}?page=1&overall__gte=90", tries=1)
        steps.append({"step": "FUT.GG player feed", "ok": True,
                      "detail": f"{len(d.get('data', []))} cards in {time.time() - t:.1f}s (feed total {d.get('total')})"})
    except Exception as e:  # noqa: BLE001
        steps.append({"step": "FUT.GG player feed", "ok": False, "detail": str(e)})
    return steps


def sync_cards(min_rating=75, status=None):
    status = status if status is not None else STATE["sync"]
    status.update(running=True, msg="starting", done=0, total=0)
    cards, page = [], 1
    try:
        while True:
            d = fetch_json(f"{API}?page={page}&overall__gte={min_rating}")
            for r in d.get("data", []):
                try:
                    cards.append(normalize_card(r))
                except Exception:  # noqa: BLE001
                    continue
            status.update(done=len(cards), total=d.get("total", 0), msg=f"page {page}")
            if not d.get("next"):
                break
            page += 1
            time.sleep(0.4)
        seen, uniq = set(), []
        for c in cards:
            if c["s"] not in seen:
                seen.add(c["s"])
                uniq.append(c)
        meta = {"synced_at": time.strftime("%Y-%m-%d %H:%M:%S"), "min_rating": min_rating,
                "source": "fut.gg", "game": "FC 27", "count": len(uniq)}
        tmp = CACHE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "cards": uniq}, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, CACHE)
        load_cache()
        status.update(running=False, msg=f"done: {len(uniq)} cards")
    except Exception as e:  # noqa: BLE001
        status.update(running=False, msg=f"failed: {e}")


def ensure_cards():
    """The .exe ships a cards.json; copy it to AppData unless the copy there is newer (e.g. after an update)."""
    shipped = os.path.join(BUNDLE, "cards.json")
    if not FROZEN or not os.path.exists(shipped):
        return
    def synced(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f).get("meta", {}).get("synced_at", "")
        except Exception:  # noqa: BLE001
            return ""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CACHE) or synced(shipped) > synced(CACHE):
        import shutil
        shutil.copyfile(shipped, CACHE)


# ------------------------------------------------------------------ saved state (squads, blacklist, preferences)
# Kept in a file rather than browser storage so the desktop window and a browser tab share it.
STATE_LOCK = threading.Lock()


def read_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def write_state(updates):
    """updates: {key: string value, or None to delete}."""
    with STATE_LOCK:
        d = read_state()
        for k, v in updates.items():
            if not isinstance(k, str) or not k.startswith("chemBuilder."):
                continue
            if v is None:
                d.pop(k, None)
            else:
                d[k] = str(v)
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
        return d


# ------------------------------------------------------------------ hand-off from the browser to the app window
# The FUTBIN bookmark and share links open http://127.0.0.1:8765/send?... in the web browser. When the desktop
# window is open, the request is queued and the window picks it up on its next ping; otherwise the browser
# tab handles it itself.
INBOX = []


def load_cache():
    if not os.path.exists(CACHE):
        STATE.update(cards=[], meta={}, by_slug={})
        return
    with open(CACHE, encoding="utf-8") as f:
        d = json.load(f)
    cards = d["cards"]
    for c in cards:
        c["_k"] = fold(c.get("fn") or c["n"]) + " " + fold(c["n"])
    by_bp = {}
    for c in cards:
        by_bp.setdefault(c["bp"], []).append(c)
    STATE.update(cards=cards, meta=d.get("meta", {}), by_slug={c["s"]: c for c in cards}, by_bp=by_bp)


def public(c):
    return {k: v for k, v in c.items() if k != "_k"}


def versions(card, limit=12):
    """Other cards of the same player (base, specials, ...), best first. Used for the 'wrong version' dropdown."""
    vs = [c for c in STATE["by_bp"].get(card.get("bp"), []) if c["s"] != card["s"]]
    vs.sort(key=lambda c: -c["ov"])
    return [public(c) for c in vs[:limit]]


def meta_lists():
    nations, leagues, clubs = {}, {}, {}
    for c in STATE["cards"]:
        if c["ni"] is not None:
            nations[c["ni"]] = c["nn"]
        if c["li"] is not None:
            leagues[c["li"]] = c["ln"]
        if c.get("ck"):
            clubs[c["ck"]] = c["cn"]
    srt = lambda m: sorted(([k, v] for k, v in m.items()), key=lambda kv: fold(kv[1]))  # noqa: E731
    return {"nations": srt(nations), "leagues": srt(leagues), "clubs": srt(clubs)}


# ------------------------------------------------------------------ search / pool

def search_cards(q, live=False, limit=40):
    """Returns {"hits": [...], "live_error": str|None}."""
    toks = fold(q).split()
    if not toks:
        return {"hits": [], "live_error": None}
    live_error = None
    hits = [c for c in STATE["cards"] if all(t in c["_k"] for t in toks)]
    hits.sort(key=lambda c: -c["ov"])
    out = [public(c) for c in hits[:limit]]
    if live and len(out) < limit:
        try:
            d = fetch_json(f"{API}?name={urllib.parse.quote(q)}", tries=2)
            have = {c["s"] for c in out}
            for r in d.get("data", []):
                c = normalize_card(r)
                if c["s"] not in have:
                    c["live"] = True
                    out.append(c)
        except Exception as e:  # noqa: BLE001
            live_error = str(e)
    return {"hits": out[:limit], "live_error": live_error}


POS_TOKENS = {"GK", "LB", "LWB", "CB", "RB", "RWB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "CF", "ST"}
MONEYISH = re.compile(r"^[\d.,]+[kKmM]?$")


def parse_line(line):
    """Pull (position, name, rating) out of a pasted line. Tolerant of tabs, numbering, prices.
    Works for 'ST Mbappe 91', 'Mbappe 91 ST', 'Mbappe', and copied table rows."""
    s = re.sub(r"^\s*(?:[-*•]|\d{1,2}[.)])\s+", "", line.strip())
    if not s:
        return None
    cols = [c.strip() for c in re.split(r"\t|\s{2,}|\|", s) if c.strip()]
    if len(cols) == 1:
        cols = s.split()
        single = True
    else:
        single = False
    pos, rating, name_cols = None, None, []
    for c in cols:
        if c.upper() in POS_TOKENS and pos is None:
            pos = c.upper()
        elif c.isdigit() and 40 <= int(c) <= 99 and rating is None:
            rating = int(c)
        elif MONEYISH.match(c) or c.upper() in POS_TOKENS:
            continue
        else:
            name_cols.append(c)
    if not name_cols:
        return None
    if single:
        name = " ".join(name_cols)
    else:
        name = name_cols[0]
    return {"pos": pos, "name": name, "rating": rating, "raw": line.strip()}


def find_cards(name, rating=None):
    toks = fold(name).split()
    if not toks:
        return []
    hits = [c for c in STATE["cards"] if all(t in c["_k"] for t in toks)]
    if rating is not None:
        exact = [c for c in hits if c["ov"] == rating]
        hits = exact or hits
    return hits


def build_pool(opts):
    gender = int(opts.get("gender") or 0)
    excl = set(opts.get("exclude_types") or [])
    banned = {str(x) for x in opts.get("blacklist") or []}  # base player ids: every version of the player
    pool = [c for c in STATE["cards"] if (not gender or c["g"] == gender) and c["ty"] not in excl
            and str(c["bp"]) not in banned]
    unmatched = []
    lines = [ln for ln in (opts.get("club_list") or "").splitlines() if ln.strip()]
    if lines:
        chosen = {}
        for ln in lines:
            slug_hit = STATE["by_slug"].get(ln.strip())
            if slug_hit:
                chosen[slug_hit["s"]] = slug_hit
                continue
            p = parse_line(ln)
            found = find_cards(p["name"], p["rating"]) if p else []
            if not found:
                unmatched.append(ln.strip())
            for c in found:
                chosen[c["s"]] = c
        pool = [c for c in chosen.values() if (not gender or c["g"] == gender) and c["ty"] not in excl
                and str(c["bp"]) not in banned]
    return pool, unmatched


def seat(entries, slots):
    """Best slot for each entry. entries: [(card, wanted_pos|None)], at most len(slots).
    Exact assignment (bitmask DP, 11 slots = 2048 states): maximise players in a preferred position,
    then players in the position they asked for, keeping the given order as the tie-break."""
    n, m = len(entries), len(slots)
    fits = [[slots[j] in {c["p"], *c["a"]} for j in range(m)] for c, _ in entries]
    score = [[(100 if fits[i][j] else 0) + (10 if entries[i][1] == slots[j] else 0) for j in range(m)]
             for i in range(n)]
    best = {0: (0, [])}
    for i in range(n):
        nxt = {}
        for mask, (sc, picks) in best.items():
            for j in range(m):
                if mask >> j & 1:
                    continue
                cand = (sc + score[i][j], picks + [j])
                key = mask | 1 << j
                if key not in nxt or cand[0] > nxt[key][0]:
                    nxt[key] = cand
        best = nxt
    return max(best.values(), key=lambda v: v[0])[1] if n else []


def build_preview(entries, slots, extra=None, notes=None, unmatched=None, **more):
    """Turn [(card, wanted_pos, source_text)] into slot rows the UI shows before anything is changed."""
    notes, unmatched = list(notes or []), list(unmatched or [])
    starters, extra = entries[:len(slots)], list(extra or []) + [e[0] for e in entries[len(slots):]]
    picks = seat([(c, w) for c, w, _ in starters], slots)
    rows = [{"slot": j, "card": None, "alts": [], "src": ""} for j in range(len(slots))]
    for (c, _, src), j in zip(starters, picks):
        rows[j].update(card=public(c), alts=versions(c), src=src)
    if len(entries) > len(slots):
        notes.append(f"{len(entries)} players found; the first {len(slots)} were placed. "
                     "The others are listed in each slot's dropdown if you want to swap one in.")
    return {"slots": slots, "rows": rows, "extra": [public(c) for c in extra], "notes": notes,
            "unmatched": unmatched, **more}


def preview_text(text, slots):
    """Pasted lines -> preview. Rating picks the version; a position puts the player in that slot."""
    entries, notes, unmatched = [], [], []
    for ln in [x for x in text.splitlines() if x.strip()]:
        p = parse_line(ln)
        if not p:
            continue
        hits = find_cards(p["name"], p["rating"])
        if not hits:
            unmatched.append(ln.strip())
            continue
        want = p["pos"]
        hits.sort(key=lambda c: (-(want in {c["p"], *c["a"]}) if want else 0,
                                 -any(s in {c["p"], *c["a"]} for s in slots), -c["ov"]))
        card = hits[0]
        if len({c["bp"] for c in hits}) > 1:
            notes.append(f"\"{p['name']}\" matches more than one player; picked {card['fn'] or card['n']}. "
                         "Use the dropdown if that's wrong.")
        entries.append((card, want, ln.strip()))
    return build_preview(entries, slots, notes=notes, unmatched=unmatched)


def cards_by_ea_ids(ids):
    """EA ids (as strings) -> ({id: card}, live_error). Missing ones are fetched from FUT.GG by id."""
    found, missing = {}, []
    for i in ids:
        c = STATE["by_slug"].get(f"27-{i}")
        if c:
            found[i] = c
        else:
            missing.append(i)
    live_error = None
    for k in range(0, len(missing), 40):
        chunk = missing[k:k + 40]
        try:
            d = fetch_json(f"{API}?ids={','.join(chunk)}", tries=2)
            for r in d.get("data", []):
                c = normalize_card(r)
                c["live"] = True
                found[str(r.get("eaId"))] = c
        except Exception as e:  # noqa: BLE001
            live_error = str(e)
    return found, live_error


def preview_ids(ids, slots):
    """EA ids in page order (from the bookmarklet on a FUTBIN squad page) -> preview."""
    ids = list(dict.fromkeys(i for i in ids if i.isdigit()))[:40]
    found, live_error = cards_by_ea_ids(ids)
    entries, seen_bp = [], set()
    for i in ids:
        c = found.get(i)
        if c and c["bp"] not in seen_bp:  # a page can show the same player twice (card + mini card)
            seen_bp.add(c["bp"])
            entries.append((c, None, f"card id {i}"))
    unmatched = [f"card id {i}" for i in ids if i not in found]
    notes = [f"Live card lookup failed: {live_error}"] if live_error else []
    return build_preview(entries, slots, notes=notes, unmatched=unmatched)


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
FGG_SQUAD_API = "https://www.fut.gg/api/squads/{uuid}/"


def parse_fgg_squad(d):
    """FUT.GG /api/squads/<uuid>/ response -> (formation name|None, {positionIdx: eaId}, manager, title, game).
    Shape read from FUT.GG's squad-builder code (Oct 2026): {"data": {"uuid", "data": {"activeFormationId",
    "managerNationId", "managerLeagueId", "title", "gameSlug", "activeGroupPositions": [{"group": "FIELD",
    "positionIdx", "playerEaId", ...}]}}}. Older saves use "activePositions" instead of activeGroupPositions."""
    outer = d.get("data", d) if isinstance(d, dict) else {}
    sq = outer.get("data", outer) if isinstance(outer, dict) else {}
    if not isinstance(sq, dict):
        raise ValueError("FUT.GG squad response not recognised")
    pos = sq.get("activeGroupPositions")
    if pos is None:
        pos = [dict(p, group="FIELD") for p in sq.get("activePositions") or []]
    if not isinstance(pos, list):
        raise ValueError("FUT.GG squad response not recognised (no player positions)")
    field = {}
    for p in pos:
        if p.get("group", "FIELD") == "FIELD" and p.get("playerEaId") and p.get("positionIdx") is not None:
            field[int(p["positionIdx"])] = str(p["playerEaId"])
    try:
        fname = FORMATION_BY_FGG.get(int(sq.get("activeFormationId")))
    except (TypeError, ValueError):
        fname = None
    mgr = {"ni": sq.get("managerNationId"), "li": sq.get("managerLeagueId")}
    return fname, field, mgr, sq.get("title") or "", str(sq.get("gameSlug") or "")


def preview_fgg(url):
    m = UUID_RE.search(url or "")
    if not m:
        raise ValueError("That doesn't look like a FUT.GG squad link (it should contain a long id like "
                         "1a2b3c4d-....). On FUT.GG open the squad, press Share, and copy the link.")
    try:
        d = fetch_json(FGG_SQUAD_API.format(uuid=m.group(0).lower()), tries=2)
    except RuntimeError as e:
        if "404" in str(e):
            raise ValueError("FUT.GG says this squad doesn't exist. Check the link, and make sure the squad "
                             "is saved on FUT.GG (press Share there, then copy the link).") from None
        raise
    fname, field, mgr, title, game = parse_fgg_squad(d)
    notes = []
    if game and game not in ("27", "fc27", "fc-27"):
        notes.append(f"This FUT.GG squad is for game '{game}', not FC 27; cards may not match.")
    if not fname:
        notes.append("The squad's formation isn't one this tool knows; players were seated by best fit.")
    slots = FORMATIONS[fname]["slots"] if fname else None
    found, live_error = cards_by_ea_ids(list(field.values()))
    if live_error:
        notes.append(f"Live card lookup failed: {live_error}")
    unmatched = [f"card id {i}" for i in field.values() if i not in found]
    if slots:
        rows = [{"slot": j, "card": None, "alts": [], "src": "FUT.GG"} for j in range(len(slots))]
        for idx, ea in field.items():
            c = found.get(ea)
            if c and 0 <= idx < len(slots):
                rows[idx].update(card=public(c), alts=versions(c))
        res = {"slots": slots, "rows": rows, "extra": [], "notes": notes, "unmatched": unmatched}
    else:
        entries = [(found[ea], None, "FUT.GG") for _, ea in sorted(field.items()) if ea in found]
        res = build_preview(entries, FORMATIONS["4-4-2"]["slots"], notes=notes, unmatched=unmatched)
        fname = "4-4-2"
    res.update(formation=fname, mgr=mgr, title=title)
    return res


def cards_for_slugs(slugs):
    """Share links carry card slugs ("27-<eaId>"). Returns {slug: card} and anything not found."""
    ids = [s.split("-", 1)[1] for s in slugs if isinstance(s, str) and s.startswith("27-")]
    found, live_error = cards_by_ea_ids(ids)
    out = {f"27-{i}": public(c) for i, c in found.items()}
    return {"cards": out, "missing": [s for s in slugs if s not in out], "live_error": live_error}


# ------------------------------------------------------------------ http

class Handler(BaseHTTPRequestHandler):
    server_version = "ChemBuilder/1.0"

    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 2_000_000:
            raise ValueError("body too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            with open(UI, "rb") as f:
                return self._send(200, f.read(), "text/html")
        if u.path == "/api/meta":
            return self._send(200, {"meta": STATE["meta"], "n": len(STATE["cards"]), **meta_lists(),
                                    "playstyles": PLAYSTYLES, "gk_playstyles": sorted(GK_PLAYSTYLES),
                                    "formations": list(FORMATIONS.values())})
        if u.path == "/api/search":
            q = (qs.get("q") or [""])[0]
            return self._send(200, search_cards(q, live=(qs.get("live") or ["0"])[0] == "1"))
        if u.path == "/api/diag":
            return self._send(200, diagnose())
        if u.path == "/api/sync_status":
            return self._send(200, STATE["sync"])
        if u.path == "/api/state":
            return self._send(200, read_state())
        if u.path == "/send":
            item = ("squad=" + qs["squad"][0]) if qs.get("squad") else ("import=" + qs["import"][0]) if qs.get("import") else ""
            if not item:
                return self._send(400, {"error": "nothing to send"})
            if LIFE.app_open():
                INBOX.append(item)
                return self._send(200, SENT_PAGE.encode("utf-8"), "text/html")
            self.send_response(302)
            self.send_header("Location", "/#" + urllib.parse.quote(item, safe="=:,-_"))
            self.end_headers()
            return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = self._body()
            if self.path == "/api/evaluate":
                fixed, free = _mgr_modes(body.get("mgr"))
                ev = eng.evaluate(body["slots"], body["squad"], fixed)
                best = eng.evaluate(body["slots"], body["squad"], free)
                return self._send(200, dict(ev, best_li=best["mgr_li"], best_total=best["total"]))
            if self.path == "/api/optimize":
                return self._send(200, self.optimize(body))
            if self.path == "/api/import_preview":
                mode = body.get("mode")
                if mode == "fgg":
                    return self._send(200, preview_fgg(body.get("url", "")))
                if mode == "ids":
                    return self._send(200, preview_ids([str(x) for x in body.get("ids") or []], body["slots"]))
                return self._send(200, preview_text(body.get("text", ""), body["slots"]))
            if self.path == "/api/cards":
                return self._send(200, cards_for_slugs(body.get("slugs") or []))
            if self.path == "/api/ping":
                LIFE.ping(body.get("tab"), app=bool(body.get("app")))
                out = {"ok": True}
                if body.get("app") and INBOX:
                    out["inbox"] = [INBOX.pop(0) for _ in range(len(INBOX))]
                return self._send(200, out)
            if self.path == "/api/state":
                return self._send(200, write_state(body.get("set") or {}))
            if self.path == "/api/open":   # the desktop window asks to open a link in the normal web browser
                url = str(body.get("url") or "")
                own = f"http://127.0.0.1:{self.server.server_address[1]}/"
                if not (url.startswith("https://www.fut.gg/") or url.startswith(own)):
                    return self._send(400, {"error": "only FUT.GG and Chem Builder links are opened"})
                webbrowser.open(url)
                return self._send(200, {"ok": True})
            if self.path == "/api/bye":
                LIFE.bye(body.get("tab"))
                return self._send(200, {"ok": True})
            if self.path == "/api/quit":
                threading.Timer(0.3, LIFE.stop).start()
                return self._send(200, {"ok": True})
            if self.path == "/api/sync":
                if STATE["sync"]["running"]:
                    return self._send(200, STATE["sync"])
                threading.Thread(target=sync_cards, args=(int(body.get("min_rating") or 75),), daemon=True).start()
                return self._send(200, {"running": True})
        except Exception as e:  # noqa: BLE001
            return self._send(400, {"error": str(e)})
        self._send(404, {"error": "not found"})

    @staticmethod
    def optimize(b):
        slots, squad, locks, mgr, o, by_pos, pool, unmatched = _search_setup(b)
        ok = None
        max_drop, min_rating = int(o.get("max_drop", 3)), int(o.get("min_rating", 0))
        fixed, free = _mgr_modes(mgr)
        val = eng.make_value(o.get("ps_prefs"), float(o.get("ps_w_plus", 3) or 0), float(o.get("ps_w", 1) or 0))
        base = eng.total_only(slots, squad, fixed)          # what the squad has right now
        base_free, li_now = eng.total_only(slots, squad, free), eng._manager_rows(slots, squad, free)[1]
        _, singles, _ = eng.top_singles(slots, squad, locks, free, by_pos, max_drop, min_rating, n=30, ok=ok, val=val)
        chain, chain_total, final = eng.plan_chain(slots, squad, locks, free, by_pos, max_drop, min_rating,
                                                   max_steps=int(o.get("max_steps", 5)), ok=ok, val=val)
        cur = list(squad)
        for st in chain:  # which manager league each step assumes (League Modifier)
            for w in st["swaps"]:
                cur[w["slot"]] = w["in"]
            st["li"] = eng._manager_rows(slots, cur, free)[1]
        k_max = max(1, min(5, int(o.get("max_steps", 5))))
        args = (slots, squad, locks, free, by_pos, max_drop, min_rating)
        combos = eng.k_swap_combos(*args, k_max=k_max, n=25, ok=ok, base=base, val=val)
        combos_mgr = eng.k_swap_combos(*args, k_max=k_max, n=25, ok=ok, base=base, mgr_change=True, val=val)
        upgrades = eng.upgrade_combos(slots, squad, locks, free, by_pos, min_rating, k_max=k_max,
                                      max_loss=max(0, int(o.get("upgrade_loss", 3))), n=25, ok=ok, base=base, val=val,
                                      max_ovr=int(o.get("upgrade_max_ovr") or 0) or None,
                                      pos_caps={k: int(v) for k, v in (o.get("upgrade_pos_caps") or {}).items() if v})
        return {                "base": base, "base_free": base_free, "li_now": li_now, "li_cur": fixed.get("li"),
                "singles": singles, "chain": chain, "chain_total": chain_total,
                "combos": combos, "combosMgr": combos_mgr, "upgrades": upgrades, "pool": len(pool), "unmatched": unmatched,
                "mgr_suggest": eng.manager_suggestions(slots, squad, fixed, top=15),
                "mgr_suggest_after": eng.manager_suggestions(slots, final, fixed)}


def _mgr_modes(mgr):
    """(current manager exactly as it is, same manager with the league free to change via League Modifier)."""
    m = {"ni": (mgr or {}).get("ni"), "li": (mgr or {}).get("li")}
    return dict(m, li_free=False), dict(m, li_free=True)


def _search_setup(b):
    slots, squad, locks, mgr = b["slots"], b["squad"], b["locks"], b.get("mgr")
    if any(c is None for c in squad):
        raise ValueError("Fill all 11 slots first.")
    o = b.get("opts", {})
    pool, unmatched = build_pool(o)
    by_pos = eng.index_pool(pool)
    return slots, squad, locks, mgr, o, by_pos, pool, unmatched


class Life:
    """Stops the app once no browser tab has been open for a while, so closing the page closes the app.
    Tabs ping every 10 s and say bye when closed. Hidden tabs can be throttled to one timer a minute,
    so a tab only counts as gone after 10 minutes of silence; a bye ends it after GRACE seconds
    (a page reload says bye and pings again well inside that)."""
    GRACE, SILENT = 30, 600

    def __init__(self):
        self.tabs, self.server, self.enabled, self.empty_since, self.seen_any = {}, None, False, None, False
        self.app_seen = 0.0
        self.lock = threading.Lock()

    def app_open(self):
        return time.time() - self.app_seen < 25  # the app window pings every 10 s

    def ping(self, tab, app=False):
        if app:
            self.app_seen = time.time()
        with self.lock:
            self.tabs[str(tab)] = time.time()
            self.empty_since, self.seen_any = None, True

    def bye(self, tab):
        with self.lock:
            self.tabs.pop(str(tab), None)

    def stop(self):
        if self.server:
            print("Stopping (no app tab open).", flush=True)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def watch(self):
        while True:
            time.sleep(5)
            if not (self.enabled and self.seen_any):  # never stop before a page has connected once
                continue
            now = time.time()
            with self.lock:
                for t, seen in list(self.tabs.items()):
                    if now - seen > self.SILENT:
                        del self.tabs[t]
                if self.tabs:
                    self.empty_since = None
                    continue
                self.empty_since = self.empty_since or now
                if now - self.empty_since < self.GRACE:
                    continue
            self.stop()
            return


LIFE = Life()

SENT_PAGE = """<!doctype html><meta charset="utf-8"><title>Sent to Chem Builder</title>
<body style="font:16px system-ui;background:#0e1420;color:#e8edf7;display:grid;place-items:center;height:90vh">
<div style="text-align:center"><div style="font-size:42px">✔</div><p>Sent to the Chem Builder window.</p>
<p style="color:#8fa0c0">You can close this tab.</p></div></body>"""


def windowless():
    """True under pythonw (start.bat), where there is no console to print to."""
    return sys.stdout is None or sys.stderr is None


def fatal(msg):
    print(msg, file=sys.stderr, flush=True)
    if os.name == "nt" and windowless():
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg + f"\n\nDetails: {LOG}", "Chem Builder", 0x10)
        except Exception:  # noqa: BLE001
            pass
    sys.exit(1)


def already_running(port):
    """Is a Chem Builder already answering on this port?"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/meta", timeout=3) as r:
            return "formations" in json.load(r)
    except Exception:  # noqa: BLE001
        return False


def start_server(port):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def selftest(port):
    """Start the server, check the page and card data answer, stop. Used by the Windows build."""
    ensure_cards()
    load_cache()
    srv = start_server(port)
    try:
        base = f"http://127.0.0.1:{port}"
        with urllib.request.urlopen(base + "/", timeout=10) as r:
            assert b"Chem Builder" in r.read()
        with urllib.request.urlopen(base + "/api/meta", timeout=10) as r:
            meta = json.load(r)
        assert meta["n"] > 1000 and len(meta["formations"]) == 29, meta.get("n")
        print(f"SELFTEST OK: {meta['n']} cards, {len(meta['formations'])} formations, ui from {UI}")
    finally:
        srv.shutdown()


def run_app(url, smoke=False):
    """Show the app in its own desktop window (pywebview: Edge WebView2 on Windows). Returns False if
    pywebview isn't available, so the caller can fall back to the browser."""
    try:
        import webview
    except ImportError:
        print("pywebview is not installed (pip install pywebview==6.2.1) - opening in the browser instead.")
        return False
    os.makedirs(DATA_DIR, exist_ok=True)
    win = webview.create_window("Chem Builder - EA FC 27", url + "?app=1", width=1500, height=950,
                                min_size=(1000, 700), background_color="#0e1420")
    if smoke:  # build check: wait for the page to render the pitch, report, close
        def check():
            ok = False
            for _ in range(60):
                time.sleep(0.5)
                try:
                    if win.evaluate_js("document.querySelectorAll('.slot').length") == 11:
                        ok = True
                        break
                except Exception:  # noqa: BLE001
                    pass
            print("SMOKE OK: the window shows the pitch" if ok else "SMOKE FAIL: pitch not shown in the window", flush=True)
            with open(os.path.join(DATA_DIR, "smoke.txt"), "w") as f:
                f.write("ok" if ok else "fail")
            win.destroy()
        webview.start(check, private_mode=False, storage_path=os.path.join(DATA_DIR, "webview"))
    else:
        webview.start(private_mode=False, storage_path=os.path.join(DATA_DIR, "webview"))
    return True


def main():
    if windowless():  # pythonw / ChemBuilder.exe: keep a log instead of printing into nothing
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        sys.stdout = sys.stderr = open(LOG, "w", encoding="utf-8", buffering=1)
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="test cards.json and the FUT.GG connection, then exit")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--sync-only", action="store_true")
    ap.add_argument("--min-rating", type=int, default=75)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--stay", action="store_true", help="keep running after the last app tab is closed")
    ap.add_argument("--app", action="store_true", help="open in its own desktop window (default for the .exe)")
    ap.add_argument("--browser", action="store_true", help="open in the web browser even from the .exe")
    ap.add_argument("--selftest", action="store_true", help="start, check the page and data, exit (build check)")
    ap.add_argument("--smoke", action="store_true", help="open the window, check it renders, close (build check)")
    a = ap.parse_args()
    ensure_cards()
    if a.selftest:
        return selftest(a.port)
    if a.check:
        load_cache()
        for st_ in diagnose():
            print(("OK   " if st_["ok"] else "FAIL ") + st_["step"] + ": " + st_["detail"])
        return
    if a.sync or a.sync_only or not os.path.exists(CACHE):
        print(f"Syncing FC 27 cards (rating >= {a.min_rating}) from FUT.GG ...")
        st = {}
        t = threading.Thread(target=sync_cards, args=(a.min_rating, st), daemon=True)
        t.start()
        while t.is_alive():
            time.sleep(2)
            print(f"  {st.get('done', 0)}/{st.get('total', '?')} {st.get('msg', '')}", flush=True)
        print(st.get("msg"))
        if not os.path.exists(CACHE):
            fatal("Card data sync failed and there is no cards.json. Run: python chem_builder.py --check")
        if a.sync_only:
            return
    app = (a.app or a.smoke or FROZEN) and not a.browser
    url = f"http://127.0.0.1:{a.port}/"
    if already_running(a.port):  # second start: just show the app that is already running
        print(f"Chem Builder is already running at {url}")
        if app and run_app(url, a.smoke):
            return
        if not a.no_browser:
            webbrowser.open(url)
        return
    load_cache()
    if not STATE["cards"]:
        fatal("No card data. Run: python chem_builder.py --sync")
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    except OSError as e:
        fatal(f"Port {a.port} is in use by another program ({e}). Close it or start with --port 8766.")
    LIFE.server = srv
    print(f"{len(STATE['cards'])} cards loaded (synced {STATE['meta'].get('synced_at', '?')}). {url}")
    serving = threading.Thread(target=srv.serve_forever, daemon=True)
    serving.start()
    if app and run_app(url, a.smoke):   # desktop window: blocks until it is closed, then the app quits
        srv.shutdown()
        return
    # browser mode (or no pywebview): the server stops ~30 s after the last tab closes
    LIFE.enabled = not (a.stay or a.no_browser)
    threading.Thread(target=LIFE.watch, daemon=True).start()
    if LIFE.enabled:
        print("The app stops by itself about 30 s after its last browser tab is closed.")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        while serving.is_alive():
            serving.join(0.5)
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
