// Qwen Cloud Voice AI Customer Support Dashboard Logic
document.addEventListener("DOMContentLoaded", () => {
    let ws = null;
    let isConnected = false;
    let isSpeaking = false;

    // Elements
    const connectBtn = document.getElementById("connectBtn");
    const speechToggleBtn = document.getElementById("speechToggleBtn");
    const userInput = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");
    const resetDbBtn = document.getElementById("resetDbBtn");
    const refreshOrdersBtn = document.getElementById("refreshOrdersBtn");
    const agentStatusLabel = document.getElementById("agentStatusLabel");
    const avatarRing = document.getElementById("avatarRing");
    const transcriptFeed = document.getElementById("transcriptFeed");
    const toolLogList = document.getElementById("toolLogList");
    const ordersList = document.getElementById("ordersList");
    const faqsList = document.getElementById("faqsList");

    // Audio Visualizer Setup
    const canvas = document.getElementById("visualizer");
    const ctx = canvas.getContext("2d");
    let animId = null;
    drawIdleWaveform();

    // Tab Switching
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(btn.dataset.tab).classList.add("active");
        });
    });

    // Quick Prompt Chips
    document.querySelectorAll(".prompt-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const text = chip.dataset.text;
            if (isConnected && ws) {
                sendUserMessage(text);
            } else {
                userInput.value = text;
            }
        });
    });

    // Connect WebSocket
    connectBtn.addEventListener("click", () => {
        if (!isConnected) {
            connectWebSocket();
        } else {
            disconnectWebSocket();
        }
    });

    // Send Message
    sendBtn.addEventListener("click", () => {
        if (userInput.value.trim()) {
            sendUserMessage(userInput.value.trim());
            userInput.value = "";
        }
    });

    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && userInput.value.trim()) {
            sendUserMessage(userInput.value.trim());
            userInput.value = "";
        }
    });

    // Voice Speech Recognition (Web Speech API input)
    let recognition = null;
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            sendUserMessage(transcript);
            speechToggleBtn.classList.remove("active");
        };

        recognition.onerror = () => {
            speechToggleBtn.classList.remove("active");
        };
    }

    speechToggleBtn.addEventListener("click", () => {
        if (!recognition) {
            alert("Speech recognition is not supported in this browser. Try Chrome/Edge.");
            return;
        }
        speechToggleBtn.classList.add("active");
        agentStatusLabel.textContent = "Listening to your microphone...";
        recognition.start();
    });

    // Reset Demo Database
    resetDbBtn.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/reset-db", { method: "POST" });
            const data = await res.json();
            alert(data.message);
            loadOrders();
            loadFaqs();
        } catch (err) {
            console.error("Failed to reset database:", err);
        }
    });

    refreshOrdersBtn.addEventListener("click", loadOrders);

    // Initial load
    loadOrders();
    loadFaqs();

    function connectWebSocket() {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/browser-stream`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            isConnected = true;
            connectBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
                Disconnect
            `;
            connectBtn.style.background = "#ef4444";
            userInput.disabled = false;
            sendBtn.disabled = false;
            speechToggleBtn.disabled = false;
            agentStatusLabel.textContent = "Connected to Qwen Cloud";
            startActiveWaveform();
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleAgentEvent(data);
        };

        ws.onclose = () => {
            disconnectWebSocket();
        };
    }

    function disconnectWebSocket() {
        if (ws) {
            ws.close();
            ws = null;
        }
        isConnected = false;
        connectBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
            Connect Simulator
        `;
        connectBtn.style.background = "";
        userInput.disabled = true;
        sendBtn.disabled = true;
        speechToggleBtn.disabled = true;
        agentStatusLabel.textContent = "Disconnected";
        avatarRing.classList.remove("speaking");
        drawIdleWaveform();
    }

    function sendUserMessage(text) {
        if (!isConnected || !ws) return;
        ws.send(JSON.stringify({ type: "user_message", text }));
    }

    function handleAgentEvent(data) {
        switch (data.type) {
            case "status":
                agentStatusLabel.textContent = data.label || data.state;
                if (data.state === "agent_speaking") {
                    avatarRing.classList.add("speaking");
                } else {
                    avatarRing.classList.remove("speaking");
                }
                break;

            case "transcript":
                appendTranscriptBubble(data.speaker, data.text);
                break;

            case "tool_call":
                appendToolCallCard(data);
                if (data.status === "completed") {
                    loadOrders(); // Auto refresh DB if an order was modified
                }
                break;

            case "audio_speech":
                // Play spoken text using Web Speech API synthesis for instant response
                playSpeechResponse(data.text);
                break;
        }
    }

    function playSpeechResponse(text) {
        if ("speechSynthesis" in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = "en-US";
            utterance.rate = 1.05;
            utterance.pitch = 1.0;
            avatarRing.classList.add("speaking");

            utterance.onend = () => {
                avatarRing.classList.remove("speaking");
                agentStatusLabel.textContent = "Listening to caller...";
            };
            window.speechSynthesis.speak(utterance);
        }
    }

    function appendTranscriptBubble(speaker, text) {
        const empty = transcriptFeed.querySelector(".transcript-empty");
        if (empty) empty.remove();

        const bubble = document.createElement("div");
        bubble.className = `msg-bubble ${speaker}`;
        bubble.innerHTML = `
            <div class="msg-header">
                <span>${speaker === "user" ? "Human Caller" : "Nova (Qwen Cloud Agent)"}</span>
                <span>${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
            </div>
            <div class="msg-body">${text}</div>
        `;
        transcriptFeed.appendChild(bubble);
        transcriptFeed.scrollTop = transcriptFeed.scrollHeight;
    }

    function appendToolCallCard(data) {
        const empty = toolLogList.querySelector(".empty-state");
        if (empty) empty.remove();

        const cardId = `tool-${data.tool_name}-${Date.now()}`;
        const card = document.createElement("div");
        card.className = "tool-card";
        card.id = cardId;
        card.innerHTML = `
            <div class="tool-card-header">
                <span class="tool-name">⚡ ${data.tool_name}()</span>
                <span class="tool-status">${data.status.toUpperCase()}</span>
            </div>
            <div class="tool-args">args: ${JSON.stringify(data.arguments)}</div>
            ${data.result ? `<div class="tool-result">result: ${JSON.stringify(data.result)}</div>` : ""}
        `;
        toolLogList.prepend(card);
    }

    async function loadOrders() {
        try {
            const res = await fetch("/api/orders");
            const data = await res.json();
            const html = `
                <table>
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Customer</th>
                            <th>Status</th>
                            <th>Carrier</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.orders.map(o => `
                            <tr>
                                <td><strong>${o.order_id}</strong></td>
                                <td>${o.customer_name}</td>
                                <td><span class="status-pill ${o.status.replace(/\s+/g, ".")}">${o.status}</span></td>
                                <td>${o.carrier} (${o.tracking_number.slice(-4)})</td>
                                <td>$${o.total_amount.toFixed(2)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `;
            ordersList.innerHTML = html;
        } catch (err) {
            console.error("Failed to load orders:", err);
        }
    }

    async function loadFaqs() {
        try {
            const res = await fetch("/api/faqs");
            const data = await res.json();
            faqsList.innerHTML = data.faqs.map(f => `
                <div class="faq-card">
                    <h4>💬 ${f.question}</h4>
                    <p>${f.answer}</p>
                </div>
            `).join("");
        } catch (err) {
            console.error("Failed to load faqs:", err);
        }
    }

    function drawIdleWaveform() {
        if (animId) cancelAnimationFrame(animId);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "rgba(59, 130, 246, 0.4)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
    }

    function startActiveWaveform() {
        let phase = 0;
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = "#10b981";
            ctx.lineWidth = 2.5;
            ctx.beginPath();

            for (let x = 0; x <= canvas.width; x += 5) {
                const amp = avatarRing.classList.contains("speaking") ? 14 : 4;
                const y = canvas.height / 2 + Math.sin((x + phase) * 0.05) * amp * Math.sin(x * 0.02);
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            phase += 3;
            animId = requestAnimationFrame(animate);
        }
        animate();
    }
});
