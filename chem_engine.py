"""Chemistry rules + swap search for EA FC 27 Ultimate Team.

Pure Python, standard library only. Card format (compact dict) -- see normalize_card
in chem_builder.py:
  s  slug (unique per card version)      n  display name        ov  overall
  p  main position                       a  alternate positions g   gender (1 men, 2 women)
  ni nation id   nn nation name          li league id   ln league name
  ck club link key (None for ICON/Hero/Hall of FUT)            cn  club name
  ty 'icon' | 'hero' | 'hof' | ''        bp base player id (same player, different version)
  fc full-chemistry card                 xc/xl/xn extra club/league/nation count
  xsl/xsn extra +1 to every league / every nation in the squad

RULES (sources checked 8 Oct 2026, see README):
  * every starter earns 0-3 chem, squad max 33
  * thresholds (counts include the player): club 2/4/7, league 3/5/8, nation 2/5/8
  * the three link types add together, capped at 3
  * manager: counts as one more member of its nation and of its league toward those thresholds
    (it lifts a player only when that crosses a threshold). Guides describe a flat "+1 if nation or
    league matches", but a real FC 27 squad (8 Oct 2026) only adds up under the threshold rule: a
    Spain/Arkema player with Spain 4->5 and Arkema 2->3 showed 3 chem in game, the flat rule gives 2.
  * the manager's LEAGUE can be changed with a League Modifier item (permanent, any league);
    there is no item for the manager's nation -> mgr = {"ni": nation id, "li": league id,
    "li_free": True} lets the engine pick the best league automatically
  * a player only earns chem and only counts for others if played in a preferred position
  * FC 27: ICON counts +1 nation and +1 to EVERY league; Hero / Hall of FUT count +1 league
    and +1 nation; ICON/Hero/Hall of FUT are full chemistry and have no club link
  * men's and women's players link through affiliated clubs (same ck), never through leagues
"""
import math
import time
from collections import Counter

CLUB_T = (2, 4, 7)
LEAGUE_T = (3, 5, 8)
NATION_T = (2, 5, 8)


def pts(n, thresholds):
    return sum(1 for t in thresholds if n >= t)


def prefs(card):
    return {card["p"], *card.get("a", [])}


def _counts(slots, squad):
    inpos = [c is not None and slots[i] in prefs(c) for i, c in enumerate(squad)]
    club, lg, nat = Counter(), Counter(), Counter()
    gl = gn = 0
    for ok, c in zip(inpos, squad):
        if not ok:
            continue
        if c.get("ck"):
            club[c["ck"]] += 1 + int(c.get("xc") or 0)
        lg[c["li"]] += 1 + int(c.get("xl") or 0)
        nat[c["ni"]] += 1 + int(c.get("xn") or 0)
        if c.get("ty") == "icon" or c.get("xsl"):
            gl += 1
        if c.get("xsn"):
            gn += 1
    return inpos, club, lg, nat, gl, gn


def _raw(slots, squad, mni=None, mli=None):
    """Per-player chemistry; mni/mli = manager nation/league, each counted as one more member of that
    nation/league toward the thresholds. None = empty slot."""
    inpos, club, lg, nat, gl, gn = _counts(slots, squad)
    rows = []
    for i, c in enumerate(squad):
        if c is None:
            rows.append(None)
        elif not inpos[i]:
            rows.append({"state": "off", "raw": 0})
        elif c.get("fc"):
            rows.append({"state": "full", "raw": 3})
        else:
            cc = club[c["ck"]] if c.get("ck") else 0
            lc = lg[c["li"]] + gl + (1 if mli is not None and c["li"] == mli else 0)
            nc = nat[c["ni"]] + gn + (1 if mni is not None and c["ni"] == mni else 0)
            cp = pts(cc, CLUB_T) if c.get("ck") else 0
            lp, np_ = pts(lc, LEAGUE_T), pts(nc, NATION_T)
            rows.append({"state": "ok", "raw": min(3, cp + lp + np_), "club": [cc, cp], "league": [lc, lp],
                         "nation": [nc, np_]})
    return rows


def _choose_league(gain, cur):
    """League Modifier choice: the league adding the most chemistry. Keeps the current league when it is
    as good as any other (no item needed); otherwise ties go to the lowest league id."""
    best = max(gain.values(), default=0)
    if cur is not None and gain.get(cur, 0) >= best:
        return cur
    return min(k for k, v in gain.items() if v == best) if best > 0 else cur


def _best_league(squad, rows, cur=None):
    """rows computed without a manager league."""
    gain = Counter()
    for c, r in zip(squad, rows):
        if r and r["state"] == "ok" and r["raw"] < 3:
            up = min(3, r["club"][1] + pts(r["league"][0] + 1, LEAGUE_T) + r["nation"][1])
            gain[c["li"]] += up - r["raw"]
    return _choose_league(gain, cur)


def _manager_rows(slots, squad, mgr):
    """Rows with the manager applied. Returns (rows, manager league used)."""
    mgr = mgr or {}
    ni, li = mgr.get("ni"), mgr.get("li")
    if mgr.get("li_free"):
        li = _best_league(squad, _raw(slots, squad, ni, None), li)
    return _raw(slots, squad, ni, li), li


def evaluate(slots, squad, mgr):
    """Full breakdown. squad: list of card-or-None aligned with slots."""
    rows, mli = _manager_rows(slots, squad, mgr)
    bare = _raw(slots, squad)
    players, total = [], 0
    for r, r0 in zip(rows, bare):
        if r is None:
            players.append(None)
        elif r["state"] == "off":
            players.append({"chem": 0, "inpos": False, "full": False})
        elif r["state"] == "full":
            total += 3
            players.append({"chem": 3, "inpos": True, "full": True})
        else:
            total += r["raw"]
            players.append({"chem": r["raw"], "inpos": True, "full": False, "club": r["club"],
                            "league": r["league"], "nation": r["nation"], "mgr": r["raw"] - r0["raw"]})
    return {"total": total, "players": players, "mgr_li": mli}


_CP = [pts(n, CLUB_T) for n in range(64)]
_LP = [pts(n, LEAGUE_T) for n in range(64)]
_NP = [pts(n, NATION_T) for n in range(64)]


def _t(c):
    """Compact read-only view of a card for the search hot path."""
    if c is None:
        return None
    return (c["p"], frozenset(c.get("a") or ()), c.get("ck") or None, c["li"], c["ni"], c.get("xc") or 0,
            c.get("xl") or 0, c.get("xn") or 0, c.get("ty") == "icon" or bool(c.get("xsl")), bool(c.get("xsn")),
            bool(c.get("fc")))


