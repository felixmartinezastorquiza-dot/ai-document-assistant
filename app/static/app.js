// Chat UI: sends questions to POST /chat and renders answers with their sources.
// All server text is inserted with textContent (never innerHTML) to prevent XSS.

const messages = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("question");
const sendButton = document.getElementById("send");
const chips = document.querySelectorAll(".chip");

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function addMessage(role, text, variant = "") {
  const message = document.createElement("div");
  message.className = `message ${role} ${variant}`.trim();
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  message.appendChild(bubble);
  messages.appendChild(message);
  scrollToBottom();
  return message;
}

function addSources(message, citations) {
  if (!citations.length) return;
  const list = document.createElement("div");
  list.className = "sources";
  for (const citation of citations) {
    const details = document.createElement("details");
    details.className = "source";
    const summary = document.createElement("summary");
    summary.textContent = `📄 Source: ${citation.source}`;
    const excerpt = document.createElement("blockquote");
    excerpt.textContent = citation.excerpt;
    details.append(summary, excerpt);
    list.appendChild(details);
  }
  message.appendChild(list);
  scrollToBottom();
}

function showTyping() {
  const message = document.createElement("div");
  message.className = "message assistant typing";
  message.setAttribute("aria-label", "Assistant is typing");
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.append(...[0, 1, 2].map(() => document.createElement("span")));
  message.appendChild(bubble);
  messages.appendChild(message);
  scrollToBottom();
  return message;
}

function setBusy(busy) {
  input.disabled = busy;
  sendButton.disabled = busy;
  chips.forEach((chip) => (chip.disabled = busy));
  if (!busy) input.focus();
}

function errorMessageFor(status, body) {
  if (status === 422) return "Please write a question between 1 and 500 characters.";
  if (body && typeof body.detail === "string") return body.detail;
  return "Something went wrong. Please try again in a moment.";
}

async function ask(question) {
  question = question.trim();
  if (!question) return;

  addMessage("user", question);
  input.value = "";
  setBusy(true);
  const typing = showTyping();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const body = await response.json().catch(() => null);
    typing.remove();

    if (!response.ok) {
      addMessage("assistant", `⚠️ ${errorMessageFor(response.status, body)}`, "error");
      return;
    }
    const message = addMessage("assistant", body.answer, body.answered ? "" : "not-found");
    addSources(message, body.citations);
  } catch {
    typing.remove();
    addMessage("assistant", "⚠️ Can't reach the server. Check your connection and try again.", "error");
  } finally {
    setBusy(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  ask(input.value);
});

chips.forEach((chip) => chip.addEventListener("click", () => ask(chip.textContent)));

input.focus();
