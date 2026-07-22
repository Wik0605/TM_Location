import { state, events, scrollTo, makePickIcon } from './state.js';

export function getCoord(target) {
    return state.pickedCoords[target] || null;
}

export function getWaypointCoords() {
    const coords = [];
    document.querySelectorAll('.waypoint-item').forEach((item) => {
        if (item._pickedCoord) coords.push(item._pickedCoord);
    });
    return coords;
}

function showBanner(target) {
    const icon = target === 'start' ? '🟢' : target === 'end' ? '🔴' : '🔵';
    const text =
        target === 'start'
            ? 'Touche la carte pour poser le DÉPART'
            : target === 'end'
            ? "Touche la carte pour poser l'ARRIVÉE"
            : "Touche la carte pour poser l'ESCALE";
    document.getElementById('pick-banner-icon').textContent = icon;
    document.getElementById('pick-banner-text').textContent = text;
    document.getElementById('pick-banner').style.display = 'flex';
}

function hideBanner() {
    document.getElementById('pick-banner').style.display = 'none';
}

export function activatePickMode(target) {
    state.pickingMode = target;
    document.getElementById('map').classList.add('picking-mode');
    document.getElementById('pick-start-btn').classList.toggle('is-active', target === 'start');
    document.getElementById('pick-end-btn').classList.toggle('is-active', target === 'end');
    document.querySelectorAll('.pick-waypoint-btn').forEach((b) => {
        b.classList.toggle('is-active', b.closest('.waypoint-item') === target);
    });
    showBanner(target);
    if (window.innerWidth < 1024) {
        scrollTo(document.getElementById('map-col'));
    }
}

export function deactivatePickMode() {
    state.pickingMode = null;
    document.getElementById('map').classList.remove('picking-mode');
    document.getElementById('pick-start-btn').classList.remove('is-active');
    document.getElementById('pick-end-btn').classList.remove('is-active');
    document.querySelectorAll('.pick-waypoint-btn').forEach((b) => b.classList.remove('is-active'));
    hideBanner();
}

export function reverseGeocode(lat, lng, el) {
    fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&accept-language=fr`)
        .then((r) => r.json())
        .then((data) => {
            el.textContent = data.display_name
                ? data.display_name.split(',').slice(0, 2).join(', ')
                : `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        })
        .catch(() => {
            el.textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        });
}

export function initPick({ attachSearch }) {
    const { map } = state;

    document.getElementById('pick-cancel-btn').addEventListener('click', deactivatePickMode);
    document.getElementById('pick-start-btn').addEventListener('click', () => {
        state.pickingMode === 'start' ? deactivatePickMode() : activatePickMode('start');
    });
    document.getElementById('pick-end-btn').addEventListener('click', () => {
        state.pickingMode === 'end' ? deactivatePickMode() : activatePickMode('end');
    });

    map.on('click', (e) => {
        if (!state.pickingMode) return;
        const { lat, lng } = e.latlng;
        const target = state.pickingMode;
        const coordStr = `${lng.toFixed(6)},${lat.toFixed(6)}`;
        const isWaypoint = target !== 'start' && target !== 'end';

        if (isWaypoint) {
            const item = target;
            if (item._pickMarker) map.removeLayer(item._pickMarker);
            const marker = L.marker([lat, lng], { icon: makePickIcon('#3b82f6') })
                .bindTooltip('Escale', { permanent: true, direction: 'top', offset: [0, -14] })
                .addTo(map);
            item._pickMarker = marker;
            item._pickedCoord = coordStr;
            const badge = item.querySelector('.waypoint-badge');
            const badgeName = item.querySelector('.waypoint-badge-name');
            badgeName.textContent = 'Localisation...';
            badge.style.display = 'flex';
            item.querySelector('.waypoint-badge-clear').onclick = () => {
                badge.style.display = 'none';
                item._pickedCoord = null;
                if (item._pickMarker) {
                    map.removeLayer(item._pickMarker);
                    item._pickMarker = null;
                }
                events.emit('coordChange');
            };
        } else {
            const color = target === 'start' ? '#22c55e' : '#ef4444';
            if (state.pickMarkers[target]) map.removeLayer(state.pickMarkers[target]);
            state.pickMarkers[target] = L.marker([lat, lng], { icon: makePickIcon(color) })
                .bindTooltip(target === 'start' ? 'Départ' : 'Arrivée', {
                    permanent: true,
                    direction: 'top',
                    offset: [0, -14],
                })
                .addTo(map);
            state.pickedCoords[target] = coordStr;
            const badgeEl = document.getElementById(`${target}-badge`);
            const badgeNameEl = document.getElementById(`${target}-badge-name`);
            badgeNameEl.textContent = 'Localisation...';
            badgeEl.style.display = 'flex';
            reverseGeocode(lat, lng, badgeNameEl);
        }

        deactivatePickMode();
        if (navigator.vibrate) navigator.vibrate(40);
        if (window.innerWidth < 1024) {
            setTimeout(() => scrollTo(document.getElementById('form-panel')), 400);
        }
        if (isWaypoint) {
            reverseGeocode(lat, lng, target.querySelector('.waypoint-badge-name'));
        }
        events.emit('coordChange');
    });

    document.getElementById('start-clear').addEventListener('click', () => {
        state.pickedCoords.start = null;
        if (state.pickMarkers.start) {
            map.removeLayer(state.pickMarkers.start);
            state.pickMarkers.start = null;
        }
        document.getElementById('start-badge').style.display = 'none';
        events.emit('coordChange');
    });

    document.getElementById('end-clear').addEventListener('click', () => {
        state.pickedCoords.end = null;
        if (state.pickMarkers.end) {
            map.removeLayer(state.pickMarkers.end);
            state.pickMarkers.end = null;
        }
        document.getElementById('end-badge').style.display = 'none';
        events.emit('coordChange');
    });

    document.getElementById('add-waypoint-btn').addEventListener('click', () => {
        const tmpl = document.getElementById('waypoint-template').content.cloneNode(true);
        const item = tmpl.querySelector('.waypoint-item');

        item.querySelector('.remove-waypoint-btn').addEventListener('click', () => {
            if (item._pickMarker) map.removeLayer(item._pickMarker);
            if (state.pickingMode === item) deactivatePickMode();
            item.remove();
            events.emit('coordChange');
        });

        item.querySelector('.pick-waypoint-btn').addEventListener('click', () => {
            if (state.pickingMode === item) {
                deactivatePickMode();
                return;
            }
            activatePickMode(item);
        });

        const searchBox = item.querySelector('.place-search');
        if (searchBox && attachSearch) attachSearch(searchBox, item);

        document.getElementById('waypoints-container').appendChild(item);
    });
}
