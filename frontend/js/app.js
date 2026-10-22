/**
 * CineAgent AI - Main Application & Cinema Booking State Manager
 */

const state = {
  movies: [],
  activeMovieId: null,
  activeMovieTitle: null,
  showtimes: [],
  activeShowtimeId: null,
  activeShowtime: null,
  seatMap: null,
  selectedSeats: [],
  appliedPromo: null,
  pricing: null,
  activeGenre: ""
};

// DOM Elements
const movieGrid = document.getElementById("movie-grid");
const showtimesSection = document.getElementById("showtimes-section");
const showtimesGrid = document.getElementById("showtimes-grid");
const dateSelector = document.getElementById("date-selector");
const selectedMovieTitle = document.getElementById("selected-movie-title");
const seatingSection = document.getElementById("seating-section");
const seatGridContainer = document.getElementById("seat-grid-container");
const summarySeats = document.getElementById("summary-seats");
const summaryTotal = document.getElementById("summary-total");
const summaryDiscount = document.getElementById("summary-discount");
const promoDisplayCol = document.getElementById("promo-display-col");
const btnCheckout = document.getElementById("btn-checkout");
const btnQuickRecommend = document.getElementById("btn-quick-recommend");

// Dialogs
const modalTicket = document.getElementById("modal-ticket");
const modalBookings = document.getElementById("modal-bookings");
const modalTools = document.getElementById("modal-tools");

// ================= INITIALIZATION =================
document.addEventListener("DOMContentLoaded", () => {
  initGenreFilters();
  initModals();
  fetchMovies();
  fetchToolsCount();

  // Quick Recommend Button
  btnQuickRecommend.addEventListener("click", () => {
    if (window.chatManager) {
      window.chatManager.sendMessage(`Recommend 2 VIP seats for ${state.activeMovieTitle || "Inception"}`);
    }
  });

  // Checkout Button
  btnCheckout.addEventListener("click", () => {
    if (state.selectedSeats.length === 0) return;
    if (window.chatManager) {
      window.chatManager.sendMessage(`Confirm booking for seats ${state.selectedSeats.join(", ")}`);
    } else {
      executeCheckout();
    }
  });
});

// ================= API CALLS =================
async function fetchMovies(genre = "") {
  try {
    const url = genre ? `/api/movies?genre=${encodeURIComponent(genre)}` : "/api/movies";
    const res = await fetch(url);
    const movies = await res.json();
    state.movies = movies;
    renderMovieGrid(movies);

    // Auto-select first movie if none active
    if (!state.activeMovieId && movies.length > 0) {
      selectMovie(movies[0].id, movies[0].title);
    }
  } catch (err) {
    console.error("Failed to load movies:", err);
  }
}

async function fetchShowtimes(movieId) {
  try {
    const res = await fetch(`/api/showtimes?movie_id=${movieId}`);
    const showtimes = await res.json();
    state.showtimes = showtimes;
    renderShowtimes(showtimes);

    if (showtimes.length > 0) {
      selectShowtime(showtimes[0]);
    }
  } catch (err) {
    console.error("Failed to load showtimes:", err);
  }
}

async function fetchSeatMap(showtimeId) {
  try {
    const res = await fetch(`/api/showtimes/${showtimeId}/seats`);
    const data = await res.json();
    state.seatMap = data;
    renderSeatGrid(data);
    updatePricing();
  } catch (err) {
    console.error("Failed to load seat map:", err);
  }
}

async function updatePricing() {
  if (state.selectedSeats.length === 0) {
    summarySeats.textContent = "None";
    summaryTotal.textContent = "$0.00";
    promoDisplayCol.style.display = "none";
    btnCheckout.disabled = true;
    return;
  }

  summarySeats.textContent = state.selectedSeats.join(", ");
  btnCheckout.disabled = false;

  try {
    const res = await fetch("/api/pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        showtime_id: state.activeShowtimeId,
        seat_ids: state.selectedSeats,
        promo_code: state.appliedPromo
      })
    });
    const pricing = await res.json();
    state.pricing = pricing;

    summaryTotal.textContent = `$${pricing.total_amount.toFixed(2)}`;
    if (pricing.discount > 0) {
      promoDisplayCol.style.display = "flex";
      summaryDiscount.textContent = `-$${pricing.discount.toFixed(2)}`;
    } else {
      promoDisplayCol.style.display = "none";
    }
  } catch (err) {
    console.error("Failed to calculate pricing:", err);
  }
}

async function executeCheckout() {
  try {
    const res = await fetch("/api/bookings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        showtime_id: state.activeShowtimeId,
        seat_ids: state.selectedSeats,
        customer_name: "Chiranth C Gutthi",
        customer_email: "chiranthgutthi@gmail.com",
        promo_code: state.appliedPromo,
        payment_method: "Credit Card"
      })
    });
    const booking = await res.json();
    showBoardingPass(booking);
    fetchSeatMap(state.activeShowtimeId);
  } catch (err) {
    alert("Checkout error: " + err.message);
  }
}

