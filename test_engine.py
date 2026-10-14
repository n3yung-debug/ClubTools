"""Rule tests for chem_engine.  Run:  python test_engine.py"""
import os
import time
import chem_builder as cb
import chem_engine as eng


def card(i, pos, ni=1, li=1, ck=None, ov=85, ty="", fc=False, g=1, alts=(), **kw):
    c = {"s": f"t{i}", "n": f"P{i}", "ov": ov, "rt": "x", "g": g, "p": pos, "a": list(alts), "ni": ni, "nn": f"N{ni}",
         "li": li, "ln": f"L{li}", "ck": ck, "cn": ck, "ty": ty, "bp": i, "fc": fc, "xc": 0, "xl": 0, "xn": 0,
         "xsl": False, "xsn": False}
    c.update(kw)
    return c


SLOTS = ["ST", "ST", "CAM", "CM", "CM", "CDM", "LB", "CB", "CB", "RB", "GK"]


def squad_of(**spec):
    return [card(i, p, **{k: v[i] if isinstance(v, list) else v for k, v in spec.items()}) for i, p in enumerate(SLOTS)]


def test_thresholds():
    # club 2/4/7, league 3/5/8, nation 2/5/8
    assert [eng.pts(n, eng.CLUB_T) for n in (1, 2, 3, 4, 6, 7)] == [0, 1, 1, 2, 2, 3]
    assert [eng.pts(n, eng.LEAGUE_T) for n in (2, 3, 4, 5, 7, 8)] == [0, 1, 1, 2, 2, 3]
    assert [eng.pts(n, eng.NATION_T) for n in (1, 2, 4, 5, 7, 8)] == [0, 1, 1, 2, 2, 3]


def test_cap_at_three():
    # 4 from one club + 8 from one nation would be 2+3=5 -> capped at 3
    sq = squad_of(ni=[1] * 8 + [2, 3, 4], li=list(range(11)), ck=["A"] * 4 + [None] * 7)
    ev = eng.evaluate(SLOTS, sq, None)
    assert ev["players"][0]["chem"] == 3, ev["players"][0]


def test_zero_when_nothing_links():
    sq = squad_of(ni=list(range(11)), li=list(range(11)), ck=[None] * 11)
    assert eng.evaluate(SLOTS, sq, None)["total"] == 0


def test_manager_counts_toward_thresholds():
    sq = squad_of(ni=list(range(11)), li=list(range(11)), ck=[None] * 11)
    # a lone player: manager makes nation count 2 (+1) and league count 2 (still 0)
    ev = eng.evaluate(SLOTS, sq, {"ni": 0, "li": 0})
    assert ev["players"][0]["chem"] == 1 and ev["total"] == 1
    # nation already on 1 point (count 2): manager -> count 3, no new threshold, so no gain
    sq = squad_of(ni=[5, 5] + list(range(20, 29)), li=list(range(11)), ck=[None] * 11)
    assert eng.evaluate(SLOTS, sq, {"ni": 5})["total"] == eng.evaluate(SLOTS, sq, None)["total"] == 2


def test_real_fc27_squad_matches_game():
    # User's in-game squad, 8 Oct 2026: 4-1-2-1-2 (2), manager Spain + Arkema Premiere Ligue, game shows 25/33.
    # Per-player badges read off the screenshot: Salma 3 (the flat "+1" rule gave her 2 -> 24).
    slots = ["GK", "RB", "CB", "CB", "LB", "CDM", "CM", "CM", "CAM", "ST", "ST"]
    spec = [("GK", "BR", "PL", "LIV"), ("RB", "ES", "LL", "ATM"), ("CB", "FR", "LL", "RMA"), ("CB", "ES", "LL", "BAR"),
            ("LB", "PT", "LL", "BAR"), ("CDM", "EN", "WSL", "ARS"), ("CM", "FR", "ARK", "PSG"), ("CM", "ES", "LIGAF", "BAR"),
            ("CAM", "BR", "NWSL", "KCC"), ("ST", "ES", "ARK", "OL"), ("ST", "BR", "LL", "RMA")]
    sq = [card(i, p, ni=n, li=l, ck=k) for i, (p, n, l, k) in enumerate(spec)]
    ev = eng.evaluate(slots, sq, {"ni": "ES", "li": "ARK", "li_free": False})
    assert [p["chem"] for p in ev["players"]] == [1, 3, 3, 3, 3, 0, 2, 3, 1, 3, 3]
    assert ev["total"] == 25


def test_off_position_gets_zero_and_does_not_count():
    sq = squad_of(ni=[1] * 11, li=[1] * 11, ck=["A"] * 11)
    base = eng.evaluate(SLOTS, sq, None)["total"]
    assert base == 33
    sq2 = list(sq)
    sq2[0] = dict(sq2[0], p="GK")  # striker slot filled by a pure GK
    ev = eng.evaluate(SLOTS, sq2, None)
    assert ev["players"][0]["chem"] == 0 and not ev["players"][0]["inpos"]
    assert ev["total"] == 30  # 10 others: club 10 (3) -> still full


def test_icon_and_hero_rules_fc27():
    # ICON: full chem, counts +1 nation and +1 to EVERY league, no club link
    sq = squad_of(ni=list(range(11)), li=[10, 10] + list(range(2, 11)), ck=[None] * 11)
    sq[2] = dict(sq[2], ty="icon", fc=True, li=2118)
    ev = eng.evaluate(SLOTS, sq, None)
    assert ev["players"][2]["chem"] == 3
    # two league-10 players + icon bonus = league count 3 -> +1 each
    assert ev["players"][0]["chem"] == 1 and ev["players"][1]["chem"] == 1
    # Hero: full chem; counts as an ordinary league/nation member (+1,+1) in FC 27
    sq = squad_of(ni=[5, 5] + list(range(2, 11)), li=[10, 10, 10] + list(range(3, 11)), ck=[None] * 11)
    sq[2] = dict(sq[2], ty="hero", fc=True, ni=5, li=10)
    ev = eng.evaluate(SLOTS, sq, None)
    # league: 3 members (2 normal + hero) -> +1 ; nation: 3 members -> +1 ; (player 0)
    assert ev["players"][0]["chem"] == 2, ev["players"][0]


def test_men_women_link_through_club_not_league():
    men = card(0, "ST", ni=1, li=53, ck="243", g=1)
    wom = card(1, "ST", ni=2, li=2222, ck="243", g=2)  # same club link key, different league
    sq = [men, wom] + [card(i, p, ni=100 + i, li=100 + i) for i, p in enumerate(SLOTS[2:], start=2)]
    ev = eng.evaluate(SLOTS, sq, None)
    assert ev["players"][0]["club"] == [2, 1] and ev["players"][1]["chem"] == 1
    assert ev["players"][0]["league"][1] == 0


def test_real_data_sibling_clubs():
    cb.load_cache()
    cards = cb.STATE["cards"]
    groups = {}
    for c in cards:
        if c["ck"]:
            groups.setdefault(c["ck"], set()).add(c["g"])
    both = [k for k, v in groups.items() if v == {1, 2}]
    assert len(both) >= 5, f"expected linked men/women club groups, got {len(both)}"


def test_swap_search_respects_locks_and_duplicates():
    cb.load_cache()
    by_slug = cb.STATE["cards"]
    pool = [c for c in by_slug if c["ov"] >= 80]
    by_pos = eng.index_pool(pool)
    pick = lambda pos, k=0: [c for c in pool if c["p"] == pos][k]  # noqa: E731
    squad = [pick(p, i) for i, p in enumerate(SLOTS)]
    locks = [True] * 11
    base, top, _ = eng.top_singles(SLOTS, squad, locks, None, by_pos, 3, 0)
    assert top == []  # everything locked -> no suggestions
    locks[3] = False
    base, top, _ = eng.top_singles(SLOTS, squad, locks, None, by_pos, 3, 0, only_positive=False)
    assert top and all(r["slot"] == 3 for r in top)
    names = {c["bp"] for i, c in enumerate(squad) if i != 3}
    assert all(r["in"]["bp"] not in names for r in top)


