# Uploading Medical Atlas to GitHub (with Git LFS)

Repository: **https://github.com/Di-Boss/Medical-Atlas.git**

Because the backend uses a large CatBoost model (`.cbm`) and you may add other heavy assets, use **Git LFS** so the repo stays cloneable and within GitHub limits.

---

## Option A: One repo (monorepo) – frontend + backend

Use this if you want **Medical-Atlas** to contain both the Next.js app and the FastAPI backend.

### 1. Install Git LFS (once per machine)

```bash
git lfs install
```

If needed: https://git-lfs.github.com/

### 2. Create the monorepo folder and copy projects

```powershell
# Example: create Medical-Atlas on Desktop and copy both projects into it
cd C:\Users\mtton\Desktop
mkdir Medical-Atlas
cd Medical-Atlas

# Copy frontend (projectAtlas) as "frontend"
xcopy "C:\Users\mtton\Desktop\projectAtlas\*" ".\frontend\" /E /I /H /Y

# Copy backend (AR Atlas) as "backend"
xcopy "C:\Users\mtton\Desktop\AR Atlas\*" ".\backend\" /E /I /H /Y
```

### 3. Add root `.gitattributes` (LFS) and `.gitignore`

In `Medical-Atlas\` (repo root), create:

**`.gitattributes`**

```
# CatBoost / ML models
*.cbm filter=lfs diff=lfs merge=lfs -text

# Other common heavy formats (optional; add as you use them)
*.pkl filter=lfs diff=lfs merge=lfs -text
*.h5 filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
*.onnx filter=lfs diff=lfs merge=lfs -text
*.safetensors filter=lfs diff=lfs merge=lfs -text
*.joblib filter=lfs diff=lfs merge=lfs -text
```

**`.gitignore`** (root – combine frontend + backend)

```
# Dependencies
node_modules/
frontend/node_modules/
.venv/
venv/
env/

# Build / cache
.next/
out/
build/
frontend/.next/
frontend/out/
__pycache__/
*.pyc
*.pyo
*.pyd

# Env and secrets
.env
.env*
*.env

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Logs and DBs
*.log
*.sqlite3
*.db

# Backend: only ignore old model name if you track the real one
# backend/src/training.cbm

# Backend build
*.pid
*.egg-info/
dist/

# Next / Vercel
*.tsbuildinfo
next-env.d.ts
.vercel
```

### 4. Track LFS and connect to GitHub

```powershell
cd C:\Users\mtton\Desktop\Medical-Atlas

git lfs install
git lfs track "*.cbm"
git lfs track "*.pkl"
# Add more: git lfs track "*.h5" etc. if needed

git init
git add .gitattributes
git add .
git commit -m "Initial commit: frontend + backend with LFS for models"

git remote add origin https://github.com/Di-Boss/Medical-Atlas.git
git branch -M main
git push -u origin main
```

If the repo already has a README on GitHub, do a pull first:

```powershell
git pull origin main --rebase
# resolve any conflicts, then
git push -u origin main
```

### 5. After first push – backend model path

The app expects the model at `backend/src/training_final_v9_ultra.cbm`. Keep that file in the repo (tracked by LFS). Do **not** add `training_final_v9_ultra.cbm` to `.gitignore`; only the old `training.cbm` is ignored in the backend.

---

## Option B: Only frontend in Medical-Atlas

If you want **Medical-Atlas** to be only the Next.js app (no backend):

1. Install LFS: `git lfs install`
2. In `projectAtlas`:
   - Add a root `.gitattributes` only if you have large files (e.g. big images); otherwise you can skip LFS.
   - Run:
   ```powershell
   cd C:\Users\mtton\Desktop\projectAtlas
   git init
   git remote add origin https://github.com/Di-Boss/Medical-Atlas.git
   git add .
   git commit -m "Initial commit: Medical Atlas frontend"
   git branch -M main
   git push -u origin main
   ```

---

## LFS tips

- **Track before adding files:** Run `git lfs track "*.cbm"` (and any other patterns) before the first `git add` of those files.
- **Check what’s tracked:** `git lfs track`
- **Clone with LFS:** After clone, run `git lfs pull` if large files are missing.
- **Quota:** GitHub gives 1 GB LFS storage and 1 GB/month bandwidth on free plans; larger files or traffic may need a paid plan.

---

## Summary

| Goal                         | Use LFS? | Repo layout                          |
|-----------------------------|----------|--------------------------------------|
| Frontend + backend in one   | Yes (.cbm and other models) | `frontend/` + `backend/` in Medical-Atlas |
| Frontend only               | Optional | Root = projectAtlas contents         |

Use **Option A** if you want a single clone for the full Medical Atlas app and to keep the `.cbm` model in Git via LFS.
