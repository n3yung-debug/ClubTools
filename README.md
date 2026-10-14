# ClubTools — EA FC 27

> **ClubTools is free** (passive ads and voluntary donations, no paywall). Read [LEGAL.md](LEGAL.md) before turning on ads: card-data permission from FUT.GG comes first. ClubTools is proprietary ([LICENSE](LICENSE)); third-party licences are generated into THIRD_PARTY_NOTICES.txt at build time.

Free Windows app for EA SPORTS FC 27 Ultimate Team: chemistry swaps, rating upgrades and complete squads built around the players you choose.

## Download

**[⬇ Download ClubTools.exe](https://github.com/n3yung-debug/ClubTools/releases/latest/download/ClubTools.exe)** (latest version, Windows 10 and 11) · [Release notes](https://github.com/n3yung-debug/ClubTools/releases/latest) · [Website](https://n3yung-debug.github.io/ClubTools/)

1. Download **ClubTools.exe** and put it anywhere (Desktop, Documents…). It's one file, with no installer.
2. Double-click it. The first time, Windows SmartScreen may say *"Windows protected your PC"* because the app isn't code-signed: click **More info → Run anyway**.
3. That's it. ClubTools offers new versions itself (an update bar on start), so you don't need to download it again.

## Run
**Desktop app (recommended):** run **ClubTools.exe**. It opens in its own window (no browser) and quits when you close the window.
- Get it from the [Download](#download) link above (the latest release). Test builds of every change are also in the repo's **Actions** tab → "Build Windows app" → **ClubTools-windows** artifact (needs a GitHub login).
- It's not code-signed, so Windows SmartScreen may say "Windows protected your PC" the first time: click **More info → Run anyway**.
- It uses Microsoft Edge WebView2, which is built into Windows 10 and 11.
- ClubTools was previously called Chem Builder. On first start it copies everything from the old `%APPDATA%\ChemBuilder` folder, so squads and settings carry over.
- Saved squads, blacklist, PlayStyle preferences and settings live in `%APPDATA%\ClubTools` (`state.json`), together with the card data and `clubtools.log`.
- Coming from the browser version? Click **Bring over browser data** once in the app: it opens a page in your browser that copies what the browser had saved into the app.
- The FUTBIN bookmark and share links open in your browser; while the app is open they are handed straight to the app window.

**From the Python files:** double-click **start.bat** (needs Python 3.9+). With `pip install pywebview==6.2.1` it opens the same app window; without it, it opens in your browser and stops about 30 s after the tab closes. **start_console.bat** shows error messages. Command line: `python chem_builder.py --app` (window) or `python chem_builder.py` (browser).

## Website

The download page is `docs/index.html` (plain HTML, no trackers), served by GitHub Pages at https://n3yung-debug.github.io/ClubTools/. Its download buttons always point at the latest release, and it reads the current version number from GitHub. Screenshots are in `docs/img/`.

## Updates

**For users:** when ClubTools.exe starts it asks GitHub for the latest release of this repository. If there is a newer version, a bar under the header shows it with **What's new**, **Update now**, **Later** and **Skip this version**. Update now downloads the new ClubTools.exe, checks it against the SHA-256 checksum GitHub records for the release file (it refuses to install anything that doesn't match, or a release without a checksum), puts it in place of the running exe and restarts. Squads and settings are untouched (they live in `%APPDATA%\ClubTools`). ⚙ → **Check for updates** checks by hand; untick **Check for updates when ClubTools starts** to turn the automatic check off. If ClubTools.exe sits in a folder it can't write to (e.g. Program Files) the bar links to the release page instead.

**Publishing an update** (the GitHub workflow `Release ClubTools` does everything):
- Push a version tag: `git tag -a v1.2.0 -m "What's new text" && git push origin v1.2.0` (or ask Claude to "release 1.2.0"), or
- on GitHub: **Actions → Release ClubTools → Run workflow**, type the version (and optionally the notes). This button appears once the workflow file is on the default branch.

The workflow builds and self-tests the exe, publishes it as a pre-release (nobody is offered it yet), then runs an old copy of ClubTools on a Windows machine that updates itself to the new release and checks the installed file's checksum. Only when that passes does it become the latest release, which every ClubTools offers on its next start. Version numbers must go up (1.2.0 → 1.2.1 / 1.3.0); release notes default to the list of changes since the previous release. Builds from the normal "Build Windows app" workflow (test builds without a version number) are offered a release published after them.

## Use

**Cheaper suggestions** (Filters): there's no price data (see LEGAL.md), so two stand-ins keep suggestions affordable:
- **Cheapest version of each player** (on by default): suggestions use the lowest-rated version of each player, e.g. the 84 base Vicky López rather than her 90 Future Stars. A promo version still shows up where it adds a position or gives different chemistry.
- **No promo cards**: only base cards (gold, base ICONs and Heroes).
- **No ICONs**: never suggest any ICON.
- **Skip ICONs rated over 90** (ticked by default): ICONs rated 90 and below can still be suggested; the ones above usually cost millions or are hardly on the market. Untick it to allow every ICON. Favourites are always allowed. To drop one card that's never on the market, blacklist it once.
- **SBC helper** (SBC tab): enter the requirements (leagues / nations / clubs in squad, max from the same league / nation / club, player quality (min / max / exactly Bronze, Silver or Gold), team rating, chemistry, rare and special cards, "min N from a league / nation / club", with "X or Y" choices such as "RB Leipzig or Frankfurt", and "min N Bronze / Silver / Gold players") or pick a preset (League & Nation Advanced). It uses as many of your own cards as it can (Filters → Only use cards I own, filled by the FUTBIN / FUT.GG club import; any card you own counts as cheaper than any card you'd buy, your lowest-rated first), then fills the rest with the lowest-rated cards that work, trying several formations. Your ICONs, Heroes and promo cards are kept out by default. Your current squad and favourites are left out by default. SBC chemistry counts no manager. Every option shows a ✓/✗ checklist, which cards are yours and which to buy (with FUTBIN links), and "Show on pitch". The main card data is gold (75+); for bronze / silver SBCs, use **Download bronze & silver cards** in the SBC tab (one time, about 17,000 cards, several minutes; kept in a separate file and only used by the SBC helper and the club import).
- **Squad rating** of the starting XI next to chemistry (the SBC way; community formula, since EA doesn't publish one; the in-game club screen also counts subs). Every suggestion shows the rating it leads to.
- **Player overview**: click a card in your squad for its stats, PlayStyles, chemistry, and FUTBIN / FUT.GG buttons.
- **Live progress** under the search button, and **Report this** on any search or import error (opens Send feedback with the error filled in).
- **Manager in every search**: the League Modifier is always free, and every search (step-by-step plan, swaps, upgrades, fill) also tries the most promising other manager nations. A result that needs a new manager card says so ("Manager from France (new manager card)") and Apply switches it. At equal chemistry your current manager wins.
- **Lock hint**: when your locks stop the chemistry plan from going further, the results name the locked players to free (e.g. "unlocking Dumornay (ST) would allow 33/33") with an Unlock and search again button.
- **Version switcher**: click a card in your squad and the picker shows every version of that player; one click switches (Undo is offered, and a favourite moves with the card).

**Favourites** (section above Blacklist): cards you'd rather play at a position even over higher-rated ones, e.g. the 84 Vicky López at CAM. Add them with the heart on a pitch card, a search result or a suggestion. Chemistry still comes first; among options with the same chemistry, **Always** picks the favourite, **Boost** counts it as N rating points higher. Required stats and the women filter don't apply to a favourite at its position; position blocks and the blacklist still do. A favourite already in your squad isn't locked: lock it if chemistry swaps shouldn't touch it.

New in 1.3 (new look):
- **Cards coloured by type**: gold, silver, bronze, TOTW, Icon, Hero, Hall of FUT, Evolution, and a fixed colour plus short label for each promo (FS, OTW, POTM…). Nation flags, full names that shrink to fit.
- **Quieter pitch**: the position picker and lock show when you point at a card; a locked slot always shows its lock.
- **Tidier panel**: mode tabs on top, chemistry ring next to the manager, the main button stays at the bottom of the screen, and the in-game total check is behind a link.
- Icons instead of emoji, the Inter font built in, light animations (off when Windows is set to reduce motion). The share image uses the new card colours and flags.

New in 1.2 (quality of life):
- **Presets** (bar above Filters): save required stats, filters, PlayStyle preferences and tab settings under a name and switch with one click (Undo after switching). Blacklist, position blocks and your club list stay global.
- **Player picker**:
  - **Browse** finds cards by nation / league / club / position / rating, sorted by rating, any face stat, weak foot, skill moves or height.
  - **⇄ Compare** opens the final-check screen against the player in that slot.
  - Results already in your squad are tagged, and a player placed twice shows **DUP** on the pitch.
- **✎ Evolve…** (picker on a filled slot): enter your evolved card's rating, positions, face stats, WF/SM and PlayStyles(+). It's used everywhere, kept under "My evolved cards", offered first in name searches (EVO tag) and carried in share links.
- **🖼 Share as image** (Squads menu): a picture of the squad with chemistry, formation and manager. Copy it, or save it as a PNG in Downloads.
- A reminder when card data is 7+ days old (new TOTW/promo cards). **?** shows keyboard shortcuts; ⚙ → "Show the quick tips again".
- The app remembers which sections were open, and has **Undo** after Clear all, preset changes and blacklist removals.
- Pick a formation (all 29 FC 27 Ultimate Team formations, taken from FUT.GG's squad builder), or edit any slot's position dropdown.
- Click an empty slot to start **fill mode**: type a name, press Enter, and the picker moves to the next empty slot (↑↓ to choose, Esc to stop). Chemistry updates live as you add players.
- Drag a card onto another slot to swap them. **Undo / Redo** (Ctrl+Z / Ctrl+Y) cover every change.
- Changing formation re-seats your players into the best-fitting slots instead of dropping them.
- **Saved squads** keeps several squads in this browser. **Share link** copies a link that opens the squad in ClubTools (the person opening it needs the app running).
- Enter your manager's nation and current league. The chemistry total is your squad exactly as it is; every suggestion also considers switching the league with a League Modifier and says which league to apply (the hint under the manager also offers it, with "Use it").
- **Import squad…** shows a preview (slot by slot, with a dropdown to pick a different version) before anything changes:
  - **FUT.GG link**: link your EA account on FUT.GG, load your squad in its Squad Builder, press Share, paste the link. Formation and manager come across too. (Reads FUT.GG's public squad endpoint; checked against FUT.GG's site code, Oct 2026.)
  - **FUTBIN**: drag the "→ ClubTools" bookmark to your bookmarks bar, open your squad on FUTBIN, click it. FUTBIN blocks programs (Cloudflare), so the bookmark reads the card ids from the page in your own browser. PENDING VALIDATION: FUTBIN's squad page couldn't be loaded from the build machine; the bookmark was tested on a page using FUTBIN's card-image naming.
  - **Your club from FUT.GG** (Import squad → **FUT.GG club**, or "Import my club from FUT.GG" in Filters / the SBC tab): on fut.gg sign in, open **GG Club**, link and sync your EA club, make sure the club isn't private, then paste your club page's address (`https://club.fut.gg/yourname` or `https://www.fut.gg/gg-club/yourname/players/`, or just the name). ClubTools reads the club's public player list (30 per page, paced) and asks **Add** or **Replace**. Evolved players are left out (add them with the evolution editor). A club link pasted in the FUT.GG squad-link box is imported the same way. Squad links can be long or short; short ones are opened to find the squad, and the error says what failed.
  - **SBC mode pitch**: switching to the SBC tab sets your squad aside and gives SBC its own pitch (empty at first). Players you place there stay while the helper builds around them; your squad comes back when you switch to another mode.
  - **Your club**: the same bookmark on a FUTBIN or FUT.GG *club* page asks what to do with the cards: **Add to my club** (fills Filters → "Only use cards I own", one line per exact card; club pages are paged, so click it on each page and they add up), **Replace my club list**, or import as a squad. Cards under 75 are recognised once the bronze & silver cards are downloaded (SBC tab); until then they're counted and skipped. PENDING VALIDATION on real club pages (they need a login, so they couldn't be opened from the build machine); tested on a page using FUTBIN's card-image names and FUT.GG's card links.
  - **Paste text**: one player per line, e.g. `ST Mbappe 91`.
- EA's FC Community API (the official club import used by FUTBIN, FUT.GG and FUTWIZ) is only open to those approved sites, so this tool goes through them and never logs in to EA.
- 🔒 locks a slot: it is never swapped, but still counts for everyone else's links.
- Results are ranked by chemistry gained, then the highest overall of the incoming card. A FUT.GG score is shown only when the feed provides one (it is empty for FC 27 so far) and is never used for ranking.
- "Find suggestions" opens a results view with a **Show** menu: the best step-by-step plan, manager change only (new manager nation, League Modifier, or both), and the best 1-, 2-, 3-, 4- and 5-player swaps (up to "Max swaps", 25 options each). Tick **include a new manager** to see swap combos that also switch to a manager of another nation (both versions are computed up front, so the toggle is instant). Every option has Apply (undoable).
- Two tabs: **⚗ Chemistry** (settings: how much lower-rated a swap may be, max swaps; button "Find chemistry upgrades"; results: plan, manager changes, 1-5 player swaps) and **▲ Rating upgrades** (settings: chemistry you'll give up, max OVR for all positions and per position; button "Find rating upgrades"; results: upgrade 1-5 players). A third tab, **✚ Fill squad**: place the players you want, leave the rest empty (click a player → **Remove player**), and "Fill empty slots" suggests up to 25 complete squads around them, ranked by chemistry then overall + PlayStyles; your players are never changed, and "Max OVR of a filler card" caps the suggestions. **Filters** below apply to all tabs, including **Don't suggest women at** (default GK and CB; they can still be suggested at their other positions, and you can still pick anyone yourself).
- **Final check before applying:** every Apply that changes players (plan, swaps, rating upgrades, Fill squad) first shows a comparison: each outgoing and incoming card side by side with overall, position, nation/league/club, face stats with differences, PlayStyles (preferred ones starred), each player's chemistry before/after, the squad total before/after and any manager or League Modifier change. Confirm applies it (undoable); Cancel leaves the squad as it is.
- **Best manager:** the hint under your manager, the Manager changes view and every Fill squad option show the nation + league that give the squad the most chemistry (with "Use it"). One search fills both tabs, so switching after a search is instant; the tab you used last is remembered, and a 33-chem squad opens on Rating upgrades. The top bar shows the app version.
- **Rating upgrades** (also in the Show menu): higher-rated cards for the same positions, 1 to 5 players, ranked by overall gained, keeping total chemistry within "chemistry you'll give up" (default 3) of what the squad has now. A squad already on 33 opens straight on these. "Max OVR of a suggested card" caps how highly rated an upgrade can be (a stand-in for price, since prices can't be read); "max OVR per position" overrides it per slot position. An upgrade must be rated higher than the current player, so a cap at or below a player's rating leaves that position without upgrades - the results say which positions and why.
- Swap lists only show combos where every swap is needed (undo any one and chemistry drops), and collapse different versions of the same players. 2+ swap lists come from a beam search, so they are very good but not guaranteed to be the absolute best; with a new manager they try up to 12 nations from your squad and the candidate cards. The whole search takes about 2 seconds and stops expanding after 8 seconds on very slow PCs.
- Every suggested card shows its face stats (PAC SHO PAS DRI DEF PHY, or the GK six) and a link to its exact FUT.GG page, where you can check the live price in your browser. The picker shows the same.
- Type the squad chemistry your game shows into "game shows" — the tool tells you if its rules agree.
- 🚫 next to any suggested card (or picker result) blacklists that exact card only, so cheaper versions of the same player can still be suggested; the search re-runs without it. "Blacklisted cards" lists them (rating and version) with ✕ to allow one again. Entries made before this change block every version of the player and are labelled "all versions". Players already in your squad are not touched.
- **Required stats** (its own section under the tabs): one row per position (your formation's; tick "Show all positions" for the rest), on two tabs: **Stars & body** (weak foot, skill moves, preferred foot, minimum height, AcceleRATE) and **Face stats** (minimum PAC/SHO/PAS/DRI/DEF/PHY). Example: 5★ SM at CM/CAM/ST, a left-footed LB, CBs 188 cm+ with 80+ pace.
  - **Require** only suggests cards that meet them. **Prefer** still suggests everyone but ranks cards that meet them higher (each stat met is worth N rating points, default 3), which avoids empty results.
  - The green number next to a position is how many cards still qualify there (amber under 10, red at 0), updated as you type.
  - **⧉** copies a row (both tabs) to other positions: tick them, or pick Attack / Midfield / Defence / All, then "Copy to N positions"; Esc cancels. The **All** row fills every shown position. **Clear all** resets.
  - Keepers don't take face-stat minimums. Chemistry swaps, rating upgrades and Fill squad use the requirement of the slot a card would play; players already in your squad are not touched. Cards show weak foot, skill moves, foot, height and AcceleRATE, in gold when they meet a requirement.
  - Needs card data synced after 12 Oct 2026 (⚙ → Update card data); older settings are converted automatically.
- **Block a player at one position**: "not at CAM" (etc.) next to a suggestion or picker result means that player, every version, is never suggested at that position again, while their other positions stay open (e.g. Bellingham not at CAM, still suggested at CM). The Blacklist section lists these blocks with ✕ to remove one, and lets you add one by name + position. Applies to chemistry swaps, rating upgrades and Fill squad; players already in your squad are not moved.
- "Only use cards I own": paste card names (one per line, optional rating: `Alisson 87`) to restrict the pool.
  Without it, the search covers every card in the database (ICONs included — tick "exclude ICONs" if you don't have any).

## PlayStyles
- Suggested cards show their PlayStyles and PlayStyles+ (PS+ outlined); the ones you prefer for that position are starred ★.
- "Preferred PlayStyles" (results settings) sets what you want per position. Defaults: GK 1v1 Close Down (FC 27's name for Rush Out); CB, LB, RB and CDM Intercept; CM Technical; CAM, LW, RW, ST Low Driven Shot and Technical; LM/RM none. "Reset to defaults" restores these.
- Each wanted PlayStyle+ counts as +3 rating points and a plain one +1 (both adjustable). Chemistry still ranks first; among equal chemistry, the better card by overall + PlayStyles comes first. In rating upgrades, an equal-overall card that adds a wanted PlayStyle counts as an upgrade.
- PlayStyle ids/names come from FUT.GG's feed and site code (Oct 2026).

## Prices
- Prices can't be read automatically (FUT.GG and FUTBIN keep them behind a Cloudflare browser check), so there is no budget filter. Every suggested card has a **FUTBIN ↗** link: it opens FUTBIN's search for that player's name (FUTBIN uses its own player ids, which aren't available to programs), listing every version so you can pick the one with the right rating and see its price. A small **fut.gg** link next to it opens the exact card on FUT.GG.

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
