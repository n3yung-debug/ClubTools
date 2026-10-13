# ClubTools: legal checklist (free, with ads and donations)

Researched 11 Oct 2026 from the sources listed at the end. **This is not legal advice.** It's a map of the issues to check with a lawyer (software and IP) and an accountant.

**Decision (11 Oct 2026):** ClubTools stays **free**. It is funded by **passive ads and voluntary donations** that unlock nothing. A paid version isn't viable without an EA partnership.

Status: 🔴 blocks ads · 🟡 to do · 🟢 done in the code

---

## 🔴 1. FUT.GG data: get written permission before showing ads
ClubTools gets its player and card data from FUT.GG's JSON API:
- the bundled `cards.json`
- "Update card data"
- live search in the player picker
- FUT.GG squad import

FUT.GG is run by **Stormstrike Inc.** Its terms (last updated 13 May 2026, Nevada law) prohibit:
- using "automated means to access, scrape, or copy data from our Services, except where expressly permitted";
- any attempt to "transfer, sell, sublicense, or otherwise commercially exploit our Services or their content".

FUT.GG's `robots.txt` also disallows `/api/*`.

Being free doesn't solve this:
- **Ad revenue** earned from a tool built on their data is "commercially exploiting" it.
- **The automated-access clause** applies even with no money involved.

**Next step:** ask Stormstrike for written permission (support@stormstrike.gg). A draft email is in `legal/fut-gg-permission-request.md`. Offer what such sites usually want: clear attribution ("Card data: FUT.GG", already shown), links to FUT.GG pages (already there, as the "fut.gg" link on every card), low request volume, and no redistribution of their price data.

**Until they say yes:** don't turn on ads.

**Alternatives if they say no:**
- **EA's own ratings site** (ea.com/games/ea-sports-fc/ratings) only covers base gold, silver and bronze cards at launch: no Icons, Heroes or promos. That would cut most of ClubTools' usefulness, and EA's own website terms would still need checking.
- **FutDB** sells API access, but its terms require explicit permission to redistribute.

## 🟢 2. EA's content policy: free with passive ads and donations fits
EA's content policy says not to use its game content commercially. It names selling and putting content "behind paywalls like Patreon". It **allows passive advertising**, giving as examples "the monetization of fan sites via passive banner ads" and video partner programmes. It also says fan projects must not imply EA endorsement. To stay inside it:
- **No paywall.** Every feature is free. Donations unlock nothing: no "supporter features", no early access, no ad-free tier for donors. ⚠️ An "ad-free for donors" perk would make donations a purchase, so avoid it.
- **Ads stay passive.** Banners only: no pop-ups, no interstitials that block the tool, no "watch an ad to use this feature".
- **Keep EA at arm's length.** No EA logos, card art or imagery (ClubTools uses none), and keep the "not affiliated" disclaimer visible (About & legal and the footer).
- ⚠️ EA's examples talk about fan *sites* and videos, not desktop apps. The cautious way to read it is to put ads on a **ClubTools website** (the download page) rather than inside the app. That's also what most ad networks support (item 3).

## 🟡 2b. Card prices (researched 13 Oct 2026)
There is no official EA price API. The options:
- **FUT.GG / FUTBIN / FUTWIZ:** their sites and apps show prices, but there's no public API. FUT.GG's terms (13 May 2026) forbid automated access and copying data "except where expressly permitted", so prices are added to the permission request in `legal/fut-gg-permission-request.md`.
- **EA's Web App transfer market:** reading it automatically means logging in with a player's EA account and automating it, against EA's terms, with a risk of account bans. Not an option.
- **FutDB (paid API):** sells player data including prices, updated every 30 minutes to 24 hours. Its FC 26 page listed €79 a month (20,000 requests a day); I couldn't confirm an FC 27 plan or price. Its terms forbid "reproduction, distribution, or modification without the explicit permission of the Provider", so ClubTools couldn't ship prices from one shared key without a deal. A "bring your own key" setting (each user pays FutDB) might work, but check with FutDB first.
- **In the app until then:** "Cheapest version of each player", "No promo cards", the max OVR caps, and a one-click version switcher.

