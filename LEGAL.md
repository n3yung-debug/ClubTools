# Selling ClubTools: legal checklist

Researched 11 Oct 2026 from the sources listed at the end. **This is not legal advice.** It's a map of the issues to take to a lawyer (ideally one who handles software and IP) and an accountant before charging money.

Status: 🔴 blocks a paid release · 🟡 needed to sell · 🟢 done in the code

---

## 🔴 1. Card data comes from FUT.GG, whose terms forbid this use
ClubTools gets its player and card data from FUT.GG's JSON API:
- the bundled `cards.json`
- "Update card data"
- live search in the player picker
- FUT.GG squad import

FUT.GG is run by **Stormstrike Inc.** Its terms (last updated 13 May 2026, Nevada law) prohibit:
- using "automated means to access, scrape, or copy data from our Services, except where expressly permitted";
- any attempt to "transfer, sell, sublicense, or otherwise commercially exploit our Services or their content".

FUT.GG's `robots.txt` also disallows `/api/*`.

**What it means:** selling a product built on that data breaks FUT.GG's terms, and they could block access or bring a claim. Even today, the public repo's `cards.json` and the free v1.0.0 release redistribute FUT.GG-derived data.

**Options:**
1. **Get written permission or a data licence from Stormstrike** (FUT.GG).
2. **License data from a provider that offers commercial terms.** FutDB / FUTDATABASE has paid API tiers, but its terms forbid "reproduction, distribution, or modification" without explicit permission, so you'd need a written commercial licence from them too.
3. Either way, the data is ultimately EA's (see 2).

Until this is settled, keep ClubTools free, or don't release it.

FUTBIN's terms also prohibit scraping without written permission. ClubTools only *links* to FUTBIN, and its import bookmarklet runs in the user's own browser on their own squad page. That's lower risk, but have it reviewed for a paid product.

## 🔴 2. EA's rules on commercial use of game content
EA's content policy says not to use its game content commercially. It names selling and putting content "behind paywalls like Patreon". It allows passive advertising, such as banner ads on fan sites. It also says fan projects must not imply EA endorsement.

Player ratings, card versions (TOTW, Icons, etc.), PlayStyles and chemistry rules are all EA game content. EA lists **FUTBIN, FUT.GG and FUTWIZ as its only official community partners** for EA account connections, which suggests a partner route exists.

**What it means:** a one-time-fee app built on FC card data is the kind of use the policy restricts.

**Options:**
1. Ask EA for permission or a partnership.
2. Monetise the way the policy allows: free app with passive ads or optional donations, no paywall.
3. Get a lawyer's opinion on whether ratings, as data, count as "game content" where you'll sell.

ClubTools uses no EA images, logos or card art (all visuals are its own), and it says it is independent. Keep it that way.

**Player names:** in the U.S., *C.B.C. Distribution v. MLB Advanced Media* (8th Cir. 2007; Supreme Court declined review in 2008) held that using player names and statistics in fantasy games was protected by the First Amendment. Other countries may differ. In the EU and UK, databases built with substantial investment can also be protected by a separate "database right", which is relevant to item 1.

## 🔴 3. The repo and the app are public and free right now
Anyone can download the source code and v1.0.0 from GitHub.

**Before selling:**
1. Make the repo **private**: GitHub → Settings → General → Danger Zone → Change visibility.
2. Move updates to a channel only buyers can use, such as the store's licensed download plus a licence-key check in the app.

The updater is built so only `UPDATE_REPO` / `UPDATE_API` in `chem_builder.py` needs to change. A licence-key check isn't built yet. The `LICENSE` file now makes clear the public code isn't licensed for reuse, but copies already downloaded can't be recalled.

---

## 🟡 4. Who sells it
Decide whether you sell as an individual or through a company (e.g. an LLC). That decision shapes liability, taxes and the name on the EULA. If you trade under the name "ClubTools" without a company, New York generally requires an assumed-name (DBA) filing; confirm with the NY Department of State or your county clerk. Then fill in the `[OWNER]` and `[support email]` placeholders in `LICENSE`, `EULA.md` and `PRIVACY.md`.

