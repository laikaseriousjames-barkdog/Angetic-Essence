/**
 * Agentic Hologram — Spatial Floating Task Spawner
 * Spawns interactive HUD nodes, terminal streams, and tools out of thin air in 3D
 */

window.SpatialTasks = (function() {
    let container = null;
    let cardCount = 0;

    function getContainer() {
        if (!container) container = document.getElementById('spatial-task-viewport');
        return container;
    }

    function escapeHtml(str) {
        return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    /**
     * Spawns a floating terminal execution card out of thin air
     */
    function spawnTerminalCard(command, output) {
        const c = getContainer();
        if (!c) return;

        cardCount++;
        const cardId = 'task_card_' + cardCount;
        const card = document.createElement('div');
        card.className = 'spatial-task-card';
        card.id = cardId;

        card.innerHTML = `
            <div class="spatial-card-header">
                <div class="spatial-card-title">
                    <span>⚡ TERMINAL EXECUTION</span>
                    <span style="opacity:0.6; font-size:9.5px;">// $ ${escapeHtml(command.slice(0, 30))}</span>
                </div>
                <button class="spatial-close-btn" onclick="SpatialTasks.dismiss('${cardId}')">✕</button>
            </div>
            <div class="spatial-card-body">
                <pre><code>${escapeHtml(output)}</code></pre>
            </div>
        `;

        c.appendChild(card);
        c.scrollTop = c.scrollHeight;
        if (window.HoloBridge && window.HoloBridge.vibrate) HoloBridge.vibrate(20);
        return cardId;
    }

    /**
     * Spawns an interactive synthesized widget out of thin air
     */
    function spawnToolCard(title, htmlCode) {
        const c = getContainer();
        if (!c) return;

        cardCount++;
        const cardId = 'task_tool_' + cardCount;
        const card = document.createElement('div');
        card.className = 'spatial-task-card';
        card.id = cardId;

        // Clean and prepare HTML payload for sandboxed execution
        const safeHtml = htmlCode
            .replace(/```html/gi, '')
            .replace(/```/g, '')
            .trim();

        card.innerHTML = `
            <div class="spatial-card-header">
                <div class="spatial-card-title">
                    <span>🔮 SYNTHESIZED TOOL</span>
                    <span style="opacity:0.8; font-size:10px;">${escapeHtml(title)}</span>
                </div>
                <button class="spatial-close-btn" onclick="SpatialTasks.dismiss('${cardId}')">✕</button>
            </div>
            <div class="spatial-card-body" style="max-height:360px; overflow:hidden;">
                <iframe id="iframe_${cardId}" style="width:100%; height:280px; border:none; border-radius:8px; background:rgba(0,0,0,0.5);" sandbox="allow-scripts allow-forms allow-same-origin allow-modals"></iframe>
            </div>
        `;

        c.appendChild(card);
        c.scrollTop = c.scrollHeight;

        // Inject HTML and script bridges into iframe
        setTimeout(() => {
            const iframe = document.getElementById(`iframe_${cardId}`);
            if (iframe && iframe.contentWindow) {
                const doc = iframe.contentWindow.document;
                doc.open();
                doc.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            body { margin: 0; padding: 12px; background: #04060b; color: #fff; font-family: sans-serif; }
                            button { background: #00f0ff; color: #000; font-weight: bold; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; margin: 4px; }
                            button:active { opacity: 0.7; }
                            input { background: #1a202c; color: #fff; border: 1px solid #4a5568; padding: 6px; border-radius: 4px; }
                        </style>
                    </head>
                    <body>
                        ${safeHtml}
                    </body>
                    </html>
                `);
                doc.close();
            }
        }, 80);

        if (window.HoloBridge && window.HoloBridge.vibrate) HoloBridge.vibrate(35);
        return cardId;
    }

    /**
     * Spawns a floating diagnostic HUD card out of thin air
     */
    function spawnTelemetryCard(title, dataObj) {
        const c = getContainer();
        if (!c) return;

        cardCount++;
        const cardId = 'task_hud_' + cardCount;
        const card = document.createElement('div');
        card.className = 'spatial-task-card';
        card.id = cardId;

        let rowsHtml = '';
        for (const [key, val] of Object.entries(dataObj)) {
            rowsHtml += `<div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px dashed rgba(255,255,255,0.06);">
                <span style="color:#718096;">${escapeHtml(key)}</span>
                <span style="color:#00ff88; font-weight:700;">${escapeHtml(String(val))}</span>
            </div>`;
        }

        card.innerHTML = `
            <div class="spatial-card-header">
                <div class="spatial-card-title">
                    <span>📡 SPATIAL TELEMETRY</span>
                    <span style="opacity:0.8; font-size:10px;">${escapeHtml(title)}</span>
                </div>
                <button class="spatial-close-btn" onclick="SpatialTasks.dismiss('${cardId}')">✕</button>
            </div>
            <div class="spatial-card-body">
                ${rowsHtml}
            </div>
        `;

        c.appendChild(card);
        c.scrollTop = c.scrollHeight;
        if (window.HoloBridge && window.HoloBridge.vibrate) HoloBridge.vibrate(20);
        return cardId;
    }

    /**
     * Dismiss a card with 3D vaporization effect
     */
    function dismiss(cardId) {
        const el = document.getElementById(cardId);
        if (!el) return;
        el.classList.add('dismissing');
        setTimeout(() => {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 380);
    }

    /**
     * Vaporize all spatial task cards
     */
    function clearAll() {
        const c = getContainer();
        if (!c) return;
        const cards = Array.from(c.querySelectorAll('.spatial-task-card'));
        cards.forEach((card, idx) => {
            setTimeout(() => {
                card.classList.add('dismissing');
                setTimeout(() => {
                    if (card.parentNode) card.parentNode.removeChild(card);
                }, 380);
            }, idx * 60);
        });
        if (window.HoloBridge && window.HoloBridge.vibrate) HoloBridge.vibrate(15);
    }

    return {
        spawnTerminalCard: spawnTerminalCard,
        spawnToolCard: spawnToolCard,
        spawnTelemetryCard: spawnTelemetryCard,
        dismiss: dismiss,
        clearAll: clearAll
    };
})();
