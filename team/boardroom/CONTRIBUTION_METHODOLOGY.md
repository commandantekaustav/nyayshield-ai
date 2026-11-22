# NyayShield AI — Team Contribution Governance, Mathematical Scoring & Attribution Standard

> **Location:** `team/boardroom/CONTRIBUTION_METHODOLOGY.md`  
> **Scope:** Governs both current Buildathon attribution and all future multi-contributor engineering evaluations for **NyayShield AI**.  
> **Automated Engine:** [`scripts/update_readme.py`](../../scripts/update_readme.py)

---

## 1. Executive Philosophy: Why Raw LOC and Commit Counts Fail

Evaluating engineering contributions solely by raw Lines of Code (LOC) or raw commit count violates **Goodhart's Law**:

> *"When a measure becomes a target, it ceases to be a good measure."* — Goodhart (1975); formalized by Strathern (1997) [1][2].

Naive metrics incentivize:
- **Commit inflation** (splitting trivial typo edits into dozens of commits).
- **Copy-paste bloat** (pasting monolithic, unrefactored code or vendored libraries).
- **High-churn instability** (introducing broken schemas that must later be reverted or rewritten, which empirical software engineering research shows strongly correlates with post-release defect density — Nagappan & Ball, ICSE 2005 [3]).

To guarantee **fair, objective, and tamper-resistant attribution**, NyayShield AI evaluates contributions across **four orthogonal dimensions**:
1. **Surviving Code Ownership** (lines that survive review, integration, and refactoring into production `main`).
2. **Verified Commit History** (non-merge commits landed on `main`).
3. **Capped Documentation & Configuration Impact** (preventing Markdown bloat from outweighing production code).
4. **Peer Review, Offline Prototype Porting, and Non-Code Deliverables** (transparently tracked without distorting engineering ownership percentages).

---

## 2. File Hygiene & Exclusion Rules

Before any metric is computed, non-authored, generated, and binary artifacts are deterministically excluded:

- **Excluded Binary & Asset Extensions:** `.lock`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.pdf`, `.ico`, `.woff`, `.ttf`
- **Excluded Lockfiles:** `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
- **Excluded Local / Secret / Reference Directories (via `.gitignore`):** `backend/.env`, `.venv/`, `node_modules/`, `frontend/dist/`, `.firebase/`, `_ref_detection/`, `_ref_clause_n_effect/`
- **Documentation & Configuration Partition (`DOC_EXTS`):** `.md`, `.txt`, `.rst`, `.json`, `.yml`, `.yaml` are tracked separately from executable source code (`Core Code Added`) so documentation changes cannot artificially inflate production code ownership.

---

## 3. Mathematical Scoring Model

Let $\mathcal{U}$ denote the set of active contributors with merged or officially ported production artifacts on `main`.

### 3.1 Surviving Code Ownership ($S_i$)
For every tracked executable source file $f \in \mathcal{F}_{\text{code}}$ (excluding `DOC_EXTS` and ignored files), `git blame --line-porcelain` counts each contributor $i$'s **surviving lines** $L^{\text{surv}}_i$ currently live on `main`:

$$S_i = \frac{L^{\text{surv}}_i}{\sum_{j \in \mathcal{U}} L^{\text{surv}}_j}, \qquad \text{Ownership \%}_i = 100 \times S_i$$

**Why Surviving Lines?**  
Empirical research at Microsoft Research (*Bird et al., ESEC/FSE 2011* [4]) established that code ownership measured on surviving, integrated lines on the main trunk is a primary predictor of architectural accountability and software quality, whereas deleted or unmerged draft lines represent unshipped churn.

### 3.2 Commit Share ($C_i$)
Counting only non-merge commits (`git log --no-merges`) merged into `main`:

$$C_i = \frac{N^{\text{commit}}_i}{\sum_{j \in \mathcal{U}} N^{\text{commit}}_j}$$

### 3.3 Capped Documentation Factor ($D_i$)
To reward high-quality technical documentation while preventing unbounded score gaming via auto-generated Markdown:

$$D_i = \min\!\left(\frac{L^{\text{doc}}_i}{500},\; 1.0\right) \times 0.10$$

Documentation credit saturates at $500$ added documentation lines ($D_i \le 0.10$), contributing at most $10$ points to the composite impact score.

### 3.4 Composite Engineering Impact Score ($I_i$)
Contributors are ranked in the project table by their weighted Composite Impact Score $I_i \in [0, 100]$:

$$I_i = 60 \cdot S_i + 30 \cdot C_i + 100 \cdot D_i$$

| Component | Weight | Rationale |
| :--- | :---: | :--- |
| **Surviving Code Ownership ($S_i$)** | **60%** | Rewards durable, production-grade code that survives review and deployment. |
| **Merged Commit Share ($C_i$)** | **30%** | Rewards sustained, incremental delivery on `main` (small, reviewable CLs [5]). |
| **Capped Documentation Factor ($D_i$)** | **10%** | Rewards architectural docs, API references, and runbooks without allowing doc-padding. |

### 3.5 Future Pull Request & Peer Review Index ($R_i$)
When executed with GitHub API access (`GITHUB_TOKEN` + `GITHUB_REPOSITORY`), `scripts/update_readme.py` also tracks collaborative review health:

