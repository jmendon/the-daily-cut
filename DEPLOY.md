# Deploying The Daily Cut

Here are your options for running The Daily Cut without needing your computer on:

---

## Option 1: Railway (Recommended - Easiest)

**Cost:** Free tier available (500 hours/month), then ~$5/month
**Setup time:** 5 minutes

1. Create account at [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Connect your GitHub and push this code to a repo
4. Railway auto-detects Flask and deploys
5. Add environment variables in Railway dashboard:
   - `ANTHROPIC_API_KEY` (optional)
   - `YOUTUBE_API_KEY` (optional)

**Pros:** Dead simple, auto-deploys on git push, free SSL
**Cons:** Free tier has limits

---

## Option 2: Render

**Cost:** Free tier available, then $7/month
**Setup time:** 5-10 minutes

1. Create account at [render.com](https://render.com)
2. New → Web Service → Connect GitHub repo
3. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Add environment variables in dashboard

**Pros:** Generous free tier, easy setup
**Cons:** Free tier spins down after inactivity (slow first load)

---

## Option 3: Fly.io

**Cost:** Free tier available, then ~$2-5/month
**Setup time:** 10-15 minutes

1. Install flyctl: `brew install flyctl`
2. Login: `fly auth login`
3. In project folder: `fly launch`
4. Deploy: `fly deploy`
5. Set secrets: `fly secrets set ANTHROPIC_API_KEY=xxx`

**Pros:** Great performance, global edge deployment
**Cons:** Requires CLI, slightly more technical

---

## Option 4: PythonAnywhere

**Cost:** Free tier available, $5/month for always-on
**Setup time:** 10 minutes

1. Create account at [pythonanywhere.com](https://pythonanywhere.com)
2. Go to "Web" tab → Add new web app
3. Choose Flask, Python 3.9+
4. Upload files or clone from GitHub
5. Set up virtual environment and install requirements

**Pros:** Python-specific, beginner friendly
**Cons:** Free tier has daily limits

---

## Option 5: Vercel (with modifications)

**Cost:** Free
**Setup time:** 15-20 minutes

Requires converting to serverless functions. Not recommended for this app due to the scraping/API calls.

---

## Quick Deploy to Railway

If you want the fastest path, here's a step-by-step for Railway:

```bash
# 1. Create a GitHub repo and push your code
cd /Users/jmendon/Documents/Pop/the-daily-cut
git init
git add .
git commit -m "Initial commit"
# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/the-daily-cut.git
git push -u origin main

# 2. Go to railway.app, sign in with GitHub
# 3. New Project → Deploy from GitHub repo → Select your repo
# 4. Railway will auto-deploy!
# 5. Click on your service → Settings → Add domain
# 6. Your app is live at https://your-app.up.railway.app
```

---

## Files to add for production

Create `Procfile` in project root:
```
web: gunicorn app:app
```

Add `gunicorn` to requirements.txt:
```
gunicorn==21.2.0
```

Create `runtime.txt` (optional, specifies Python version):
```
python-3.11.0
```

---

## Environment Variables to Set

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask session secret (generate random string) |
| `ANTHROPIC_API_KEY` | No | For podcast summaries |
| `YOUTUBE_API_KEY` | No | For better interview search |
| `NEWS_API_KEY` | No | For more award headlines |

---

## Estimated Monthly Costs

| Platform | Free Tier | Paid |
|----------|-----------|------|
| Railway | 500 hrs/month | ~$5/mo |
| Render | 750 hrs/month (spins down) | $7/mo |
| Fly.io | 3 shared VMs | ~$2-5/mo |
| PythonAnywhere | Limited | $5/mo |

For personal use, Railway or Render free tiers should be sufficient!
