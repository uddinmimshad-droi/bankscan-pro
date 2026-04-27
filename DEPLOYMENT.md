# BankScan Pro Deployment Guide

BankScan Pro has two parts:

1. Frontend website: deploy on Vercel.
2. Backend PDF/OCR API: deploy on Render using Docker.

This split is required because the backend needs system packages (`tesseract-ocr` and `poppler-utils`) for scanned PDF OCR. Vercel is good for the frontend, but the OCR backend should run on a Docker web service.

## 1. Install Required Tools On Windows

### Node.js LTS

Download and install Node.js LTS from the official site:

https://nodejs.org/en/download

After installation, close and reopen PowerShell, then check:

```powershell
node -v
npm -v
```

### Git

Download and install Git for Windows:

https://git-scm.com/download/win

After installation, close and reopen PowerShell, then check:

```powershell
git --version
```

### Vercel CLI

After Node.js is installed:

```powershell
npm install -g vercel
vercel login
```

Official Vercel CLI docs:

https://vercel.com/docs/cli

## 2. Put This Project On GitHub

Create or use a GitHub repository, then run:

```powershell
cd "C:\Users\india\OneDrive\Pictures\Documents\New project\bankscan-pro"
git init
git branch -M main
git add .
git commit -m "Deploy BankScan Pro"
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

Do not commit real customer PDFs or Excel outputs. The backend `.dockerignore` excludes them from Docker builds, but Git can still add them unless you use `.gitignore`.

## 3. Deploy Backend On Render

1. Go to https://render.com
2. Sign up or log in.
3. Click `New +` > `Web Service`.
4. Connect your GitHub repo.
5. Select this repository.
6. Use these settings:
   - Runtime / Language: Docker
   - Root Directory: `backend`
   - Health Check Path: `/health`
   - Plan: Starter or higher recommended for OCR
7. Add environment variable:
   - `CORS_ORIGINS=*`
8. Deploy.

Official Render Web Service docs:

https://render.com/docs/web-services

Official Render Docker docs:

https://render.com/docs/docker

After deployment, Render gives you a URL like:

```text
https://bankscan-pro-api.onrender.com
```

Test it:

```text
https://bankscan-pro-api.onrender.com/health
```

## 4. Deploy Frontend On Vercel

From the project root:

```powershell
cd "C:\Users\india\OneDrive\Pictures\Documents\New project\bankscan-pro"
vercel login
vercel deploy --prod
```

Official Vercel deploy docs:

https://vercel.com/docs/cli/deploy

## 5. Connect Frontend To Backend

The frontend reads the backend URL from browser local storage.

After the Vercel site opens, press `F12`, go to Console, and run:

```javascript
localStorage.setItem("bankscanApiUrl", "https://YOUR-RENDER-BACKEND-URL.onrender.com");
location.reload();
```

Replace the URL with your real Render backend URL.

## Production Notes

- Use Render Starter or higher for large PDFs and OCR.
- OCR for scanned PDFs requires Docker backend because it installs Tesseract and Poppler.
- Uploaded PDFs and generated Excel files are stored on the backend filesystem. For serious production use, connect cloud storage such as S3, Cloudflare R2, or Vercel Blob.
- Do not upload customer bank PDFs to public GitHub repositories.
