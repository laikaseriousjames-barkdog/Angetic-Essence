# 🛡️ Angetic Essence — Local Autonomous AI Agent Cyberdeck

Angetic Essence is a robust, local multi-agent orchestration console built for system engineers, security auditors, and QA automators. Three autonomous agents (Donald Knuth, Ada Lovelace, and Alan Turing) collaborate concurrently to execute system diagnostics, run security audits within a sandboxed Kali Linux VM, and perform mobile QA via an Android Debug Bridge (ADB) controller.

🔗 **Official Landing Page (Live on GitHub Pages):**  
[https://laikaseriousjames-barkdog.github.io/Angetic-Essence/](https://laikaseriousjames-barkdog.github.io/Angetic-Essence/)

---

## ⚡ Quick Start (Windows)

Choose one of the following methods to start Angetic Essence:

### Method A: Standalone Executable (No Python Required)
You can directly run the pre-built desktop application launcher.
1. Navigate to the `dist/` directory.
2. Double-click [AngeticEssence.exe](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/dist/AngeticEssence.exe).
3. The dashboard server will start, and your web browser will automatically open to `http://127.0.0.1:5000`.

### Method B: Launching via Batch Scripts (Python Environment)
If you have python or a virtual environment set up, you can launch via the following helper scripts. They automatically detect local virtual environments (`.venv/`) and system `python`/`py` commands:

*   **[launcher.bat](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/launcher.bat)**: Double-click to start the standard Command Center dashboard and open the browser.
*   **[ae.bat](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/ae.bat)**: Launches the core agent reasoning engine and the dashboard in User/Freemium Mode.
*   **[ae1.bat](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/ae1.bat)**: Launches Owner Mode, running the local licensing server, the autonomous agent watchdog, and the dashboard.

---

## 💼 Commercial & Licensing Setup

Angetic Essence has two main operating modes: **Freemium Mode** (locked VM/ADB bridges) and **Pro Mode** (unlocked system capabilities). For commercial use, you can activate Pro features in two ways:

### 1. Developer Bypass (Offline Dev Mode)
To bypass the license validator for development or testing:
1. Open [ae.bat](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/ae.bat) or set the environment variable:
   ```cmd
   set AE_DEV_MODE=true
   ```
2. Run the application. The terminal will log `[DEV MODE] Bypassing license validation` and unlock all system bridges.

### 2. Self-Hosted License Server (Production Commercial Use)
To host your own license server and generate private, cryptographically verified commercial keys:
1. Double-click [ae1.bat](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/ae1.bat) to launch the licensing server on `http://127.0.0.1:8080`.
2. Generate a commercial license key by sending a POST request to your local `/admin/generate` endpoint:
   ```bash
   curl -X POST http://127.0.0.1:8080/admin/generate \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer change-me-in-production" \
        -d "{\"email\":\"commercial@yourcompany.com\", \"tier\":\"perpetual\", \"name\":\"Commercial User\"}"
   ```
   This will return a custom, signed `license_key`.
3. Open [config.yaml](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/config.yaml) in the application directory and configure the key and validation URL:
   ```yaml
   license:
     key: "YOUR_GENERATED_KEY"
     validation_url: "http://127.0.0.1:8080/validate"
   ```
4. Restart the application. It will cryptographically validate against your self-hosted server and display a green `FULL ACCESS` badge.

---

## 🛠️ Hardened Build System

If you make modifications to the source code, you can build a standalone executable:
1. Ensure dependencies are installed in your virtual environment.
2. Run the build script:
   ```cmd
   py build_exe.py
   ```
   This compiles a hardened single-file executable to the `dist/` folder and includes all necessary hidden imports (such as Flask, PyAutoGUI, Stripe, PIL, Eventlet, and SocketIO).

---

## 📁 Repository Structure

*   [website/](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/website) — The project landing page source, deployed to GitHub Pages.
*   [core/](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/core) — Agent reasoning, system trace monitoring, sandbox manager, and licensing.
*   [agents/](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/agents) — Knuth (Developer), Lovelace (Tester), and Turing (Critic/Researcher).
*   [vm/](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/vm) — Kali Linux VM integration bridges.
*   [android/](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/android) — Android Debug Bridge (ADB) device automations.
*   [license_server/](file:///c:/Users/evosp/Downloads/angeticbackup/agent_zero/license_server) — Crypto-signed license server backend.
