# Viral Demo Script Blueprints — Angetic Essence Launch

This document provides step-by-step recording instructions and copywriting blueprints for launching Angetic Essence organically. These scripts are engineered for highly technical audiences on Twitter/X, Hacker News, and Reddit (`r/LocalLLaMA`, `r/selfhosted`, `r/netsec`).

---

## Script 1: "The Network Auditor" (Kali Linux VM Bridge)
**Objective:** Show three local agents collaborating to boot a Kali VM, execute Nmap, analyze port vulnerabilities, and return a clean security diagnostic report in under 60 seconds.

### Stage Directions (What to Record on Screen)
1. **[0:00 - 0:10] Dashboard Boot:** 
   - Start with the dashboard open. Click the **START** button in the header.
   - Show the terminal log scrolling as Knuth, Lovelace, and Turing initialize.
   - Point your cursor to the green **FULL ACCESS** badge to emphasize it is running locally.

2. **[0:10 - 0:25] Command Input & VM Boot:**
   - Switch to the **COMMANDS** tab.
   - Type this instruction in the chat: `/critic /developer run a fast security audit on the local network router at 192.168.1.1` and hit enter.
   - Show the **KALI LINUX VM** card transition to **BOOTING**, then **ONLINE**.

3. **[0:25 - 0:45] Tool Execution:**
   - Show the **Turing** (Critic) agent's status change to "running" and last action change to `Executing kali_exec: nmap -sV -F 192.168.1.1`.
   - Show the virtual terminal console in the dashboard displaying the live Nmap output text streaming.

4. **[0:45 - 1:00] Report Analysis:**
   - Show the chat response from the agent listing the open ports (e.g., Port 80, Port 443, Port 22), identifying the web interface, warning that SSH (Port 22) is open, and giving 3 quick hardening steps.

### Precise Dashboard Terminal Output to Show
```text
[Knuth] Initializing news-based intelligence loop...
[Lovelace] Verification suites booted: pytest-coverage ready.
[Turing] Booting Kali Linux WSL VM...
[Turing] WSL VM Online. IP: 172.21.32.1
[Turing] Executing tool: kali_exec {"command": "nmap -sV -F 192.168.1.1"}
root@kali:~$ nmap -sV -F 192.168.1.1
Starting Nmap 7.94 ( https://nmap.org ) at 2026-06-22 03:10 EST
Nmap scan report for 192.168.1.1
Host is up (0.0050s latency).
Not shown: 98 closed tcp ports (reset)
PORT    STATE SERVICE VERSION
22/tcp  open  ssh     OpenSSH 9.2p1 Debian 2+deb12u2
80/tcp  open  http    nginx 1.22.1

Service info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

[Turing] Analysis complete. 2 ports open. Host is vulnerable to SSH brute-forcing if default keys exist.
```

### Social Copy (The Caption)
*   **Twitter/X**: 
    > Stop sending your infrastructure logs to cloud APIs. 🛠️ Here are 3 local AI agents collaborating inside a sandboxed dashboard to automatically boot a Kali Linux VM, run Nmap, and audit port security. 100% offline, local GGUF backend. #SelfHosting #NetSec #AIAgents
*   **Reddit (r/LocalLLaMA / r/selfhosted)**:
    > **Title:** I built a local multi-agent console that controls a sandboxed Kali Linux VM and Android ADB. No cloud, budget-governed, runs on local models.
    > 
    > **Body:** Hey everyone, I got tired of agent frameworks that only write text. I wanted an agent that can interact with operating systems directly. Angetic Essence launches three historical agents (Knuth, Lovelace, Turing) that run concurrent loops. Under Pro mode, they run tools inside a Kali Linux WSL/Docker container to automate security audits. Standard chat is completely free/local, system-level bridges are unlocked via a cryptographic license key. Check the demo video below.

---

## Script 2: "The Mobile QA Auditor" (Android ADB Bridge)
**Objective:** Show the ADB controller installing an APK file from a URL to a local emulator/device, taking a screenshot, and verifying that the app is active.

### Stage Directions (What to Record on Screen)
1. **[0:00 - 0:10] Android Device Setup:**
   - Show the dashboard open in the **ADB** tab.
   - Click **REFRESH**. Show a local Android device serial number (e.g. `emulator-5554`) display instantly in green under connected devices.

2. **[0:10 - 0:30] Agent Instruction:**
   - Go to the **COMMANDS** tab.
   - Enter this prompt: `/developer install this debug application from http://192.168.1.50/app-debug.apk and verify it opens successfully`
   - Show the developer agent **Knuth**'s last action update to: `install_apk_from_url: http://192.168.1.50/app-debug.apk`

3. **[0:30 - 0:50] Emulator Action (Split Screen / PIP):**
   - If possible, show a picture-in-picture of the Android Emulator window.
   - Show the app downloading in the logs, the install message displaying `Success`, and then the app opening on the emulator.
   - Show **Knuth** executing `adb_screenshot` to capture the emulator's screen.

4. **[0:50 - 1:00] Verify UI Screen Capture:**
   - Switch back to the dashboard's main tab and show the captured screenshot preview displaying in real-time under the **SCREEN PREVIEW** card.
   - Show the agent confirming that the application booted to the login view successfully.

### Precise Dashboard Terminal Output to Show
```text
[Knuth] Executing host-side download: http://192.168.1.50/app-debug.apk
[Knuth] APK downloaded to temp/app-debug.apk (12.4 MB)
[Knuth] Installing package via ADB Bridge...
$ adb -s emulator-5554 install temp/app-debug.apk
Success
[Knuth] Launching package: com.angetic.essence.debug
$ adb -s emulator-5554 shell monkey -p com.angetic.essence.debug 1
[Knuth] Capturing screen verification...
[Knuth] Screenshot saved. Screen Preview matches com.angetic.essence.debug landing view.
```

### Social Copy (The Caption)
*   **Twitter/X**: 
    > Android QA automation using natural language. 📱 Watch our local developer agent download an APK, install it to a running emulator via ADB, launch the app, and capture a screen preview to confirm the build is healthy. All controlled from a local agent dashboard. #AndroidDev #QAAutomation #AIAgents
*   **Reddit (r/androiddev / r/QAAutomations)**:
    > **Title:** Local AI agent framework that automatically controls real Android devices and emulators.
    > 
    > **Body:** We built an ADB bridge into a local multi-agent dashboard. Instead of writing boilerplate Appium or python-adb scripts, you can chat with the agents directly to fetch latest APK builds from your staging servers, install them, execute basic shell commands, and take verification screenshots. Runs offline on your local rig. Let me know what you think of this workflow!
