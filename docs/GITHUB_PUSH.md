# GitHub push checklist (NestQuant Studio v0.1)

Local commit ready: `01b6b7439b702cec61caa00e5b987250d7cd74b0` on `main`.

## Why push failed from PromptQL

1. **Mutating GitHub API calls** (`POST /user/repos`, Contents write) require an **in-app Approve** in PromptQL. Approvals timed out (408).
2. **GitHub App installations = 0** for this account via the integration. `git push` returned:
   `Permission to Minavic16/NestQuant-Prod.git denied to Minavic16` (403).
3. Existing `Minavic16/studio` is a **different** Next.js app — do not overwrite it.
4. `Minavic16/NestQuant-Prod` is nearly empty but push still needs write permission via the PromptQL GitHub App / OAuth scopes.

## Fix (do this on GitHub + PromptQL)

### A. Install PromptQL GitHub App (required for reliable push)

1. PromptQL → Data / Integrations → **GitHub** → Settings → **Manage installations**
2. Install on **Minavic16** (user account)
3. Grant access to either:
   - **All repositories**, or
   - Select: create `nestquant-studio` first, then grant it (and optionally `NestQuant-Prod`)

### B. Create the empty repo (pick one)

**Option 1 — you create in browser (fastest):**
- https://github.com/new → name `nestquant-studio` → Public → **no** README/gitignore/license → Create

**Option 2 — Approve bot modal:**
- When NestQuant Bot requests `POST /user/repos` for `nestquant-studio`, click **Approve** within the timeout window

### C. Re-trigger the bot

Message: `@NestQuant Bot GitHub App installed and nestquant-studio repo is ready — push v0.1`

### D. Manual push from a machine with your credentials (backup)

```bash
tar xzf nestquant-studio-v0.1.0.tar.gz && cd nestquant-studio
git init  # if needed; or use the tarball without .git and:
# prefer: clone empty repo then copy files
git clone https://github.com/Minavic16/nestquant-studio.git
# copy source in, then:
git add -A
git commit -m "feat: NestQuant Studio production-candidate v0.1"
git push -u origin main
```

Or from the VM copy after App is installed (bot will do this).
