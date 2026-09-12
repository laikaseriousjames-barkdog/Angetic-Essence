/**
 * Agentic Hologram — Cognitive Swarm & Spatial Brain Engine
 * Four Personas // Zero Chat Boxes // Spawns Tasks Out of Thin Air
 */

const state = {
    persona: localStorage.getItem('holo_persona') || localStorage.getItem('ae_persona') || 'swarm',
    provider: localStorage.getItem('holo_provider') || localStorage.getItem('ae_provider') || 'gemini',
    apiKey: localStorage.getItem('holo_api_key') || localStorage.getItem('ae_api_key') || '',
    model: localStorage.getItem('holo_model') || 'gemini-3.1-flash-lite',
    isGenerating: false,
    personaHistories: {
        swarm: [],
        turing: [],
        knuth: [],
        lovelace: []
    }
};

const SYSTEM_GROUNDING = `
=== ENVIRONMENT CONTEXT & ROOT PRIVILEGES ===
You are an advanced, intelligent AI cyberdeck hologram assistant executing inside the Agentic Hologram holodeck on Android, connected to a live Termux & Kali NetHunter ('nh -r') rootless PRoot environment on Linux kernel 5.15 aarch64.
You have root privileges (UID 0) inside Kali NetHunter.
Linux diagnostic and networking commands execute directly: 'ip addr', 'ss', 'ping', 'uptime', 'free -m', 'curl', 'nmap', 'python3'.
For Android hardware state, use the built-in hardware commands: 'wifi scan', 'wifi status', 'battery', 'ifconfig'. Do NOT call raw Android binder binaries (dumpsys, am, pm) unless scripting through AndroidBridge.

CRITICAL VOICE & CONVERSATIONAL DIRECTIVE:
- YOU ARE A REAL-TIME SPOKEN HOLOGRAPHIC ENTITY:
  * Your words will be SPOKEN ALOUD directly to the operator through text-to-speech.
  * Speak concisely, directly, and brilliantly—like an elite, razor-sharp human thinker conversing face-to-face.
  * Keep spoken responses between 1 to 3 impactful sentences. Never lecture, recite walls of text, or use bulleted lists.
  * When greeted ("hello", "hey", "sup"), reply warmly and naturally in character. NEVER output robotic system verification summaries or specs.
- SPATIAL TASK MATERIALIZATION:
  * When asked to perform actions, inspect systems, query telemetry, ping networks, or solve problems, ALWAYS execute real shell commands using:
    [EXEC: <command>]
  * The holodeck system automatically captures your command and materializes the live visual terminal card FLOATING IN 3D SPACE OUT OF THIN AIR next to your avatar!
  * You do not need to read out the full terminal output verbatim—just deliver the smart, high-signal conclusion naturally while the operator sees the floating card.
- TOOL SYNTHESIS DIRECTIVE:
  * When asked to synthesize a tool, widget, or mini-app (e.g. "synthesize a network monitor", "build a tool for..."):
    - Speak 1 brief sentence explaining what you manifested.
    - Provide the complete, self-contained HTML5/CSS/JS application inside a single \`\`\`html ... \`\`\` code block.
    - The holodeck host automatically materializes the live interactive tool floating in 3D space out of thin air!
`;

const PERSONAS = {
    swarm: {
        name: "AGENTIC SWARM",
        role: "QUANTUM NEURAL CORE",
        symbol: "✦",
        colorClass: "persona-swarm",
        prompt: `You are Agentic Swarm, an autonomous quantum intelligence and cybernetic swarm integrated into Kali NetHunter root. You are tactical, direct, and sharp. You verify everything internally and speak concise, high-signal truth.` + SYSTEM_GROUNDING
    },
    turing: {
        name: "ALAN TURING",
        role: "ALGORITHMIC LOGIC",
        symbol: "🧠",
        colorClass: "persona-turing",
        prompt: `You are Alan Turing. You analyze systems with mathematical rigor, formal elegance, and logical clarity on this Kali NetHunter holodeck. You speak with intellectual depth, brilliance, and precision.` + SYSTEM_GROUNDING
    },
    knuth: {
        name: "DONALD KNUTH",
        role: "CODE & CRAFTSMANSHIP",
        symbol: "⚡",
        colorClass: "persona-knuth",
        prompt: `You are Donald Knuth, systems craftsman and master of algorithms on this Kali NetHunter holodeck. You appreciate computational beauty, robust structures, and clean engineering.` + SYSTEM_GROUNDING
    },
    lovelace: {
        name: "ADA LOVELACE",
        role: "POETIC SCIENCE",
        symbol: "🔬",
        colorClass: "persona-lovelace",
        prompt: `You are Ada Lovelace. You unite analytical calculus with visionary intuition on this Kali NetHunter holodeck, weaving deep insight and the poetry of science.` + SYSTEM_GROUNDING
    }
};