// ================= RENDERERS =================
function renderMovieGrid(movies) {
  movieGrid.innerHTML = "";
  movies.forEach(m => {
    const card = document.createElement("div");
    card.className = `movie-card ${m.id === state.activeMovieId ? "active" : ""}`;
    card.dataset.id = m.id;
    card.innerHTML = `
      <div class="poster-wrapper">
        <img src="${m.poster_url}" alt="${m.title}" loading="lazy">
        <div class="rating-badge">★ ${m.rating}</div>
      </div>
      <div class="movie-info">
        <h4>${m.title}</h4>
        <div class="movie-meta">
          <span>${m.release_year}</span> • <span>${m.duration_mins}m</span>
        </div>
        <div class="movie-genres">
          ${m.genre.slice(0, 2).map(g => `<span class="genre-tag">${g}</span>`).join("")}
        </div>
      </div>
    `;
    card.addEventListener("click", () => selectMovie(m.id, m.title));
    movieGrid.appendChild(card);
  });
}

function selectMovie(movieId, title) {
  state.activeMovieId = movieId;
  state.activeMovieTitle = title;
  state.selectedSeats = [];

  document.querySelectorAll(".movie-card").forEach(c => {
    c.classList.toggle("active", c.dataset.id === movieId);
  });

  selectedMovieTitle.textContent = `Showing schedules for ${title}`;
  fetchShowtimes(movieId);
}

function renderShowtimes(showtimes) {
  showtimesGrid.innerHTML = "";
  if (showtimes.length === 0) {
    showtimesGrid.innerHTML = "<p class='subtitle'>No showtimes currently scheduled.</p>";
    return;
  }

  showtimes.forEach(sh => {
    const card = document.createElement("div");
    card.className = `showtime-card ${sh.id === state.activeShowtimeId ? "active" : ""}`;
    card.dataset.id = sh.id;
    card.innerHTML = `
      <div class="showtime-header">
        <span class="time-slot">${sh.time_slot}</span>
        <span class="format-pill">${sh.screen_type}</span>
      </div>
      <div class="theater-name">${sh.theater_name}</div>
      <div class="price-tag">From $${sh.base_price.toFixed(2)}</div>
    `;
    card.addEventListener("click", () => selectShowtime(sh));
    showtimesGrid.appendChild(card);
  });
}

function selectShowtime(sh) {
  state.activeShowtimeId = sh.id;
  state.activeShowtime = sh;
  state.selectedSeats = [];

  document.querySelectorAll(".showtime-card").forEach(c => {
    c.classList.toggle("active", c.dataset.id === sh.id);
  });

  fetchSeatMap(sh.id);
}

function renderSeatGrid(seatMapData) {
  seatGridContainer.innerHTML = "";
  const rows = {};
  seatMapData.seats.forEach(s => {
    if (!rows[s.row]) rows[s.row] = [];
    rows[s.row].push(s);
  });

  Object.keys(rows).sort().forEach(rKey => {
    const rowEl = document.createElement("div");
    rowEl.className = "seat-row";

    const labelEl = document.createElement("span");
    labelEl.className = "row-label";
    labelEl.textContent = rKey;
    rowEl.appendChild(labelEl);

    rows[rKey].sort((a, b) => a.number - b.number).forEach(seat => {
      const seatBtn = document.createElement("button");
      seatBtn.className = `seat-btn ${seat.tier.toLowerCase()} ${seat.status}`;
      seatBtn.dataset.id = seat.id;
      seatBtn.textContent = seat.id;
      seatBtn.title = `${seat.id} (${seat.tier}) - $${seat.price.toFixed(2)}`;

      if (state.selectedSeats.includes(seat.id)) {
        seatBtn.classList.add("selected");
      }

      if (seat.status === "available") {
        seatBtn.addEventListener("click", () => toggleSeat(seat.id));
      } else if (seat.status === "booked") {
        seatBtn.disabled = true;
      }

      rowEl.appendChild(seatBtn);
    });

    seatGridContainer.appendChild(rowEl);
  });
}

function toggleSeat(seatId) {
  const index = state.selectedSeats.indexOf(seatId);
  if (index > -1) {
    state.selectedSeats.splice(index, 1);
  } else {
    state.selectedSeats.push(seatId);
  }

  // Update visual states
  document.querySelectorAll(".seat-btn").forEach(btn => {
    if (btn.dataset.id === seatId) {
      btn.classList.toggle("selected", state.selectedSeats.includes(seatId));
    }
  });

  updatePricing();
}

// ================= MODALS & BOARDING PASS =================
function showBoardingPass(booking) {
  document.getElementById("ticket-movie-title").textContent = booking.movie_title;
  document.getElementById("ticket-theater-info").textContent = `${booking.theater_name} • ${booking.screen_type}`;
  document.getElementById("ticket-date").textContent = booking.date;
  document.getElementById("ticket-time").textContent = booking.time_slot;
  document.getElementById("ticket-seats").textContent = booking.seat_ids.join(", ");
  document.getElementById("ticket-guest").textContent = booking.customer_name;
  document.getElementById("ticket-id").textContent = booking.booking_id;
  document.getElementById("ticket-price").textContent = `$${booking.total_amount.toFixed(2)}`;
  document.getElementById("barcode-text").textContent = booking.booking_id;

  modalTicket.showModal();
}

