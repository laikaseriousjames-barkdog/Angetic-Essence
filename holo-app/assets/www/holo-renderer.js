/**
 * Agentic Hologram — 3D Physical Hologram Rendering Engine
 * Live geometric 3D avatar visualization for Swarm, Turing, Knuth, and Lovelace
 */

window.HoloRenderer = (function() {
    let canvas, ctx;
    let width, height, centerX, centerY;
    let currentPersona = 'swarm';
    let animationState = 'idle'; // 'idle', 'listening', 'thinking', 'speaking'
    let audioEnergy = 0;
    let targetEnergy = 0;
    let rotationAngle = 0;
    let pitchAngle = 0.2;
    let lastFrameTime = 0;
    const FRAME_INTERVAL = 1000 / 60;

    // Atmospheric holographic floating dust
    const PARTICLE_COUNT = 45;
    const particles = [];

    function init() {
        canvas = document.getElementById('holo-stage-canvas');
        if (!canvas) return;
        ctx = canvas.getContext('2d');

        resize();
        window.addEventListener('resize', resize);

        // Init ambient particles
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.4,
                vy: -Math.random() * 0.8 - 0.2, // rise upward like a holo beam
                size: Math.random() * 2 + 1,
                alpha: Math.random() * 0.6 + 0.2,
                pulse: Math.random() * Math.PI
            });
        }

        requestAnimationFrame(renderLoop);
    }

    function resize() {
        if (!canvas) return;
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
        centerX = width / 2;
        centerY = height * 0.44; // elevated center stage
    }

    // 3D Projection math
    function project3D(x, y, z, rotY, rotX) {
        // Rotate around Y
        const cosY = Math.cos(rotY);
        const sinY = Math.sin(rotY);
        const x1 = x * cosY - z * sinY;
        const z1 = z * cosY + x * sinY;

        // Rotate around X
        const cosX = Math.cos(rotX);
        const sinX = Math.sin(rotX);
        const y2 = y * cosX - z1 * sinX;
        const z2 = z1 * cosX + y * sinX;

        // Perspective division
        const fov = 480;
        const distance = 420;
        const scale = fov / (fov + z2 + distance);

        return {
            x: centerX + x1 * scale,
            y: centerY + y2 * scale,
            scale: scale,
            z: z2
        };
    }

    // ==========================================
    // 1. SWARM: Quantum Polyhedron & Swarm Cluster
    // ==========================================
    function drawSwarm(time, glowColor, energy) {
        const baseRadius = 85 + energy * 45;
        const speed = animationState === 'thinking' ? 0.045 : 0.015;
        rotationAngle += speed;

        // Core pulsating sphere
        ctx.beginPath();
        const coreGrad = ctx.createRadialGradient(centerX, centerY, 5, centerX, centerY, 60 + energy * 30);
        coreGrad.addColorStop(0, '#ffffff');
        coreGrad.addColorStop(0.3, glowColor);
        coreGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = coreGrad;
        ctx.arc(centerX, centerY, 60 + energy * 30, 0, Math.PI * 2);
        ctx.fill();

        // 3D Icosahedron / Octahedron vertices
        const vertices = [
            { x: 0, y: -baseRadius, z: 0 },
            { x: 0, y: baseRadius, z: 0 },
            { x: -baseRadius, y: 0, z: 0 },
            { x: baseRadius, y: 0, z: 0 },
            { x: 0, y: 0, z: -baseRadius },
            { x: 0, y: 0, z: baseRadius },
            // Nested ring
            { x: -baseRadius * 0.7, y: -baseRadius * 0.7, z: baseRadius * 0.7 },
            { x: baseRadius * 0.7, y: -baseRadius * 0.7, z: -baseRadius * 0.7 },
            { x: -baseRadius * 0.7, y: baseRadius * 0.7, z: -baseRadius * 0.7 },
            { x: baseRadius * 0.7, y: baseRadius * 0.7, z: baseRadius * 0.7 }
        ];

        const projected = vertices.map(v => project3D(v.x, v.y, v.z, rotationAngle, pitchAngle + Math.sin(time * 0.002) * 0.15));

        // Connect edges
        ctx.strokeStyle = glowColor;
        ctx.lineWidth = 1.6;
        for (let i = 0; i < projected.length; i++) {
            for (let j = i + 1; j < projected.length; j++) {
                const dist = Math.hypot(vertices[i].x - vertices[j].x, vertices[i].y - vertices[j].y, vertices[i].z - vertices[j].z);
                if (dist < baseRadius * 1.5) {
                    ctx.beginPath();
                    ctx.moveTo(projected[i].x, projected[i].y);
                    ctx.lineTo(projected[j].x, projected[j].y);
                    ctx.globalAlpha = Math.min(1, Math.max(0.2, (projected[i].scale + projected[j].scale) * 0.5));
                    ctx.stroke();
                }
            }
        }
        ctx.globalAlpha = 1;

        // Orbiting satellite drones
        const droneCount = 8;
        for (let i = 0; i < droneCount; i++) {
            const angle = time * 0.0025 * (i % 2 === 0 ? 1 : -1) + (i * Math.PI * 2) / droneCount;
            const orbitR = baseRadius * 1.45 + Math.sin(time * 0.004 + i) * 15;
            const dx = Math.cos(angle) * orbitR;
            const dz = Math.sin(angle) * orbitR;
            const dy = Math.sin(time * 0.003 + i) * 35;
            const p = project3D(dx, dy, dz, rotationAngle * 0.5, pitchAngle);

            ctx.beginPath();
            ctx.arc(p.x, p.y, 4.5 * p.scale, 0, Math.PI * 2);
            ctx.fillStyle = '#ffffff';
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = 10;
            ctx.fill();
            ctx.shadowBlur = 0;
        }
    }

    // ==========================================
    // 2. TURING: Algorithmic 4D Tesseract & Logic Matrix
    // ==========================================
    function drawTuring(time, glowColor, energy) {
        const size = 65 + energy * 30;
        rotationAngle += 0.012;
        const wAngle = time * 0.0018; // 4th dimensional rotation

        // 16 vertices of a 4D Hypercube
        const tesseractVerts = [];
        for (let x = -1; x <= 1; x += 2) {
            for (let y = -1; y <= 1; y += 2) {
                for (let z = -1; z <= 1; z += 2) {
                    for (let w = -1; w <= 1; w += 2) {
                        // Rotate in 4D (ZW plane)
                        const cosW = Math.cos(wAngle);
                        const sinW = Math.sin(wAngle);
                        const rotZ = z * cosW - w * sinW;
                        const rotW = w * cosW + z * sinW;

                        // 4D to 3D perspective projection
                        const fov4D = 2.5;
                        const scale4D = fov4D / (fov4D + rotW * 0.55);

                        tesseractVerts.push({
                            x: x * size * scale4D,
                            y: y * size * scale4D,
                            z: rotZ * size * scale4D
                        });
                    }
                }
            }
        }

        const proj = tesseractVerts.map(v => project3D(v.x, v.y, v.z, rotationAngle, 0.25));

        // Connect 4D edges (differ by only 1 coordinate in 4D)
        ctx.strokeStyle = glowColor;
        ctx.lineWidth = 1.4;
        for (let i = 0; i < tesseractVerts.length; i++) {
            for (let j = i + 1; j < tesseractVerts.length; j++) {
                // Check if vertices differ by exactly 1 axis
                let diffs = 0;
                const binaryI = i.toString(2).padStart(4, '0');
                const binaryJ = j.toString(2).padStart(4, '0');
                for (let b = 0; b < 4; b++) {
                    if (binaryI[b] !== binaryJ[b]) diffs++;
                }
                if (diffs === 1) {
                    ctx.beginPath();
                    ctx.moveTo(proj[i].x, proj[i].y);
                    ctx.lineTo(proj[j].x, proj[j].y);
                    ctx.globalAlpha = Math.min(1, (proj[i].scale + proj[j].scale) * 0.45);
                    ctx.stroke();
                }
            }
        }
        ctx.globalAlpha = 1;

        // Glowing Turing logic core
        ctx.beginPath();
        ctx.arc(centerX, centerY, 28 + energy * 18, 0, Math.PI * 2);
        ctx.fillStyle = '#ff007f';
        ctx.shadowColor = '#ff007f';
        ctx.shadowBlur = 24;
        ctx.fill();
        ctx.shadowBlur = 0;
    }

    // ==========================================
    // 3. KNUTH: Computational Fractal Monolith & Compiler Tree
    // ==========================================
    function drawKnuth(time, glowColor, energy) {
        const baseHeight = 110 + energy * 35;
        rotationAngle += 0.01;

        // Central crystalline monolith prism
        const sides = 6;
        const topRadius = 25;
        const bottomRadius = 45;
        const height3D = baseHeight;

        const topVerts = [];
        const botVerts = [];

        for (let i = 0; i < sides; i++) {
            const a = (i * Math.PI * 2) / sides;
            topVerts.push({ x: Math.cos(a) * topRadius, y: -height3D * 0.6, z: Math.sin(a) * topRadius });
            botVerts.push({ x: Math.cos(a) * bottomRadius, y: height3D * 0.6, z: Math.sin(a) * bottomRadius });
        }

        const projTop = topVerts.map(v => project3D(v.x, v.y, v.z, rotationAngle, 0.25));
        const projBot = botVerts.map(v => project3D(v.x, v.y, v.z, rotationAngle, 0.25));

        // Draw crystal facets
        ctx.strokeStyle = glowColor;
        ctx.lineWidth = 1.8;

        // Top cap & Bottom cap
        for (let i = 0; i < sides; i++) {
            const next = (i + 1) % sides;
            // Top ring
            ctx.beginPath();
            ctx.moveTo(projTop[i].x, projTop[i].y);
            ctx.lineTo(projTop[next].x, projTop[next].y);
            ctx.stroke();

            // Bottom ring
            ctx.beginPath();
            ctx.moveTo(projBot[i].x, projBot[i].y);
            ctx.lineTo(projBot[next].x, projBot[next].y);
            ctx.stroke();

            // Vertical pillars
            ctx.beginPath();
            ctx.moveTo(projTop[i].x, projTop[i].y);
            ctx.lineTo(projBot[i].x, projBot[i].y);
            ctx.stroke();
        }

        // Branching binary tree nodes in golden light
        const levels = 3;
        function drawBranch(x, y, z, len, angle, depth) {
            if (depth > levels) return;
            const x2 = x + Math.cos(angle) * len;
            const y2 = y - len * 0.8;
            const z2 = z + Math.sin(angle) * len;

            const p1 = project3D(x, y, z, rotationAngle, 0.25);
            const p2 = project3D(x2, y2, z2, rotationAngle, 0.25);

            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.lineWidth = Math.max(0.8, 3 - depth);
            ctx.strokeStyle = '#ffb700';
            ctx.stroke();

            drawBranch(x2, y2, z2, len * 0.65, angle + 0.65, depth + 1);
            drawBranch(x2, y2, z2, len * 0.65, angle - 0.65, depth + 1);
        }

        drawBranch(0, -height3D * 0.6, 0, 45 + energy * 20, 0, 1);
        drawBranch(0, -height3D * 0.6, 0, 45 + energy * 20, Math.PI, 1);
    }

    // ==========================================
    // 4. LOVELACE: Celestial Analytical Astrolabe
    // ==========================================
    function drawLovelace(time, glowColor, energy) {
        const radius = 95 + energy * 40;
        rotationAngle += 0.014;

        // Three interlocking celestial rings rotating on independent 3D planes
        const RING_SEGMENTS = 36;
        function drawRing(rotXOffset, rotYOffset, rotZOffset, r, color, width) {
            ctx.beginPath();
            for (let i = 0; i <= RING_SEGMENTS; i++) {
                const theta = (i * Math.PI * 2) / RING_SEGMENTS;
                let x = Math.cos(theta) * r;
                let y = Math.sin(theta) * r;
                let z = 0;

                // 3D coordinate rotation
                const p = project3D(x, y, z, rotationAngle + rotYOffset, pitchAngle + rotXOffset);
                if (i === 0) ctx.moveTo(p.x, p.y);
                else ctx.lineTo(p.x, p.y);
            }
            ctx.strokeStyle = color;
            ctx.lineWidth = width;
            ctx.stroke();
        }

        // Equatorial, Meridia, and Oblique rings
        drawRing(0, 0, 0, radius, '#00ff88', 2.2);
        drawRing(Math.PI / 3, time * 0.0015, 0, radius * 0.92, '#ffffff', 1.4);
        drawRing(-Math.PI / 3, -time * 0.0012, 0, radius * 0.85, '#00f0ff', 1.4);

        // Core stellar nucleus
        ctx.beginPath();
        ctx.arc(centerX, centerY, 32 + energy * 20, 0, Math.PI * 2);
        const grad = ctx.createRadialGradient(centerX, centerY, 2, centerX, centerY, 38 + energy * 20);
        grad.addColorStop(0, '#ffffff');
        grad.addColorStop(0.4, '#00ff88');
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.fill();
    }

    // ==========================================
    // RENDER LOOP
    // ==========================================
    function renderLoop(currentTime) {
        requestAnimationFrame(renderLoop);
        if (document.hidden) return; // Battery & GPU save when app is backgrounded
        if (currentTime - lastFrameTime < FRAME_INTERVAL) return;
        lastFrameTime = currentTime;

        ctx.clearRect(0, 0, width, height);

        // Smooth energy interpolation for audio reactivity
        audioEnergy += (targetEnergy - audioEnergy) * 0.22;

        // Render ambient rising particles
        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            if (p.y < 0) {
                p.y = height;
                p.x = Math.random() * width;
            }

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 240, 255, ${p.alpha * 0.4})`;
            ctx.fill();
        }

        // Color mapping per persona
        let glowColor = '#00f0ff';
        if (currentPersona === 'turing') glowColor = '#ff007f';
        else if (currentPersona === 'knuth') glowColor = '#ffb700';
        else if (currentPersona === 'lovelace') glowColor = '#00ff88';

        // Draw the selected active physical hologram
        if (currentPersona === 'swarm') {
            drawSwarm(currentTime, glowColor, audioEnergy);
        } else if (currentPersona === 'turing') {
            drawTuring(currentTime, glowColor, audioEnergy);
        } else if (currentPersona === 'knuth') {
            drawKnuth(currentTime, glowColor, audioEnergy);
        } else if (currentPersona === 'lovelace') {
            drawLovelace(currentTime, glowColor, audioEnergy);
        }
    }

    return {
        init: init,
        setPersona: function(persona) {
            currentPersona = persona.toLowerCase();
        },
        setAnimationState: function(state) {
            animationState = state;
            if (state === 'thinking') targetEnergy = 0.8;
            else if (state === 'speaking') targetEnergy = 0.6;
            else if (state === 'listening') targetEnergy = 0.35;
            else targetEnergy = 0;
        },
        setAudioLevel: function(level) {
            // level between 0 and 1
            targetEnergy = Math.max(0, Math.min(1, level));
        }
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    window.HoloRenderer.init();
});