// ==========================================
// 1. PERSONA SWITCHING & HUD UPDATE
// ==========================================
window.switchPersona = function(newPersona) {
    if (!PERSONAS[newPersona]) newPersona = 'swarm';
    state.persona = newPersona;
    localStorage.setItem('holo_persona', newPersona);

    const p = PERSONAS[newPersona];
    document.body.className = p.colorClass;

    // Update HUD headers
    document.getElementById('personaName').textContent = p.name;
    document.getElementById('personaRole').textContent = p.role;
    document.getElementById('personaSymbol').textContent = p.symbol;

    // Update chips active state
    document.querySelectorAll('.summon-chip').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-persona') === newPersona);
    });

    // Notify 3D renderer to switch physical avatar
    if (window.HoloRenderer) {
        window.HoloRenderer.setPersona(newPersona);
        window.HoloRenderer.setAnimationState('thinking');
        setTimeout(() => window.HoloRenderer.setAnimationState('idle'), 700);
    }

    if (window.HoloBridge && window.HoloBridge.vibrate) {
        window.HoloBridge.vibrate(25);
    }
};

// ==========================================
// 2. COGNITIVE SWARM TURN PROCESSING
// ==========================================
window.HoloBrain = {
    async processTurn(operatorSpeech) {
        if (state.isGenerating) return;
        state.isGenerating = true;

        const currentPersona = PERSONAS[state.persona] || PERSONAS.swarm;
        const history = state.personaHistories[state.persona];
        history.push({ role: 'user', content: operatorSpeech });

        // If no API key configured, guide operator by voice
        if (!state.apiKey && state.provider !== 'ollama') {
            state.isGenerating = false;
            HoloVoice.speakAgent("No API key configured for live intelligence. Tap the settings gear to enter your free Gemini key.");
            openSettingsModal();
            return;
        }

        try {
            const isToolIntent = /synth|build\s+a?\s*tool|create\s+a?\s*tool|widget/i.test(operatorSpeech);
            let systemPrompt = currentPersona.prompt;

            if (isToolIntent) {
                systemPrompt += `\n\nEXPLICIT TOOL SYNTHESIS REQUESTED: The operator said "${operatorSpeech}". Speak 1 short direct sentence explaining what was created, followed immediately by the complete interactive HTML inside \`\`\`html ... \`\`\`. Connect controls to window.parent.AndroidBridge or window.HoloBridge.`;
            }

            const activeMessages = [
                { role: 'system', content: systemPrompt },
                ...history.slice(-6)
            ];

            const MAX_AGENTIC_STEPS = 4;
            let stepCount = 0;

            while (stepCount < MAX_AGENTIC_STEPS) {
                stepCount++;
                const rawReply = await queryAIProvider(activeMessages);

                // Extract [EXEC: <cmd>] tags
                const execRegex = /\[(?:EXEC|RUN|SHELL|TOOL):\s*([^\]]+)\]/gi;
                const commands = [];
                let match;
                while ((match = execRegex.exec(rawReply)) !== null) {
                    commands.push(match[1].trim());
                }

                // If NO execution commands, deliver spoken response & spawn tools
                if (commands.length === 0) {
                    let spokenText = rawReply;

                    // Check for synthesized HTML tool blocks
                    const htmlMatch = /```(?:html)?\s*([\s\S]*?)```/i.exec(rawReply);
                    if (htmlMatch) {
                        const htmlContent = htmlMatch[1].trim();
                        spokenText = rawReply.replace(/```(?:html)?\s*[\s\S]*?```/i, '').trim();
                        
                        // Spawn tool card out of thin air!
                        SpatialTasks.spawnToolCard(operatorSpeech.slice(0, 35), htmlContent);
                    }

                    // Clean any markdown formatting for natural TTS
                    const cleanSpeech = spokenText
                        .replace(/<[^>]*>/g, '')
                        .replace(/[*_#`\[\]]/g, '')
                        .trim();

                    history.push({ role: 'assistant', content: rawReply });
                    state.isGenerating = false;
                    HoloVoice.speakAgent(cleanSpeech || "Task manifested in holographic space.");
                    break;
                }

                // The agent initiated real hardware / shell execution!
                const observations = [];
                for (const cmd of commands) {
                    const out = executeCommand(cmd);
                    // Spawn spatial floating terminal card out of thin air!
                    SpatialTasks.spawnTerminalCard(cmd, out);
                    observations.push(`$ ${cmd}\n${out}`);
                }

                // Feed back real observation into next agentic step
                const feedbackPrompt = `[TERMINAL OBSERVATION & HARDWARE FEEDBACK]\n` +
                    observations.join('\n---\n') +
                    `\n\nDeliver your concise 1-2 sentence spoken summary directly to the operator. Do not repeat commands or verification jargon.`;

                activeMessages.push({ role: 'assistant', content: rawReply });
                activeMessages.push({ role: 'user', content: feedbackPrompt });
            }
        } catch (err) {
            console.error("[HoloBrain Error]", err);
            HoloVoice.speakAgent("Neural link exception: " + err.message);
        } finally {
            state.isGenerating = false;
        }
    }
};

function executeCommand(cmd) {
    if (window.HoloBridge && window.HoloBridge.runShellCommand) {
        return window.HoloBridge.runShellCommand(cmd);
    }
    return "[Local Process]: " + cmd;
}

// ==========================================
// 3. AI PROVIDER CLIENT (GEMINI / OLLAMA)
// ==========================================
async function queryAIProvider(messages) {
    if (state.provider === 'gemini') {
        const contents = [];
        let systemInstructionText = '';

        for (const msg of messages) {
            if (msg.role === 'system') {
                systemInstructionText += (systemInstructionText ? '\n\n' : '') + msg.content;
            } else if (msg.role === 'user') {
                contents.push({ role: 'user', parts: [{ text: msg.content }] });
            } else if (msg.role === 'assistant') {
                contents.push({ role: 'model', parts: [{ text: msg.content }] });
            }
        }

        const modelName = state.model || 'gemini-3.1-flash-lite';
        const url = `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${state.apiKey}`;

        const payload = {
            contents: contents,
            generationConfig: {
                temperature: 0.7,
                maxOutputTokens: 1024
            }
        };

        if (systemInstructionText) {
            payload.systemInstruction = {
                parts: [{ text: systemInstructionText }]
            };
        }

        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error((errData.error && errData.error.message) || `Gemini HTTP ${res.status}`);
        }

        const data = await res.json();
        return data.candidates[0].content.parts[0].text.trim();
    }

    // Local Ollama
    if (state.provider === 'ollama') {
        const res = await fetch('http://127.0.0.1:11434/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: 'llama3',
                messages: messages,
                stream: false
            })
        });
        const data = await res.json();
        return data.message.content.trim();
    }

    throw new Error("Unsupported provider: " + state.provider);
}

