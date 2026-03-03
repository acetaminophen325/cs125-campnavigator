/**
 * app.js – UCI Camp Navigator frontend
 *
 * Responsibilities:
 *  - Initialize Leaflet map centered on UCI campus
 *  - Fetch /api/buildings → populate dropdown + add map markers
 *  - Handle geolocation + building-select to set user position
 *  - POST /api/rank → render result cards + highlight map markers
 */

/* ============================================================
   Constants
============================================================ */
const UCI_CENTER = [33.6405, -117.8443];
const UCI_ZOOM   = 16;

// JS Date.getDay() → Python day token
const DAY_TOKENS = ["Su", "M", "Tu", "W", "Th", "F", "Sa"];

/* ============================================================
   State
============================================================ */
let userLatLon = null;          // [lat, lon] chosen by user
let buildingsData = [];         // array of {code, name, lat, lon}
let buildingMarkers = {};       // code → Leaflet CircleMarker
let resultMarkers = [];         // Leaflet markers for current results
let userMarker = null;          // red pin for user location
let activeCardIndex = null;     // index of highlighted result card

/* ============================================================
   Map setup
============================================================ */
const map = L.map("map").setView(UCI_CENTER, UCI_ZOOM);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19,
}).addTo(map);

/* ============================================================
   DOM references
============================================================ */
const btnGeolocate    = document.getElementById("btn-geolocate");
const buildingSelect  = document.getElementById("building-select");
const daySelect       = document.getElementById("day-select");
const timeInput       = document.getElementById("time-input");
const btnNow          = document.getElementById("btn-now");
const chkOngoing      = document.getElementById("chk-ongoing");
const btnSearch       = document.getElementById("btn-search");
const locationStatus  = document.getElementById("location-status");
const searchError     = document.getElementById("search-error");
const resultsSection  = document.getElementById("results-section");
const resultsList     = document.getElementById("results-list");
const resultsCount    = document.getElementById("results-count");

/* ============================================================
   Helpers
============================================================ */
function nowDayToken() {
  return DAY_TOKENS[new Date().getDay()];
}