def _ttotal(slots, ts, mni, mli, free):
    """Squad chemistry from _t() tuples. Same rules as evaluate(); the manager league is folded in as a
    per-league gain so a free league (League Modifier) costs nothing extra."""
    club, lg, nat = {}, {}, {}
    gl = gn = 0
    live = []
    for i, t in enumerate(ts):
        if t is None:
            continue
        pos = slots[i]
        if pos != t[0] and pos not in t[1]:
            continue
        live.append(t)
        if t[2]:
            club[t[2]] = club.get(t[2], 0) + 1 + t[5]
        lg[t[3]] = lg.get(t[3], 0) + 1 + t[6]
        nat[t[4]] = nat.get(t[4], 0) + 1 + t[7]
        if t[8]:
            gl += 1
        if t[9]:
            gn += 1
    total, gain = 0, {}
    for t in live:
        if t[10]:
            total += 3
            continue
        base = (_CP[club[t[2]]] if t[2] else 0) + _NP[nat[t[4]] + gn + (1 if t[4] == mni and mni is not None else 0)]
        lc = lg[t[3]] + gl
        r0 = base + _LP[lc]
        if r0 >= 3:
            total += 3
            continue
        total += r0
        r1 = base + _LP[lc + 1]
        up = (3 if r1 > 3 else r1) - r0
        if up:
            gain[t[3]] = gain.get(t[3], 0) + up
    li = _choose_league(gain, mli) if free else mli
    return total + (gain.get(li, 0) if li is not None else 0)


def total_only(slots, squad, mgr):
    """Squad chemistry only (the search hot path)."""
    mgr = mgr or {}
    return _ttotal(slots, [_t(c) for c in squad], mgr.get("ni"), mgr.get("li"), mgr.get("li_free"))


def manager_options(slots, squad, mgr, top=8):
    """What a manager of each nation would give this squad (league still follows mgr settings).
    Nation can only change by using a different manager card; the league has an item."""
    mgr = dict(mgr or {})
    cur = total_only(slots, squad, mgr)
    nations = {}
    for c in squad:
        if c is not None:
            nations[c["ni"]] = c.get("nn")
    out = []
    for ni, nn in nations.items():
        t = total_only(slots, squad, dict(mgr, ni=ni))
        out.append({"ni": ni, "nn": nn, "total": t, "d": t - cur})
    out.sort(key=lambda r: (-r["total"], r["nn"] or ""))
    none_total = total_only(slots, squad, dict(mgr, ni=None))
    return {"current": cur, "no_nation": none_total, "options": out[:top]}


def manager_suggestions(slots, squad, mgr, top=6):
    """Manager changes that raise squad chemistry, measured against the current manager as it is:
    a League Modifier (another league), a manager of another nation (new manager card), or both.
    Only nations/leagues already in the squad can help."""
    mgr = dict(mgr or {})
    cur_ni, cur_li = mgr.get("ni"), mgr.get("li")
    cur = total_only(slots, squad, {"ni": cur_ni, "li": cur_li})
    nations = {c["ni"]: c.get("nn") for c in squad if c is not None}
    leagues = {c["li"]: c.get("ln") for c in squad if c is not None}
    out = []
    for ni in set(nations) | {cur_ni}:
        for li in set(leagues) | {cur_li}:
            if ni is None and li is None:
                continue
            t = total_only(slots, squad, {"ni": ni, "li": li})
            if t <= cur:
                continue
            out.append({"ni": ni, "nn": nations.get(ni), "li": li, "ln": leagues.get(li), "total": t, "d": t - cur,
                        "nation": ni != cur_ni, "league": li != cur_li})
    # drop options a simpler change already matches (e.g. new nation + new league = new nation alone)
    def simpler(o, p):
        return (p["nation"] <= o["nation"] and p["league"] <= o["league"] and (p["nation"], p["league"]) != (o["nation"], o["league"])
                and (not p["nation"] or p["ni"] == o["ni"]) and (not p["league"] or p["li"] == o["li"]))
    out = [o for o in out if not any(simpler(o, p) and p["total"] >= o["total"] for p in out)]
    # most chemistry first; on a tie the cheaper change (league item only < new manager < both)
    key = lambda o: (-o["total"], o["nation"] * 2 + o["league"], str(o["nn"]), str(o["ln"]))  # noqa: E731
    out.sort(key=key)
    # always show the best of each kind (league item only / new manager only / both), then the rest
    firsts = [next(o for o in out if (o["nation"], o["league"]) == k) for k in ((False, True), (True, False), (True, True))
              if any((o["nation"], o["league"]) == k for o in out)]
    rest = [o for o in out if all(o is not f for f in firsts)]
    return sorted(firsts + rest[:max(0, top - len(firsts))], key=key)


# --------------------------------------------------------------------------- search

POS_GROUP = {"GK": "GK", "CB": "DEF", "LB": "DEF", "RB": "DEF", "CDM": "MID", "CM": "MID", "LM": "MID", "RM": "MID",
             "CAM": "ATT", "LW": "ATT", "RW": "ATT", "ST": "ATT"}


def plain_value(c, pos):
    return c["ov"]


def boost(val, c, pos):
    """Rating points a favourite card gets at this position (0 for everything else)."""
    b = getattr(val, "boost", None)
    return b(c, pos) if b else 0


def _with_favs(found, cands, val, pos, ok=None):
    """Make sure every favourite for this position is on a shortlist, even if it would not have made the cut."""
    seen = {c["s"] for c in found}
    for c in cands:
        if c["s"] not in seen and boost(val, c, pos) and (ok is None or ok(c)):
            seen.add(c["s"])
            found.append(c)
    return found


def make_value(prefs=None, w_plus=3, w_ps=1, soft=None, w_soft=0, favs=None, w_fav=0):
    """Card value used for ranking: overall + a bonus for the PlayStyles you want in that position.
    prefs = {"GK": [ids], "CDM": [...], "ST": [...], ...} per position (group keys DEF/MID/ATT are still
    understood for positions without their own entry); a wanted PlayStyle+ is worth w_plus rating points,
    a plain wanted PlayStyle w_ps. soft: preferred stats per position (see _checks), each criterion met is
    worth w_soft rating points. favs: {(card slug, position)} the user prefers there, each worth w_fav rating
    points; favourites also get that much leeway wherever a search filters on overall (rating drop, upgrades)."""
    want = {g: frozenset(ids) for g, ids in (prefs or {}).items() if ids}
    if not want or (not w_plus and not w_ps):
        want = {}
    soft = soft if soft and w_soft else None   # preferred stats: w_soft rating points per criterion met
    favs = frozenset(tuple(x) for x in favs or ()) if w_fav else frozenset()
    if not want and not soft and not favs:
        return plain_value
    cache = {}

    def value(c, pos):
        key = (c["s"], pos)
        v = cache.get(key)
        if v is None:
            v = c["ov"]
            w = want.get(pos) if pos in (prefs or {}) else want.get(POS_GROUP.get(pos))
            if w:
                pp, ps = c.get("pp") or (), c.get("ps") or ()
                v += sum(w_plus if x in pp else w_ps if x in ps else 0 for x in w)
            if soft:
                v += w_soft * pref_points(c, pos, soft)
            if (c["s"], pos) in favs:
                v += w_fav
            cache[key] = v
        return v
    if favs:
        value.boost = lambda c, pos: w_fav if (c["s"], pos) in favs else 0
    return value


