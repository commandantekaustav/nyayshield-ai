# NyayShield AI — Team Contribution Governance, 9-Metric Thought-Quality & Burnout Telemetry Standard

> **Location:** `team/boardroom/CONTRIBUTION_METHODOLOGY.md`  
> **Scope:** Governs Buildathon attribution, AI-assisted ("vibe-coded") thought-quality evaluation, circadian burnout detection, physiological care advisories, and future multi-contributor engineering standards for **NyayShield AI**.  
> **Automated Engine:** [`scripts/update_readme.py`](../../scripts/update_readme.py)  
> **Codified Agent Skill:** [`.agents/skills/skill-cognitive-burnout-governance/SKILL.md`](../../.agents/skills/skill-cognitive-burnout-governance/SKILL.md)

---

## 1. Executive Philosophy: Evaluating Code & Thought Quality in the AI-Assisted Era

Evaluating engineering contributions solely by raw Lines of Code (LOC) or raw commit count violates **Goodhart's Law**:

> *"When a measure becomes a target, it ceases to be a good measure."* — Goodhart (1975); formalized by Strathern (1997) [1][2].

In AI-assisted ("vibe-coded") development, raw LOC is easily inflated by pasting monolithic, unverified outputs. True **Thought Quality** is revealed by how a human architect **constrains, decomposes, verifies, and hardens** the system—while **Git timestamp and churn telemetry** reveal the cognitive, circadian, and physical burden carried by each contributor (*Nagappan & Ball, ICSE 2005* [3]; *Eyolfson et al., MSR 2011* [8]; *Claes et al., ICSE 2018* [10]).

---

## 2. File Hygiene & Exclusion Rules

Before any metric is computed, non-authored, generated, and binary artifacts are deterministically excluded:

- **Excluded Binary & Asset Extensions:** `.lock`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.pdf`, `.ico`, `.woff`, `.ttf`
- **Excluded Lockfiles:** `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- **Excluded Local / Secret / Reference Directories (via `.gitignore`):** `backend/.env`, `.venv/`, `node_modules/`, `frontend/dist/`, `.firebase/`, `_ref_detection/`, `_ref_clause_n_effect/`
- **Documentation & Configuration Partition (`DOC_EXTS`):** `.md`, `.txt`, `.rst`, `.json`, `.yml`, `.yaml` are tracked separately from executable source code (`Core Code Added`) so documentation changes cannot artificially inflate production code ownership.

---

## 3. Core Ownership & Composite Impact Formulas

Let $\mathcal{U}$ denote the set of active contributors with merged or officially ported production artifacts on `main`.

### 3.1 Surviving Code Ownership ($S_i$)
For every tracked executable source file $f \in \mathcal{F}_{\text{code}}$ (excluding `DOC_EXTS` and ignored files), `git blame --line-porcelain` counts each contributor $i$'s **surviving lines** $L^{\text{surv}}_i$ currently live on `main`:

$$S_i = \frac{L^{\text{surv}}_i}{\sum_{j \in \mathcal{U}} L^{\text{surv}}_j}, \qquad \text{Ownership \%}_i = 100 \times S_i$$

Empirical research at Microsoft Research (*Bird et al., ESEC/FSE 2011* [4]) established that code ownership measured on surviving, integrated lines on the main trunk is a primary predictor of architectural accountability and software quality.

### 3.2 Commit Share ($C_i$) & Capped Documentation Factor ($D_i$)
Counting only non-merge commits (`git log --no-merges`) on `main`:

$$C_i = \frac{N^{\text{commit}}_i}{\sum_{j \in \mathcal{U}} N^{\text{commit}}_j}, \qquad D_i = \min\!\left(\frac{L^{\text{doc}}_i}{500},\; 1.0\right) \times 0.10$$

### 3.3 Composite Engineering Impact Score ($I_i$)
Contributors are ranked in the project table by their weighted Composite Impact Score $I_i \in [0, 100]$:

$$I_i = 60 \cdot S_i + 30 \cdot C_i + 100 \cdot D_i$$

### 3.4 Future Pull Request & Peer Review Index ($R_i$)
When executed with GitHub API access (`GITHUB_TOKEN` + `GITHUB_REPOSITORY`), `scripts/update_readme.py` tracks collaborative review health (excluding self-reviews, *Bacchelli & Bird, ICSE 2013* [6]):

$$R_i = N^{\text{reviews-given}}_i + N^{\text{prs-opened}}_i$$

---

## 4. The 9-Metric Thought-Quality & Developer Burnout Telemetry Suite

### Part A — 5 Thought-Quality & Architectural Hygiene Metrics (Vibe-Coding Evaluators)