$$R_i = N^{\text{reviews\_given}}_i + N^{\text{prs\_opened}}_i$$

Self-reviews are strictly excluded (`reviewer != pr_author`), aligning with empirical findings on the defect-prevention value of independent peer review (*Bacchelli & Bird, ICSE 2013* [6]).

---

## 4. Special Governance & Attribution Rules

### Rule A — Author Identity Normalization
Local machine Git aliases (e.g., `vangaja rakshasha` and `Kaustav Basu` sharing `kaustavbasu97@gmail.com`) are unified via `AUTHOR_MAP` in `scripts/update_readme.py` so one engineer's history is never fragmented across multiple rows.

### Rule B — Offline Prototype Porting & Clean-Scope Attribution
When a contributor supplies a working prototype offline (e.g., via `.zip` rather than Git) that contains unrefactored monoliths or leaked secrets (`.env`), **only the sanitized, refactored, surviving core module lines integrated into production `main` are attributed to that contributor**:
- **Applied Case (`Ishika`):** Credited strictly for the surviving lines of the 3 core optical defect detection modules (`backend/services/vision/image_prep.py`, `backend/services/vision/geometry_guard.py`, and `frontend/src/components/AnnotationCanvas.tsx`), while deducting those lines from the integrator's count so $\sum_i \text{Ownership \%}_i = 100.0\%$ exactly. The unrefactored `.zip` dump (`_ref_detection/`) remains gitignored and uncounted.

### Rule C — Trunk Protection & Unmerged / Drifted Branches
Consistent with **Trunk-Based Development** (*Forsgren, Humble, & Kim, 2018* [7]) and **Google Engineering Practices** [5]:
1. All feature work MUST use scoped branches (`feat/<topic>`, `fix/<topic>`, `docs/<topic>`) — never opaque names like `b1`.
2. Contributors MUST sync/rebase against `origin/main` frequently (every 15–30 minutes during active sprints) to prevent schema drift.
3. **Unmerged branches do not count toward production code ownership.** Code that introduces P0 schema breakages (such as corrupting a Pydantic model) or fails `tsc` / `py_compile` / unit tests is blocked by GitHub Branch Protection (`Required approvals = 1`) and excluded from production metrics until fixed and merged.

### Rule D — Transparent Non-Code Attribution
Non-code deliverables (pitch decks, business strategy, UI mockups, user interviews, legal domain research) are **never fabricated as fake code commits**. Instead, they are credited transparently in the **Role & Contributed Scope** column (e.g., *Anwesha — Pitch Deck & Presentation Slides (Non-Code)*) so judges and stakeholders see the full team picture without distorting engineering ownership percentages.

---

## 5. Future Contribution Protocol (Post-Hackathon Scaling)

For all future work on NyayShield AI:
1. **Branch & Sync:** Branch from latest `main` (`git checkout -b feat/<feature>`), rebase frequently (`git pull --rebase origin main`).
2. **Automated Verification Gate:** Every PR must pass:
   - `python -m py_compile backend/services/triage.py backend/models/schemas.py`
   - `python -m backend.tests.test_self_consistency`
   - `npm --prefix frontend run build` (`0` TypeScript errors)
3. **Zero-Secret Hygiene:** `.env` files and API keys must never be committed or shared inside `.zip` archives.
4. **Metric Refresh:** After merging PRs into `main`, run `python scripts/update_readme.py` (or trigger the GitHub Action once billing/public settings allow) to recompute the live ownership table automatically.

---

## 6. References & Citations

1. **Goodhart, C. A. E. (1975).** *Problems of Monetary Management: The U.K. Experience.* Papers in Monetary Economics, Reserve Bank of Australia.
2. **Strathern, M. (1997).** *"Improving ratings": Audit in the British University system.* European Review, 5(3), 305–321.
3. **Nagappan, N., & Ball, T. (2005).** *Use of Relative Code Churn Measures to Predict System Defect Density.* Proceedings of the 27th International Conference on Software Engineering (ICSE 2005), pp. 284–292. IEEE.
4. **Bird, C., Nagappan, N., Murphy, B., Gall, H., & Devanbu, P. (2011).** *Don't Touch My Code! Examining the Effects of Ownership on Software Quality.* Proceedings of the 19th ACM SIGSOFT Symposium and the 13th European Conference on Foundations of Software Engineering (ESEC/FSE 2011), pp. 4–14. ACM.
5. **Winters, T., Manshreck, T., & Wright, H. (2020).** *Software Engineering at Google: Lessons Learned from Programming Over Time.* O'Reilly Media (and [Google Engineering Practices Documentation](https://google.github.io/eng-practices/)).
6. **Bacchelli, A., & Bird, C. (2013).** *Expectations, Outcomes, and Challenges of Modern Code Review.* Proceedings of the 2013 International Conference on Software Engineering (ICSE 2013), pp. 712–721. IEEE.
7. **Forsgren, N., Humble, J., & Kim, G. (2018).** *Accelerate: The Science of Lean Software and DevOps: Building and Scaling High Performing Technology Organizations.* IT Revolution Press.
