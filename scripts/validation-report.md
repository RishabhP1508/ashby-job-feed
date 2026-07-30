# Ashby board validation report

Generated 2026-07-30T22:34:24Z. Run was clean.

## Headline

- **shipped**: 308 companies in `frontend/src/data/companies.json`
- **found**: 347 (shipped plus withheld plus Ashby-seen-but-unresolved)

`found` is the measure of pipeline health. The acceptance gate withholds real
boards on purpose, so a gap between found and shipped means corroboration is
failing, not that the pipeline is broken. Those need opposite fixes.

## Counts

- probed companies: 816
- confirmed boards still live: 21 of 23
- found by exact-name slug: 264
- found by derived slug, named tier (ungated): 2
- found by derived slug, cross-confirmed: 8
- found by careers-page scrape: 13
- shipped by manual override: 0
- withheld, derived slug unconfirmed: 23
- Ashby confirmed, slug unresolved: 16
- not found: 467
- confirmed slug now dead: 2
- error, unresolved: 0
- shipped with 0 open roles: 36
- rejected by override: 0

Timing: pass 1 0s, pass 2 306s

## Verify by eye

Every acceptance carrying residual risk, sorted by ascending job count so the
emptiest and most suspicious boards come first. A 200 proves a board exists, not
that it belongs to this company: Ashby slugs are first-come and the API exposes no
company name, so job titles are the cheapest available signal. A gaming company
with nursing roles means the wrong board was grabbed.

- **Catalyst** -> `catalyst` (0 roles)
  - no open roles
- **Chronosphere** -> `chronospherejobs` (0 roles) [found on chronosphere.io]
  - no open roles
- **Fathom** -> `fathom` (0 roles)
  - no open roles
- **Fellow** -> `fellow` (0 roles)
  - no open roles
- **Figure** -> `figure` (0 roles)
  - no open roles
- **Heirloom** -> `heirloomcarbon` (0 roles) [heirloomcarbon.com references heirloomcarbon]
  - no open roles
- **Hex** -> `hex` (0 roles)
  - no open roles
- **Loom** -> `loom` (0 roles)
  - no open roles
- **MagicSchool AI** -> `magicschool` (0 roles) [magicschool.ai references magicschool]
  - no open roles
- **Mercury** -> `mercury` (0 roles)
  - no open roles
- **Vast** -> `vast` (0 roles)
  - no open roles
- **Ghost** -> `ghost` (1 roles)
  - Founding Engineer (Technical Staff)
- **ReadMe** -> `readme` (1 roles)
  - Enterprise Support Engineer (Customer Experience)
- **Depot** -> `depot` (2 roles)
  - Staff Software Engineer (Engineering); Head of Developer Growth Marketing (Marketing)
- **Levels** -> `levels` (2 roles)
  - Software Engineer (UK - Non London) (Levels Technologies Ltd); Mid Full Stack / Backend Engineer (Levels Technologies Ltd)
- **Maven** -> `maven` (2 roles)
  - Senior/Staff Software Engineer (Engineering); Principal Designer (Product)
- **Tango** -> `tango` (2 roles)
  - Keep me in mind! (Engineering); Senior Product Manager (Product)
- **Zed** -> `zed` (2 roles)
  - Open Source Engineer (Engineering); Designer (Engineering)
- **Cedar** -> `cedar` (3 roles)
  - Cedar Home Advisor (Sales & Marketing); Head of Transaction Support and Admin (Legal and Compliance); Mid Level Front End Engineer (Product and Technology)
- **Knock** -> `knock` (3 roles)
  - Engineering Manager, Platform (Engineering); DevOps Engineer (Engineering); Infrastructure Engineer (Engineering)
- **Runway** -> `runway` (4 roles)
  - ⚙️ Senior/Staff Platform Engineer (EPD); ⚙️ Senior/Staff Product Engineer (EPD); 📈 Forward Deployed Finance Partner (Go-To-Market)
- **Jack & Jill** -> `jack-jill-external-ats` (5 roles) [found on jackandjill.ai]
  - Founding Engineer (£240k+ ) (Engineering); Founding Designer (£180k+) (Engineering); Founding GTM Operator (£150k+) (GTM)