def test_performance_and_plan():
    cb.load_cache()
    pool = [c for c in cb.STATE["cards"] if c["ov"] >= 78]
    by_pos = eng.index_pool(pool)
    pick = lambda pos, k: [c for c in pool if c["p"] == pos][k]  # noqa: E731
    squad = [pick(p, 5 + 3 * i) for i, p in enumerate(SLOTS)]
    locks = [False] * 11
    t = time.time()
    base, singles, allr = eng.top_singles(SLOTS, squad, locks, None, by_pos, 4, 0)
    t1 = time.time() - t
    t = time.time()
    pairs = eng.synergy_pairs(SLOTS, squad, locks, None, by_pos, allr, base, 4, 0)
    t2 = time.time() - t
    t = time.time()
    chain, total, _final = eng.plan_chain(SLOTS, squad, locks, None, by_pos, 4, 0, 5)
    t3 = time.time() - t
    print(f"  base {base}; singles {len(singles)} ({t1:.2f}s); pairs {len(pairs)} ({t2:.2f}s); chain {len(chain)} steps -> {total} ({t3:.2f}s)")
    assert total >= base
    # replaying the chain through the full evaluator must give the same total
    cur = list(squad)
    for st in chain:
        for s in st["swaps"]:
            cur[s["slot"]] = s["in"]
    assert eng.evaluate(SLOTS, cur, None)["total"] == total


def test_ranking_is_chem_then_overall():
    r = [{"d": 2, "dr": 5, "in": {"ov": 80}}, {"d": 2, "dr": -1, "in": {"ov": 90}}, {"d": 3, "dr": -9, "in": {"ov": 70}}]
    r.sort(key=eng._rank_key)
    assert [x["in"]["ov"] for x in r] == [70, 90, 80]


def test_manager_free_league_picks_best():
    # 3 players share league 7 but sit on 2 league pts (count 3 -> 1)... build: manager nation matches nobody
    sq = squad_of(ni=list(range(11)), li=[7, 7] + list(range(20, 29)), ck=[None] * 11)
    ev = eng.evaluate(SLOTS, sq, {"ni": 99, "li": None, "li_free": True})
    assert ev["mgr_li"] == 7 and ev["players"][0]["chem"] == 1 and ev["players"][1]["chem"] == 1
    ev2 = eng.evaluate(SLOTS, sq, {"ni": 99, "li": 20, "li_free": False})
    assert ev2["total"] == 0  # fixed league 20: a lone player + manager = 2, below the 3 needed


def test_manager_nation_options():
    sq = squad_of(ni=[5] * 4 + list(range(20, 27)), li=list(range(11)), ck=[None] * 11)
    o = eng.manager_options(SLOTS, sq, {"ni": None, "li": None, "li_free": False})
    assert o["options"][0]["ni"] == 5 and o["options"][0]["d"] == 4  # Spain-style 4 -> 5: each of 4 goes 1 -> 2


def test_manager_suggestions_cover_nation_and_league():
    # 4 from nation 5 (league 9 x2 + others); manager nation 1 / league 0 helps nobody
    sq = squad_of(ni=[5] * 4 + list(range(20, 27)), li=[9, 9] + list(range(30, 39)), ck=[None] * 11)
    s = eng.manager_suggestions(SLOTS, sq, {"ni": 1, "li": 0, "li_free": False})
    best = s[0]
    assert best["ni"] == 5 and best["li"] == 9 and best["nation"] and best["league"]
    assert best["d"] == 4 + 2  # nation 4->5: four players +1; league 2->3: two players +1
    league_only = [o for o in s if not o["nation"]]
    assert league_only and league_only[0]["li"] == 9 and league_only[0]["d"] == 2
    assert eng.manager_suggestions(SLOTS, sq, {"ni": 5, "li": 9, "li_free": False}) == []  # already best


def test_k_swap_combos_finds_pair_that_only_works_together():
    # everyone isolated; two candidates from a new nation 70 only link with each other (nation 2 -> +1 each)
    sq = squad_of(ni=list(range(11)), li=list(range(11)), ck=[None] * 11, ov=80)
    pool = [card(100, "ST", ni=70, li=50, ov=80), card(101, "CAM", ni=70, li=51, ov=80), card(102, "CM", ni=71, li=52, ov=80)]
    res = eng.k_swap_combos(SLOTS, sq, [False] * 11, None, eng.index_pool(pool), max_drop=0, k_max=3)["by_k"]
    assert res[1] == []  # no single swap helps
    pair = res[2][0]
    assert {w["in"]["s"] for w in pair["swaps"]} == {"t100", "t101"} and pair["d"] == 2
    assert res[3] == []  # a third swap adds nothing, so no 3-swap combo is listed
    locked = eng.k_swap_combos(SLOTS, sq, [True, True] + [False] * 9, None, eng.index_pool(pool), max_drop=0, k_max=2)["by_k"]
    assert locked[2] == []  # both ST slots locked, so the pair is impossible


def test_blacklist_removes_every_version_of_a_player():
    cb.load_cache()
    pool, _ = cb.build_pool({})
    assert any(c["bp"] == 231747 for c in pool) and sum(c["bp"] == 231747 for c in pool) > 1  # several Mbappé cards
    pool, _ = cb.build_pool({"blacklist": [231747]})
    assert not any(c["bp"] == 231747 for c in pool)
    pool, _ = cb.build_pool({"blacklist": ["231747"], "club_list": "Mbappe\nAlisson"})  # also within "cards I own"
    assert [c["n"] for c in pool] == ["Alisson"]
    r = cb.Handler.optimize(_opt_body(blacklist=[c["bp"] for c in cb.STATE["cards"] if c["ty"] == "icon"][:400]))
    incoming = {w["in"]["bp"] for k in r["combos"]["by_k"].values() for x in k for w in x["swaps"]}
    banned = {c["bp"] for c in cb.STATE["cards"] if c["ty"] == "icon"}
    assert incoming and not incoming & banned


def test_upgrades_raise_rating_within_chem_budget():
    # full-chem squad: everyone nation 1 / league 1 / club A, rated 80
    sq = squad_of(ni=[1] * 11, li=[1] * 11, ck=["A"] * 11, ov=80)
    assert eng.total_only(SLOTS, sq, None) == 33
    pool = [card(200, "ST", ni=1, li=1, ck="A", ov=88),   # same links, better: no chem lost
            card(201, "ST", ni=9, li=9, ck="Z", ov=95),   # big upgrade, links nothing
            card(202, "GK", ni=1, li=1, ck="A", ov=79)]   # worse: never an "upgrade"
    res = eng.upgrade_combos(SLOTS, sq, [False] * 11, None, eng.index_pool(pool), k_max=2, max_loss=3)
    one = res["by_k"][1]
    assert res["floor"] == 30 and all(x["total"] >= 30 for k in res["by_k"].values() for x in k)
    assert one[0]["swaps"][0]["in"]["s"] == "t201" and one[0]["dr"] == 15 and one[0]["total"] == 30
    assert all(w["in"]["ov"] > w["out"]["ov"] for k in res["by_k"].values() for x in k for w in x["swaps"])
    strict = eng.upgrade_combos(SLOTS, sq, [False] * 11, None, eng.index_pool(pool), k_max=2, max_loss=0)
    assert [w["in"]["s"] for w in strict["by_k"][1][0]["swaps"]] == ["t200"] and strict["by_k"][1][0]["total"] == 33
    assert strict["by_k"][2] == []  # the only other upgrade (t201) costs chemistry
    capped = eng.upgrade_combos(SLOTS, sq, [False] * 11, None, eng.index_pool(pool), k_max=2, max_loss=3, max_ovr=90)
    assert all(w["in"]["ov"] <= 90 for k in capped["by_k"].values() for x in k for w in x["swaps"])
    assert capped["by_k"][1][0]["swaps"][0]["in"]["s"] == "t200"  # the 95 is over the cap
    st_only = eng.upgrade_combos(SLOTS, sq, [False] * 11, None, eng.index_pool(pool), k_max=1, max_loss=3,
                                 max_ovr=85, pos_caps={"ST": 99})   # per-position cap beats the general one
    assert {w["in"]["s"] for x in st_only["by_k"][1] for w in x["swaps"]} == {"t200", "t201"}
    blocked = eng.upgrade_combos(SLOTS, sq, [False] * 11, None, eng.index_pool(pool), k_max=1, max_ovr=80)
    st = [w for w in blocked["slots"] if w["pos"] == "ST"][0]
    assert blocked["by_k"][1] == [] and st["higher"] == 2 and st["in_cap"] == 0 and st["cap"] == 80
    two = res["by_k"][2][0]
    assert {w["in"]["s"] for w in two["swaps"]} == {"t200", "t201"} and two["dr"] == 23 and two["total"] >= 30


