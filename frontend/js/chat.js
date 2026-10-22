/**
 * CineAgent AI - Chat & ReAct Agent Orchestration Controller
 */

class ChatManager {
  constructor() {
    this.messagesContainer = document.getElementById("chat-messages");
    this.inputForm = document.getElementById("chat-input-form");
    this.textInput = document.getElementById("chat-input");
    this.thinkingIndicator = document.getElementById("agent-thinking");
    this.btnClearChat = document.getElementById("btn-clear-chat");
    this.quickPromptChips = document.querySelectorAll(".prompt-chip");
    this.sessionId = "session_" + Math.random().toString(36).substring(2, 9);

    this.init();
  }

  init() {
    this.inputForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = this.textInput.value.trim();
      if (!text) return;
      this.sendMessage(text);
      this.textInput.value = "";
    });

    this.quickPromptChips.forEach(chip => {
      chip.addEventListener("click", () => {
        const prompt = chip.dataset.prompt;
        this.sendMessage(prompt);
      });
    });

    this.btnClearChat.addEventListener("click", () => {
      this.sessionId = "session_" + Math.random().toString(36).substring(2, 9);
      this.messagesContainer.innerHTML = `
        <div class="message-bubble agent-message">
          <div class="bubble-header">
            <span class="name">CineAgent</span>
            <span class="time">Just now</span>
          </div>
          <div class="bubble-content">
            🔄 Session reset. I am ready to help you explore movies, reserve seats, or manage tickets!
          </div>
        </div>
      `;
    });
  }

  async sendMessage(userMessage) {
    this.appendUserMessage(userMessage);
    this.showThinking(true);

    try {
      const payload = {
        message: userMessage,
        session_id: this.sessionId,
        current_movie_id: window.cinemaState ? window.cinemaState.activeMovieId : null,
        current_showtime_id: window.cinemaState ? window.cinemaState.activeShowtimeId : null
      };

      const res = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      this.showThinking(false);
      this.appendAgentMessage(data.reply, data.tool_calls || []);

      // Execute UI Action requested by the Agent
      if (data.ui_action) {
        this.handleUIAction(data.ui_action);
      }
    } catch (err) {
      this.showThinking(false);
      this.appendAgentMessage("⚠️ Sorry, I encountered a temporary connection issue. Please try again.");
      console.error("Agent chat error:", err);
    }
  }

  appendUserMessage(text) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble user-message";
    bubble.innerHTML = `
      <div class="bubble-header">
        <span class="name">You</span>
        <span class="time">${this.formatCurrentTime()}</span>
      </div>
      <div class="bubble-content">${this.escapeHTML(text)}</div>
    `;
    this.messagesContainer.appendChild(bubble);
    this.scrollToBottom();
  }

  appendAgentMessage(text, toolCalls = []) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble agent-message";

    let toolBadgesHTML = "";
    if (toolCalls && toolCalls.length > 0) {
      toolBadgesHTML = toolCalls.map(tc => `
        <div class="tool-trace-badge">
          <div class="tool-trace-summary" onclick="this.nextElementSibling.classList.toggle('open'); this.parentElement.classList.toggle('expanded');">
            <span>⚡ <strong>${tc.tool_name}</strong></span>
            <span>${tc.execution_time_ms}ms ▾</span>
          </div>
          <div class="tool-trace-details" style="display:none;">
            <strong>Args:</strong> ${JSON.stringify(tc.arguments, null, 2)}
            <br>
            <strong>Result:</strong> ${JSON.stringify(tc.result, null, 2)}
          </div>
        </div>
      `).join("");
    }

    bubble.innerHTML = `
      <div class="bubble-header">
        <span class="name">CineAgent</span>
        <span class="time">${this.formatCurrentTime()}</span>
      </div>
      <div class="bubble-content">${this.parseMarkdown(text)}</div>
      ${toolBadgesHTML}
    `;

    // Add click listeners to collapsible tool traces
    bubble.querySelectorAll(".tool-trace-summary").forEach(header => {
      header.addEventListener("click", () => {
        const details = header.nextElementSibling;
        details.style.display = details.style.display === "none" ? "block" : "none";
      });
    });

    this.messagesContainer.appendChild(bubble);
    this.scrollToBottom();
  }

  handleUIAction(action) {
    if (!action || !action.type) return;

    if (action.type === "SELECT_SHOWTIME") {
      if (action.movie_id && window.selectMovie) {
        window.selectMovie(action.movie_id, action.movie_title);
      }
      if (action.showtime_id && window.cinemaState) {
        window.cinemaState.activeShowtimeId = action.showtime_id;
        window.fetchSeatMap(action.showtime_id);
      }
    } else if (action.type === "SELECT_SEATS") {
      if (window.cinemaState && action.seat_ids) {
        window.cinemaState.selectedSeats = [...action.seat_ids];
        if (window.cinemaState.seatMap) {
          // Trigger visual selection update
          document.querySelectorAll(".seat-btn").forEach(btn => {
            const isSelected = action.seat_ids.includes(btn.dataset.id);
            btn.classList.toggle("selected", isSelected);
          });
        }
        // Recalculate pricing
        const summaryTotal = document.getElementById("summary-total");
        const summarySeats = document.getElementById("summary-seats");
        summarySeats.textContent = action.seat_ids.join(", ");
        fetch("/api/pricing", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            showtime_id: action.showtime_id || window.cinemaState.activeShowtimeId,
            seat_ids: action.seat_ids,
            promo_code: window.cinemaState.appliedPromo
          })
        }).then(r => r.json()).then(p => {
          summaryTotal.textContent = `$${p.total_amount.toFixed(2)}`;
          document.getElementById("btn-checkout").disabled = false;
        });
      }
    } else if (action.type === "BOOKING_CONFIRMED") {
      if (window.showBoardingPass && action.booking) {
        window.showBoardingPass(action.booking);
      }
    } else if (action.type === "PROMO_APPLIED") {
      if (window.cinemaState && action.pricing && action.pricing.promo_info) {
        window.cinemaState.appliedPromo = action.pricing.promo_info.code;
        const promoDisplayCol = document.getElementById("promo-display-col");
        const summaryDiscount = document.getElementById("summary-discount");
        const summaryTotal = document.getElementById("summary-total");
        promoDisplayCol.style.display = "flex";
        summaryDiscount.textContent = `-$${action.pricing.discount.toFixed(2)}`;
        summaryTotal.textContent = `$${action.pricing.total_amount.toFixed(2)}`;
      }
    } else if (action.type === "REFRESH_SEATS") {
      if (window.cinemaState && window.cinemaState.activeShowtimeId) {
        window.fetchSeatMap(window.cinemaState.activeShowtimeId);
      }
    }
  }

  showThinking(isThinking) {
    this.thinkingIndicator.style.display = isThinking ? "flex" : "none";
    if (isThinking) this.scrollToBottom();
  }

  scrollToBottom() {
    setTimeout(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }, 50);
  }

  formatCurrentTime() {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  escapeHTML(str) {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
  }

  parseMarkdown(str) {
    if (!str) return "";
    let html = this.escapeHTML(str);
    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic *text* or _text_
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.*?)_/g, '<em>$1</em>');
    // Inline code `text`
    html = html.replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.1); padding:2px 5px; border-radius:3px; font-family:var(--font-mono); font-size:12px;">$1</code>');
    // Bullet points
    html = html.replace(/^\s*[•\-\*]\s+(.*)$/gm, '<li style="margin-left:16px;">$1</li>');
    // Line breaks
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }
}

// Instantiate global chat manager
document.addEventListener("DOMContentLoaded", () => {
  window.chatManager = new ChatManager();
});
