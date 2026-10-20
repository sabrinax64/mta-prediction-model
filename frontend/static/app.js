const map = L.map("map").setView([40.7128, -73.95], 11);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
  maxZoom: 19,
}).addTo(map);

const markersByTrip = new Map();

function colorForDelay(delaySeconds) {
  if (delaySeconds === null || delaySeconds === undefined) return "#888888";
  if (delaySeconds < 60) return "#2ecc71"; // on time / early
  if (delaySeconds < 300) return "#f1c40f"; // mildly late
  return "#e74c3c"; // significantly late
}

function renderTrains(trains) {
  const seen = new Set();

  for (const train of trains) {
    if (train.lat === null || train.lon === null) continue;
    seen.add(train.trip_id);

    const color = colorForDelay(train.delay_seconds);
    const label = train.delay_seconds === null
      ? "unknown"
      : `${train.delay_seconds > 0 ? "+" : ""}${Math.round(train.delay_seconds / 60)} min`;

    let marker = markersByTrip.get(train.trip_id);
    if (!marker) {
      marker = L.circleMarker([train.lat, train.lon], { radius: 6 }).addTo(map);
      markersByTrip.set(train.trip_id, marker);
    }
    marker.setLatLng([train.lat, train.lon]);
    marker.setStyle({ color, fillColor: color, fillOpacity: 0.9 });
    marker.bindPopup(
      `<b>${train.route_id}</b> (${train.direction})<br>` +
      `next: ${train.stop_name ?? train.current_stop_id}<br>` +
      `delay: ${label}`
    );
  }

  // Drop markers for trains no longer present in this snapshot.
  for (const [tripId, marker] of markersByTrip.entries()) {
    if (!seen.has(tripId)) {
      map.removeLayer(marker);
      markersByTrip.delete(tripId);
    }
  }
}

function connect() {
  const statusEl = document.getElementById("status");
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${window.location.host}/ws/live`);

  ws.onopen = () => { statusEl.textContent = "live"; };
  ws.onclose = () => {
    statusEl.textContent = "disconnected, retrying in 3s...";
    setTimeout(connect, 3000);
  };
  ws.onerror = () => ws.close();
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    renderTrains(data.trains);
    statusEl.textContent = `live — ${data.trains.length} trains, updated ${new Date().toLocaleTimeString()}`;
  };
}

connect();