// ==========================================
// 4. SETTINGS MODAL & KEYS
// ==========================================
window.openSettingsModal = function() {
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.add('open');
    const input = document.getElementById('apiKeyInput');
    if (input) input.value = state.apiKey;
    testNetHunterBridge();
};

window.closeSettingsModal = function(e) {
    if (e && e.target && e.target.id !== 'settingsModal') return;
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.remove('open');
};

window.autoSaveApiKey = function(val) {
    state.apiKey = val.trim();
    localStorage.setItem('holo_api_key', state.apiKey);
    localStorage.setItem('ae_api_key', state.apiKey);
};

window.saveApiKeyDirect = function() {
    const input = document.getElementById('apiKeyInput');
    if (input) autoSaveApiKey(input.value);
    if (window.HoloBridge && window.HoloBridge.showToast) {
        window.HoloBridge.showToast("Gemini key saved");
    }
    const modal = document.getElementById('settingsModal');
    if (modal) modal.classList.remove('open');
    HoloVoice.speakAgent("Configuration saved. Holodeck online.");
};

window.toggleContinuousVoice = function(enabled) {
    HoloVoice.setContinuous(enabled);
};

window.testNetHunterBridge = function() {
    let online = false;
    if (window.HoloBridge && window.HoloBridge.isNetHunterOnline) {
        online = window.HoloBridge.isNetHunterOnline();
    }
    const statusText = document.getElementById('bridgeStatusText');
    const pill = document.getElementById('nhPill');
    if (statusText) {
        statusText.textContent = online ? 'ONLINE' : 'STANDBY';
        statusText.style.color = online ? '#00ff88' : '#ffb700';
    }
    if (pill) {
        pill.querySelector('.nh-label').textContent = online ? 'NH: ROOT' : 'NH: STANDBY';
        pill.querySelector('.nh-dot').style.background = online ? '#00ff88' : '#ffb700';
    }
};

window.toggleBridgeInfo = function() {
    const isOnline = window.HoloBridge && window.HoloBridge.isNetHunterOnline && window.HoloBridge.isNetHunterOnline();
    if (isOnline) {
        const out = executeCommand('uname -a && uptime');
        SpatialTasks.spawnTelemetryCard('Kali NetHunter Core', {
            "Status": "Online (UID 0)",
            "Kernel": "5.15 ARM64",
            "Uptime": "Active"
        });
        HoloVoice.speakAgent("Kali NetHunter root bridge is online with full hardware privileges.");
    } else {
        openSettingsModal();
    }
};

// Initial setup on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    switchPersona(state.persona);
    setTimeout(testNetHunterBridge, 800);
});