- **Regard** -> `regard` (5 roles)
  - VP of Engineering (Engineering); Full Stack Software Engineer (Engineering); Data Engineer (Engineering)
- **Twelve** -> `twelve` (5 roles)
  - Future Opportunities at Twelve (Twelve); EH&S Lead (Environmental Health & Safety); Plant Operations Manager (Jet Fuel Plant) (Plant Development)
- **Unify** -> `unify` (5 roles)
  - Senior Software Engineer, Product (Engineering); Staff Software Engineer, Platform (Engineering); Staff Software Engineer, Product (Engineering)
- **Arcade** -> `arcade` (6 roles)
  - Arcade Talent Network (Engineering); Senior Applied AI Engineer (Engineering); Senior Machine Learning Engineer (Engineering)
- **Guild** -> `guild` (6 roles)
  - Brand & Marketing Designer (Design); Engineer, Production Engineering (Engineering); Demand Generation Lead (Marketing & Comms)
- **Kit** -> `kit` (6 roles)
  - Lead Growth Marketing Manager, Acquisition (Growth); Lead Growth Marketing Manager (Growth); Brand Project Manager - Contractor (Growth)
- **Unit** -> `unit` (6 roles)
  - Senior Backend Engineer (Engineering); GTM Lead (Bay Area) (Go To Market); Senior Distributed Systems Engineer (Engineering)
- **LILT** -> `lilt-corporate` (7 roles) [found on lilt.com]
  - Account Development Representative (ADR) (Sales); Forward Deployed Engineer (Engineering); Enterprise Account Executive (Sales)
- **Mosaic** -> `mosaic` (7 roles)
  - Global Head of Sales (Go-To-Market); Head of EMEA Sales (Go-To-Market); Software Engineer (Engineering)
- **Rime** -> `rime` (7 roles)
  - Machine Learning Scientist (Modeling); Founding Account Executive (Revenue); Forward Deployed Engineer (Revenue)
- **Sweep** -> `sweep` (7 roles)
  - Sales Development Representative (Sales); Strategic Account Executive (Sales); Senior Back-End Developer (R&D)
- **Convex** -> `convex-dev` (8 roles) [found on convex.dev]
  - Software Engineer, Infra/Systems (Engineering); Software Engineer, API Platform (Engineering); Software Engineer, Product (Engineering)
- **Railway** -> `railway` (8 roles)
  - Senior Full-Stack Engineer - Product (Product); Infrastructure Engineer (Platform); Developer Relations (Product)
- **Blackbird** -> `blackbird-labs-inc` (9 roles) [found on blackbird.xyz]
  - Senior/Staff Backend Engineer (Engineering); Partnerships Strategy & Ops Associate - New York, NY (Loyalty); Senior/Staff Fullstack Engineer (Engineering)
- **Captions** -> `mirage` (9 roles) [found on captions.ai]
  - Software Engineer, Web Product (Engineering); Lifecycle Marketing Lead (Marketing); Technical Recruiter (Operations)
- **Sift** -> `sift` (9 roles)
  - Forward Deployed Engineer, Trust and Safety (Customer Experience); Product & Customer Learning Manager (Customer Experience); Machine Learning Engineer (Engineering)
- **Artisan** -> `artisan` (10 roles)
  - Growth (Marketing); Build Your Own Role (Build Your Own Role); Applied AI (Engineering)
- **Pika** -> `pika` (10 roles)
  - Research Scientist, Foundation Model (Research); Software Engineer, AI Infra (Engineering); ML Engineer, Inference & Optimization (Research)
- **Resend** -> `resend` (10 roles)
  - Product Engineer (Engineering); Product Engineer (Engineering); Security Engineer, Platform (Engineering)
- **Bland AI** -> `bland` (13 roles) [bland.ai references bland]
  - Senior Infrastructure Engineer (Engineering); Partner Success Manager (Post Sales); Technical Account Manager (Post Sales)
- **Character AI** -> `character` (13 roles) [character.ai references character]
  - Machine Learning Infrastructure Engineer (Technical Staff - ML); Research Engineer, Post-Training (All Industry Levels) (Technical Staff - ML); Software Engineer, Core Product (Technical Staff - Engineering)
