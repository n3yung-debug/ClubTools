# Chem Builder — EA FC 27

Local tool that shows how to raise squad chemistry, with lockable players.

## Run
**Desktop app (recommended):** run **ChemBuilder.exe**. It opens in its own window (no browser) and quits when you close the window.
- Get it from GitHub: the repo's **Actions** tab → latest "Build Windows app" run → **ChemBuilder-windows** artifact (a zip containing ChemBuilder.exe).
- It's not code-signed, so Windows SmartScreen may say "Windows protected your PC" the first time: click **More info → Run anyway**.
- It uses Microsoft Edge WebView2, which is built into Windows 10 and 11.
- Saved squads, blacklist, PlayStyle preferences and settings live in `%APPDATA%\ChemBuilder` (`state.json`), together with the card data and `chem_builder.log`.
- Coming from the browser version? Click **Bring over browser data** once in the app: it opens a page in your browser that copies what the browser had saved into the app.
- The FUTBIN bookmark and share links open in your browser; while the app is open they are handed straight to the app window.

**From the Python files:** double-click **start.bat** (needs Python 3.9+). With `pip install pywebview==6.2.1` it opens the same app window; without it, it opens in your browser and stops about 30 s after the tab closes. **start_console.bat** shows error messages. Command line: `python chem_builder.py --app` (window) or `python chem_builder.py` (browser).