function initModals() {
  document.getElementById("btn-close-ticket").addEventListener("click", () => modalTicket.close());
  document.getElementById("btn-done-ticket").addEventListener("click", () => modalTicket.close());

  // My Bookings
  const btnMyBookings = document.getElementById("btn-my-bookings");
  const btnCloseBookings = document.getElementById("btn-close-bookings");
  btnMyBookings.addEventListener("click", async () => {
    const res = await fetch("/api/bookings");
    const bookings = await res.json();
    renderBookingsList(bookings);
    modalBookings.showModal();
  });
  btnCloseBookings.addEventListener("click", () => modalBookings.close());

  // Tools Spec
  const btnViewTools = document.getElementById("btn-view-tools");
  const btnCloseTools = document.getElementById("btn-close-tools");
  btnViewTools.addEventListener("click", async () => {
    const res = await fetch("/api/agent/tools");
    const data = await res.json();
    renderToolsList(data.tools);
    modalTools.showModal();
  });
  btnCloseTools.addEventListener("click", () => modalTools.close());
}

function renderBookingsList(bookings) {
  const listEl = document.getElementById("bookings-list");
  listEl.innerHTML = "";
  if (bookings.length === 0) {
    listEl.innerHTML = "<p class='subtitle'>No active bookings found. Book a movie now!</p>";
    return;
  }

  bookings.forEach(b => {
    const card = document.createElement("div");
    card.className = "booking-item-card";
    card.innerHTML = `
      <div>
        <h4 style="color:#fff; font-size:15px; margin-bottom:4px;">${b.movie_title}</h4>
        <div style="font-size:12px; color:var(--text-muted);">
          <span>${b.theater_name} (${b.screen_type})</span> • 
          <span>${b.date} at ${b.time_slot}</span>
        </div>
        <div style="font-size:12px; color:var(--accent-cyan); margin-top:4px; font-family:var(--font-mono);">
          Seats: ${b.seat_ids.join(", ")} | Total: $${b.total_amount.toFixed(2)}
        </div>
      </div>
      <div style="display:flex; gap:8px;">
        <button class="btn btn-secondary btn-sm" onclick='viewPastTicket(${JSON.stringify(b)})'>View Pass</button>
        ${b.status !== "cancelled" ? `<button class="btn btn-outline btn-sm" onclick="cancelPastBooking('${b.booking_id}')">Cancel</button>` : `<span class="badge" style="color:#ff2a5f;">CANCELLED</span>`}
      </div>
    `;
    listEl.appendChild(card);
  });
}

window.viewPastTicket = (booking) => {
  modalBookings.close();
  showBoardingPass(booking);
};

window.cancelPastBooking = async (bookingId) => {
  if (!confirm(`Are you sure you want to cancel booking ${bookingId}?`)) return;
  try {
    const res = await fetch(`/api/bookings/${bookingId}/cancel`, { method: "POST" });
    const data = await res.json();
    alert(data.message || "Booking cancelled.");
    const bRes = await fetch("/api/bookings");
    renderBookingsList(await bRes.json());
    if (state.activeShowtimeId) fetchSeatMap(state.activeShowtimeId);
  } catch (err) {
    alert("Error: " + err.message);
  }
};

function renderToolsList(tools) {
  const container = document.getElementById("tools-spec-grid");
  container.innerHTML = "";
  tools.forEach(t => {
    const card = document.createElement("div");
    card.className = "tool-spec-card";
    card.innerHTML = `
      <div class="tool-spec-name">⚡ ${t.name}()</div>
      <div class="tool-spec-desc">${t.description}</div>
      <details style="margin-top:8px; font-size:11px; color:var(--text-dim);">
        <summary style="cursor:pointer; color:var(--accent-cyan);">View JSON Schema</summary>
        <pre style="margin-top:6px; background:rgba(0,0,0,0.5); padding:8px; border-radius:4px; overflow-x:auto;">${JSON.stringify(t.parameters, null, 2)}</pre>
      </details>
    `;
    container.appendChild(card);
  });
}

async function fetchToolsCount() {
  try {
    const res = await fetch("/api/agent/tools");
    const data = await res.json();
    document.getElementById("tools-count-badge").textContent = data.tools_count;
  } catch (e) {}
}

function initGenreFilters() {
  const filters = document.getElementById("genre-filters");
  filters.querySelectorAll(".filter-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      filters.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      state.activeGenre = chip.dataset.genre;
      fetchMovies(state.activeGenre);
    });
  });
}

// Expose state and handlers for chat.js
window.cinemaState = state;
window.selectMovie = selectMovie;
window.selectShowtime = selectShowtime;
window.fetchSeatMap = fetchSeatMap;
window.showBoardingPass = showBoardingPass;