- **ConductorOne** -> `C1` (13 roles) [found on conductorone.com]
  - Sales Development Representative (Sales); Sr. Solutions Engineer (Sales); Enterprise Account Executive (East) (Sales)
- **Town** -> `town` (13 roles)
  - Staff Backend Engineer (EPD); AI Product Engineer (EPD); Product Designer (EPD)
- **Sent** -> `sent` (15 roles)
  - Create Your Own (Other); VP of Finance (Operations); Growth Advisor (Sales and GTM)
- **Opal** -> `opal` (16 roles)
  - Software Engineer (Engineering); Forward Deployed Engineer (Engineering); Enterprise Account Executive - West Coast (Sales)
- **Second Front** -> `Second-Front-Systems` (16 roles) [found on secondfront.com]
  - Engineering Manager (Engineering Leadership); Director, Demand Generation (Growth); Senior Solutions Architect (Mission Success)
- **Coder** -> `coder` (18 roles)
  - Technical Enablement Manager (Revenue); Software Engineer (AI Governance) (Research & Development); Forward Deployed Engineering Manager (Revenue)
- **Warp** -> `warp` (19 roles)
  - Sales Development Representative (Sales); Account Executive (Sales); Software Engineer, Product (Engineering)
- **Kin** -> `kin` (20 roles)
  - Staff Software Engineer, Front-End Focus (Engineering); Senior Software Engineer, Back-End Focus (Engineering); Insurance Sales Representative (Brokerage, Base Salary + Monthly Incentives) (Sales)
- **Dust** -> `dust` (21 roles)
  - Account Executive (Sales); Software Engineer (Product); Software Engineer, Frontend (Product)
- **Omni** -> `omni` (21 roles)
  - Product Engineer (Engineering); Software Engineer, Growth Data Platform (Growth Engineering); Managing Architect - EMEA (French Speaking) (Solutions Architecture)
- **Oyster** -> `oyster` (21 roles)
  - Senior Deal Strategy & Operations Specialist (Go To Market); Customer Success Manager (EMEA) (Go To Market); Oyster Talent Community Sign Up (People)
- **Front** -> `frontcareers` (22 roles) [front.com pointed at frontcareers, not frontapp]
  - AI Engineer - GTM / Operations (Contract) (G&A); Senior Software Engineer - Front End Architecture / React Native (EPD); Senior Software Engineer - Front End Architecture / React Native (EPD)
- **Nightfall** -> `nightfall-ai` (22 roles) [found on nightfall.ai]
  - Senior Backend Software Engineer (R&D); Endpoint Engineer - Mac OS (R&D); Data Loss Prevention (DLP) Analyst (R&D)
- **Tonal** -> `tonal` (22 roles)
  - Showroom Sales Supervisor (full-time) (Revenue); Supply Chain Operations Program Manager (Operations); Showroom Sales Supervisor (Part Time) (Revenue)
- **Column** -> `column` (23 roles)
  - I don't fit into any of these roles! (Other); Software Engineer (Product & Engineering); Growth (Go-to-Market)
- **Radiant** -> `radiant` (23 roles)
  - Senior Talent Partner (Talent & People); Senior Network Engineer (Infrastructure Operations); Senior Manager, Field & Experiential Marketing (Marketing)
- **Socket** -> `socket` (24 roles)
  - Customer Success Manager, SMB (Go-to-Market); Enterprise Account Executive (Go-to-Market); Sr. Software Engineer (Engineering)
- **Teleport** -> `goteleport` (24 roles) [goteleport.com references goteleport]
  - Senior Account Development Representative- Enterprise (Revenue); Senior Field Engineer (Revenue); Senior Product Designer (Product)
- **Hebbia** -> `hebbia-ai` (26 roles) [found on hebbia.ai]
  - Technical Delivery (Post-Sales); Forward Deployed Banker (AI Strategist) (AI Strategy); Forward Deployed Investor (AI Strategist) (AI Strategy)
- **Sana Labs** -> `sana-roles` (31 roles) [found on sanalabs.com]
  - GTM Associate (Go-To-Market); GTM Manager (Account Executive) (Go-To-Market); Design Engineer (Engineering)
- **Render** -> `render` (34 roles)
  - Engineering Manager, Product (Engineering); Open Application (All Teams); Account Executive (Sales)