def test_playstyle_preferences_rank_and_upgrade():
    val = eng.make_value({"GK": [31], "ATT": [34, 16]}, w_plus=3, w_ps=1)
    gk_plus = card(300, "GK", ov=86, pp=[31])          # 1v1 Close Down+ -> 89
    gk_plain = card(301, "GK", ov=87, ps=[28])         # no wanted PlayStyle -> 87
    st = card(302, "ST", ov=85, ps=[34, 16], pp=[])    # Low Driven + Technical -> 87
    assert val(gk_plus, "GK") == 89 and val(gk_plain, "GK") == 87 and val(st, "ST") == 87
    assert val(st, "CB") == 85 and eng.plain_value(gk_plus, "GK") == 86  # no preference for defenders here
    per_pos = eng.make_value({"CDM": [12], "CM": [16], "CAM": [16]})
    mid = card(304, "CM", ov=84, ps=[12, 16])
    assert per_pos(mid, "CDM") == 85 and per_pos(mid, "CM") == 85 and per_pos(mid, "LM") == 84
    assert eng.make_value({"CM": []})(mid, "CM") == 84  # an empty list for a position means no preference there
    # same chemistry gain for both keepers: the 1v1 Close Down+ one is suggested first
    sq = squad_of(ni=[1] * 10 + [2], li=[1] * 10 + [2], ck=[None] * 11, ov=85)
    for c in (gk_plus, gk_plain):
        c.update(ni=1, li=1)
    _, top, _ = eng.top_singles(SLOTS, sq, [False] * 11, None, eng.index_pool([gk_plain, gk_plus]), 5, 0, val=val)
    assert top[0]["in"]["s"] == "t300"
    _, top, _ = eng.top_singles(SLOTS, sq, [False] * 11, None, eng.index_pool([gk_plain, gk_plus]), 5, 0)
    assert top[0]["in"]["s"] == "t301"  # without preferences: higher overall first
    # upgrades: an equal-rated keeper that adds 1v1 Close Down+ counts as an upgrade
    full = squad_of(ni=[1] * 11, li=[1] * 11, ck=["A"] * 11, ov=80)
    same = card(303, "GK", ni=1, li=1, ck="A", ov=80, pp=[31])
    up = eng.upgrade_combos(SLOTS, full, [False] * 11, None, eng.index_pool([same]), k_max=1, max_loss=0, val=val)
    assert up["by_k"][1][0]["swaps"][0]["in"]["s"] == "t303" and up["by_k"][1][0]["dr"] == 0 and up["by_k"][1][0]["dv"] == 3
    assert eng.upgrade_combos(SLOTS, full, [False] * 11, None, eng.index_pool([same]), k_max=1)["by_k"][1] == []


def test_alternate_positions_and_playstyles_follow_the_slot():
    # a CB-main card with CDM as an alternate is suggested for CDM and judged on the CDM preference
    sq = squad_of(ni=[1] * 11, li=[1] * 11, ck=[None] * 11, ov=80)
    alt = card(400, "CB", alts=("CDM",), ni=1, li=1, ov=81, ps=[12])            # Intercept
    plain = card(401, "CDM", ni=1, li=1, ov=81)
    val = eng.make_value({"CDM": [12], "CB": []})
    by_pos = eng.index_pool([alt, plain])
    assert alt in by_pos["CDM"] and alt in by_pos["CB"]
    locks = [s != "CDM" for s in SLOTS]
    _, top, _ = eng.top_singles(SLOTS, sq, locks, None, by_pos, 5, 0, only_positive=False, val=val)
    assert top[0]["in"]["s"] == "t400" and top[0]["v"] == 82  # CDM preference applied though its main position is CB
    assert val(alt, "CB") == 81                                 # same card in a CB slot: no CB preference set


def test_fill_squad_completes_around_fixed_players():
    # 5 placed players from nation 1 / league 1 / club A; the pool has a linking card and a non-linking
    # (higher rated) card for every position
    sq = squad_of(ni=[1] * 11, li=[1] * 11, ck=["A"] * 11, ov=85)
    keep = {0, 2, 6, 9, 10}
    partial = [c if i in keep else None for i, c in enumerate(sq)]
    pool = []
    for i, pos in enumerate(SLOTS):
        pool.append(card(500 + i, pos, ni=1, li=1, ck="A", ov=84))   # links with everyone
        pool.append(card(600 + i, pos, ni=900 + i, li=900 + i, ck=f"Z{i}", ov=90))   # better rated, links nothing
    res = eng.fill_squad(SLOTS, partial, None, eng.index_pool(pool))
    best = res["options"][0]
    assert res["empty"] == [i for i in range(11) if i not in keep]
    assert best["total"] == 33 and {f["slot"] for f in best["fills"]} == set(res["empty"])
    assert all(f["in"]["ni"] == 1 for f in best["fills"])            # chemistry beats rating
    filled = list(partial)
    for f in best["fills"]:
        filled[f["slot"]] = f["in"]
    assert eng.total_only(SLOTS, filled, None) == 33 and all(filled[i] is partial[i] for i in keep)
    capped = eng.fill_squad(SLOTS, partial, None, eng.index_pool(pool), max_ovr=80)
    assert capped["options"] == [] and capped["no_cards"]           # nothing rated 80 or lower exists
    assert eng.fill_squad(SLOTS, sq, None, eng.index_pool(pool))["options"] == []  # nothing to fill


def test_no_women_at_chosen_positions():
    w = card(700, "CB", alts=("CDM",), g=2)
    m = card(701, "CB")
    by_pos = eng.index_pool([w, m], no_women={"GK", "CB"})
    assert by_pos["CB"] == [m] and by_pos["CDM"] == [w]   # still suggested where allowed
    assert eng.index_pool([w, m])["CB"] == [w, m]


def test_player_blocked_at_one_position_only():
    # e.g. Bellingham (CM, alt CAM): never suggested at CAM, every version, still fine at CM
    v1, v2 = card(710, "CM", alts=("CAM",)), card(711, "CM", alts=("CAM",))
    v2["bp"] = v1["bp"]
    other = card(712, "CAM")
    by_pos = eng.index_pool([v1, v2, other], pos_bans=[(v1["bp"], "CAM")])
    assert by_pos["CAM"] == [other] and by_pos["CM"] == [v1, v2]
    assert cb.pos_bans({"pos_bans": [{"bp": 5, "pos": "CAM"}, {"bp": 6, "pos": "XX"}, {"pos": "CM"}]}) == [("5", "CAM")]


def test_position_ban_reaches_the_search():
    cb.load_cache()
    b = _opt_body()
    _, _, _, _, _, by_pos, _, _ = cb._search_setup(b)
    victim = by_pos["CAM"][0]
    b = _opt_body(pos_bans=[{"bp": victim["bp"], "pos": "CAM"}])
    _, _, _, _, _, by_pos, _, _ = cb._search_setup(b)
    assert all(c["bp"] != victim["bp"] for c in by_pos["CAM"])
    assert any(c["bp"] == victim["bp"] for p in eng.prefs(victim) if p != "CAM" for c in by_pos.get(p, [])) \
        or eng.prefs(victim) == ["CAM"]