def _checks(c, pos, r):
    """One True/False per criterion set in requirement r for card c at position pos.
    r: {"wf", "sm": min stars, "ft": "L"/"R", "ht": min height cm, "ar": AcceleRATE name,
        "fs": [min PAC, SHO, PAS, DRI, DEF, PHY]}. Face stats never apply to keepers; unknown values fail."""
    out = []
    for k in ("wf", "sm", "ht"):
        need = r.get(k) or 0
        if need:
            out.append((c.get(k) or 0) >= need)
    if r.get("ft"):
        out.append(c.get("ft") == r["ft"])
    if r.get("ar"):
        out.append(c.get("ar") == r["ar"])
    mins = r.get("fs") or ()
    if pos != "GK":
        fs = c.get("fs") if c.get("p") != "GK" else None
        for k, m in enumerate(mins):
            if m:
                out.append(bool(fs) and fs[k] >= m)
    return out


def meets(c, pos, reqs):
    """Does card c satisfy every requirement for position pos? reqs: {position: requirement, see _checks}."""
    r = reqs.get(pos) if reqs else None
    return not r or all(_checks(c, pos, r))


def pref_points(c, pos, reqs):
    """How many of the preferred criteria for pos card c meets (used when requirements are 'prefer', not 'require')."""
    r = reqs.get(pos) if reqs else None
    return sum(_checks(c, pos, r)) if r else 0


def index_pool(pool, no_women=(), pos_bans=(), reqs=None, keep=()):
    """Cards by every position they can play. no_women: positions where women's cards are never suggested
    (they can still play their other positions). pos_bans: (base player id, position) pairs - that player,
    every version, is never suggested at that position (still fine at the others). reqs: see meets().
    keep: (card slug, position) favourites the user picked by hand - the women filter and required stats
    don't apply to them there (position blocks still do)."""
    no_women = set(no_women or ())
    banned = {(str(bp), pos) for bp, pos in pos_bans or ()}
    keep = set(keep or ())
    by_pos = {}
    for c in pool:
        for p in prefs(c):
            if banned and (str(c.get("bp")), p) in banned:
                continue
            if (c["s"], p) in keep:
                pass
            elif c.get("g") == 2 and p in no_women:
                continue
            elif reqs and not meets(c, p, reqs):
                continue
            by_pos.setdefault(p, []).append(c)
    return by_pos


BASE_RARITY = ("rare", "common", "non-rare")


def _chem_key(c):
    """Cards with the same key give exactly the same chemistry (same player, nation, league, club and extras)."""
    return (str(c.get("bp")), c.get("g"), c["ni"], c["li"], c.get("ck"), bool(c.get("fc")), c.get("xc", 0),
            c.get("xl", 0), c.get("xn", 0), bool(c.get("xsl")), bool(c.get("xsn")))


def cheapest_versions(by_pos, floor=0, keep=()):
    """Per position, keep only the lowest-rated version of each player among versions that give the same
    chemistry (a stand-in for the cheapest, since there are no prices). A promo version still shows up where it
    adds a position or different chemistry. floor: versions rated below it don't count (min rating filter).
    keep: (slug, position) favourites, always kept."""
    keep = set(keep or ())
    out = {}
    for pos, cards in by_pos.items():
        best, kept = {}, []
        for c in cards:
            if (c["s"], pos) in keep:
                kept.append(c)
                continue
            if c["ov"] < floor:
                continue
            k = _chem_key(c)
            b = best.get(k)
            # lower rating wins; at the same rating a base card beats a special one
            rank = (c["ov"], str(c.get("rt", "")).lower() not in BASE_RARITY)
            if b is None or rank < b[0]:
                best[k] = (rank, c)
        seen = {c["s"] for c in kept}
        out[pos] = kept + [c for _, c in best.values() if c["s"] not in seen]
    return out


def _slot_candidates(i, slots, squad, by_pos, max_drop, min_rating, val=plain_value):
    cur, pos = squad[i], slots[i]
    floor = cur["ov"] - max_drop   # a favourite coming in gets its bonus as leeway on the rating drop
    others = {c["bp"] for j, c in enumerate(squad) if j != i and c}
    for cand in by_pos.get(pos, ()):
        if (cand["ov"] < min_rating or cand["ov"] + boost(val, cand, pos) < floor or cand["bp"] in others
                or cand["s"] == cur["s"]):
            continue
        yield cand


def single_swaps(slots, squad, locks, mgr, by_pos, max_drop=3, min_rating=0, val=plain_value):
    mgr = mgr or {}
    mni, mli, free = mgr.get("ni"), mgr.get("li"), mgr.get("li_free")
    ts = [_t(c) for c in squad]
    base = _ttotal(slots, ts, mni, mli, free)
    out = []
    for i, cur in enumerate(squad):
        if locks[i] or cur is None:
            continue
        keep = ts[i]
        for cand in _slot_candidates(i, slots, squad, by_pos, max_drop, min_rating, val):
            ts[i] = _t(cand)
            t = _ttotal(slots, ts, mni, mli, free)
            out.append({"slot": i, "out": cur, "in": cand, "total": t, "d": t - base,
                        "dr": cand["ov"] - cur["ov"], "v": val(cand, slots[i])})
        ts[i] = keep
    return base, out


def _rank_key(r):
    return (-r["d"], -r.get("v", r["in"]["ov"]), -r["dr"])  # most chem first, then best card (overall + PlayStyles)


def top_singles(slots, squad, locks, mgr, by_pos, max_drop, min_rating, n=30, only_positive=True, ok=None,
                val=plain_value):
    """ok(card) -> bool is an optional affordability check on the INCOMING card only. It is called lazily,
    walking down the ranked list, so price lookups happen only for cards that would otherwise be shown."""
    base, allr = single_swaps(slots, squad, locks, mgr, by_pos, max_drop, min_rating, val)
    res = [r for r in allr if (r["d"] > 0 or not only_positive)]
    res.sort(key=_rank_key)
    if ok is not None:
        keep = []
        for r in res:
            if len(keep) >= n:
                break
            if ok(r["in"]):
                keep.append(r)
        res = keep
    return base, res[:n], allr


