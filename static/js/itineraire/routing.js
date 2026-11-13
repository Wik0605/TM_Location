import { state } from './state.js';

const SNAP_WARN_THRESHOLD_M = 50;
const SNAP_VISIBLE_GAP_M = 10;

export function drawRoute(geojson, coords, snappedWaypoints) {
    const { map, markersLayer } = state;
    if (state.routeLayer) map.removeLayer(state.routeLayer);
    markersLayer.clearLayers();
    if (state.pickMarkers.start) { map.removeLayer(state.pickMarkers.start); state.pickMarkers.start = null; }
    if (state.pickMarkers.end) { map.removeLayer(state.pickMarkers.end); state.pickMarkers.end = null; }
    state.routeLayer = L.geoJSON(geojson, {
        style: { color: '#4f46e5', weight: 5, opacity: 0.85 },
    }).addTo(map);
    coords.forEach((coord, i) => {
        const [lon, lat] = coord.split(',').map(parseFloat);
        const color = i === 0 ? '#22c55e' : i === coords.length - 1 ? '#ef4444' : '#3b82f6';
        const snap = snappedWaypoints && snappedWaypoints[i];
        const walkM = snap && snap.walk_m ? snap.walk_m : 0;
        const snapLat = snap && snap.lat != null ? snap.lat : lat;
        const snapLon = snap && snap.lon != null ? snap.lon : lon;

        const label = i === 0 ? 'Départ' : i === coords.length - 1 ? 'Arrivée' : `Escale ${i}`;

        if (walkM >= SNAP_VISIBLE_GAP_M) {
            const ghostHtml = `<div style="background:#9ca3af;width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.3);opacity:0.95"></div>`;
            L.marker([lat, lon], {
                icon: L.divIcon({ html: ghostHtml, className: '', iconSize: [16, 16], iconAnchor: [8, 8] }),
            }).bindTooltip(`${label} demandé`, { permanent: false, direction: 'top' }).addTo(markersLayer);

            L.polyline([[lat, lon], [snapLat, snapLon]], {
                color: '#000000',
                weight: 6,
                opacity: 0.55,
            }).addTo(markersLayer);
            L.polyline([[lat, lon], [snapLat, snapLon]], {
                color: '#ffffff',
                weight: 3.5,
                opacity: 1,
                dashArray: '8,8',
            }).addTo(markersLayer);

            const midLat = (lat + snapLat) / 2;
            const midLon = (lon + snapLon) / 2;
            const meters = Math.round(walkM);
            const walkText = meters >= 1000
                ? `${(meters / 1000).toFixed(1).replace('.', ',')} km à pied`
                : `${meters} m à pied`;
            const labelHtml = `<div style="background:white;border:1.5px solid #374151;border-radius:9999px;padding:3px 10px;font-size:12px;font-weight:700;color:#111827;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,0.25);display:inline-flex;align-items:center;gap:5px;transform:translate(-50%,-50%)"><span style="font-size:13px">🚶</span>${walkText}</div>`;
            L.marker([midLat, midLon], {
                icon: L.divIcon({ html: labelHtml, className: '', iconSize: [1, 1], iconAnchor: [0, 0] }),
                interactive: false,
                keyboard: false,
            }).addTo(markersLayer);
        }

        const html = `<div style="background:${color};width:20px;height:20px;border-radius:50%;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.45)"></div>`;
        L.marker([snapLat, snapLon], {
            icon: L.divIcon({ html, className: '', iconSize: [20, 20], iconAnchor: [10, 10] }),
        }).bindTooltip(walkM >= SNAP_VISIBLE_GAP_M ? `${label} (voiture)` : label, { permanent: false, direction: 'top' }).addTo(markersLayer);
    });
    map.fitBounds(state.routeLayer.getBounds(), { padding: [30, 30] });
}

function renderSnapWarnings(snappedWaypoints, totalCoords) {
    const container = document.getElementById('snap-warnings');
    if (!container) return;
    container.innerHTML = '';
    if (!snappedWaypoints || !snappedWaypoints.length) return;
    const labels = snappedWaypoints.map((_, i) => {
        if (i === 0) return 'Départ';
        if (i === totalCoords - 1) return 'Arrivée';
        return `Escale ${i}`;
    });
    const items = snappedWaypoints
        .map((wp, i) => ({ wp, label: labels[i] }))
        .filter(({ wp }) => wp && wp.walk_m >= SNAP_WARN_THRESHOLD_M);
    if (!items.length) return;
    const list = items
        .map(({ wp, label }) => {
            const m = Math.round(wp.walk_m);
            return `<li><strong>${label}</strong> : ~${m} m à pied jusqu'à la route accessible</li>`;
        })
        .join('');
    container.innerHTML = `
        <div class="bg-amber-50 border-l-4 border-amber-500 rounded-2xl px-3 py-2 mt-2">
            <p class="text-[10px] font-black uppercase tracking-widest text-amber-700 mb-1">Zone restreinte</p>
            <ul class="text-[11px] text-amber-900 leading-snug space-y-0.5 list-disc pl-4">${list}</ul>
        </div>`;
}

export async function calcBackend(coords) {
    const waypoints = coords.map((c) => {
        const [lon, lat] = c.split(',').map(parseFloat);
        return [lat, lon];
    });
    const url = `/api/voitures/${state.CAR_ID}/itineraire/calculer`;
    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ waypoints }),
    });
    if (resp.status === 429) return { quotaExceeded: true };
    if (!resp.ok) return null;
    const data = await resp.json();
    drawRoute(data.polyline, coords, data.snapped_waypoints);
    renderSnapWarnings(data.snapped_waypoints, coords.length);
    return {
        distanceKm: data.distance_km,
        isFallback: data.source === 'haversine',
        token: data.token,
        zoneRoutiere: data.zone_routiere,
        snappedWaypoints: data.snapped_waypoints,
    };
}