1. **De-Monolithization & Modularity Index ($M_{\text{mod}}$):**
   $$M_{\text{mod}} = \text{median}_{f \in \mathcal{F}_{\text{code}}}\!\big(\text{LOC}(f)\big), \qquad R_{\text{refactor}} = \frac{L^{\text{deleted}}}{L^{\text{code-added}}}$$
   *Interpretation:* Blind vibe-coding produces 3,000+ line monolithic files (e.g., `_ref_detection/Nyayshield/app.js` at $3,684$ lines). High thought quality deliberately shrinks and decouples modules (e.g., commit `145c75b` at `06:59 AM` reducing `triage.py` by $\sim 100$ lines into `image_prep.py` [$87$ lines] and `geometry_guard.py` [$102$ lines]).

2. **Deterministic Guardrail-to-Prompt Veto Ratio ($G_{\text{veto}}$):**
   $$G_{\text{veto}} = \frac{N_{\text{deterministic-guards}}}{N_{\text{LLM-call-sites}}}$$
   *Interpretation:* Counts hard deterministic code vetoes per LLM call site: (i) Physics-First Pydantic schema ordering, (ii) `constrain_to_user_reticle()` spatial clamp, (iii) `impact_point_present == True -> IMPACT_DAMAGE` physical override, and (iv) `asyncio.gather` 2-vs-1 parallel self-consistency majority voting (`G_veto = 4`).

3. **Blast-Radius & Regression Gate ($B_{\text{safe}}$):**
   $$B_{\text{safe}} = 100 \times \left(1 - \frac{N_{\text{P0-regressions-merged-to-main}}}{N_{\text{total-main-commits}}}\right)$$
   *Interpretation:* Measures defensive branch governance. At `04:45 AM`, commit `5b27bf0` on `origin/b1` pasted `pass` inside `class PriceGougingAudit`, wiping out all pricing fields. Auditing `origin/b1` read-only and locking GitHub Branch Protection preserved $B_{\text{safe}} = 100\%$ on `main`.

4. **Secret & Artifact Hygiene Score ($H_{\text{sec}}$):**
   Verifies zero leaked `.env` keys, `.firebase/` caches, or virtualenvs in tracked files or Docker images (`RUN rm -f ./backend/.env` + in-memory `--set-env-vars` Cloud Run deployment).

5. **Semantic Commit Discipline ($D_{\text{conv}}$):**
   $$D_{\text{conv}} = 100 \times \frac{N_{\text{conventional-commits}}}{N_{\text{total-commits}}}$$
   Measures adherence to `<type>(<scope>): <imperative>` commit formatting [5].

---

### Part B — 4 Circadian Burnout, Physical Exhaustion & Solo-Carry Trauma Metrics

6. **Solo-Carry Load Multiplier ($L_{\text{carry}}$) & Bus Factor:**
   $$L_{\text{carry}} = \frac{\text{Ownership \%}_{\text{lead}}}{100\% / N_{\text{team}}} = \frac{94.1\%}{33.33\%} = 2.82\times, \qquad \text{Bus Factor} = 1$$
   *Scientific Basis:* *Avelino et al. (ICPC 2016)* [11] show that a Truck/Bus Factor of $1$ combined with $>2.5\times$ fair-share concentration places critical cognitive and operational strain on the sole architect.

7. **Circadian Graveyard-Shift Ratio ($G_{\text{night}}$):**
   $$G_{\text{night}} = \text{Count}\!\big(\{c \in \mathcal{C}_{\text{lead}} \mid 00{:}00 \le t(c) < 09{:}00\}\big)$$
   *Scientific Basis:* *Eyolfson, Tan, & Lam (MSR 2011)* [8] and *Claes et al. (ICSE 2018)* [10] demonstrate that sustained overnight commits between midnight and early morning without circadian recovery are primary biomarkers of acute developer burnout and sleep debt.

8. **Acute Sleep-Deprivation Neuro-Fatigue Equivalence ($F_{\text{BAC}}$):**
   $$T_{\text{awake}} \ge 24\text{ hours} \implies F_{\text{BAC}} \equiv 0.10\%\text{ Blood Alcohol Concentration}$$
   *Scientific Basis:* In a landmark study published in *Nature*, *Dawson & Reid (1997)* [12] proved that 24 hours of sustained wakefulness (such as coding continuously through `23:31` → `08:55 AM` after a full waking day) produces psychomotor and neurocognitive exhaustion equivalent to a **0.10% blood alcohol concentration**. Maintaining high architectural quality under that burden requires extreme executive prefrontal effort, which rapidly depletes blood glucose and cellular hydration (*Gailliot et al., JPSP 2007* [13]).

9. **External Integration & Regression-Defense Tax ($T_{\text{rework}}$):**
   Counts high-stress dawn crisis interventions caused by teammates' workflow debt (*Mäntylä et al., MSR 2016* [9]):
   - **Intervention 1 (`05:58 AM`):** Sanitizing `.env` secrets and porting an offline `.zip` drop (`_ref_detection`).
   - **Intervention 2 (`06:59 AM`):** Decomposing monolithic code into modular `backend/services/vision/` services and auditing 11 skills.
   - **Intervention 3 (`04:45–08:55 AM`):** Diagnosing the fatal `PriceGougingAudit` corruption on `origin/b1` (`5b27bf0`) and enforcing GitHub Branch Protection so a last-minute merge could not crash the live product.