def synergy_pairs(slots, squad, locks, mgr, by_pos, allsingles, base, max_drop, min_rating,
                  per_slot=35, n=20, ok=None, val=plain_value):
    """Two swaps that only pay off together (each alone is worse than the pair)."""
    single_d = {(r["slot"], r["in"]["s"]): r["d"] for r in allsingles}
    mg = mgr or {}
    shortlist = {}
    for i, cur in enumerate(squad):
        if locks[i] or cur is None:
            continue
        cands = list(_slot_candidates(i, slots, squad, by_pos, max_drop, min_rating, val))
        leagues = Counter(c["li"] for c in squad if c)
        nations = Counter(c["ni"] for c in squad if c)
        clubs = Counter(c["ck"] for j, c in enumerate(squad) if c and c.get("ck") and j != i)

        def potential(c):
            return (leagues[c["li"]] + nations[c["ni"]] + 2 * clubs.get(c.get("ck"), 0)
                    + (0 if mg.get("li_free") else (1 if c["li"] == mg.get("li") else 0))
                    + (1 if c["ni"] == mg.get("ni") else 0)
                    + (3 if c.get("ty") == "icon" else 0))
        cands.sort(key=lambda c: (potential(c), c["ov"]), reverse=True)
        top_pot = cands[:per_slot]
        top_single = sorted(cands, key=lambda c: single_d.get((i, c["s"]), -99), reverse=True)[:per_slot // 2]
        seen, merged = set(), []
        for c in top_pot + top_single:
            if c["s"] not in seen:
                seen.add(c["s"])
                merged.append(c)
        shortlist[i] = merged
    idx = sorted(shortlist)
    t0 = [_t(c) for c in squad]
    ts = list(t0)
    tc = {c["s"]: _t(c) for lst in shortlist.values() for c in lst}
    out = []
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            i, j = idx[a], idx[b]
            excl = {c["bp"] for k, c in enumerate(squad) if c and k not in (i, j)}
            for ci in shortlist[i]:
                for cj in shortlist[j]:
                    if ci["bp"] == cj["bp"]:
                        continue
                    if ci["bp"] in excl or cj["bp"] in excl:
                        continue
                    ts[i], ts[j] = tc[ci["s"]], tc[cj["s"]]
                    t = _ttotal(slots, ts, mg.get("ni"), mg.get("li"), mg.get("li_free"))
                    ts[i], ts[j] = t0[i], t0[j]
                    d = t - base
                    if d <= 0:
                        continue
                    if d > single_d.get((i, ci["s"]), -99) and d > single_d.get((j, cj["s"]), -99):
                        out.append({"swaps": [
                            {"slot": i, "out": squad[i], "in": ci},
                            {"slot": j, "out": squad[j], "in": cj}],
                            "total": t, "d": d,
                            "dr": ci["ov"] + cj["ov"] - squad[i]["ov"] - squad[j]["ov"]})
    out.sort(key=lambda r: (-r["d"], -sum(w["in"]["ov"] for w in r["swaps"]), -r["dr"]))
    if ok is not None:
        keep = []
        for r in out:
            if len(keep) >= n:
                break
            if all(ok(w["in"]) for w in r["swaps"]):
                keep.append(r)
        out = keep
    return out[:n]


def plan_chain(slots, squad, locks, mgr, by_pos, max_drop=3, min_rating=0, max_steps=5, ok=None, val=plain_value):
    """Greedy path: repeatedly apply the best swap (or best synergy pair)."""
    steps, cur, locks = [], list(squad), list(locks)
    total = total_only(slots, cur, mgr)
    for _ in range(max_steps):
        base, top, allr = top_singles(slots, cur, locks, mgr, by_pos, max_drop, min_rating, n=1, ok=ok, val=val)
        if top:
            best = top[0]
            cur[best["slot"]] = best["in"]
            locks[best["slot"]] = True
            total = best["total"]
            steps.append({"swaps": [{"slot": best["slot"], "out": best["out"], "in": best["in"]}],
                          "total": total})
            continue
        pairs = synergy_pairs(slots, cur, locks, mgr, by_pos, allr, base, max_drop, min_rating, n=1, ok=ok, val=val)
        if not pairs:
            break
        best = pairs[0]
        for s in best["swaps"]:
            cur[s["slot"]] = s["in"]
            locks[s["slot"]] = True
        total = best["total"]
        steps.append({"swaps": best["swaps"], "total": total})
    return steps, total, cur


def _shortlist(slots, squad, locks, mgr, by_pos, max_drop, min_rating, allsingles, per_slot, ok=None,
               val=plain_value):
    """Per unlocked slot: the best single swaps plus the cards with the most link potential
    (same club/league/nation as the rest of the squad, manager, ICONs)."""
    single_d = {(r["slot"], r["in"]["s"]): r["d"] for r in allsingles}
    mg = mgr or {}
    leagues = Counter(c["li"] for c in squad if c)
    nations = Counter(c["ni"] for c in squad if c)
    out = {}
    for i, cur in enumerate(squad):
        if locks[i] or cur is None:
            continue
        clubs = Counter(c["ck"] for j, c in enumerate(squad) if c and c.get("ck") and j != i)
        cands = [c for c in _slot_candidates(i, slots, squad, by_pos, max_drop, min_rating, val)]

        def potential(c):
            return (leagues[c["li"]] + nations[c["ni"]] + 2 * clubs.get(c.get("ck"), 0)
                    + (0 if mg.get("li_free") else (1 if c["li"] == mg.get("li") else 0))
                    + (1 if c["ni"] == mg.get("ni") else 0) + (3 if c.get("ty") == "icon" else 0))
        pos = slots[i]
        by_pot = sorted(cands, key=lambda c: (potential(c), val(c, pos)), reverse=True)
        by_single = sorted(cands, key=lambda c: (single_d.get((i, c["s"]), -99), val(c, pos)), reverse=True)
        seen, merged = set(), []
        for c in by_single[:per_slot] + by_pot[:per_slot]:
            if c["s"] not in seen and (ok is None or ok(c)):
                seen.add(c["s"])
                merged.append(c)
        out[i] = _with_favs(merged, cands, val, pos, ok)
    return out


def k_swap_combos(slots, squad, locks, mgr, by_pos, max_drop=3, min_rating=0, k_max=3, n=25,
                  beam=24, per_slot=15, ok=None, mgr_change=False, base=None, time_limit=8.0, val=plain_value):
    """Best squads reachable with exactly 1..k_max player swaps (beam search over a per-slot shortlist).
    The manager league is always free (League Modifier); each result says which league it uses.
    mgr_change=True also lets the search switch the manager's nation (a new manager card): every candidate
    nation gets its own seed and keeps a few states in the beam, so changes that only pay off after some
    swaps survive. Every swap in a listed combo is needed (undoing any one loses chemistry), and other
    versions of the same players are collapsed. Stops expanding after time_limit seconds.
    Returns {"by_k": {k: [ {swaps, total, d, dr, li, league, mgr} ]}, "timed_out": bool}."""
    started = time.time()
    mgr = dict(mgr or {}, li_free=True)
    cur_li = mgr.get("li")
    if base is None:
        base = total_only(slots, squad, dict(mgr, li_free=False))
    _, allr = single_swaps(slots, squad, locks, mgr, by_pos, max_drop, min_rating, val)
    sl = _shortlist(slots, squad, locks, mgr, by_pos, max_drop, min_rating, allr, per_slot, ok, val)
    configs = [mgr]
    if mgr_change:
        seen_n = Counter(c["ni"] for c in squad if c)
        for cands in sl.values():
            seen_n.update(c["ni"] for c in cands)
        configs += [dict(mgr, ni=ni) for ni, _ in seen_n.most_common() if ni != mgr.get("ni")][:12]
    nations = {}
    for c in squad:
        if c:
            nations[c["ni"]] = c.get("nn")
    for cands in sl.values():
        for c in cands:
            nations.setdefault(c["ni"], c.get("nn"))
    tc = {c["s"]: _t(c) for cands in sl.values() for c in cands}
    t0 = [_t(c) for c in squad]
    cfg = [(m.get("ni"), m.get("li")) for m in configs]
    best = {}  # (k, swap key, config) -> (total, squad)
    frontier = [((), list(squad), t0, ci) for ci in range(len(configs))]
    timed_out = False
    for k in range(1, k_max + 1):
        if time.time() - started > time_limit:
            timed_out = True
            break
        nxt = {}
        for swaps, sq, ts, ci in frontier:
            used = {s for s, _ in swaps}
            mni, mli = cfg[ci]
            for i, cands in sl.items():
                if i in used:
                    continue
                bps = {c["bp"] for j, c in enumerate(sq) if c and j != i}
                for c in cands:
                    if c["bp"] in bps:
                        continue
                    key = tuple(sorted(swaps + ((i, c["s"]),)))
                    if (key, ci) in nxt:
                        continue
                    nts = list(ts)
                    nts[i] = tc[c["s"]]
                    nxt[(key, ci)] = (_ttotal(slots, nts, mni, mli, True), sq, nts, i, c)
        ranked = sorted(nxt.items(), key=lambda kv: (-kv[1][0], kv[0][1] != 0, -val(kv[1][4], slots[kv[1][3]])))
        materialise = {}

        def squad_of(entry):
            _, sq, _, i, c = entry
            new = list(sq)
            new[i] = c
            return new
        for (key, ci), entry in ranked:
            if entry[0] <= base or len(materialise) >= 6 * n:
                break
            materialise[(key, ci)] = squad_of(entry)
            best[(k, key, ci)] = (entry[0], materialise[(key, ci)], entry[2])
        keep, per_cfg = [], Counter()
        for (key, ci), entry in ranked:
            if len(keep) < beam or per_cfg[ci] < 3:
                sq = materialise.get((key, ci)) or squad_of(entry)
                keep.append((key, sq, entry[2], ci))
                per_cfg[ci] += 1
            elif len(keep) >= beam + 3 * len(configs):
                break
        frontier = keep
    out = {k: [] for k in range(1, k_max + 1)}
    order = sorted(best.items(), key=lambda kv: (kv[0][0], -kv[1][0], kv[0][2] != 0,
                                                 -sum(val(kv[1][1][s], slots[s]) for s, _ in kv[0][1])))
    seen = set()
    for (k, key, ci), (t, sq, ts) in order:
        if len(out[k]) >= n:
            continue
        players = (k, tuple(sorted((s, sq[s]["bp"]) for s, _ in key)))
        if players in seen:  # same players (other card versions / other manager): keep the best-ranked one
            continue
        m = configs[ci]
        needed = True
        for slot, _ in key:
            back = list(ts)
            back[slot] = t0[slot]
            if _ttotal(slots, back, cfg[ci][0], cfg[ci][1], True) >= t:
                needed = False
                break
        if not needed:
            continue
        seen.add(players)
        _, li = _manager_rows(slots, sq, m)
        swaps = [{"slot": s, "out": squad[s], "in": sq[s]} for s, _ in key]
        out[k].append({"swaps": swaps, "total": t, "d": t - base,
                       "dr": sum(w["in"]["ov"] - w["out"]["ov"] for w in swaps),
                       "dv": sum(val(w["in"], slots[w["slot"]]) - val(w["out"], slots[w["slot"]]) for w in swaps),
                       "li": li, "league": li != cur_li,
                       "mgr": None if ci == 0 else {"ni": m["ni"], "nn": nations.get(m["ni"]), "nation": True}})
    return {"by_k": out, "timed_out": timed_out}


def upgrade_combos(slots, squad, locks, mgr, by_pos, min_rating=0, k_max=3, max_loss=3, n=25,
                   beam=30, per_slot=15, ok=None, base=None, time_limit=6.0, val=plain_value, max_ovr=None,
                   pos_caps=None):
    """Rating upgrades: swap in HIGHER-rated cards for the same positions while squad chemistry stays at or
    above base - max_loss (base = the squad as it is, with the current manager). Ranked by overall
    gained, then chemistry. The manager league is free (League Modifier); results say which league they use.
    Beam search per number of upgraded players (1..k_max); every swap is a strict rating upgrade.
    max_ovr caps the overall of a suggested card; pos_caps {"ST": 90, ...} overrides it per position (of the slot).
    Returns {"by_k": {k: [ {swaps, total, d, dr, li, league} ]}, "floor": int, "timed_out": bool,
             "slots": [ {slot, pos, cur, cap, higher, in_cap, keep_chem} ]} - the last explains empty results."""
    started = time.time()
    mgr = dict(mgr or {}, li_free=True)
    mni, mli, cur_li = mgr.get("ni"), mgr.get("li"), mgr.get("li")
    if base is None:
        base = total_only(slots, squad, dict(mgr, li_free=False))
    floor = base - max_loss
    t0 = [_t(c) for c in squad]
    # shortlist per slot: upgrades that keep chemistry best on their own, plus the biggest upgrades still in range
    sl, tc, why = {}, {}, []
    for i, cur in enumerate(squad):
        if locks[i] or cur is None:
            continue
        cap = (pos_caps or {}).get(slots[i]) or max_ovr or None
        n_higher = n_cap = n_keep = 0
        others = {c["bp"] for j, c in enumerate(squad) if c and j != i}
        scored = []
        ts = list(t0)
        pos, cur_v = slots[i], val(cur, slots[i])
        for c in by_pos.get(pos, ()):
            # an upgrade = a better card for this position: higher overall, or wanted PlayStyles worth more
            if (val(c, pos) <= cur_v or c["ov"] + boost(val, c, pos) < cur["ov"] + boost(val, cur, pos)
                    or c["ov"] < min_rating or c["bp"] in others):
                continue
            n_higher += 1
            if cap and c["ov"] > cap:  # price stand-in: nothing above this overall
                continue
            n_cap += 1
            tc[c["s"]] = ts[i] = _t(c)
            t = _ttotal(slots, ts, mni, mli, True)
            n_keep += t >= floor
            scored.append((t, c))
        why.append({"slot": i, "pos": pos, "cur": cur["ov"], "cap": cap, "higher": n_higher, "in_cap": n_cap,
                    "keep_chem": n_keep})
        by_chem = sorted(scored, key=lambda x: (-x[0], -val(x[1], pos)))
        by_ov = sorted((x for x in scored if x[0] >= floor), key=lambda x: (-val(x[1], pos), -x[0]))
        seen, merged = set(), []
        for _, c in by_chem[:per_slot] + by_ov[:per_slot]:
            if c["s"] not in seen and (ok is None or ok(c)):
                seen.add(c["s"])
                merged.append(c)
        _with_favs(merged, [c for _, c in scored], val, pos, ok)
        if merged:
            sl[i] = merged
    best = {}
    frontier = [((), list(squad), t0, 0)]
    timed_out = False
    for k in range(1, k_max + 1):
        if time.time() - started > time_limit:
            timed_out = True
            break
        nxt = {}
        for swaps, sq, ts, g in frontier:
            used = {s for s, _ in swaps}
            for i, cands in sl.items():
                if i in used:
                    continue
                bps = {c["bp"] for j, c in enumerate(sq) if c and j != i}
                for c in cands:
                    if c["bp"] in bps:
                        continue
                    key = tuple(sorted(swaps + ((i, c["s"]),)))
                    if key in nxt:
                        continue
                    nts = list(ts)
                    nts[i] = tc[c["s"]]
                    nxt[key] = (_ttotal(slots, nts, mni, mli, True), g + val(c, slots[i]) - val(squad[i], slots[i]),
                                sq, nts, i, c)
        ok_states = sorted((kv for kv in nxt.items() if kv[1][0] >= floor), key=lambda kv: (-kv[1][1], -kv[1][0]))
        low = sorted((kv for kv in nxt.items() if kv[1][0] < floor), key=lambda kv: (-kv[1][0], -kv[1][1]))
        keep = []
        for key, (t, g, sq, nts, i, c) in ok_states[:max(beam, 3 * n)] + low[:10]:
            new = list(sq)
            new[i] = c
            if t >= floor:
                best[(k, key)] = (t, g, new)
            keep.append((key, new, nts, g))
        frontier = keep[:beam] + [x for x in keep[len(ok_states[:max(beam, 3 * n)]):]]
    out = {k: [] for k in range(1, k_max + 1)}
    seen = set()
    for (k, key), (t, g, sq) in sorted(best.items(), key=lambda kv: (kv[0][0], -kv[1][1], -kv[1][0])):
        if len(out[k]) >= n:
            continue
        players = (k, tuple(sorted((s, sq[s]["bp"]) for s, _ in key)))
        if players in seen:
            continue
        seen.add(players)
        _, li = _manager_rows(slots, sq, mgr)
        swaps = [{"slot": s, "out": squad[s], "in": sq[s]} for s, _ in key]
        out[k].append({"swaps": swaps, "total": t, "d": t - base, "dv": g, "li": li, "league": li != cur_li,
                       "dr": sum(w["in"]["ov"] - w["out"]["ov"] for w in swaps)})
    return {"by_k": out, "floor": floor, "timed_out": timed_out, "slots": why}


def fill_squad(slots, squad, mgr, by_pos, min_rating=0, max_ovr=None, pos_caps=None, val=plain_value, n=25,
               beam=60, per_slot=40, time_limit=8.0):
    """Fill the empty slots of a partly picked squad. The players already placed are kept as they are.
    Per empty slot a shortlist of cards that link best with the placed players (club, league, nation,
    manager, ICONs) and the best-rated ones; a beam search fills one slot at a time, then each result is
    polished by single swaps until nothing improves. Ranked by squad chemistry (manager league free:
    League Modifier), then overall + PlayStyle value. Returns {"options": [...], "empty": [slot idx],
    "timed_out": bool}; each option: {fills: [{slot, in}], total, li, league, avg_ov, value}."""
    started = time.time()
    mgr = dict(mgr or {}, li_free=True)
    mni, mli = mgr.get("ni"), mgr.get("li")
    empty = [i for i, c in enumerate(squad) if c is None]
    fixed = [c for c in squad if c is not None]
    if not empty:
        return {"options": [], "empty": [], "timed_out": False}
    fixed_bp = {c["bp"] for c in fixed}
    leagues = Counter(c["li"] for c in fixed)
    nations = Counter(c["ni"] for c in fixed)
    clubs = Counter(c["ck"] for c in fixed if c.get("ck"))

    def potential(c):
        return (2 * clubs.get(c.get("ck"), 0) + leagues[c["li"]] + nations[c["ni"]]
                + (1 if mni is not None and c["ni"] == mni else 0) + (4 if c.get("ty") == "icon" else 0)
                + (3 if c.get("fc") else 0))
    sl, tc = {}, {}
    for i in empty:
        pos = slots[i]
        cap = (pos_caps or {}).get(pos) or max_ovr or None
        cands = [c for c in by_pos.get(pos, ()) if c["ov"] >= min_rating and (not cap or c["ov"] <= cap)
                 and c["bp"] not in fixed_bp]
        by_pot = sorted(cands, key=lambda c: (potential(c), val(c, pos)), reverse=True)
        by_val = sorted(cands, key=lambda c: val(c, pos), reverse=True)
        seen, merged = set(), []
        for c in by_pot[:per_slot] + by_val[:per_slot // 4]:
            if c["s"] not in seen:
                seen.add(c["s"])
                merged.append(c)
                tc[c["s"]] = _t(c)
        for c in _with_favs(merged, cands, val, pos):
            tc.setdefault(c["s"], _t(c))
        sl[i] = merged
    if any(not sl[i] for i in empty):
        return {"options": [], "empty": empty, "timed_out": False,
                "no_cards": [slots[i] for i in empty if not sl[i]]}
    order = sorted(empty, key=lambda i: len(sl[i]))           # tightest slots first
    t0 = [_t(c) for c in squad]

    def value_of(sq):
        return sum(val(c, slots[i]) for i, c in enumerate(sq) if c is not None and squad[i] is None)
    frontier = [(list(squad), t0)]
    timed_out = False
    for i in order:
        if time.time() - started > time_limit:
            timed_out = True
            break
        nxt = {}
        for sq, ts in frontier:
            bps = {c["bp"] for c in sq if c}
            for c in sl[i]:
                if c["bp"] in bps:
                    continue
                key = tuple(sorted((j, sq[j]["s"]) for j in empty if sq[j] is not None and j != i) + [(i, c["s"])])
                if key in nxt:
                    continue
                nts = list(ts)
                nts[i] = tc[c["s"]]
                nxt[key] = (_ttotal(slots, nts, mni, mli, True), sq, nts, i, c)
        ranked = sorted(nxt.values(), key=lambda e: (-e[0], -val(e[4], slots[e[3]])))
        frontier = []
        for t, sq, nts, j, c in ranked[:beam]:
            new = list(sq)
            new[j] = c
            frontier.append((new, nts))
    if timed_out or any(sq[i] is None for sq, _ in frontier for i in empty):
        frontier = [(sq, ts) for sq, ts in frontier if all(sq[i] is not None for i in empty)]

    def polish(sq, ts):
        """Single swaps on the filled slots while they raise (chemistry, value)."""
        best = (_ttotal(slots, ts, mni, mli, True), value_of(sq))
        for _ in range(4):
            improved = False
            for i in empty:
                bps = {c["bp"] for j, c in enumerate(sq) if c and j != i}
                for c in sl[i]:
                    if c["bp"] in bps or c["s"] == sq[i]["s"]:
                        continue
                    nts = list(ts)
                    nts[i] = tc[c["s"]]
                    t = _ttotal(slots, nts, mni, mli, True)
                    v = best[1] - val(sq[i], slots[i]) + val(c, slots[i])
                    if (t, v) > best:
                        sq = list(sq)
                        sq[i], ts, best, improved = c, nts, (t, v), True
                        bps = {x["bp"] for j, x in enumerate(sq) if x and j != i}
            if not improved or time.time() - started > time_limit + 2:
                break
        return sq, ts, best
    finals, seen = [], set()

    def keep(t, v, sq):
        key = tuple(sorted(sq[i]["bp"] for i in empty))   # other versions of the same players count as one
        if key not in seen:
            seen.add(key)
            finals.append((t, v, sq))
    for sq, ts in frontier[:max(n * 2, 40)]:                   # polished: the best each start leads to
        psq, _, (t, v) = polish(sq, ts)
        keep(t, v, psq)
    for sq, ts in frontier:                                     # unpolished: keeps the list varied
        keep(_ttotal(slots, ts, mni, mli, True), value_of(sq), sq)
    finals.sort(key=lambda x: (-x[0], -x[1]))
    out = []
    for t, v, sq in finals[:n]:
        _, li = _manager_rows(slots, sq, mgr)
        out.append({"fills": [{"slot": i, "in": sq[i]} for i in empty], "total": t, "li": li, "league": li != mli,
                    "avg_ov": round(sum(c["ov"] for c in sq) / len(sq), 1), "value": v})
    return {"options": out, "empty": empty, "timed_out": timed_out}


# --------------------------------------------------------------------------- SBC helper

def sbc_card_cost(c, owned):
    """What using a card in an SBC 'costs' without price data: cards you own are nearly free (the lower rated
    the better, to keep your good ones), bought cards cost more the higher they are rated, promos and
    ICONs/Heroes much more."""
    over = max(0, c["ov"] - 75)
    special = str(c.get("rt") or "").lower() not in BASE_RARITY and not str(c.get("rt") or "").lower().startswith("base ")
    star = c.get("ty") in ("icon", "hero")
    if owned:   # your low cards are nearly free; a good one only gets used when it saves buying an expensive card,
        # and your ICONs / Heroes / promos only as a last resort
        return 0.2 + 0.35 * over ** 1.3 + (30 if special else 0) + (60 if star else 0)
    return 3 + 2 * over ** 1.6 + (8 if special else 0) + (25 if star else 0)


def _sbc_counts(cards, key):
    n = Counter(c[key] for c in cards if c.get(key) is not None)
    return len(n), (max(n.values()) if n else 0), n


def sbc_check(slots, cards, req, mgr=None):
    """Every requirement of an SBC against a full squad -> (list of {label, ok, have}, shortfall score).
    req keys: leagues/nations/clubs {op: exactly|min|max, n}, same_league/same_nation/same_club {op, n},
    rating (min), chem (min), rare (min), special (min), from: [{kind: league|nation|club, id, n}]."""
    rows, short = [], 0.0
    def cmp(label, have, rule):
        nonlocal short
        if not rule or rule.get("n") in (None, ""):
            return
        n, op = int(rule["n"]), rule.get("op", "min")
        miss = abs(have - n) if op == "exactly" else max(0, n - have) if op == "min" else max(0, have - n)
        short += miss
        rows.append({"label": f"{label}: {'Exactly' if op == 'exactly' else 'Min.' if op == 'min' else 'Max.'} {n}",
                     "ok": miss == 0, "have": have})
    for key, field, same in (("leagues", "li", "same_league"), ("nations", "ni", "same_nation"), ("clubs", "ck", "same_club")):
        count, top, _ = _sbc_counts(cards, field)
        cmp({"leagues": "Leagues", "nations": "Nations", "clubs": "Clubs"}[key], count, req.get(key))
        cmp({"same_league": "Same league", "same_nation": "Same nation", "same_club": "Same club"}[same], top, req.get(same))
    for f in req.get("from") or []:
        field = {"league": "li", "nation": "ni", "club": "ck"}.get(f.get("kind"))
        if field and f.get("n"):
            have = sum(1 for c in cards if str(c.get(field)) == str(f.get("id")))
            cmp(f"From {f.get('name') or f.get('id')}", have, {"op": f.get("op", "min"), "n": f["n"]})
    if req.get("rating"):
        r = squad_rating(cards)
        exact = r["exact"] if r else 0
        rows.append({"label": f"Team rating: Min. {int(req['rating'])}", "ok": bool(r) and r["rating"] >= int(req["rating"]),
                     "have": r["rating"] if r else 0})
        if not (r and r["rating"] >= int(req["rating"])):
            short += max(0.25, int(req["rating"]) - exact) * 3
    if req.get("chem"):
        m = mgr or {}
        chem = _ttotal(slots, [_t(c) for c in cards], m.get("ni"), m.get("li"), False)
        rows.append({"label": f"Chemistry: Min. {int(req['chem'])}", "ok": chem >= int(req["chem"]), "have": chem})
        short += max(0, int(req["chem"]) - chem) * 0.6
    for key, label, test in (("rare", "Rare players", lambda c: str(c.get("rt") or "").lower() != "common"),
                             ("special", "Special (promo) cards", lambda c: str(c.get("rt") or "").lower() not in BASE_RARITY
                              and not str(c.get("rt") or "").lower().startswith("base "))):
        if req.get(key):
            have = sum(1 for c in cards if test(c))
            rows.append({"label": f"{label}: Min. {int(req[key])}", "ok": have >= int(req[key]), "have": have})
            short += max(0, int(req[key]) - have)
    return rows, short


def sbc_solve(slots, by_pos, owned, req, mgr=None, time_limit=6.0, n=3, seed=None, avoid=()):
    """Build SBC squads that meet req (see sbc_check) as cheaply as possible: cards you own first (owned:
    set of card slugs), then the lowest-rated cards that work. Simulated annealing over the 11 slots, players
    always in position. Returns up to n distinct valid squads [{cards, cost, owned, checks}], best first,
    or the closest attempt (valid False) when none meets everything in time."""
    import random
    rnd = random.Random(seed)
    avoid = set(avoid)
    cands = {}
    for pos in set(slots):
        cs = [c for c in by_pos.get(pos, ()) if c["s"] not in avoid]
        own = [c for c in cs if c["s"] in owned]
        cheap = sorted((c for c in cs if c["s"] not in owned), key=lambda c: sbc_card_cost(c, False))
        cands[pos] = (own, cheap)
    cost_of = {}

    def cost(c):
        v = cost_of.get(c["s"])
        if v is None:
            v = cost_of[c["s"]] = sbc_card_cost(c, c["s"] in owned)
        return v

    def pick(pos, rnd_):
        own, cheap = cands[pos]
        if own and rnd_.random() < 0.55:
            return rnd_.choice(own)
        if not cheap:
            return rnd_.choice(own) if own else None
        # mostly cheap cards, sometimes anything (needed for rating / rare leagues)
        k = int(len(cheap) * (rnd_.random() ** 3))
        return cheap[min(k, len(cheap) - 1)]

    def score(sq):
        _, short = sbc_check(slots, sq, req, mgr)
        return short * 100 + sum(cost(c) for c in sq), short

    if any(not (cands[p][0] or cands[p][1]) for p in slots):
        return {"solutions": [], "closest": None, "reason": "no cards for " + ", ".join(sorted({p for p in slots if not (cands[p][0] or cands[p][1])}))}
    started = time.time()
    found, best_any = {}, None
    while time.time() - started < time_limit:
        sq, used = [], set()
        for pos in slots:
            for _ in range(20):
                c = pick(pos, rnd)
                if c and c["bp"] not in used:
                    break
            sq.append(c)
            used.add(c["bp"])
        cur, cur_short = score(sq)
        temp = 60.0
        for it in range(2500):
            i = rnd.randrange(11)
            c = pick(slots[i], rnd)
            if c is None or c["s"] == sq[i]["s"] or any(j != i and x["bp"] == c["bp"] for j, x in enumerate(sq)):
                continue
            old = sq[i]
            sq[i] = c
            new, new_short = score(sq)
            if new <= cur or rnd.random() < math.exp((cur - new) / max(temp, 0.01)):
                cur, cur_short = new, new_short
            else:
                sq[i] = old
            temp *= 0.997
            if cur_short == 0:
                key = frozenset(x["s"] for x in sq)
                if key not in found or found[key][0] > cur:
                    found[key] = (cur, list(sq))
        if best_any is None or cur < best_any[0]:
            best_any = (cur, list(sq))
        if len(found) >= 40 and time.time() - started > time_limit / 2:
            break
    def pack(cost_, sq):
        rows, short = sbc_check(slots, sq, req, mgr)
        return {"cards": sq, "cost": round(sum(cost(c) for c in sq), 1), "owned": sum(1 for c in sq if c["s"] in owned),
                "checks": rows, "valid": short == 0, "rating": (squad_rating(sq) or {}).get("rating"),
                "chem": _ttotal(slots, [_t(c) for c in sq], (mgr or {}).get("ni"), (mgr or {}).get("li"), False)}
    ranked = sorted(found.values(), key=lambda x: x[0])
    sols, seen = [], []
    for cost_, sq in ranked:   # keep answers that differ by at least two cards
        ids = {c["s"] for c in sq}
        if any(len(ids ^ s) < 4 for s in seen):
            continue
        seen.append(ids)
        sols.append(pack(cost_, sq))
        if len(sols) >= n:
            break
    return {"solutions": sols, "closest": None if sols else (pack(*best_any) if best_any else None), "reason": ""}


def squad_rating(cards):
    """Squad rating of a full starting eleven as SBCs count it (community formula; EA hasn't published one):
    total of the ratings, plus how far each player is above the average, rounded, divided by 11 and rounded
    down. Returns {"rating": int, "exact": float} or None if a slot is empty."""
    if len(cards) != 11 or any(c is None for c in cards):
        return None
    ovs = [int(c["ov"]) for c in cards]
    total = sum(ovs)
    avg = total / 11
    adjusted = total + sum(o - avg for o in ovs if o > avg)
    return {"rating": int(math.floor(round(adjusted) / 11)), "exact": round(adjusted / 11, 2)}


def candidate_nations(slots, squad, by_pos, mgr=None, k=6, top=25):
    """Manager nations worth trying in a search, best first (the current one left out): nations of the
    players in the squad count most, then nations common among the top-rated cards for the squad's positions
    (the ones a search would bring in)."""
    cur = (mgr or {}).get("ni")
    score = Counter()
    for c in squad:
        if c is not None and c.get("ni") is not None:
            score[c["ni"]] += 3
    for pos in set(slots):
        for c in sorted(by_pos.get(pos, ()), key=lambda c: -c["ov"])[:top]:
            if c.get("ni") is not None:
                score[c["ni"]] += 1
    return [ni for ni, _ in score.most_common() if ni != cur][:k]


def best_manager(slots, squad, mgr=None):
    """The manager nation + league that give this squad the most chemistry (every nation and league in the
    squad is tried; ties keep the current nation/league). Returns {ni, li, total, current, nation, league}."""
    mgr = mgr or {}
    cur_ni, cur_li = mgr.get("ni"), mgr.get("li")
    ts = [_t(c) for c in squad]
    current = _ttotal(slots, ts, cur_ni, cur_li, False)
    nations = {c["ni"] for c in squad if c is not None} | {cur_ni}
    leagues = {c["li"] for c in squad if c is not None} | {cur_li}
    best = (current, 0, cur_ni, cur_li)
    for ni in nations:
        for li in leagues:
            t = _ttotal(slots, ts, ni, li, False)
            key = (t, -((ni != cur_ni) + (li != cur_li)))   # on a tie, fewer changes
            if key > best[:2]:
                best = (t, key[1], ni, li)
    t, _, ni, li = best
    return {"ni": ni, "li": li, "total": t, "current": current, "nation": ni != cur_ni, "league": li != cur_li}
