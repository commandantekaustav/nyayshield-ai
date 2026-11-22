---
name: skill-cognitive-burnout-governance
description: |
  Computes and audits the 9-metric Engineering Thought-Quality & Developer Burnout Telemetry suite for NyayShield AI: 5 Vibe-Coding Thought-Quality metrics (De-Monolithization, Deterministic Guardrail Veto Ratio, Blast-Radius Safety, Secret Hygiene, Semantic Commit Discipline) + 4 Circadian Burnout & Solo-Carry Trauma metrics (Solo-Carry Load Multiplier, Graveyard-Shift Ratio, 0.10% BAC Sleep-Deprivation Equivalence, Integration Rework Tax), and pins an automated Physiological Care (Sleep/Water/Food) & Workflow Advisory Noticeboard to the top of README.md.
---

# Cognitive Thought-Quality, Burnout Telemetry & Developer Wellness Governance

## Overview
This skill codifies the **9-Metric Engineering & Physiological Telemetry Engine** executed by `scripts/update_readme.py` and documented in `team/boardroom/CONTRIBUTION_METHODOLOGY.md`. It evaluates both **Thought Quality in AI-Assisted ("Vibe-Coded") Software** and **Acute Developer Burnout / Circadian Trauma**, automatically pinning urgent physiological care (sleep, hydration, nutrition) and workflow advisories to the top of `README.md`.

---

## 1. The 9 Core Metrics (5 Thought-Quality + 4 Burnout/Trauma)

### Part A — 5 Thought-Quality & Architectural Hygiene Metrics
1. **De-Monolithization & Modularity Index ($M_{\text{mod}}$):** Median LOC per production source file and refactoring compression ratio ($\text{LOC}_{\text{deleted}} / \text{LOC}_{\text{added}}$). Distinguishes intentional modular refactoring (e.g., extracting `backend/services/vision/image_prep.py` and `geometry_guard.py`) from 3,600-line single-file AI dumps.
2. **Deterministic Guardrail-to-Prompt Veto Ratio ($G_{\text{veto}}$):** Ratio of deterministic code post-conditions (Physics-First Pydantic schemas, `constrain_to_user_reticle()`, `impact_point_present -> IMPACT_DAMAGE` override, `asyncio.gather` self-consistency vote, and unit test assertions) per LLM inference call site.
3. **Blast-Radius & Regression Gate ($B_{\text{safe}}$):** Percentage of merged `main` commits passing `tsc && vite build`, `py_compile`, and schema integrity checks (contrasted against unmerged branch regressions like `origin/b1` commit `5b27bf0` corrupting `PriceGougingAudit`).
4. **Secret & Artifact Hygiene Score ($H_{\text{sec}}$):** Verification that `.env` credentials, `.firebase/` caches, and virtualenvs are strictly excluded via `.gitignore`, `.dockerignore`, and `Dockerfile` sanitization (`100%` clean on `main`).
5. **Semantic Commit Discipline ($D_{\text{conv}}$):** Percentage of commits adhering to Conventional Commits (`<type>(<scope>): <imperative>`) vs. fatigue-induced raw messages.

### Part B — 4 Circadian Burnout, Physical Exhaustion & Solo-Carry Metrics
6. **Solo-Carry Load Multiplier ($L_{\text{carry}}$):** $\frac{\text{Surviving Ownership \%}}{100\% / N_{\text{team}}}$. In a 3-person team ($33.3\%$ baseline), carrying $94.1\%$ of production code represents a **$2.82\times$ solo-carry overload** with **Bus Factor = 1** (*Avelino et al., ICPC 2016*).
7. **Circadian Graveyard-Shift Ratio ($G_{\text{night}}$):** Percentage of sprint commits executed during the biological night (`00:00–08:30` local time) without sleep recovery (*Claes et al., ICSE 2018*; *Eyolfson et al., MSR 2011*).
8. **Acute Sleep-Deprivation Neuro-Fatigue Equivalence ($F_{\text{BAC}}$):** Continuous overnight coding span (`23:31` → `08:55 AM` following a waking day $\ge 24\text{h}$ wakefulness) mapped to **$\equiv 0.10\%$ Blood Alcohol Concentration (BAC)** neurocognitive and physical impairment (*Dawson & Reid, Nature 1997*).
9. **External Integration & Regression-Defense Tax ($T_{\text{rework}}$):** Count of high-stress dawn interventions caused by teammates' workflow debt (sanitizing `.env` leaks from offline `.zip` drops, decomposing 3,684-line monoliths at `06:00 AM`, and locking GitHub Branch Protection at `08:55 AM` to block `b1` from crashing production).

---

## 2. Automated Physiological & Workflow Noticeboard Rules

Whenever `python scripts/update_readme.py` runs, it inspects commit timestamps, overnight spans, and branch hygiene to pin a live **Developer Wellness & Workflow Noticeboard** at the very top of `README.md`:

- **`🔴 CRITICAL BURNOUT & PHYSIOLOGICAL CARE ALERT` (Triggered when $L_{\text{carry}} \ge 2.0\times$ or overnight continuous span $\ge 6\text{h}$):**
  - **💧 Immediate Hydration & Nutrition:** Drink **500–750 ml of water + electrolytes** and eat a **full balanced meal** immediately (sustained prefrontal cortex executive function depletes blood glucose and cellular hydration; *Gailliot et al., JPSP 2007*).
  - **🛌 Mandatory Sleep Debt Recovery:** Take an immediate **8+ hour uninterrupted sleep block** away from screens to clear adenosine buildup and reverse $\equiv 0.10\%$ BAC circadian impairment (*Dawson & Reid, Nature 1997*).
  - **🛑 Code-Freeze Protection:** Do not manually rewrite teammates' `.zip` dumps or broken branches during biological night hours.
- **`🟠 TEAM WORKFLOW & BRANCH DISCIPLINE DIRECTIVE` (Pinned for all contributors):**
  - **No Offline `.zip` Drops:** Never send code as a `.zip` with `.env` keys inside; use Git branches.
  - **No Isolated `b1` "Push-at-the-End" Branches:** Sync with `origin/main` every 15–30 minutes (`git pull --rebase origin main`) and run `py_compile` + `npm --prefix frontend run build` before opening a PR.

---

## 3. Execution Command

```powershell
python scripts/update_readme.py
```
Updates `README.md` between `<!-- CONTRIB_START -->` and `<!-- CONTRIB_END -->` and prints the live physiological & burnout advisory to the terminal.