def test_required_weak_foot_skills_and_stats():
    st = {"wf": 5, "sm": 4, "fs": [90, 0, 0, 0, 0, 0]}
    r = {"ST": st, "CM": st, "CB": {"wf": 0, "sm": 0, "fs": [80, 0, 0, 0, 0, 0]}}
    good = card(720, "ST", alts=("CM",), wf=5, sm=4, fs=[92, 80, 75, 85, 40, 70])
    slow = card(721, "ST", wf=5, sm=5, fs=[85, 90, 80, 88, 40, 75])   # PAC 85 < 90
    weak = card(722, "ST", wf=4, sm=5, fs=[95, 90, 80, 88, 40, 75])   # 4* WF
    unknown = card(723, "ST", fs=[95, 90, 80, 88, 40, 75])            # no WF/SM data: not met
    keeper = card(724, "GK", wf=2, sm=1, fs=[85, 84, 80, 86, 50, 84])
    fast_cb = card(725, "CB", wf=2, sm=2, fs=[82, 40, 60, 65, 85, 80])
    slow_cb = card(726, "CB", wf=5, sm=5, fs=[70, 40, 60, 65, 88, 85])
    assert eng.meets(good, "ST", r) and eng.meets(good, "CM", r)
    assert not eng.meets(slow, "ST", r) and not eng.meets(weak, "ST", r) and not eng.meets(unknown, "ST", r)
    assert eng.meets(weak, "LW", r) and eng.meets(keeper, "GK", r)   # positions without requirements
    assert eng.meets(fast_cb, "CB", r) and not eng.meets(slow_cb, "CB", r)   # CB: only pace matters, not skills
    by_pos = eng.index_pool([good, slow, weak, unknown, keeper, fast_cb, slow_cb], reqs=r)
    assert by_pos["ST"] == [good] and by_pos["GK"] == [keeper] and by_pos["CB"] == [fast_cb]
    # server side: new per-position shape, older single-set shape, and nothing set
    z = [0] * 6
    row = lambda **k: dict({"wf": 0, "sm": 0, "ht": 0, "ft": "", "ar": "", "fs": z}, **k)  # noqa: E731
    assert cb.reqs({"reqs": {"by_pos": {"ST": {"sm": 5, "fs": z}, "CB": {"fs": [80, 0, 0, 0, 0, 0]},
                                        "XX": {"sm": 5}, "LW": {"wf": 0, "sm": 0, "fs": z},
                                        "GK": {"wf": 3, "fs": [90, 0, 0, 0, 0, 0]}}}}) == {
        "ST": row(sm=5), "CB": row(fs=[80, 0, 0, 0, 0, 0]), "GK": row(wf=3, fs=[])}
    assert cb.reqs({"reqs": {"wf": 5, "pos": ["ST", "XX"]}}) == {"ST": row(wf=5, fs=[])}
    assert cb.reqs({"reqs": {"by_pos": {"ST": {"wf": 0, "sm": 0, "fs": z}}}}) is None
    assert cb.reqs({"reqs": {"wf": 5, "pos": []}}) is None


def test_foot_height_accelerate_and_prefer_mode():
    r = {"LB": {"ft": "L"}, "CB": {"ht": 188}, "ST": {"ar": "Explosive", "sm": 5}}
    lefty = card(730, "LB", ft="L"); righty = card(731, "LB", ft="R")
    tall = card(732, "CB", ht=191); short = card(733, "CB", ht=180); unknown = card(734, "CB")
    quick = card(735, "ST", ar="Explosive", sm=5); lengthy = card(736, "ST", ar="Lengthy", sm=5)
    assert eng.meets(lefty, "LB", r) and not eng.meets(righty, "LB", r)
    assert eng.meets(tall, "CB", r) and not eng.meets(short, "CB", r) and not eng.meets(unknown, "CB", r)
    assert eng.meets(quick, "ST", r) and not eng.meets(lengthy, "ST", r)
    assert eng.pref_points(lengthy, "ST", r) == 1 and eng.pref_points(quick, "ST", r) == 2
    # prefer: nothing is filtered out, but meeting criteria adds w_soft rating points each
    val = eng.make_value(None, 3, 1, r, 4)
    assert val(quick, "ST") == quick["ov"] + 8 and val(lengthy, "ST") == lengthy["ov"] + 4 and val(righty, "LB") == righty["ov"]
    o = {"reqs": {"mode": "prefer", "w": 4, "by_pos": {"ST": {"sm": 5}}}}
    assert cb.reqs(o) is None and cb.soft_reqs(o)[0]["ST"]["sm"] == 5 and cb.soft_reqs(o)[1] == 4
    assert cb.soft_reqs({"reqs": {"by_pos": {"ST": {"sm": 5}}}}) == (None, 0)   # default is require
    assert cb.reqs({"reqs": {"by_pos": {"LB": {"ft": "X", "ht": 0}}}}) is None    # invalid foot ignored


def test_fill_squad_respects_required_stats():
    fixed = [card(800 + i, p, ni=100 + i, li=200 + i, wf=3, sm=3) for i, p in enumerate(SLOTS)]
    squad = list(fixed)
    squad[0] = None   # an empty ST slot
    five = card(850, "ST", ni=100, li=200, wf=5, sm=5, ov=80)
    four = card(851, "ST", ni=101, li=201, wf=4, sm=5, ov=90)   # better rated but only 4* WF
    by_pos = eng.index_pool([five, four], reqs={"ST": {"wf": 5, "sm": 0, "fs": []}})
    res = eng.fill_squad(SLOTS, squad, None, by_pos)
    picks = {o["fills"][0]["in"]["s"] for o in res["options"]}
    assert picks == {five["s"]}


def test_favourite_wins_when_chemistry_is_equal():
    # empty CM slot: two cards that link the same, the favourite is rated lower but is picked at CM only
    fixed = [card(900 + i, p, ni=1, li=1, ck="A") for i, p in enumerate(SLOTS)]
    squad = list(fixed)
    squad[3] = None
    fav = card(950, "CM", ni=1, li=1, ck="A", ov=84, alts=("CDM",))
    big = card(951, "CM", ni=1, li=1, ck="A", ov=87, alts=("CDM",))
    by_pos = eng.index_pool([fav, big])
    plain = eng.fill_squad(SLOTS, squad, None, by_pos)
    assert plain["options"][0]["fills"][0]["in"]["s"] == big["s"]
    val = eng.make_value(favs={(fav["s"], "CM")}, w_fav=5)
    assert val(fav, "CM") == 89 and val(fav, "CDM") == 84 and val(big, "CM") == 87
    res = eng.fill_squad(SLOTS, squad, None, by_pos, val=val)
    assert res["options"][0]["fills"][0]["in"]["s"] == fav["s"]
    # chemistry still comes first: a favourite that links nothing loses to a linking card
    lone = card(952, "CM", ni=9, li=9, ck="Z", ov=84)
    res = eng.fill_squad(SLOTS, squad, None, eng.index_pool([lone, big]), val=eng.make_value(favs={(lone["s"], "CM")}, w_fav=5))
    assert res["options"][0]["fills"][0]["in"]["s"] == big["s"]


def test_favourite_counts_as_upgrade_and_within_rating_drop():
    sq = squad_of(ni=[1] * 11, li=[1] * 11, ck=["A"] * 11, ov=86)
    locks = [False] * 11
    fav = card(960, "CB", ni=1, li=1, ck="A", ov=81)      # 5 lower: blocked by a 3-point rating drop on its own
    by_pos = eng.index_pool([fav])
    _, plain = eng.single_swaps(SLOTS, sq, locks, None, by_pos, max_drop=3)
    assert not plain
    val = eng.make_value(favs={(fav["s"], "CB")}, w_fav=6)
    _, liked = eng.single_swaps(SLOTS, sq, locks, None, by_pos, max_drop=3, val=val)
    assert {r["slot"] for r in liked} == {7, 8} and all(r["in"]["s"] == fav["s"] for r in liked)
    # a favourite already in the squad can still be swapped out when that raises chemistry (it is not a lock)
    sq2 = list(sq)
    sq2[7] = card(961, "CB", ni=9, li=9, ck="Z", ov=86)                  # links nothing
    by2 = eng.index_pool([card(962, "CB", ni=1, li=1, ck="A", ov=85)])
    _, out = eng.single_swaps(SLOTS, sq2, locks, None, by2, max_drop=3, val=eng.make_value(favs={(sq2[7]["s"], "CB")}, w_fav=100))
    assert any(r["slot"] == 7 and r["d"] > 0 for r in out)
    # rating upgrades: 81 + 6 beats an 86 at CB
    up = eng.upgrade_combos(SLOTS, sq, locks, None, by_pos, k_max=1, max_loss=3, val=val)
    assert any(s["in"]["s"] == fav["s"] for o in up["by_k"].get(1, []) for s in o["swaps"])
    assert not eng.upgrade_combos(SLOTS, sq, locks, None, by_pos, k_max=1, max_loss=3)["by_k"].get(1)


