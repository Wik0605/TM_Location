import { state } from './state.js';

export function firstValid(...promises) {
    return new Promise((resolve) => {
        let done = false;
        let pending = promises.length;
        promises.forEach((p) => {
            p.then((v) => {
                if (!done && v !== null) {
                    done = true;
                    resolve(v);
                }
            }).finally(() => {
                pending--;
                if (pending === 0 && !done) resolve(null);
            });
        });
    });
}

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

export async function calcBRouter(coords) {
    try {
        const url = `https://brouter.de/brouter?lonlats=${coords.join('|')}&profile=car-eco&alternativeidx=0&format=geojson`;
        const resp = await fetch(url);
        if (!resp.ok) return null;
        const geojson = await resp.json();
        if (!geojson.features?.[0]) return null;
        drawRoute(geojson, coords);
        return parseFloat(geojson.features[0].properties['track-length']) / 1000;
    } catch {
        return null;
    }
}

export async function calcOSRM(coords) {
    try {
        const url = `https://router.project-osrm.org/route/v1/driving/${coords.join(';')}?overview=full&geometries=geojson`;
        const resp = await fetch(url);
        if (!resp.ok) return null;
        const data = await resp.json();
        if (data.code !== 'Ok' || !data.routes?.[0]) return null;
        const geojson = {
            type: 'FeatureCollection',
            features: [{ type: 'Feature', geometry: data.routes[0].geometry, properties: {} }],
        };
        drawRoute(geojson, coords);
        return data.routes[0].distance / 1000;
    } catch {
        return null;
    }
}

function haversineKm(a, b) {
    const [lon1, lat1] = a.split(',').map(parseFloat);
    const [lon2, lat2] = b.split(',').map(parseFloat);
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const s =
        Math.sin(dLat / 2) ** 2 +
        Math.cos((lat1 * Math.PI) / 180) *
            Math.cos((lat2 * Math.PI) / 180) *
            Math.sin(dLon / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
}

export function calcFallback(coords) {
    let total = 0;
    for (let i = 0; i < coords.length - 1; i++) {
        total += haversineKm(coords[i], coords[i + 1]);
    }
    return Promise.resolve(total * 1.3);
}