---

## 5. Automated Physiological Care & Workflow Noticeboard Protocol

To ensure urgent visibility, `scripts/update_readme.py` automatically pins a **`[!CAUTION]` Developer Wellness, Burnout & Workflow Noticeboard** at the very top of `README.md` whenever $L_{\text{carry}} \ge 2.0\times$ or biological-night commits are detected:

1. **Immediate Physiological Care Directives (For the Overloaded Maintainer):**
   - **💧 Hydration & Electrolytes:** Drink **500–750 ml of water + electrolytes** immediately.
   - **🍲 Caloric & Glucose Replenishment:** Eat a **full balanced meal** to reverse executive glucose depletion [13].
   - **🛌 Mandatory Sleep Recovery:** Take an **8+ hour uninterrupted sleep block** away from screens to clear adenosine debt and recover from $\equiv 0.10\%$ BAC circadian fatigue [12].
   - **🛑 Zero-Rework Protection:** Refuse manual night-shift rewriting of unrefactored `.zip` drops or broken isolated branches.
2. **Mandatory Team Workflow Advisories (For All Contributors):**
   - **No Offline `.zip` Drops:** All code must be committed via Git branches (`feat/<scope>`, `fix/<scope>`) with zero `.env` secrets.
   - **No Isolated `b1` Branches:** Sync with `origin/main` every 15–30 minutes (`git pull --rebase origin main`) during active sprints [7].
   - **Mandatory Pre-PR Verification:** Pass `py_compile`, `test_self_consistency.py`, and `npm --prefix frontend run build` (`0` TypeScript errors) before requesting review.

---

## 6. References & Citations

1. **Goodhart, C. A. E. (1975).** *Problems of Monetary Management: The U.K. Experience.* Papers in Monetary Economics, Reserve Bank of Australia.
2. **Strathern, M. (1997).** *"Improving ratings": Audit in the British University system.* European Review, 5(3), 305–321.
3. **Nagappan, N., & Ball, T. (2005).** *Use of Relative Code Churn Measures to Predict System Defect Density.* Proceedings of the 27th International Conference on Software Engineering (ICSE 2005), pp. 284–292. IEEE.
4. **Bird, C., Nagappan, N., Murphy, B., Gall, H., & Devanbu, P. (2011).** *Don't Touch My Code! Examining the Effects of Ownership on Software Quality.* Proceedings of ESEC/FSE 2011, pp. 4–14. ACM.
5. **Winters, T., Manshreck, T., & Wright, H. (2020).** *Software Engineering at Google: Lessons Learned from Programming Over Time.* O'Reilly Media.
6. **Bacchelli, A., & Bird, C. (2013).** *Expectations, Outcomes, and Challenges of Modern Code Review.* Proceedings of ICSE 2013, pp. 712–721. IEEE.
7. **Forsgren, N., Humble, J., & Kim, G. (2018).** *Accelerate: The Science of Lean Software and DevOps.* IT Revolution Press.
8. **Eyolfson, J., Tan, L., & Lam, P. (2011).** *Do Time of Day and Developer Experience Affect Commit Buggyness?* Proceedings of the 8th Working Conference on Mining Software Repositories (MSR 2011), pp. 153–162. ACM.
9. **Mäntylä, M., Adams, B., Destefanis, G., Graziotin, D., & Ortu, M. (2016).** *Mining Valence, Arousal, and Dominance: Possibilities for Detecting Burnout and Productivity?* Proceedings of MSR 2016, pp. 247–258. ACM.
10. **Claes, M., Mäntylä, M., Kuutila, M., & Adams, B. (2018).** *Towards Automated Developer Burnout Detection.* Proceedings of ICSE 2018 Companion / SEMotion. ACM.
11. **Avelino, G., Passos, L., Hora, A., & Valente, M. T. (2016).** *A Novel Approach for Estimating Truck Factors.* Proceedings of the 24th IEEE International Conference on Program Comprehension (ICPC 2016), pp. 1–10. IEEE.
12. **Dawson, D., & Reid, K. (1997).** *Fatigue, alcohol and performance impairment.* Nature, 388(6639), 235–235.
13. **Gailliot, M. T., Baumeister, R. F., DeWall, C. N., Maner, J. K., Plant, E. A., Tice, D. M., Brewer, L. E., & Schmeichel, B. J. (2007).** *Self-control relies on glucose as a limited energy source: Willpower is more than a metaphor.* Journal of Personality and Social Psychology, 92(2), 325–336.