def test_favourite_skips_required_stats_and_women_filter_but_not_blocks():
    w = card(970, "CAM", wf=3, sm=4, g=2, alts=("CM",))
    reqs = {"CAM": {"wf": 0, "sm": 5, "fs": []}, "CM": {"wf": 0, "sm": 5, "fs": []}}
    assert "CAM" not in eng.index_pool([w], reqs=reqs)
    by = eng.index_pool([w], no_women={"CAM", "CM"}, reqs=reqs, keep={(w["s"], "CAM")})
    assert by.get("CAM") == [w] and "CM" not in by                      # only where it is a favourite
    assert "CAM" not in eng.index_pool([w], pos_bans=[(970, "CAM")], keep={(w["s"], "CAM")})


def test_cheapest_versions_keeps_lowest_with_same_chemistry():
    base = card(980, "CM", ov=84, rt="Rare", bp=77, alts=("CAM",))
    promo = card(981, "CM", ov=90, rt="Future Stars", bp=77, alts=("CAM", "ST"))   # adds ST
    moved = card(982, "CM", ov=88, rt="Team of the week", bp=77, ck="B")          # other club: own chemistry
    other = card(983, "CM", ov=86, rt="Rare", bp=78)
    by = eng.cheapest_versions(eng.index_pool([base, promo, moved, other]))
    assert {c["s"] for c in by["CM"]} == {base["s"], moved["s"], other["s"]}
    assert {c["s"] for c in by["CAM"]} == {base["s"]} and [c["s"] for c in by["ST"]] == [promo["s"]]
    # below the minimum rating the base card doesn't count, so the promo stays
    assert {c["s"] for c in eng.cheapest_versions(eng.index_pool([base, promo]), floor=85)["CM"]} == {promo["s"]}
    # a favourite version is always kept
    kept = eng.cheapest_versions(eng.index_pool([base, promo]), keep={(promo["s"], "CM")})
    assert {c["s"] for c in kept["CM"]} == {base["s"], promo["s"]}


def test_server_cheap_versions_and_no_promo():
    cb.load_cache()
    mb = cb.STATE["by_bp"][231747]                       # Mbappé: Rare 91 and Destined for Glory 91
    assert {c["rt"] for c in mb} >= {"Rare", "Destined for Glory"}
    pool, _ = cb.build_pool({})
    st = [c for c in cb.search_index({"cheap_versions": True}, pool)["ST"] if c["bp"] == 231747]
    assert [c["rt"] for c in st] == ["Rare"]
    assert len([c for c in cb.search_index({}, pool)["ST"] if c["bp"] == 231747]) == 2
    nopromo, _ = cb.build_pool({"exclude_types": ["promo"]})
    rts = {c["rt"] for c in nopromo}
    assert "Rare" in rts and "Base Icon" in rts and not rts & {"Team of the week", "Future Stars", "Destined for Glory"}


def test_icon_rating_cap():
    cb.load_cache()
    pool, _ = cb.build_pool({"icon_max": 90})
    assert max(c["ov"] for c in pool if c["ty"] == "icon") == 90 and max(c["ov"] for c in pool if c["ty"] == "hero") == 89
    assert any(c["ty"] == "icon" for c in pool) and max(c["ov"] for c in pool if c["ty"] == "") > 87   # others untouched
    pele = next(c for c in cb.STATE["cards"] if c["n"] == "Pelé" and c["ty"] == "icon")
    kept, _ = cb.build_pool({"icon_max": 87, "favs": [{"s": pele["s"], "pos": "CAM"}]})
    assert any(c["s"] == pele["s"] for c in kept)                     # a favourite is always allowed


def test_lock_hint_names_the_locked_players_that_block_chemistry():
    cb.load_cache()
    meta_f = {f["name"]: f for f in cb.FORMATIONS.values()}
    slots = meta_f["4-1-2-1-2 (2)"]["slots"]
    by = cb.STATE["by_slug"]
    pick = {"ST": ["27-265898", "27-231443"], "CAM": ["27-247827"], "CM": ["27-233662", "27-271446"], "CDM": ["27-237289"],
            "LB": ["27-265674"], "CB": ["27-278046", "27-268889"], "RB": ["27-226161"], "GK": ["27-259532"]}
    squad = [by[pick[p].pop(0)] for p in slots]
    fr = next(c["ni"] for c in cb.STATE["cards"] if c["nn"] == "France")
    ark = next(c["li"] for c in cb.STATE["cards"] if c["ln"] == "Arkema Première Ligue")
    locks = [p != "CB" or i == 2 for i, p in enumerate(slots)]       # only one CB free
    r = cb.Handler.optimize({"slots": slots, "squad": squad, "locks": locks, "mgr": {"ni": fr, "li": ark},
                             "opts": {"max_drop": 6, "max_steps": 8}})
    assert r["chain_total"] == 32 and r["lock_hint"]["total"] == 33
    assert all(locks[i] for i in r["lock_hint"]["slots"]) and r["lock_hint"]["slots"]
    free = cb.Handler.optimize({"slots": slots, "squad": squad, "locks": [False] * 11, "mgr": {"ni": fr, "li": ark}, "opts": {}})
    assert free["lock_hint"] is None


def test_feedback_posts_to_the_google_form():
    import urllib.request as ur
    old = (cb.FEEDBACK_FORM, dict(cb.FEEDBACK_FIELDS), ur.urlopen)
    sent = {}

    class Resp:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=0):
        sent["url"], sent["data"] = req.full_url, req.data.decode()
        return Resp()
    try:
        cb.FEEDBACK_FORM = ""
        assert not cb.feedback_ready()
        try:
            cb.send_feedback({"type": "Bug", "message": "hello there"}); raise AssertionError("should refuse")
        except ValueError as e:
            assert cb.FEEDBACK_EMAIL in str(e)
        cb.FEEDBACK_FORM = "1FAIpQLSf" + "x" * 30
        cb.FEEDBACK_FIELDS.update(type="entry.111111", message="entry.222222", contact="entry.333333", version="entry.444444")
        assert cb.feedback_ready()
        ur.urlopen = fake
        cb.FEEDBACK_LAST["t"] = 0
        for bad in ({"type": "Spam", "message": "hello there"}, {"type": "Bug", "message": "hi"}):
            try:
                cb.send_feedback(bad); raise AssertionError(bad)
            except ValueError:
                pass
        assert cb.send_feedback({"type": "Feature request", "message": "Add a price filter please", "contact": "me@x.com"}) == {"ok": True}
        assert sent["url"] == f"https://docs.google.com/forms/d/e/{cb.FEEDBACK_FORM}/formResponse"
        assert "entry.111111=Feature+request" in sent["data"] and "entry.222222=Add+a+price+filter+please" in sent["data"]
        assert "entry.333333=me%40x.com" in sent["data"] and "entry.444444=" in sent["data"]
        try:   # too soon after the last one
            cb.send_feedback({"type": "Bug", "message": "another one"}); raise AssertionError("rate limit")
        except ValueError:
            pass
    finally:
        cb.FEEDBACK_FORM, ur.urlopen = old[0], old[2]
        cb.FEEDBACK_FIELDS.clear(); cb.FEEDBACK_FIELDS.update(old[1]); cb.FEEDBACK_LAST["t"] = 0