## Use
- Pick a formation (all 29 FC 27 Ultimate Team formations, taken from FUT.GG's squad builder), or edit any slot's position dropdown.
- Click an empty slot to start **fill mode**: type a name, press Enter, and the picker moves to the next empty slot (↑↓ to choose, Esc to stop). Chemistry updates live as you add players.
- Drag a card onto another slot to swap them. **Undo / Redo** (Ctrl+Z / Ctrl+Y) cover every change.
- Changing formation re-seats your players into the best-fitting slots instead of dropping them.
- **Saved squads** keeps several squads in this browser. **Share link** copies a link that opens the squad in Chem Builder (the person opening it needs the app running).
- Enter your manager's nation and current league. The chemistry total is your squad exactly as it is; every suggestion also considers switching the league with a League Modifier and says which league to apply (the hint under the manager also offers it, with "Use it").
- **Import squad…** shows a preview (slot by slot, with a dropdown to pick a different version) before anything changes:
  - **FUT.GG link**: link your EA account on FUT.GG, load your squad in its Squad Builder, press Share, paste the link. Formation and manager come across too. (Reads FUT.GG's public squad endpoint; checked against FUT.GG's site code, Oct 2026.)
  - **FUTBIN**: drag the "→ Chem Builder" bookmark to your bookmarks bar, open your squad on FUTBIN, click it. FUTBIN blocks programs (Cloudflare), so the bookmark reads the card ids from the page in your own browser. PENDING VALIDATION: FUTBIN's squad page couldn't be loaded from the build machine; the bookmark was tested on a page using FUTBIN's card-image naming.
  - **Paste text**: one player per line, e.g. `ST Mbappe 91`.
- EA's FC Community API (the official club import used by FUTBIN, FUT.GG and FUTWIZ) is only open to those approved sites, so this tool goes through them and never logs in to EA.
- 🔒 locks a slot: it is never swapped, but still counts for everyone else's links.
- Results are ranked by chemistry gained, then the highest overall of the incoming card. A FUT.GG score is shown only when the feed provides one (it is empty for FC 27 so far) and is never used for ranking.
- "Find suggestions" opens a results view with a **Show** menu: the best step-by-step plan, manager change only (new manager nation, League Modifier, or both), and the best 1-, 2-, 3-, 4- and 5-player swaps (up to "Max swaps", 25 options each). Tick **include a new manager** to see swap combos that also switch to a manager of another nation (both versions are computed up front, so the toggle is instant). Every option has Apply (undoable).
- Two tabs: **⚗ Chemistry** (settings: how much lower-rated a swap may be, max swaps; button "Find chemistry upgrades"; results: plan, manager changes, 1-5 player swaps) and **▲ Rating upgrades** (settings: chemistry you'll give up, max OVR for all positions and per position; button "Find rating upgrades"; results: upgrade 1-5 players). A third tab, **✚ Fill squad**: place the players you want, leave the rest empty (click a player → **Remove player**), and "Fill empty slots" suggests up to 25 complete squads around them, ranked by chemistry then overall + PlayStyles; your players are never changed, and "Max OVR of a filler card" caps the suggestions. **Filters** below apply to all tabs, including **Don't suggest women at** (default GK and CB; they can still be suggested at their other positions, and you can still pick anyone yourself).
- **Best manager:** the hint under your manager, the Manager changes view and every Fill squad option show the nation + league that give the squad the most chemistry (with "Use it"). One search fills both tabs, so switching after a search is instant; the tab you used last is remembered, and a 33-chem squad opens on Rating upgrades. The top bar shows the app version.
- **Rating upgrades** (also in the Show menu): higher-rated cards for the same positions, 1 to 5 players, ranked by overall gained, keeping total chemistry within "chemistry you'll give up" (default 3) of what the squad has now. A squad already on 33 opens straight on these. "Max OVR of a suggested card" caps how highly rated an upgrade can be (a stand-in for price, since prices can't be read); "max OVR per position" overrides it per slot position. An upgrade must be rated higher than the current player, so a cap at or below a player's rating leaves that position without upgrades - the results say which positions and why.
- Swap lists only show combos where every swap is needed (undo any one and chemistry drops), and collapse different versions of the same players. 2+ swap lists come from a beam search, so they are very good but not guaranteed to be the absolute best; with a new manager they try up to 12 nations from your squad and the candidate cards. The whole search takes about 2 seconds and stops expanding after 8 seconds on very slow PCs.
- Every suggested card shows its face stats (PAC SHO PAS DRI DEF PHY, or the GK six) and a link to its exact FUT.GG page, where you can check the live price in your browser. The picker shows the same.
- Type the squad chemistry your game shows into "game shows" — the tool tells you if its rules agree.
- 🚫 next to any suggested card (or picker result) blacklists that player in every card version; the search re-runs without them. The list is saved in the browser under "Blacklisted players", where ✕ allows a player again. Players already in your squad are not touched.
- "Only use cards I own": paste card names (one per line, optional rating: `Alisson 87`) to restrict the pool.
  Without it, the search covers every card in the database (ICONs included — tick "exclude ICONs" if you don't have any).

## PlayStyles
- Suggested cards show their PlayStyles and PlayStyles+ (PS+ outlined); the ones you prefer for that position are starred ★.
- "Preferred PlayStyles" (results settings) sets what you want per position. Defaults: GK 1v1 Close Down (FC 27's name for Rush Out); CB, LB, RB and CDM Intercept; CM Technical; CAM, LW, RW, ST Low Driven Shot and Technical; LM/RM none. "Reset to defaults" restores these.
- Each wanted PlayStyle+ counts as +3 rating points and a plain one +1 (both adjustable). Chemistry still ranks first; among equal chemistry, the better card by overall + PlayStyles comes first. In rating upgrades, an equal-overall card that adds a wanted PlayStyle counts as an upgrade.
- PlayStyle ids/names come from FUT.GG's feed and site code (Oct 2026).

## Prices
- Prices can't be read automatically (FUT.GG and FUTBIN keep them behind a Cloudflare browser check), so there is no budget filter. Every suggested card links to its FUT.GG page, where the price is one click away.

## Rules implemented (checked 8 Oct 2026 against community guides; no EA primary source found)
- 0–3 chem per starter, max 33. Counts include the player. Club 2/4/7, league 3/5/8, nation 2/5/8; types add, capped at 3.
- Manager: counts exactly like one more player of its nation and league (managers have no club). Guides describe a flat "+1 if nation or league matches", but a real FC 27 squad checked on 8 Oct 2026 (25/33 in game) only adds up under the threshold rule; it is a test in test_engine.py. The league can be changed with a League Modifier item; the nation cannot.
- Must be in a preferred position (main + alternate) to earn chem or count for others.
- FC 27: ICON = full chem, +1 nation, +1 to every league. Hero / Hall of FUT = full chem, +1 league, +1 nation. None of them have a club link.
- Men's and women's players link through affiliated clubs, not leagues.

## Known limits
- FUT.GG's JSON feed is undocumented and could change; FUTBIN blocked automated access in testing, so it is not implemented.
- Price is not included (the feed had no usable prices). Formations come from FUT.GG's data and match FIFPlay's FC 27 list; not checked against EA's in-game screen directly.
- Evolved cards missing from the cache: use "also search FUT.GG live" in the picker, or add a custom card.
- The plan and the 2+ swap lists are heuristic searches (single swaps are exhaustive).
- `python test_engine.py` runs the rule tests.

## Troubleshooting "failed to fetch players"
1. Click **Test connection** in the app (or run `python chem_builder.py --check`). It checks cards.json, DNS, and the FUT.GG card feed, and names the cause (blocked/403, rate limited/429, certificate error from a firewall doing HTTPS inspection, DNS filter, timeout).
2. Normal searching never touches the internet: it reads cards.json next to chem_builder.py. Keep all files from the zip in one folder, and start the app with `python chem_builder.py` from that folder.
3. The feed is undocumented; a 404 means FUT.GG changed it and the sync code needs updating.
