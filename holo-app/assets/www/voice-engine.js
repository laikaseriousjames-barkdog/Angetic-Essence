/**
 * Agentic Hologram — Voice Control & Real-Time Conversational Engine
 * Continuous Voice-First Turn-Taking // Audio Reactive Lip-Sync // Speech Recognition
 */

window.HoloVoice = (function() {
    let recognition = null;
    let isListening = false;
    let isSpeaking = false;
    let isContinuous = true;
    let currentSpeechText = '';
    let speechSilenceTimer = null;
    let audioAnimInterval = null;

    // DOM References
    let orbContainer, orbCore, voiceStatusLabel, transcriptText, transcriptSpeaker, eqBars;

    function init() {
        orbContainer = document.querySelector('.voice-orb-container');
        orbCore = document.getElementById('orbCore');
        voiceStatusLabel = document.getElementById('voiceStatusLabel');
        transcriptText = document.getElementById('transcriptText');
        transcriptSpeaker = document.getElementById('transcriptSpeaker');
        eqBars = document.getElementById('eqBars');

        initSpeechRecognition();
        
        // Auto-start continuous listening after brief pause
        setTimeout(() => {
            if (isContinuous && !isListening && !isSpeaking) {
                startListening();
            }
        }, 1200);
    }

    function initSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
            recognition = new SpeechRec();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                isListening = true;
                updateVoiceState('listening');
            };

            recognition.onresult = (event) => {
                let interim = '';
                let final = '';

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript;
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }

                const spoken = (final || interim).trim();
                if (spoken) {
                    showTranscript('OPERATOR', spoken);
                    pulseEqualizer(true);

                    // Silence detection timeout for auto-dispatching speech turns
                    clearTimeout(speechSilenceTimer);
                    speechSilenceTimer = setTimeout(() => {
                        if (spoken.length > 1) {
                            handleVoiceInput(spoken);
                        }
                    }, 1400);
                }
            };

            recognition.onerror = (event) => {
                if (event.error !== 'no-speech') {
                    console.log("[HoloVoice] Speech error:", event.error);
                }
                pulseEqualizer(false);
            };

            recognition.onend = () => {
                isListening = false;
                pulseEqualizer(false);
                // If continuous mode is on and we are not currently speaking, re-open listening
                if (isContinuous && !isSpeaking) {
                    setTimeout(() => {
                        try {
                            if (!isListening && !isSpeaking) recognition.start();
                        } catch (e) {}
                    }, 400);
                } else if (!isSpeaking) {
                    updateVoiceState('idle');
                }
            };
        } else {
            console.log("[HoloVoice] Web Speech API not supported; using native bridge fallback.");
        }
    }

    function startListening() {
        if (isSpeaking) {
            stopSpeaking();
        }

        // Native Android Bridge SpeechRecognizer
        if (window.HoloBridge && window.HoloBridge.startNativeVoiceRecognition) {
            window.HoloBridge.startNativeVoiceRecognition();
            isListening = true;
            updateVoiceState('listening');
            return;
        }

        // Browser Web Speech API
        if (recognition) {
            try {
                recognition.start();
            } catch (e) {
                // If already started, ignore
            }
        } else {
            updateVoiceState('listening');
            showTranscript('OPERATOR', 'Listening...');
        }
    }

    function stopListening() {
        if (window.HoloBridge && window.HoloBridge.stopNativeVoiceRecognition) {
            window.HoloBridge.stopNativeVoiceRecognition();
        }
        if (recognition) {
            try { recognition.stop(); } catch (e) {}
        }
        isListening = false;
        pulseEqualizer(false);
        updateVoiceState('idle');
    }

    function toggleListening() {
        if (isListening) {
            stopListening();
        } else {
            startListening();
        }
    }

    // ========================================================
    // VOICE TURN DISPATCHER & NATURAL INTENT ROUTING
    // ========================================================
    async function handleVoiceInput(rawText) {
        const text = rawText.trim();
        if (!text) return;

        stopListening();
        updateVoiceState('processing');
        showTranscript('OPERATOR', text);

        const lower = text.toLowerCase();

        // 1. Direct voice persona switching
        if (lower.includes('switch to turing') || lower === 'turing' || lower.includes('activate turing')) {
            window.switchPersona('turing');
            speakAgent("Alan Turing online. What formal system shall we analyze?");
            return;
        }
        if (lower.includes('switch to swarm') || lower === 'swarm' || lower.includes('activate swarm') || lower.includes('hey swarm')) {
            window.switchPersona('swarm');
            speakAgent("Agentic Swarm online. Ready for tactical directives.");
            return;
        }
        if (lower.includes('switch to knuth') || lower === 'knuth' || lower.includes('activate knuth')) {
            window.switchPersona('knuth');
            speakAgent("Donald Knuth online. What algorithms shall we craft?");
            return;
        }
        if (lower.includes('switch to lovelace') || lower === 'lovelace' || lower.includes('activate lovelace')) {
            window.switchPersona('lovelace');
            speakAgent("Ada Lovelace online. What poetry of science shall we explore?");
            return;
        }

        // 2. Spatial card dismissal by voice
        if (lower.includes('dismiss') || lower.includes('clear tasks') || lower.includes('clear cards') || lower === 'close') {
            SpatialTasks.clearAll();
            speakAgent("Spatial tasks dismissed.");
            return;
        }

        // 3. Direct hardware query interception
        if (lower.includes('scan wifi') || lower.includes('wi-fi scan') || lower.includes('scan networks')) {
            const res = executeHardware('wifi scan');
            SpatialTasks.spawnTerminalCard('wifi scan', res);
            speakAgent("Scanning wireless environment. Telemetry card materialized.");
            return;
        }
        if (lower.includes('battery') || lower.includes('power state')) {
            const res = executeHardware('battery');
            SpatialTasks.spawnTelemetryCard('Power Subsystem', { "Battery State": res, "Charging": "USB", "Status": "Optimal" });
            speakAgent(res);
            return;
        }
        if (lower.includes('flashlight on') || lower.includes('torch on')) {
            executeHardware('torch on');
            speakAgent("Torch enabled.");
            return;
        }
        if (lower.includes('flashlight off') || lower.includes('torch off')) {
            executeHardware('torch off');
            speakAgent("Torch disabled.");
            return;
        }

        // 4. Conversational Turn & Tool Synthesis via Cognitive Swarm
        if (window.HoloBrain && window.HoloBrain.processTurn) {
            await window.HoloBrain.processTurn(text);
        } else {
            speakAgent("Online and standing by.");
        }
    }

    function executeHardware(cmd) {
        if (window.HoloBridge && window.HoloBridge.runShellCommand) {
            return window.HoloBridge.runShellCommand(cmd);
        }
        return "Hardware command executed: " + cmd;
    }

    // ========================================================
    // PHYSICAL AGENT VOICE SYNTHESIS & LIP-SYNC
    // ========================================================
    function speakAgent(text) {
        if (!text) return;
        isSpeaking = true;
        updateVoiceState('speaking');
        
        const persona = window.state ? window.state.persona : 'swarm';
        const personaName = (persona || 'Swarm').toUpperCase();
        showTranscript(personaName, text);

        // Animate 3D hologram lip-sync & audio energy
        startHoloLipSync();

        // 1. Native Android TTS via HoloBridge
        if (window.HoloBridge && window.HoloBridge.speakPersona) {
            window.HoloBridge.speakPersona(text, persona);

            // Poll for when speaking ends
            const checkEnd = setInterval(() => {
                if (window.HoloBridge.isSpeaking && !window.HoloBridge.isSpeaking()) {
                    clearInterval(checkEnd);
                    onSpeechFinished();
                }
            }, 250);

            // Safety timeout based on word count
            const words = text.split(/\s+/).length;
            const approxDurationMs = Math.max(1600, words * 380);
            setTimeout(() => {
                clearInterval(checkEnd);
                onSpeechFinished();
            }, approxDurationMs);
            return;
        }

        // 2. Fallback Web Speech Synthesis
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const clean = text.replace(/<[^>]*>/g, '').replace(/```[\s\S]*?```/g, '').replace(/[#*_`]/g, '');
            const utterance = new SpeechSynthesisUtterance(clean);
            
            // Set persona voice pitch/rate
            if (persona === 'swarm') { utterance.pitch = 0.85; utterance.rate = 1.05; }
            else if (persona === 'turing') { utterance.pitch = 1.0; utterance.rate = 0.98; }
            else if (persona === 'knuth') { utterance.pitch = 0.92; utterance.rate = 0.95; }
            else if (persona === 'lovelace') { utterance.pitch = 1.18; utterance.rate = 1.02; }

            utterance.onend = () => { onSpeechFinished(); };
            utterance.onerror = () => { onSpeechFinished(); };

            window.speechSynthesis.speak(utterance);
        } else {
            setTimeout(onSpeechFinished, 2000);
        }
    }

    function stopSpeaking() {
        isSpeaking = false;
        if (window.HoloBridge && window.HoloBridge.stopSpeaking) {
            window.HoloBridge.stopSpeaking();
        }
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
        stopHoloLipSync();
        updateVoiceState('idle');
    }

    function onSpeechFinished() {
        if (!isSpeaking) return;
        isSpeaking = false;
        stopHoloLipSync();
        updateVoiceState('idle');

        // Automatically resume continuous voice listening for natural turn-taking
        if (isContinuous) {
            setTimeout(() => {
                if (!isListening && !isSpeaking) {
                    startListening();
                }
            }, 600);
        }
    }

    // Audio reactive hologram modulation
    function startHoloLipSync() {
        stopHoloLipSync();
        audioAnimInterval = setInterval(() => {
            // Simulated dynamic speech modulation wave (0.25 to 0.85)
            const level = 0.35 + Math.sin(Date.now() * 0.015) * 0.28 + Math.random() * 0.2;
            if (window.HoloRenderer) {
                window.HoloRenderer.setAudioLevel(level);
            }
            animateEqualizerBars(level);
        }, 60);
    }

    function stopHoloLipSync() {
        if (audioAnimInterval) clearInterval(audioAnimInterval);
        audioAnimInterval = null;
        if (window.HoloRenderer) window.HoloRenderer.setAudioLevel(0);
        animateEqualizerBars(0);
    }

    function animateEqualizerBars(energy) {
        if (!eqBars) return;
        const bars = eqBars.querySelectorAll('.bar');
        bars.forEach((b, i) => {
            if (energy <= 0.05) {
                b.style.height = '4px';
            } else {
                const h = Math.max(4, Math.min(26, Math.sin(Date.now() * 0.02 + i) * 14 * energy + energy * 18));
                b.style.height = `${h}px`;
            }
        });
    }

    function pulseEqualizer(active) {
        if (!eqBars) return;
        const bars = eqBars.querySelectorAll('.bar');
        bars.forEach((b, i) => {
            b.style.height = active ? `${Math.random() * 18 + 6}px` : '4px';
        });
    }

    function updateVoiceState(state) {
        if (!orbContainer || !voiceStatusLabel) return;
        orbContainer.classList.remove('listening', 'speaking', 'processing');

        if (state === 'listening') {
            orbContainer.classList.add('listening');
            voiceStatusLabel.textContent = 'LISTENING...';
            if (window.HoloRenderer) window.HoloRenderer.setAnimationState('listening');
        } else if (state === 'speaking') {
            orbContainer.classList.add('speaking');
            voiceStatusLabel.textContent = 'SPEAKING';
            if (window.HoloRenderer) window.HoloRenderer.setAnimationState('speaking');
        } else if (state === 'processing') {
            orbContainer.classList.add('processing');
            voiceStatusLabel.textContent = 'COMPUTING...';
            if (window.HoloRenderer) window.HoloRenderer.setAnimationState('thinking');
        } else {
            voiceStatusLabel.textContent = 'TAP OR SPEAK';
            if (window.HoloRenderer) window.HoloRenderer.setAnimationState('idle');
        }
    }

    function showTranscript(speaker, text) {
        if (transcriptSpeaker) transcriptSpeaker.textContent = speaker.toUpperCase();
        if (transcriptText) transcriptText.textContent = text;
    }

    // Native bridge callbacks
    function onNativeSpeechResult(text) {
        handleVoiceInput(text);
    }
    function onNativeAudioLevel(rmsdB) {
        const normalized = Math.max(0, Math.min(1, (rmsdB + 2) / 14));
        if (window.HoloRenderer) window.HoloRenderer.setAudioLevel(normalized);
        animateEqualizerBars(normalized);
    }
    function onNativeStateChange(state) {
        updateVoiceState(state);
    }

    return {
        init: init,
        startListening: startListening,
        stopListening: stopListening,
        toggleListening: toggleListening,
        speakAgent: speakAgent,
        stopSpeaking: stopSpeaking,
        injectCommand: function(cmd) { handleVoiceInput(cmd); },
        onNativeSpeechResult: onNativeSpeechResult,
        onNativeAudioLevel: onNativeAudioLevel,
        onNativeStateChange: onNativeStateChange,
        setContinuous: function(val) { isContinuous = val; }
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    window.HoloVoice.init();
});