def test_searches_try_other_manager_nations():
    cb.load_cache()
    by = cb.STATE["by_slug"]
    slots = cb.FORMATIONS["4-1-2-1-2 (2)"]["slots"]
    pick = {"ST": ["27-265898", "27-231443"], "CAM": ["27-247827"], "CM": ["27-233662", "27-271446"], "CDM": ["27-237289"],
            "LB": ["27-265674"], "CB": ["27-278046", "27-268889"], "RB": ["27-226161"], "GK": ["27-259532"]}
    squad = [by[pick[p].pop(0)] for p in slots]
    nat = lambda n: next(c["ni"] for c in cb.STATE["cards"] if c["nn"] == n)   # noqa: E731
    ark = next(c["li"] for c in cb.STATE["cards"] if c["ln"] == "Arkema Première Ligue")
    o = {"max_drop": 3, "cheap_versions": True, "icon_max": 90, "exclude_types": ["icon"]}
    locks = [True] * 11
    locks[2] = locks[3] = False
    bad = {"ni": nat("Japan"), "li": ark}                    # nobody in the squad is Japanese
    nations = eng.candidate_nations(slots, squad, cb.search_index(o, cb.build_pool(o)[0]), bad)
    assert nat("France") in nations and nat("Japan") not in nations
    # fill: the best options use a French manager, and say so
    sq2 = [c if i not in (8, 9, 10) else None for i, c in enumerate(squad)]
    f = cb.Handler.fill({"slots": slots, "squad": sq2, "mgr": bad, "opts": o})
    assert f["options"][0]["total"] == 33 and f["options"][0]["mgr"]["ni"] == nat("France")
    # with the best manager already in place nothing suggests a new one
    good = cb.Handler.fill({"slots": slots, "squad": sq2, "mgr": {"ni": nat("France"), "li": ark}, "opts": o})
    assert all(x["mgr"] is None for x in good["options"][:5])
    # upgrades: the same upgrade with and without a new manager -> the one without
    r = cb.Handler.optimize({"slots": slots, "squad": squad, "locks": locks, "mgr": bad, "opts": o})
    ups = r["upgrades"]["by_k"][1]
    keys = [tuple(sorted((w["slot"], w["in"]["bp"]) for w in x["swaps"])) for x in ups]
    assert len(keys) == len(set(keys)) and any(x["mgr"] is None for x in ups)
    assert r["chain_total"] >= r["base"] and (r["chain_mgr"] is None or r["chain_mgr"]["ni"] != bad["ni"])


def test_squad_rating_community_formula():
    mk = lambda ovs: [{"ov": o} for o in ovs]   # noqa: E731
    assert eng.squad_rating(mk([84] * 10 + [90])) == {"rating": 85, "exact": 85.04}   # the outlier lifts it
    assert eng.squad_rating(mk([84] * 11))["rating"] == 84
    assert eng.squad_rating(mk([86, 86] + [84] + [83] * 8))["rating"] == 84
    assert eng.squad_rating(mk([84] * 10)) is None and eng.squad_rating(mk([84] * 10) + [None]) is None


def test_sbc_check_counts_requirements():
    sq = squad_of(ni=[1] * 6 + [2] * 5, li=[1] * 4 + [2] * 4 + [3] * 3, ck=["A"] * 3 + [None] * 8, ov=80)
    rows, short = eng.sbc_check(SLOTS, sq, {"leagues": {"op": "exactly", "n": 3}, "nations": {"op": "exactly", "n": 2},
                                            "same_league": {"op": "max", "n": 4}, "same_club": {"op": "max", "n": 2},
                                            "rating": 80})
    by = {r["label"]: r for r in rows}
    assert by["Leagues: Exactly 3"]["ok"] and by["Nations: Exactly 2"]["ok"] and by["Same league: Max. 4"]["ok"]
    assert not by["Same club: Max. 2"]["ok"] and by["Same club: Max. 2"]["have"] == 3 and short == 1
    assert by["Team rating: Min. 80"]["ok"]


def test_sbc_build_uses_your_club_first():
    cb.load_cache()
    req = {"leagues": {"op": "exactly", "n": 3}, "nations": {"op": "exactly", "n": 2},
           "same_league": {"op": "max", "n": 6}, "same_nation": {"op": "max", "n": 6}, "chem": 30}
    r = cb.sbc_build({"req": req, "formation": "4-4-2", "opts": {}})
    s = r["solutions"][0]
    assert s["valid"] and s["chem"] >= 30 and not any(s["own"])                 # nothing owned: all to buy
    rows, short = eng.sbc_check(s["slots"], s["cards"], req)
    assert short == 0 and len({c["li"] for c in s["cards"]}) == 3 and len({c["ni"] for c in s["cards"]}) == 2
    club = "\n".join(c["s"] + "  " + c["n"] for c in s["cards"][:6])            # own six of those cards
    r2 = cb.sbc_build({"req": req, "formation": "4-4-2", "opts": {"club_list": club}, "prefer_owned": True})
    assert r2["owned"] == 6 and r2["solutions"][0]["valid"] and sum(r2["solutions"][0]["own"]) >= 5
    # default: lowest-rated build, and each option says how many club cards can be swapped in (still valid)
    r4 = cb.sbc_build({"req": req, "formation": "4-4-2", "opts": {"club_list": club}})
    w = [x.get("with_club") for x in r4["solutions"] if x.get("with_club")]   # (whether any fit depends on the build)
    assert all(all(c["ok"] for c in x["checks"]) and x["owned"] >= x["swapped"] >= 1 for x in w)
    # a card you own that's identical to one in the squad (another player, lower rated) always swaps in
    twin = dict(s["cards"][3], s="27-own-twin", bp=-424242, ov=s["cards"][3]["ov"] - 1)
    by_pos = {s["slots"][3]: [twin]}
    cards, n = eng.sbc_use_owned(s["slots"], s["cards"], by_pos, {twin["s"]}, req)
    assert n == 1 and twin["s"] in {c["s"] for c in cards} and eng.sbc_check(s["slots"], cards, req)[1] == 0   # (either CB slot)
    # protected cards (e.g. your squad) are never used
    avoid = [c["s"] for c in s["cards"]]
    r3 = cb.sbc_build({"req": req, "formation": "4-4-2", "opts": {}, "avoid": avoid})
    assert not ({c["s"] for c in r3["solutions"][0]["cards"]} & set(avoid))


def test_sbc_quality_and_or_rules():
    sq = squad_of(ni=1, li=1, ck=["A", "B"] + [None] * 9, ov=[60, 70] + [80] * 9)
    assert [eng.tier(c) for c in sq[:3]] == ["bronze", "silver", "gold"]
    req = {"quality": {"op": "min", "tier": "silver"},
           "from": [{"kind": "club", "ids": ["A", "B"], "op": "min", "n": 2, "name": "A or B"},
                    {"kind": "quality", "ids": ["silver"], "op": "min", "n": 1}]}
    rows, short = eng.sbc_check(SLOTS, sq, req)
    by = {r["label"]: r for r in rows}
    assert by["From A or B: Min. 2"]["ok"] and by["Silver: Min. 1"]["ok"]
    assert not by["Player quality: Min. Silver"]["ok"] and short == 1        # the 60 is a bronze
    assert eng.quality_ok(sq[0], {"op": "max", "tier": "silver"}) and not eng.quality_ok(sq[2], {"op": "max", "tier": "silver"})
    assert eng.quality_ok(sq[1], {"op": "exactly", "tier": "silver"})


def test_sbc_cost_prefers_any_owned_card_then_lowest_rated():
    hi, lo, promo = {"s": "a", "ov": 90, "rt": "Rare"}, {"s": "b", "ov": 50, "rt": "Rare"}, {"s": "c", "ov": 99, "rt": "TOTY", "ty": "icon"}
    assert max(eng.sbc_card_cost(c, True) for c in (hi, lo, promo)) < min(eng.sbc_card_cost(c, False) for c in (hi, lo))
    assert eng.sbc_card_cost(lo, True) < eng.sbc_card_cost(hi, True)
    costs = [eng.sbc_card_cost({"s": str(o), "ov": o, "rt": "Rare"}, False) for o in range(45, 95)]
    assert costs == sorted(costs) and len(set(costs)) == len(costs)      # buying: lowest overall is cheapest


def test_sbc_build_uses_bronze_and_silver_cards():
    cb.load_cache()
    gold = [c for c in cb.STATE["cards"] if c["ty"] == "" and c["rt"] == "Rare"]
    low = []
    for i, c in enumerate(gold[:900]):   # silver / bronze copies of real players (same league, nation, club)
        low.append(dict(c, s=f"27-9{i:06d}", bp=-1 - i, ov=55 + i % 20, rt="Rare"))
    saved = cb.STATE["low"], cb.STATE["by_slug"]
    try:
        cb.STATE["low"] = low
        cb.STATE["by_slug"] = dict(saved[1], **{c["s"]: c for c in low})
        req = {"quality": {"op": "max", "tier": "silver"}, "from": [{"kind": "quality", "ids": ["silver"], "op": "min", "n": 1}],
               "clubs": {"op": "min", "n": 4}, "chem": 10}
        r = cb.sbc_build({"req": req, "formation": "4-4-2", "opts": {}})
        s = r["solutions"][0]
        assert s["valid"] and all(c["ov"] < 75 for c in s["cards"]) and not r["need_low"]
        club = "\n".join(c["s"] for c in low[::2])
        r2 = cb.sbc_build({"req": req, "formation": "4-4-2", "opts": {"club_list": club}, "prefer_owned": True})
        assert r2["solutions"][0]["valid"] and sum(r2["solutions"][0]["own"]) >= 9   # bronze/silver club cards recognised and used
        cb.STATE["low"] = []
        assert cb.sbc_needs_low(req) and not cb.sbc_needs_low({"quality": {"op": "min", "tier": "silver"}})
    finally:
        cb.STATE["low"], cb.STATE["by_slug"] = saved


