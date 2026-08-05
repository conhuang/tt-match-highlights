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

## 5. Frontend & UI Directives for Agents
- **UI Primitives Mandate**: ALWAYS use the standardized UI primitive components in `frontend/src/components/ui/` (`Button`, `Card`, `Badge`) for all new UI features. NEVER write raw unstyled `<button>` tags or ad-hoc inline styles (`style={{ display: 'flex', ... }}`).
- **CSS Design Tokens**: Reference predefined CSS variables in `index.css` (`var(--card-bg)`, `var(--card-border)`, `var(--text-primary)`, `var(--accent-blue-light)`). NEVER use arbitrary hardcoded hex colors in component files.
- **Iconography Standard**: ALWAYS use native `lucide-react` icons (e.g., `<Activity />`, `<Target />`, `<Settings />`). NEVER use raw text emojis in UI buttons or headers.
- **Component Seams & Modularity**: Keep components focused, reusable, and self-contained. Place modals in `components/`, sub-cards in `components/`, and shared state in `types.ts`.