## 🟡 3. Where the ads go
- **Google AdSense** is for websites. Its policies set out supported in-app web views (Android and iOS mobile only), and it bans showing ads "as a result of the actions of software applications such as toolbars". I found no policy that allows AdSense inside a desktop app, so **don't put AdSense in the app**.
- **Recommended: a ClubTools website** (download page, guides, changelog) with passive banner ads. This matches EA's own example ("fan sites via passive banner ads") and AdSense's normal use. The app links to it.
- **In-app ads**, if you want them later:
  - **Desktop ad networks:** AdsJumbo sells an SDK for Windows desktop apps, but it's built for .NET WinForms/WPF apps (ClubTools is not one), and its fill and pay claims are self-reported.
  - **A single, non-tracking "sponsor" banner** sold directly (e.g. to an FC content creator) is simpler and more privacy-friendly. I can build this slot when you want it.
- Before any ads go live, update `PRIVACY.md` to name the ad provider and what it collects. AdSense on a website also needs a cookie and consent notice for EU and UK visitors.

## 🟢 4. Donations: built in, needs your link
- **In the app:** a "♥ Support" button (header and About) appears once `SUPPORT_URL` in `chem_builder.py` is set. Only https links to Ko-fi, Buy Me a Coffee, PayPal.me or GitHub Sponsors are accepted.
- **The wording** says donations are voluntary and unlock nothing.
- **Recommended platform: Ko-fi.** Reported to take **no platform fee on donations** (payment processor fees still apply). Buy Me a Coffee takes 5%. GitHub Sponsors takes no fee on personal sponsorships but is aimed at open-source contributors.
- **Taxes:** donations and ad income are **taxable income** to you, not charitable gifts, so donors can't deduct them. Keep records and ask an accountant how to report them.

## 🟡 5. Public repo and licence
Free distribution means the public GitHub releases are fine as the download channel. The `LICENSE` stays proprietary freeware: anyone may use ClubTools free, but not resell or re-host it. That stops others from putting your app on their own ad-filled download sites. If you'd rather make it open source, that's a separate decision (MIT or GPL); tell me.

## 🟡 6. Terms and owner details
`EULA.md` (now a free licence, covering donations and ads) and `PRIVACY.md` are drafts, shown in the app under ⚙ → About & legal. Fill in the `[OWNER]` and `[support email]` placeholders and have a lawyer review them.

## 🟡 7. The "ClubTools" name
A quick search found no software trademark called "ClubTools". A Brazilian hand-tool shop uses "Club Tools", and there are club-management software marks such as ClubConnect and ClubCount. Run a proper USPTO search before investing in the brand (a website, social accounts).

## 🟡 8. Code signing (trust, not law)
The exe is unsigned, so Windows SmartScreen warns people. This matters more once strangers download it from your website.

---

