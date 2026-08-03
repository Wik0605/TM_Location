import { state } from './state.js';

export function drawRoute(geojson, coords) {
    const { map, markersLayer } = state;
    if (state.routeLayer) map.removeLayer(state.routeLayer);
    markersLayer.clearLayers();
    state.routeLayer = L.geoJSON(geojson, {
        style: { color: '#4f46e5', weight: 5, opacity: 0.85 },
    }).addTo(map);
    coords.forEach((coord, i) => {
        const [lon, lat] = coord.split(',').map(parseFloat);
        const color = i === 0 ? '#22c55e' : i === coords.length - 1 ? '#ef4444' : '#3b82f6';
        const html = `<div style="background:${color};width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4)"></div>`;
        L.marker([lat, lon], {
            icon: L.divIcon({ html, className: '', iconSize: [16, 16], iconAnchor: [8, 8] }),
        }).addTo(markersLayer);
    });
    map.fitBounds(state.routeLayer.getBounds(), { padding: [30, 30] });
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
    drawRoute(data.polyline, coords);
    return {
        distanceKm: data.distance_km,
        isFallback: data.source === 'haversine',
        token: data.token,
    };
}