- **Scribe** -> `scribe` (35 roles)
  - Customer Success Manager, Mid-Market (Customer Success); Customer Success Manager, Enterprise (Customer Success); Business Development Representative (Sales)
- **Rho** -> `rho` (38 roles)
  - Accelerator Partnerships Lead (GTM); Founding Account Executive, Los Angeles (GTM); Senior Product Designer (Product)
- **Speak** -> `speak` (41 roles)
  - Product Designer, Enterprise (Design); AI Product Engineer (Engineering); Machine Learning Engineer, Voice (Engineering)
- **Owner** -> `owner` (49 roles)
  - Applied AI Lead (G&A); Senior Software Engineer, Backend (Engineering, Product, and Design); Senior Associate, Product Analytics & Applied AI (G&A)
- **Writer** -> `writer` (55 roles)
  - Software engineer, generative AI (Engineering, product & design); Security engineer, detection and response (Engineering, product & design); Software engineer, generative AI (UK) (Engineering, product & design)
- **Range** -> `range` (56 roles)
  - Software Engineer (Engineering); Financial Planner (Financial Planning); Investment Specialist (Investments)
- **Docker** -> `docker` (58 roles)
  - Senior Software Engineer, Docker Desktop, Go/Backend Focus (East Coast) (Engineering); Senior Sales Engineer, Strategic Accounts (US West Coast) (Sales); Account Executive, Mid-Enterprise (Central) (Sales)
- **Lambda** -> `lambda` (58 roles)
  - Senior Platform Engineer - Core Infrastructure (Data Center Business); Senior HPC Platform Hardware Engineer (Data Center Business); Engineering Manager - Control Plane (Data Center Business)
- **Clay** -> `claylabs` (68 roles) [clay.com references claylabs]
  - Growth Strategist, Enterprise (Customer Success) (CX); Commercial Counsel (Legal); Strategic Finance (Finance)
- **Higgsfield** -> `higgsfieldai` (69 roles) [higgsfield.ai references higgsfieldai]
  - Growth Product Manager (PLG) (Engineering & Product); GTM Director (PLG) (Marketing & Sales); Product Manager, Lifecycle & Retention (Engineering & Product)
- **Apex Space** -> `apex-technology-inc` (92 roles) [found on apexspace.com]
  - Principal Spacecraft GNC Engineer (Engineering); Mission Integration Engineer (Mission Services); Senior Spacecraft Mechanical Engineer (Engineering)
- **Voodoo** -> `voodoo` (112 roles)
  - QA Engineer - Puzzle & Midcore Games (Gaming); Game Developer - Puzzle Games (Gaming); Publishing Manager - Vietnam (Gaming)
- **Lightspeed Commerce** -> `lightspeedhq` (152 roles) [named tier, derived slug]
  - Senior/Staff Product Analyst (Technology); Outbound Sales Development Representative - Retail (Sales); Chargé(e) de Comptes - Détaillants (Sales)
- **Sierra** -> `sierra` (172 roles)
  - Sales Engineer (Sales); High Growth Enterprise Account Executive (Sales); Sales Director (Sales)
- **Applied Intuition** -> `applied` (268 roles) [applied.co references applied]
  - Hardware Test Engineer (Vehicle OS); Software Engineer - Motion Planning (Fallback Stack) (Self-Driving Systems); ML Runtime Optimization Engineer (Self-Driving Systems)
- **Saronic Technologies** -> `saronic` (271 roles) [named tier, derived slug]
  - Accounts Payable Specialist (Finance & Accounting); Electrical Engineer R&D Technician (Engineering); Workplace Assistant (People)

## Derived slug, unconfirmed (withheld, manual review queue)

A live board was found but the slug is a derived variant and the careers page did not corroborate it. Add an approved entry to scripts/manual-overrides.json to ship it.

