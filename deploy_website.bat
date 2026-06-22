@echo off
title Angetic Essence — Website Deploy
cd /d "%~dp0"

echo ============================================================
echo   ANGETIC ESSENCE — Website Deploy to GitHub Pages
echo ============================================================
echo.

:: ── Config ──
:: Change these to match your GitHub username and repo name
set GITHUB_USER=your-username
set REPO_NAME=angetic-essence
set BRANCH=gh-pages

echo [!] Before running, create an empty repo on GitHub:
echo     https://github.com/new
echo     Repository name: %REPO_NAME%
echo     Do NOT initialize with README, .gitignore, or license.
echo.

pause
echo.

:: ── Init git ──
if not exist website\.git (
    echo [1/5] Initializing git repository...
    git init website
) else (
    echo [1/5] Git repository already exists.
)

:: ── Create .gitignore ──
echo [2/5] Creating .gitignore...
if not exist website\.gitignore (
    echo __pycache__/ > website\.gitignore
    echo *.pyc >> website\.gitignore
    echo .DS_Store >> website\.gitignore
)

:: ── Switch to orphan branch for clean Pages deploy ──
echo [3/5] Creating %BRANCH% branch...
git -C website checkout --orphan %BRANCH% 2>nul
git -C website rm -rf . 2>nul

:: ── Add all files ──
echo [4/5] Adding files...
git -C website add -A
git -C website status

:: ── Commit ──
echo [5/5] Committing...
git -C website commit -m "Initial beta landing page — Angetic Essence"

:: ── Remote ──
echo.
echo Setting remote origin...
git -C website remote add origin https://github.com/%GITHUB_USER%/%REPO_NAME%.git 2>nul

echo.
echo ============================================================
echo   READY TO PUBLISH
echo ============================================================
echo.
echo   Run the following command to push:
echo.
echo     git -C website push -u origin %BRANCH% --force
echo.
echo   Then enable GitHub Pages:
echo     1. Go to https://github.com/%GITHUB_USER%/%REPO_NAME%/settings/pages
echo     2. Source: Deploy from a branch
echo     3. Branch: %BRANCH% / (root)
echo     4. Save
echo.
echo   Your site will be live at:
echo     https://%GITHUB_USER%.github.io/%REPO_NAME%/
echo.
echo   Or use Cloudflare Pages for a custom domain:
echo     1. Log into Cloudflare Dashboard
echo     2. Workers & Pages ^> Create ^> Connect to Git
echo     3. Select this repo, branch: %BRANCH%, directory: website/
echo     4. Deploy
echo.
pause