def test_server_reads_favourites():
    o = {"favs": [{"s": "27-271446", "pos": "CM"}, {"s": "x", "pos": "nope"}, "junk"], "fav_w": "7"}
    assert cb.favs(o) == ({("27-271446", "CM")}, 7.0)
    assert cb.favs({})[1] == 10.0 and cb.favs({"fav_w": 999})[1] == 100.0
    v = cb.value_fn(dict(o, ps_prefs={}))
    assert v({"s": "27-271446", "ov": 84}, "CM") == 91 and v({"s": "27-271446", "ov": 84}, "ST") == 84


def test_best_manager_finds_nation_and_league():
    # 4 from nation 5 and 2 from league 9: the best manager is nation 5 + league 9 (4 + 2 chemistry)
    sq = squad_of(ni=[5] * 4 + list(range(20, 27)), li=[9, 9] + list(range(30, 39)), ck=[None] * 11)
    b = eng.best_manager(SLOTS, sq, {"ni": 1, "li": 0})
    assert (b["ni"], b["li"]) == (5, 9) and b["nation"] and b["league"] and b["total"] - b["current"] == 6
    same = eng.best_manager(SLOTS, sq, {"ni": 5, "li": 9})
    assert not same["nation"] and not same["league"] and same["total"] == same["current"]


def test_blacklist_single_card_keeps_other_versions():
    cb.load_cache()
    versions = [c for c in cb.STATE["cards"] if c["bp"] == 231747]   # Mbappé: several versions
    assert len(versions) > 1
    banned = versions[0]["s"]
    pool, _ = cb.build_pool({"blacklist_cards": [banned]})
    left = [c for c in pool if c["bp"] == 231747]
    assert banned not in {c["s"] for c in left} and len(left) == len(versions) - 1


def test_club_list_card_id_lines():
    cb.load_cache()
    pool, unmatched = cb.build_pool({"club_list": "27-50563395  Mbappé 91 (Destined for Glory)\n27-999999999  Nobody 99\n"})
    assert [c["s"] for c in pool] == ["27-50563395"] and unmatched == ["27-999999999  Nobody 99"]
    r = cb.club_ids(["50563395", "50563395", "999999999", "x"])
    assert [c["s"] for c in r["cards"]] == ["27-50563395"] and r["unknown"] == 1


def test_name_matching_prefers_word_starts():
    cb.load_cache()
    assert {c["n"] for c in cb.find_cards("Isco")} == {"Isco"}            # not Francisco Trincão
    assert any(c["n"].startswith("Vini") for c in cb.find_cards("Vini"))
    assert cb.search_cards("isco")["hits"][0]["n"] == "Isco"


def test_parse_line():
    assert cb.parse_line("1. ST Mbappe 91")["name"] == "Mbappe"
    p = cb.parse_line("Mbappe 91 ST")
    assert p["rating"] == 91 and p["pos"] == "ST"
    assert cb.parse_line("Kylian Mbappé\t91\t12,500")["rating"] == 91
    assert cb.parse_line("   ") is None


def test_import_preview_text():
    cb.load_cache()
    r = cb.preview_text("ST Mbappe 91\nGK Alisson\nnot a real playerzzz", ["GK", "ST"])
    assert r["rows"][0]["card"]["p"] == "GK" and r["rows"][1]["card"]["n"].startswith("Mbapp")
    assert r["unmatched"] == ["not a real playerzzz"]
    assert any(a["bp"] == r["rows"][1]["card"]["bp"] for a in r["rows"][1]["alts"])  # other Mbappé versions offered


def test_seat_puts_everyone_in_position():
    slots = ["GK", "ST", "CB", "LB"]
    entries = [(card(1, "ST"), None), (card(2, "LB", alts=("CB",)), None), (card(3, "CB"), None), (card(4, "GK"), None)]
    picks = cb.seat(entries, slots)
    assert [slots[j] for j in picks] == ["ST", "LB", "CB", "GK"]
    # asked-for position wins a tie between two valid slots
    picks = cb.seat([(card(1, "CB", alts=("LB",)), "LB"), (card(2, "CB", alts=("LB",)), None)], ["CB", "LB"])
    assert picks == [1, 0]


def test_formations_table():
    assert len(cb.FORMATIONS) == 29
    for f in cb.FORMATIONS.values():
        assert len(f["slots"]) == 11 and f["slots"][0] == "GK" and f["slots"].count("GK") == 1
        assert not {"LWB", "RWB", "CF"} & set(f["slots"])
    assert sorted(cb.FORMATIONS["4-2-1-3"]["slots"]) == sorted(["GK", "RB", "CB", "CB", "LB", "CDM", "CDM", "CAM", "RW", "ST", "LW"])


def test_fgg_squad_import():
    cb.load_cache()
    ids = {0: "212831", 9: "231747", 10: "37576"}  # Alisson GK, Mbappé ST, Ronaldo (ICON) ST in 4-4-2
    fake_resp = {"data": {"uuid": "x", "data": {"activeFormationId": "16", "managerNationId": 18, "managerLeagueId": 53,
                 "gameSlug": "27", "title": "Weekend League", "activeGroupPositions":
                 [{"group": "FIELD", "positionIdx": k, "playerEaId": int(v)} for k, v in ids.items()] +
                 [{"group": "SUBSTITUTE", "positionIdx": 0, "playerEaId": 1}]}}}
    real = cb.fetch_json
    calls = []
    cb.fetch_json = lambda url, tries=4: calls.append(url) or (fake_resp if "/squads/" in url else {"data": []})
    try:
        r = cb.preview_fgg("https://www.fut.gg/27/squad-builder/0a1b2c3d-1111-2222-3333-444455556666/")
    finally:
        cb.fetch_json = real
    assert calls[0] == "https://www.fut.gg/api/squads/0a1b2c3d-1111-2222-3333-444455556666/"
    assert r["formation"] == "4-4-2" and r["mgr"] == {"ni": 18, "li": 53} and r["title"] == "Weekend League"
    assert r["rows"][9]["card"]["s"] == "27-231747" and r["rows"][10]["card"]["s"] == "27-37576"
    assert r["rows"][1]["card"] is None  # empty slot stays empty
    # short / share links: opened, and the squad id taken from where they lead, the page, or the link itself
    U = "0a1b2c3d-1111-2222-3333-444455556666"
    real_open = cb.open_link
    pages = {"https://fut.gg/s/Ab12": (f"https://www.fut.gg/27/squad-builder/{U}/", ""),
             "https://www.fut.gg/s/Cd34": ("https://www.fut.gg/s/Cd34", f'<script>{{"squadUuid":"{U}"}}</script>'),
             "https://www.fut.gg/27/squad-builder/Xy9Z": ("https://www.fut.gg/27/squad-builder/Xy9Z", "<html></html>"),
             "https://www.fut.gg/s/none": ("https://www.fut.gg/s/none", "<html>nothing here</html>")}
    cb.open_link = lambda url, limit=0: pages[url]
    cb.fetch_json = lambda url, tries=4: calls.append(url) or (
        fake_resp if url.endswith((f"/squads/{U}/", "/squads/Xy9Z/")) else
        (_ for _ in ()).throw(RuntimeError("HTTP 404 Not Found")) if "/squads/" in url else {"data": []})
    try:
        for link in ("fut.gg/s/Ab12", "https://www.fut.gg/s/Cd34", "https://www.fut.gg/27/squad-builder/Xy9Z"):
            assert cb.preview_fgg(link)["formation"] == "4-4-2", link
        try:
            cb.preview_fgg("https://www.fut.gg/s/none")
            assert False
        except ValueError as e:
            assert "couldn't find a FUT.GG squad" in str(e)
        try:
            cb.preview_fgg("not a link")
            assert False
        except ValueError:
            pass
    finally:
        cb.fetch_json, cb.open_link = real, real_open