## 🟢 Done in the code (this change)
- **Third-party licences checked.** Every component inside the exe allows commercial, closed-source distribution:
  - pywebview and pycparser (BSD-3-Clause)
  - pythonnet, clr_loader, bottle and proxy_tools (MIT)
  - cffi (MIT-0)
  - typing_extensions and the Python runtime (PSF)
  - the PyInstaller bootloader (GPL-2.0+ with the "Bootloader Exception", which explicitly allows commercial use)
  - pyinstaller-hooks-contrib runtime hooks
  - the Microsoft WebView2 SDK DLLs (BSD-style licence from Microsoft's NuGet package)
  - the Inter typeface (SIL Open Font License 1.1: bundling it in software is allowed; the font itself can't be sold on its own), the flag-icons nation flags (MIT) and the Lucide interface icons (ISC). Their licences are in `legal/` and in THIRD_PARTY_NOTICES.txt. The flags are plain national flags: no club badges or league logos, which are trademarks.
- **Licence notices generated on every build.** `tools/gen_notices.py` writes `THIRD_PARTY_NOTICES.txt` from the actual installed packages. The build **fails** if a shipped component has no licence text or a new package appears unclassified. The file is bundled in the exe, shown in the app and attached to each release, and the exe's self-test checks it's inside.
- **Bundle check after every build.** `tools/check_bundle.py` reads the list of modules PyInstaller actually packed. The build **fails** if any module comes from a package the notices don't cover, or if PyInstaller's own Python package is inside: only its bootloader is under the commercial-use exception, and the rest is plain GPL. This caught a real problem: the earlier exes (including the free v1.0.0) contained PyInstaller and setuptools modules because pywebview's build hook was swept in. They are now excluded. Builds from now on contain only Python, ClubTools, pywebview and its runtime dependencies.
- **`LICENSE`:** proprietary, all rights reserved, with a trademark notice.
- **In-app ⚙ → About & legal:** the independent-product disclaimer, trademark credits (EA SPORTS FC™, Ultimate Team™), the data source, a privacy summary, the EULA, the privacy notice and third-party licences. The footer links to it too.
- **Wording:** the header badge now reads "for FC 27" (compatibility, not branding) and the window title is just "ClubTools". No EA logos or art anywhere.

---

## Sources
- FUT.GG / Stormstrike Inc. terms (updated 13 May 2026): https://stormstrike.gg/terms (fut.gg/terms redirects here)
- FUT.GG robots.txt: https://www.fut.gg/robots.txt
- FUTBIN terms: https://www.futbin.com/tos
- FutDB terms: https://futdb.digitalsable.com/terms and pricing: https://futdb.app/
- EA content policy: https://help.ea.com/en/articles/security-and-rules/ea-content-policy/
- Google AdSense programme policies: https://support.google.com/adsense/answer/48182
- Desktop ad network example (AdsJumbo): https://adsjumbo.com/monetize-desktop-apps
- GitHub Sponsors fees: https://docs.github.com/en/sponsors/getting-started-with-github-sponsors/about-github-sponsors
- Ko-fi / Buy Me a Coffee fees (secondary sources): https://schoolmaker.com/blog/ko-fi-pricing and https://schoolmaker.com/blog/buy-me-a-coffee-pricing
- EA ratings site (base items only): https://www.ea.com/games/ea-sports-fc/ratings
- FutDB terms: https://futdb.digitalsable.com/terms ; FC 26 plan page (€79/month, prices every 30 min to 24 h): https://www.futdatabase.com/
- Stormstrike contact: support@stormstrike.gg (from https://stormstrike.gg/terms)
- EA community partners (FUTBIN, FUT.GG, FUTWIZ): https://help.ea.com/en/articles/ea-sports-fc/community-api/
- C.B.C. v. MLB Advanced Media, 505 F.3d 818 (8th Cir. 2007): https://www.quimbee.com/cases/c-b-c-distribution-and-marketing-inc-v-major-league-baseball-advanced-media-l-p
- PyInstaller licence (Bootloader Exception): COPYING.txt in the pyinstaller 6.22.3 wheel; https://pyinstaller.org/en/v3.2/license.html
- Microsoft WebView2 SDK licence: LICENSE.txt in the Microsoft.Web.WebView2 1.0.3856.49 NuGet package
- Inter (OFL-1.1), flag-icons (MIT), Lucide (ISC): LICENSE files in the npm packages @fontsource-variable/inter 5.3.0, flag-icons 7.5.0 and lucide-static 1.55.0
- Package licences: METADATA of the exact wheels the build installs (pywebview 6.2.1, pythonnet 3.2.1, clr_loader 0.3.1, cffi 2.1.1, pycparser 3.11, bottle 0.13.4, proxy_tools 0.1.0, typing_extensions 4.16.0)
