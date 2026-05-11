const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const questionEl = document.getElementById("question");
const sendButtonEl = document.getElementById("send-button");
const newChatButtonEl = document.getElementById("new-chat-button");
const statusDotEl = document.querySelector(".status-dot");

function appendMessage(role, text) {
	const message = document.createElement("article");
	message.className = `message ${role}`;

	const label = document.createElement("div");
	label.className = "message-label";
	label.textContent = role === "user" ? "You" : "Assistant";

	const body = document.createElement("div");
	body.className = "message-body";
	// Parse markdown
	if (window.marked) {
		body.innerHTML = marked.parse(text);
	} else {
		body.textContent = text;
	}

	message.append(label, body);
	messagesEl.appendChild(message);
	messagesEl.scrollTop = messagesEl.scrollHeight;
	return body;
}

function updateMessage(bodyEl, text) {
	if (window.marked) {
		bodyEl.innerHTML = marked.parse(text);
	} else {
		bodyEl.textContent = text;
	}
	messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setBusy(isBusy) {
	questionEl.disabled = isBusy;
	sendButtonEl.disabled = isBusy;
	sendButtonEl.textContent = isBusy ? "Sending..." : "Send";
}

let sessionId = null;

async function initSession() {
	try {
		const response = await fetch("/api/v1/chat/session", { method: "POST" });
		const data = await response.json();
		sessionId = data.session_id;
	} catch (error) {
		console.error("Failed to initialize session:", error);
	}
}

function resetChat() {
	messagesEl.innerHTML = "";
	sessionId = null;
	initSession();
	appendMessage(
		"assistant",
		"Hello. I can help you inspect ads, creatives, and performance data. Ask me a question to get started."
	);
}

// Initialize session on load
resetChat();

newChatButtonEl.addEventListener("click", () => {
	resetChat();
});

// Auto-resize textarea
questionEl.addEventListener("input", function() {
	this.style.height = "auto";
	this.style.height = (this.scrollHeight) + "px";
});

formEl.addEventListener("submit", async (event) => {
	event.preventDefault();

	const question = questionEl.value.trim();
	if (!question) {
		return;
	}

	appendMessage("user", question);
	questionEl.value = "";
	questionEl.style.height = "auto"; // Reset height
	questionEl.focus();

	const pendingBody = appendMessage("assistant", "Thinking...");
	setBusy(true);

	try {
		if (!sessionId) {
			await initSession();
		}

		const response = await fetch("/api/v1/chat/message", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({ session_id: sessionId, message: question }),
		});

		const data = await response.json();
		if (!response.ok) {
			throw new Error(data.detail || "Unable to reach the chatbot backend.");
		}

		updateMessage(pendingBody, data.response || "No answer returned.");
	} catch (error) {
		updateMessage(pendingBody, error instanceof Error ? error.message : "Unexpected error.");
		pendingBody.parentElement.classList.add("error");
	} finally {
		setBusy(false);
	}
});

questionEl.addEventListener("keydown", (event) => {
	if (event.key === "Enter" && !event.shiftKey) {
		event.preventDefault();
		formEl.requestSubmit();
	}
});

// Health check API polling
async function checkHealth() {
	try {
		// Assuming /api/v1/health is the health endpoint.
		// If it's something else, adjust accordingly.
		const response = await fetch("/api/v1/health", { method: "GET" });
		if (response.ok) {
			statusDotEl.classList.add("connected");
			statusDotEl.parentElement.setAttribute("title", "Backend Status: Connected");
		} else {
			statusDotEl.classList.remove("connected");
			statusDotEl.parentElement.setAttribute("title", "Backend Status: Disconnected");
		}
	} catch (error) {
		statusDotEl.classList.remove("connected");
		statusDotEl.parentElement.setAttribute("title", "Backend Status: Offline");
	}
}

// Check immediately on load, then every 30 seconds
checkHealth();
setInterval(checkHealth, 30000);