def test_ids_import_dedupes_and_seats():
    cb.load_cache()
    real = cb.fetch_json
    cb.fetch_json = lambda url, tries=4: {"data": []}  # unknown id: live lookup finds nothing
    try:
        r = cb.preview_ids(["231747", "231747", "37576", "999999999"], ["ST", "GK"])
    finally:
        cb.fetch_json = real
    assert [x["card"]["s"] for x in r["rows"]] == ["27-231747", "27-37576"]  # duplicate id placed once
    assert r["unmatched"] == ["card id 999999999"]


def test_whats_new_uses_release_notes():
    import os
    real, old = cb._github_json, os.environ.get("CLUBTOOLS_FAKE_VERSION")
    calls = []
    cb._github_json = lambda url: calls.append(url) or {"body": "New\n- thing"}
    cb.WHATSNEW.clear()
    try:
        os.environ["CLUBTOOLS_FAKE_VERSION"] = "1.7.3 · 2026-10-14 17:00 UTC (abc1234)"
        r = cb.whats_new()
        assert r["version"] == "1.7.3" and r["notes"] == "New\n- thing" and calls[0].endswith("/releases/tags/v1.7.3")
        cb.whats_new()
        assert len(calls) == 1   # cached
        os.environ["CLUBTOOLS_FAKE_VERSION"] = "2026-10-14 17:00 UTC (abc1234)"   # test build: no popup
        assert cb.whats_new()["version"] is None
    finally:
        cb._github_json = real
        cb.WHATSNEW.clear()
        if old is None:
            os.environ.pop("CLUBTOOLS_FAKE_VERSION", None)
        else:
            os.environ["CLUBTOOLS_FAKE_VERSION"] = old


def test_update_version_compare():
    assert cb.version_info("1.2.0 · 2026-10-11 11:20 UTC (abc1234)")[0] == (1, 2, 0)
    assert cb.version_info("2026-10-11 11:20 UTC (abc1234)")[0] is None
    assert cb.is_newer("v1.2.0", "2026-10-12T10:00:00Z", "1.1.9 · 2026-10-11 11:20 UTC (x)")
    assert not cb.is_newer("v1.2.0", "2026-10-12T10:00:00Z", "1.2.0 · 2026-10-12 09:50 UTC (x)")
    assert not cb.is_newer("v1.10.0", "2026-10-12T10:00:00Z", "1.10.1")
    assert cb.is_newer("v1.10.0", "2026-10-12T10:00:00Z", "1.9.9")       # numeric, not text, comparison
    assert cb.is_newer("v1.0.0", "2026-10-12T10:00:00Z", "2026-10-11 11:20 UTC (x)")       # test build, older
    assert not cb.is_newer("v1.0.0", "2026-10-11T11:25:00Z", "2026-10-11 11:20 UTC (x)")   # built alongside
    assert not cb.is_newer("v9.0.0", "2026-10-12T10:00:00Z", "dev")   # from the Python files: never


def test_update_check_reads_release(monkeypatch=None):
    rel = {"tag_name": "v9.9.9", "published_at": "2030-01-01T00:00:00Z", "html_url": "https://github.com/n3yung-debug/x",
           "body": "notes", "assets": [{"name": "ClubTools.exe", "browser_download_url": "https://github.com/a/b",
                                        "size": 3, "digest": "sha256:" + "0" * 64}]}
    old_json, old_ver = cb._github_json, cb.current_version
    try:
        cb._github_json, cb.current_version = (lambda url: rel), (lambda: "1.0.0")
        cb.check_update()
        assert cb.UPDATE["state"] == "available" and cb.UPDATE["latest"]["version"] == "9.9.9"
        assert cb.UPDATE["latest"]["asset"]["digest"].startswith("sha256:")
        rel["assets"] = []   # a release without the exe is never offered
        cb.check_update()
        assert cb.UPDATE["state"] == "current"
    finally:
        cb._github_json, cb.current_version = old_json, old_ver


def test_update_download_is_verified():
    import hashlib, io, tempfile
    data = b"new exe bytes"
    good = "sha256:" + hashlib.sha256(data).hexdigest()

    class Resp(io.BytesIO):
        def __init__(self, url): super().__init__(data); self.url = url
        def geturl(self): return self.url
        def __enter__(self): return self
        def __exit__(self, *a): self.close()
    real = cb.urllib.request.urlopen
    d = tempfile.mkdtemp()
    dest = os.path.join(d, "ClubTools.new.exe")
    try:
        cb.urllib.request.urlopen = lambda req, timeout=0: Resp("https://release-assets.githubusercontent.com/x")
        cb.download_verified("https://github.com/o/r/releases/download/v1/ClubTools.exe", good, dest)
        assert open(dest, "rb").read() == data
        for url, dg, why in [("https://github.com/x", "sha256:" + "1" * 64, "doesn't match"),
                             ("https://github.com/x", "", "no checksum"),
                             ("https://evil.example/x", good, "unexpected download address"),
                             ("http://github.com/x", good, "unexpected download address")]:
            try:
                cb.download_verified(url, dg, dest)
                raise AssertionError("accepted " + why)
            except RuntimeError as e:
                assert why in str(e), e
            assert not os.path.exists(dest)   # nothing half-downloaded or unverified is left behind
        cb.urllib.request.urlopen = lambda req, timeout=0: Resp("https://evil.example/x")   # redirected elsewhere
        try:
            cb.download_verified("https://github.com/x", good, dest)
            raise AssertionError("accepted a redirect to another host")
        except RuntimeError as e:
            assert "redirected" in str(e)
    finally:
        cb.urllib.request.urlopen = real


def test_update_swap_keeps_old_until_restart():
    import tempfile
    d = tempfile.mkdtemp()
    exe, new = os.path.join(d, "ClubTools.exe"), os.path.join(d, "ClubTools.new.exe")
    open(exe, "w").write("old"); open(new, "w").write("new")
    old = cb.swap_exe(exe, new)
    assert open(exe).read() == "new" and open(old).read() == "old" and not os.path.exists(new)


def test_support_link_only_known_donation_sites():
    old = cb.SUPPORT_URL
    try:
        for url, ok in [("https://ko-fi.com/clubtools", True), ("https://www.buymeacoffee.com/x", True),
                        ("https://github.com/sponsors/x", True), ("https://github.com/x/y", False),
                        ("http://ko-fi.com/x", False), ("https://evil.example/ko-fi.com", False), ("", False)]:
            cb.SUPPORT_URL = url
            assert (cb.support_url() == url and url != "") == ok, url
    finally:
        cb.SUPPORT_URL = old


def test_assets_only_bundled_files():
    assert cb.asset_file("/assets/flags/fr.svg") and cb.asset_file("/assets/fonts/inter-latin-wght-normal.woff2")
    for bad in ("/assets/flags/../../chem_builder.py", "/assets/flags/..%2fchem_builder.py", "/assets/x/fr.svg",
                "/assets/flags/FR.svg", "/assets/flags/fr.svg.py", "/assets/flags/nope.svg", "/assets/flags/"):
        assert cb.asset_file(bad) is None, bad
    import json
    names = json.load(open(cb.asset_file("/assets/flags/names.json"), encoding="utf-8"))
    with open(os.path.join(cb.HERE, "cards.json"), encoding="utf-8") as f:
        data = json.load(f)
    nations = {c["nn"] for c in (data["cards"] if isinstance(data, dict) else data) if c.get("nn")}
    assert len(nations) > 50
    assert all(n.lower() in names for n in nations), sorted(n for n in nations if n.lower() not in names)
    assert all(cb.asset_file(f"/assets/flags/{f}.svg") for f in set(names.values()))


def _opt_body(**opts):
    cb.load_cache()
    pool = [c for c in cb.STATE["cards"] if c["ov"] >= 80]
    pick = lambda pos, k: [c for c in pool if c["p"] == pos][k]  # noqa: E731
    squad = [cb.public(pick(p, 5 + 3 * i)) for i, p in enumerate(SLOTS)]
    for c in squad:
        c["_k"] = ""
    return {"slots": SLOTS, "squad": squad, "locks": [False] * 11, "mgr": None,
            "opts": dict({"max_drop": 4, "pairs": False, "max_steps": 3}, **opts)}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok  ", name)
    print("ALL PASSED")
