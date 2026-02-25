# Deploy Medical Atlas on a VPS from GitHub

This guide assumes a **Linux VPS** (Ubuntu 22.04 or similar). You’ll clone the repo, run the **backend** (FastAPI + PostgreSQL) and **frontend** (Next.js), and put **nginx** in front.

---

## 1. VPS basics

- SSH access to the server.
- A domain (or subdomain) pointing to the VPS IP (optional; you can use the IP only).
- Recommended: at least 2 GB RAM (backend loads a CatBoost model).

---

## 2. Install dependencies (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y git git-lfs python3.11 python3.11-venv python3-pip nodejs npm postgresql postgresql-contrib nginx
```

- **Node 18+**: If `node -v` is old, use [NodeSource](https://github.com/nodesource/distributions) or [nvm](https://github.com/nvm-sh/nvm).
- **Git LFS**: Required to pull the model file (`.cbm`).

```bash
git lfs install
```

---

## 3. Clone the repo and pull LFS

```bash
cd /opt   # or another directory you prefer
sudo git clone https://github.com/Di-Boss/Medical-Atlas.git
sudo chown -R $USER:$USER Medical-Atlas
cd Medical-Atlas
git lfs pull
```

Confirm the model is there:

```bash
ls -la backend/src/training_final_v9_ultra.cbm
```

---

## 4. PostgreSQL

Create a database and user:

```bash
sudo -u postgres psql -c "CREATE USER atlas_app WITH PASSWORD 'YOUR_SECURE_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE atlas_db OWNER atlas_app;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE atlas_db TO atlas_app;"
```

If your API uses a schema (e.g. `medportal`), create it and grant usage:

```bash
sudo -u postgres psql -d atlas_db -c "CREATE SCHEMA IF NOT EXISTS medportal;"
sudo -u postgres psql -d atlas_db -c "GRANT ALL ON SCHEMA medportal TO atlas_app;"
```

Create tables and seed data using your backend’s scripts (e.g. migrations or `setup_db.py`), then create at least one doctor for login.

---

## 5. Backend (FastAPI)

```bash
cd /opt/Medical-Atlas/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in `backend/` (same folder as `src/`):

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=atlas_db
POSTGRES_USER=atlas_app
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD
JWT_SECRET=your-long-random-jwt-secret-at-least-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Run once to verify:

```bash
uvicorn src.api:app --host 127.0.0.1 --port 8000
```

You should see “Model loaded successfully!” and no DB errors. Stop with Ctrl+C.

---

## 6. Frontend (Next.js)

```bash
cd /opt/Medical-Atlas/frontend
npm ci
```

Optional: if the backend is not on the same host, set the API URL at build time:

```bash
export NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm run build
```

Run in production:

```bash
npm run start
```

Runs on port 3000 by default. The app will call the backend at `NEXT_PUBLIC_API_URL` or `http://127.0.0.1:8000`.

---

## 7. systemd (keep backend and frontend running)

**Backend service** – `/etc/systemd/system/medical-atlas-api.service`:

```ini
[Unit]
Description=Medical Atlas FastAPI
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/Medical-Atlas/backend
Environment="PATH=/opt/Medical-Atlas/backend/.venv/bin"
ExecStart=/opt/Medical-Atlas/backend/.venv/bin/uvicorn src.api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Frontend service** – `/etc/systemd/system/medical-atlas-web.service`:

```ini
[Unit]
Description=Medical Atlas Next.js
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/Medical-Atlas/frontend
Environment="NODE_ENV=production"
Environment="NEXT_PUBLIC_API_URL=http://127.0.0.1:8000"
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

If you use a different user (e.g. `deploy`), change `User=` and `Group=` and ensure that user owns `/opt/Medical-Atlas`.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable medical-atlas-api medical-atlas-web
sudo systemctl start medical-atlas-api medical-atlas-web
sudo systemctl status medical-atlas-api medical-atlas-web
```

---

## 8. Nginx (reverse proxy)

Create a server block, e.g. `/etc/nginx/sites-available/medical-atlas`:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/medical-atlas /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Use `http://YOUR_DOMAIN_OR_IP` to open the app. Login and all API calls go through Next.js (port 3000), which forwards to the backend (8000).

---

## 9. CORS (if you use a domain)

The backend allows `http://localhost:3000` by default. If you access the site by domain (e.g. `https://atlas.example.com`), update CORS in `backend/src/api.py`:

```python
allow_origins=["http://localhost:3000", "https://atlas.example.com", "http://YOUR_VPS_IP"],
```

Then restart the API:

```bash
sudo systemctl restart medical-atlas-api
```

---

## 10. HTTPS (recommended)

Use Certbot with nginx:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d atlas.example.com
```

Then use `https://atlas.example.com` in CORS and in `NEXT_PUBLIC_API_URL` if needed.

---

## 11. Updates from GitHub

```bash
cd /opt/Medical-Atlas
git pull
git lfs pull
cd backend && source .venv/bin/activate && pip install -r requirements.txt && cd ..
cd frontend && npm ci && npm run build && cd ..
sudo systemctl restart medical-atlas-api medical-atlas-web
```

---

## Checklist

| Step | What |
|------|------|
| 1 | Install git, git-lfs, Python 3.11, Node 18+, PostgreSQL, nginx |
| 2 | Clone repo and run `git lfs pull` |
| 3 | Create PostgreSQL DB and user, run migrations/seed |
| 4 | Backend: venv, `pip install -r requirements.txt`, `.env` |
| 5 | Frontend: `npm ci`, `npm run build` |
| 6 | systemd units for API and Next.js |
| 7 | Nginx proxy to port 3000 |
| 8 | Adjust CORS if using a domain; add HTTPS with certbot |

If something fails, check:

- `sudo journalctl -u medical-atlas-api -f`
- `sudo journalctl -u medical-atlas-web -f`
- `sudo tail -f /var/log/nginx/error.log`
