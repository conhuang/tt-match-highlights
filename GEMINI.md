ok # Engineering Rules & Guidelines

## 1. Visual Verification via Playwright Before Pushing
- **Rule**: ALWAYS test all UI and full-stack changes visually in the browser using Playwright (`browser_navigate`, `browser_click`, `browser_take_screenshot`) **BEFORE** committing or pushing to Git.
- Never claim a UI feature is complete without capturing empirical browser screenshot proof.

## 2. Feature Branch Workflow
- **Rule**: ALWAYS create and develop new features on a dedicated feature branch (e.g., `feature/beta-google-auth`) first.
- **NEVER push feature work directly to `main`**. Only merge or push feature branches once fully verified.

## 3. Local Development Testing via `start_dev.sh`
- **Rule**: ALWAYS run and test local backend + frontend changes using `./start_dev.sh` before deploying to production or staging.
- Ensure environment variables in `.env.dev` or `start_dev.sh` match the expected local dev configuration.

## 4. Root Cause Analysis Before Fixing Bugs
- **Rule**: When debugging an error or issue, ALWAYS identify and extract the empirical root cause FIRST.
- Clearly explain the exact problem and your proposed fix to the user BEFORE modifying code.
