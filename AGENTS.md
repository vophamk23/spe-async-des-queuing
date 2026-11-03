# 🧭 AI AGENT GUIDELINES & CODING GUARDRAILS
> Project: Discrete-Event Queuing Simulation (DES) & Asynchronous Engine (CO3007 - HK261)  
> Based on the 4 Golden Principles of **Andrej Karpathy** and HCMUT Academic Engineering Standards.

---

## PART 1: ANDREJ KARPATHY'S 4 CORE PRINCIPLES

### 1. Think Before Coding
- **Don't assume. Don't hide confusion. Surface tradeoffs:**
  - Before implementing, explicitly state your foundational assumptions.
  - If a request has multiple reasonable interpretations, present the options and tradeoffs instead of silently picking one.
  - If something is unclear or contradictory, stop, identify the confusion, and ask for clarification.
  - Actively push back when a simpler approach exists or when requirements conflict with one another.

### 2. Simplicity First
- **Minimum code that solves the problem. Nothing speculative:**
  - Combat the tendency toward over-engineering: no speculative abstractions, no unrequested configurability, no "flexibility" for hypothetical future scenarios.
  - Write the simplest code that could possibly work correctly.
  - Self-check: *"Would a senior engineer consider this code unnecessarily overcomplicated?"* If yes, simplify immediately.

### 3. Surgical Changes
- **Touch only what you must. Clean up only your own mess:**
  - When editing existing code:
    - **Do NOT "improve"** adjacent code, comments, or formatting that is working and unrelated.
    - **Do NOT refactor** components that are healthy and free of bugs.
    - Strictly adhere to the existing codebase's code style, even if you have a different habit.
    - If you notice pre-existing dead or redundant code, point it out to the user — **do NOT delete it without permission**.
  - When changes create orphans:
    - Clean up unused `import` statements, variables, or helper functions created by your own modifications.
    - Do not delete pre-existing dead code unless explicitly requested.
  - **Golden Rule:** Every modified line of code must be directly traceable to the user's explicit request.

### 4. Goal-Driven Execution
- **Define success criteria. Loop until verified:**
  - Transform vague instructions into verifiable milestones:
    - Instead of *"Add validation"*, transform to: *"Write tests for invalid inputs, then write code to make those tests pass."*
    - Instead of *"Fix bug X"*, transform to: *"Write a test reproducing bug X, then fix code until the test passes."*
    - Instead of *"Refactor Y"*, transform to: *"Ensure the entire test suite passes before and after refactoring."*
  - For multi-step tasks, provide a concise plan:
    1. `[Step 1]` → Verification Criteria: `[What to check]`
    2. `[Step 2]` → Verification Criteria: `[What to check]`
  - Solid success criteria allow the agent to self-correct and verify independently without wasting user time.

---

## PART 2: PROJECT INVARIANTS & DOMAIN CONSTRAINTS

When operating within this codebase, the AI Agent must strictly enforce the following invariants:

### 1. Test Suite Integrity
- The project has **31 automated tests** located in `simulator/tests/`:
  - `test_async_engine.py` (8 tests)
  - `test_bkitevsim_framework.py` (8 tests)
  - `test_verification.py` (15 tests)
- **Every code modification MUST ensure 31/31 tests remain 100% PASSED (`pytest tests/`).**
- Never delete, comment out, or weaken test assertion criteria to bypass an error.

### 2. Verification & Validation (V&V) Standards
- All 67 theoretical benchmark scenarios across 6 Kendall models ($M/M/1, M/M/1/K, M/M/\infty, M/M/n/n, M/M/c, M/M/c/K$) and Jackson queuing networks must maintain **Relative Error $RE \le 5.0\%$** against closed-form analytical solutions.
- Always satisfy the Flow Conservation Law: $N_{arrived} = N_{completed} + N_{in\_system} + N_{dropped}$ with absolute error equal to 0.

### 3. Strict Adherence to the `bkitevsim` Framework
- All simulations must adhere to the official `bkitevsim` architectural hierarchy:
  - Logical Processes: `BkSysLogicalProcess` and `BkSysCoLogicalProcess`.
  - Dispatchers: `Dispatcher` and `DistributedEventDispatcher`.
  - Priority Queues: `MinHeapPriorityQueue` and $\mathcal{O}(1)$ `LadderQueue`.
  - Asynchronous Coordination: `asyncio.Future`, `TaskGroup`, `Runner`.
- Do not reintroduce or reference legacy, non-standardized architectures outside the official package.

### 4. LaTeX Report & Excel Artifact Preservation
- When updating academic reports in `report/`:
  - Ensure `pdflatex -interaction=nonstopmode main.tex` compiles with exit code 0.
  - Preserve the TikZ double border, HCMUT logo, and 9-member contribution table.
- When updating the automated test runner:
  - Keep both Excel files fully synchronized: `DanhSach_TestCases_Input.xlsx` (Input specifications) and `BaoCao_KetQua_KiemThu.xlsx` (Execution report).