## 🟡 5. Sales tax and VAT
- **New York:** prewritten software is taxable even when downloaded (NY advisory opinion TSB-A-15(51)S).
- **EU:** a seller based outside the EU must charge EU VAT from the **first** sale to an EU consumer. The non-Union OSS registration covers this.
- **Simplest route:** sell through a **merchant of record** such as Lemon Squeezy or Paddle (about 5% + 50¢ per sale). They become the legal seller, calculate and remit sales tax and VAT, and Lemon Squeezy includes licence keys. One 2026 report says Lemon Squeezy is being folded into Stripe's own merchant-of-record product, so check its status when you choose.
- Income tax on profits still applies; ask an accountant.

## 🟡 6. Customer-facing terms
Drafts are written: `EULA.md` (licence, restrictions, no affiliation, data accuracy, warranty disclaimer, liability cap, governing law) and `PRIVACY.md`. Both are shown in the app under ⚙ → About & legal. To do:
- fill in the placeholders and have a lawyer review;
- align the refund policy with the store's terms;
- in the EU and UK, buyers of digital content have a 14-day right to withdraw. It's only lost if they expressly agree to immediate access and acknowledge losing it, which merchants of record usually handle in checkout.

## 🟡 7. The "ClubTools" name
A quick search found no software trademark called "ClubTools". A Brazilian hand-tool shop uses "Club Tools", and there are club-management software marks such as ClubConnect and ClubCount. Before you invest in the brand:
- run a proper search on USPTO (and EUIPO/UKIPO if you'll sell there);
- consider registering it (class 9: downloadable software).

## 🟡 8. Code signing (trust, not law)
The exe is unsigned, so Windows SmartScreen warns buyers. A code-signing certificate removes most warnings and is expected of paid software.

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
- **Licence notices generated on every build.** `tools/gen_notices.py` writes `THIRD_PARTY_NOTICES.txt` from the actual installed packages. The build **fails** if a shipped component has no licence text or a new package appears unclassified. The file is bundled in the exe, shown in the app and attached to each release, and the exe's self-test checks it's inside.
- **`LICENSE`:** proprietary, all rights reserved, with a trademark notice.
- **In-app ⚙ → About & legal:** the independent-product disclaimer, trademark credits (EA SPORTS FC™, Ultimate Team™), the data source, a privacy summary, the EULA, the privacy notice and third-party licences. The footer links to it too.
- **Wording:** the header badge now reads "for FC 27" (compatibility, not branding) and the window title is just "ClubTools". No EA logos or art anywhere.

## Not changed: your decisions
- Replacing the FUT.GG data source and removing the bundled data (item 1).
- Asking EA, or switching to an ads/donation model (item 2).
- Making the repo private, choosing a store, licence keys (items 3 and 5).

---

## Sources
- FUT.GG / Stormstrike Inc. terms (updated 13 May 2026): https://stormstrike.gg/terms (fut.gg/terms redirects here)
- FUT.GG robots.txt: https://www.fut.gg/robots.txt
- FUTBIN terms: https://www.futbin.com/tos
- FutDB terms: https://futdb.digitalsable.com/terms and pricing: https://futdb.app/
- EA content policy: https://help.ea.com/en/articles/security-and-rules/ea-content-policy/
- EA community partners (FUTBIN, FUT.GG, FUTWIZ): https://help.ea.com/en/articles/ea-sports-fc/community-api/
- C.B.C. v. MLB Advanced Media, 505 F.3d 818 (8th Cir. 2007): https://www.quimbee.com/cases/c-b-c-distribution-and-marketing-inc-v-major-league-baseball-advanced-media-l-p
- NY sales tax on downloaded software, TSB-A-15(51)S: https://www.tax.ny.gov/pdf/advisory_opinions/sales/a15_51s.pdf
- EU VAT for non-EU sellers (non-Union OSS): https://docs.stripe.com/tax/use-stripe-to-register/non-union-oss
- Merchant-of-record comparison (Lemon Squeezy / Paddle): https://alexcloudstar.com/blog/merchant-of-record-indie-saas-2026/
- PyInstaller licence (Bootloader Exception): COPYING.txt in the pyinstaller 6.22.3 wheel; https://pyinstaller.org/en/v3.2/license.html
- Microsoft WebView2 SDK licence: LICENSE.txt in the Microsoft.Web.WebView2 1.0.3856.49 NuGet package
- Package licences: METADATA of the exact wheels the build installs (pywebview 6.2.1, pythonnet 3.2.1, clr_loader 0.3.1, cffi 2.1.1, pycparser 3.11, bottle 0.13.4, proxy_tools 0.1.0, typing_extensions 4.16.0)