- **Arrive Logistics** -> `arrive` (careers page did not corroborate the derived slug)
- **AssemblyAI** -> `assembly` (careers page did not corroborate the derived slug)
- **Axiom Space** -> `axiom` (careers page did not corroborate the derived slug)
- **Bunny.net** -> `bunny` (careers page did not corroborate the derived slug)
- **Chroma** -> `trychroma` (careers page did not corroborate the derived slug)
- **Generate Biomedicines** -> `generate` (careers page did not corroborate the derived slug)
- **Hims & Hers** -> `hims-and-hers` (careers page did not corroborate the derived slug)
- **Impulse Space** -> `impulse` (careers page did not corroborate the derived slug)
- **Incident.io** -> `incident` (careers page did not corroborate the derived slug)
- **Ironclad** -> `ironcladhq` (careers page did not corroborate the derived slug)
- **Ledger Investing** -> `ledger` (careers page did not corroborate the derived slug)
- **Lighthouse** -> `lighthousehq` (careers page did not corroborate the derived slug)
- **Orca Security** -> `orca` (careers page did not corroborate the derived slug)
- **Origin** -> `originhq` (careers page did not corroborate the derived slug)
- **Pivot Bio** -> `pivot` (careers page did not corroborate the derived slug)
- **Plenty** -> `plentylabs` (careers page did not corroborate the derived slug)
- **Rain AI** -> `rain` (careers page did not corroborate the derived slug)
- **Rec Room** -> `rec` (careers page did not corroborate the derived slug)
- **Sanctuary AI** -> `sanctuary` (careers page did not corroborate the derived slug)
- **Terra CO2** -> `terra` (careers page did not corroborate the derived slug)
- **Trunk Tools** -> `trunk` (careers page did not corroborate the derived slug)
- **Uniswap Labs** -> `uniswap` (careers page did not corroborate the derived slug)
- **Velocity Global** -> `velocity` (careers page did not corroborate the derived slug)

## Ashby confirmed, slug unresolved

The site shows an Ashby embed or ashby_jid but no slug could be extracted, usually because JavaScript injects it. Resolve these by hand.

- **11x** (11x.ai shows Ashby, no slug extractable)
- **Deno** (deno.com shows Ashby, no slug extractable)
- **Eppo** (geteppo.com shows Ashby, no slug extractable)
- **EvenUp** (evenuplaw.com shows Ashby, no slug extractable)
- **Jasper** (jasper.ai shows Ashby, no slug extractable)
- **Lakera** (lakera.ai shows Ashby, no slug extractable)
- **Magic** (magic.dev shows Ashby, no slug extractable)
- **Mistral AI** (mistral.ai shows Ashby, no slug extractable)
- **Motion** (usemotion.com shows Ashby, no slug extractable)
- **Northflank** (northflank.com shows Ashby, no slug extractable)
- **Ricursive Intelligence** (ricursive.com shows Ashby, no slug extractable)
- **Roadsurfer** (roadsurfer.com shows Ashby, no slug extractable)
- **Robin AI** (robinai.com shows Ashby, no slug extractable)
- **Spellbook** (spellbook.legal shows Ashby, no slug extractable)
- **Viz.ai** (viz.ai shows Ashby, no slug extractable)
- **Voltage Park** (voltagepark.com shows Ashby, no slug extractable)

## Error, unresolved

Throttling, blocks, or transport failures. Not cached, so a rerun retries them.

_none_

## Previously confirmed, now 404

These known-good slugs stopped resolving.

- **Figma** (known slug now 404s)
- **welevel** (known slug now 404s)

## Rejected by manual override

Excluded on purpose.

_none_

## Resolved only by scraping

Slug guessing alone would have missed these, which is why the careers-page fallback earns its place.

- **Apex Space** -> `apex-technology-inc` (92 roles) [found on apexspace.com]
  - Principal Spacecraft GNC Engineer (Engineering); Mission Integration Engineer (Mission Services); Senior Spacecraft Mechanical Engineer (Engineering)
- **Blackbird** -> `blackbird-labs-inc` (9 roles) [found on blackbird.xyz]
  - Senior/Staff Backend Engineer (Engineering); Partnerships Strategy & Ops Associate - New York, NY (Loyalty); Senior/Staff Fullstack Engineer (Engineering)
- **Captions** -> `mirage` (9 roles) [found on captions.ai]
  - Software Engineer, Web Product (Engineering); Lifecycle Marketing Lead (Marketing); Technical Recruiter (Operations)
- **Chronosphere** -> `chronospherejobs` (0 roles) [found on chronosphere.io]
  - no open roles
