# Share this tool with a friend

## Easiest: one-click browser use (GitHub Codespaces)

**Send them this link:**

### 👉 https://codespaces.new/clayy30/planset-generator

What happens:
1. Friend signs into GitHub (free account is fine)
2. Clicks **Create codespace**
3. Cloud machine builds (~1–2 min first time)
4. App starts on port **8787** and the browser opens the UI
5. They use the wizard → Generate planset → Print to PDF

If the UI does not auto-open: in Codespaces go to the **Ports** tab → port **8787** → open in browser (set visibility to **Public** if they want a shareable preview URL from that session).

> Codespaces free tier is limited hours/month per GitHub account. Fine for demos and real planset work.

---

## Repo (code + docs only — not a live app)

https://github.com/clayy30/planset-generator

## Releases

https://github.com/clayy30/planset-generator/releases

## Local install (power users)

```bash
git clone https://github.com/clayy30/planset-generator.git
cd planset-generator
./run.sh
# open http://127.0.0.1:8787/
```

Requires Python 3.13 preferred and `poppler` (`brew install poppler`) for cut-sheet rasters.