function nowTimeStr() {
  const d = new Date();
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${h}:${m}`;
}

function timeStrToMin(timeStr) {
  // "HH:MM" → minutes since midnight
  const [h, m] = timeStr.split(":").map(Number);
  return h * 60 + m;
}

function scoreColor(score) {
  // score 0–1 → CSS color
  if (score >= 0.7) return "#22c55e";
  if (score >= 0.4) return "#f59e0b";
  return "#ef4444";
}

function setUserPin(lat, lon) {
  userLatLon = [lat, lon];

  if (userMarker) userMarker.remove();

  userMarker = L.circleMarker([lat, lon], {
    radius: 9,
    color: "#fff",
    weight: 2.5,
    fillColor: "#ef4444",
    fillOpacity: 1,
  }).addTo(map).bindTooltip("You are here", { permanent: false });

  map.setView([lat, lon], Math.max(map.getZoom(), UCI_ZOOM));

  // Enable search button
  btnSearch.disabled = false;
  searchError.textContent = "";
}

/* ============================================================
   Load buildings
============================================================ */
async function loadBuildings() {
  try {
    const res = await fetch("/api/buildings");
    const data = await res.json();
    buildingsData = data.buildings;

    // Populate dropdown
    buildingsData.forEach(b => {
      const opt = document.createElement("option");
      opt.value = b.code;
      opt.textContent = `${b.name} (${b.code})`;
      buildingSelect.appendChild(opt);
    });

    // Add blue circle markers to map
    buildingsData.forEach(b => {
      const marker = L.circleMarker([b.lat, b.lon], {
        radius: 7,
        color: "#0064a4",
        weight: 2,
        fillColor: "#0064a4",
        fillOpacity: 0.25,
      }).addTo(map);

      marker.bindTooltip(`<strong>${b.name}</strong><br>${b.code}`, {
        direction: "top",
        offset: [0, -6],
      });

      buildingMarkers[b.code] = marker;
    });
  } catch (err) {
    console.error("Failed to load buildings:", err);
    locationStatus.textContent = "Could not load buildings.";
  }
}

/* ============================================================
   Geolocation
============================================================ */
btnGeolocate.addEventListener("click", () => {
  if (!navigator.geolocation) {
    locationStatus.textContent = "Geolocation is not supported by this browser.";
    return;
  }

  locationStatus.textContent = "Detecting your location…";
  btnGeolocate.disabled = true;

  navigator.geolocation.getCurrentPosition(
    pos => {
      const { latitude: lat, longitude: lon } = pos.coords;
      setUserPin(lat, lon);
      buildingSelect.value = "";
      locationStatus.textContent = `GPS: ${lat.toFixed(5)}, ${lon.toFixed(5)}`;
      btnGeolocate.disabled = false;
    },
    err => {
      locationStatus.textContent = `Location error: ${err.message}`;
      btnGeolocate.disabled = false;
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
});

/* ============================================================
   Building dropdown
============================================================ */
buildingSelect.addEventListener("change", () => {
  const code = buildingSelect.value;
  if (!code) return;

  const bldg = buildingsData.find(b => b.code === code);
  if (!bldg) return;

  setUserPin(bldg.lat, bldg.lon);
  locationStatus.textContent = `Selected: ${bldg.name}`;
});

/* ============================================================
   Time defaults + reset
============================================================ */
function resetTime() {
  daySelect.value = nowDayToken();
  timeInput.value = nowTimeStr();
}

resetTime();

btnNow.addEventListener("click", resetTime);

/* ============================================================
   Search
============================================================ */
btnSearch.addEventListener("click", async () => {
  searchError.textContent = "";

  if (!userLatLon) {
    searchError.textContent = "Please set your location first.";
    return;
  }

  const [lat, lon] = userLatLon;
  const day       = daySelect.value;
  const now_min   = timeStrToMin(timeInput.value);
  const include_ongoing = chkOngoing.checked;

  btnSearch.textContent = "Searching…";
  btnSearch.disabled = true;

  try {
    const res = await fetch("/api/rank", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, day, now_min, include_ongoing, top_k: 10 }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Server error");
    }

    const data = await res.json();
    renderResults(data.results);
  } catch (err) {
    searchError.textContent = err.message;
    console.error("Rank error:", err);
  } finally {
    btnSearch.textContent = "Find Nearby Classes";
    btnSearch.disabled = false;
  }
});

/* ============================================================
   Render results
============================================================ */
function clearResultMarkers() {
  resultMarkers.forEach(m => m.remove());
  resultMarkers = [];

  // Reset building markers to default style
  Object.values(buildingMarkers).forEach(m => {
    m.setStyle({ fillColor: "#0064a4", fillOpacity: 0.25, color: "#0064a4" });
    m.setRadius(7);
  });
}

function renderResults(results) {
  clearResultMarkers();
  resultsList.innerHTML = "";
  activeCardIndex = null;

  resultsSection.hidden = false;
  resultsCount.textContent = `${results.length} found`;

  if (results.length === 0) {
    resultsList.innerHTML = `
      <li class="results-empty">
        No classes found nearby.<br>Try a different time or location.
      </li>`;
    return;
  }

  results.forEach((r, idx) => {
    // ---- Card ----
    const li = document.createElement("li");
    li.className = "result-card";
    li.dataset.idx = idx;

    const color = scoreColor(r.score);
    const scorePct = Math.round(r.score * 100);
    const distStr = r.distance_m < 100
      ? `${Math.round(r.distance_m)}m`
      : `${(r.distance_m / 1000).toFixed(2)}km`;

    const minsStr = r.minutes_until_start < 0
      ? `${Math.abs(r.minutes_until_start)}min ago`
      : r.minutes_until_start === 0
        ? "Starting now"
        : `in ${r.minutes_until_start}min`;

    li.innerHTML = `
      <div class="card-top">
        <span class="card-course">${r.course_id}</span>
        <span class="card-score" style="background:${color}">${scorePct}%</span>
      </div>
      <div class="card-title">${r.title}</div>
      <div class="card-meta">
        <span>&#128337; ${r.start_time}–${r.end_time}</span>
        <span>&#127968; ${r.building_name} ${r.room}</span>
        <span>&#128205; ${distStr}</span>
        <span>&#9201; ${minsStr}</span>
      </div>
      <div class="score-bar-track">
        <div class="score-bar-fill" style="width:${scorePct}%;background:${color}"></div>
      </div>`;

    li.addEventListener("click", () => highlightResult(idx, results));
    resultsList.appendChild(li);

    // ---- Map marker ----
    if (r.lat != null && r.lon != null) {
      const bMarker = buildingMarkers[r.building_code];
      if (bMarker) {
        bMarker.setStyle({
          fillColor: color,
          fillOpacity: 0.6,
          color: color,
        });
        bMarker.setRadius(10);
      }

      // Invisible marker just for tooltip/click targeting
      const rMarker = L.circleMarker([r.lat, r.lon], {
        radius: 0,
        opacity: 0,
        fillOpacity: 0,
      }).addTo(map);

      resultMarkers.push(rMarker);
    } else {
      resultMarkers.push(null);
    }
  });
}

function highlightResult(idx, results) {
  // Remove previous active style
  if (activeCardIndex !== null) {
    const prev = resultsList.querySelector(`[data-idx="${activeCardIndex}"]`);
    if (prev) prev.classList.remove("active");
  }

  activeCardIndex = idx;
  const card = resultsList.querySelector(`[data-idx="${idx}"]`);
  if (card) {
    card.classList.add("active");
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  const r = results[idx];
  if (r.lat != null && r.lon != null) {
    map.setView([r.lat, r.lon], Math.max(map.getZoom(), 17));
    const bMarker = buildingMarkers[r.building_code];
    if (bMarker) bMarker.openTooltip();
  }
}

/* ============================================================
   Boot
============================================================ */
loadBuildings();