- **ConductorOne** -> `C1` (13 roles) [found on conductorone.com]
  - Sales Development Representative (Sales); Sr. Solutions Engineer (Sales); Enterprise Account Executive (East) (Sales)
- **Convex** -> `convex-dev` (8 roles) [found on convex.dev]
  - Software Engineer, Infra/Systems (Engineering); Software Engineer, API Platform (Engineering); Software Engineer, Product (Engineering)
- **Front** -> `frontcareers` (22 roles) [front.com pointed at frontcareers, not frontapp]
  - AI Engineer - GTM / Operations (Contract) (G&A); Senior Software Engineer - Front End Architecture / React Native (EPD); Senior Software Engineer - Front End Architecture / React Native (EPD)
- **Hebbia** -> `hebbia-ai` (26 roles) [found on hebbia.ai]
  - Technical Delivery (Post-Sales); Forward Deployed Banker (AI Strategist) (AI Strategy); Forward Deployed Investor (AI Strategist) (AI Strategy)
- **Jack & Jill** -> `jack-jill-external-ats` (5 roles) [found on jackandjill.ai]
  - Founding Engineer (£240k+ ) (Engineering); Founding Designer (£180k+) (Engineering); Founding GTM Operator (£150k+) (GTM)
- **LILT** -> `lilt-corporate` (7 roles) [found on lilt.com]
  - Account Development Representative (ADR) (Sales); Forward Deployed Engineer (Engineering); Enterprise Account Executive (Sales)
- **Nightfall** -> `nightfall-ai` (22 roles) [found on nightfall.ai]
  - Senior Backend Software Engineer (R&D); Endpoint Engineer - Mac OS (R&D); Data Loss Prevention (DLP) Analyst (R&D)
- **Sana Labs** -> `sana-roles` (31 roles) [found on sanalabs.com]
  - GTM Associate (Go-To-Market); GTM Manager (Account Executive) (Go-To-Market); Design Engineer (Engineering)
- **Second Front** -> `Second-Front-Systems` (16 roles) [found on secondfront.com]
  - Engineering Manager (Engineering Leadership); Director, Demand Generation (Growth); Senior Solutions Architect (Mission Success)

## Industries

Final list after merges and drops.

- AI: 102
- Aerospace: 4
- Analytics: 16
- Biotech: 9
- Climate: 7
- Construction: 6
- Consumer: 12
- Cybersecurity: 26
- Defense: 6
- Design: 7
- DevTools: 61
- Education: 16
- Energy: 8
- Fintech: 33
- Food: 4
- Gaming: 3
- HR & Recruiting: 11
- Hardware: 8
- Health & Wellness: 7
- Healthcare: 21
- Infrastructure: 29
- Insurance: 4
- Legal: 4
- Marketing: 16
- Marketplace: 6
- Productivity: 24
- Real Estate: 3
- Robotics: 7
- Transportation: 3
- Web3: 9

### Merges and drops applied

- merged Retail into Consumer: had 2, under 3
- merged Travel into Consumer: had 1, under 3
- dropped Logistics: 2 companies, under 3, no merge target

1 shipped companies ended with no industry label and will not appear under any chip:

- project44

## Slug collisions resolved before probing

A slug owned by a confirmed company is stripped from every other candidate list, and contested candidates go to whichever company ranked them highest. Without this, an aerospace company could ship pointing at Vast.ai's board.

- Vast: dropped `vastai`, owned by Vast.ai
- Twelve Labs: dropped `twelve`, assigned to Twelve
- PlayAI: dropped `play`, assigned to Play
- Maven Clinic: dropped `maven`, assigned to Maven
- Arcadia Science: dropped `arcadia`, assigned to Arcadia
- Form Bio: dropped `form`, assigned to Form Energy
- Apollo GraphQL: dropped `apollo`, assigned to Apollo.io
- Sana Benefits: dropped `sana`, assigned to Sana Labs
- Play: dropped `playai`, assigned to PlayAI
- Twelve: dropped `twelvelabs`, assigned to Twelve Labs
- Sublime Systems: dropped `sublime`, assigned to Sublime Security
- Sierra Space: dropped `sierra`, assigned to Sierra
- Playco: dropped `play`, assigned to Play

## Manual overrides applied

_none_

