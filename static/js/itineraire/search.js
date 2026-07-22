import { state } from './state.js';
import { activatePickMode } from './pick.js';

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';

function formatSuggestion(item) {
    const parts = (item.display_name || '').split(',').map((s) => s.trim());
    const addr = item.address || {};
    const title =
        addr.village ||
        addr.suburb ||
        addr.neighbourhood ||
        addr.road ||
        addr.city ||
        addr.town ||
        addr.hamlet ||
        parts[0] ||
        'Lieu';
    const context = parts
        .slice(1, 4)
        .filter((p) => p && p !== title)
        .join(', ');
    return { title, sub: context };
}

function searchPlaces(query, signal) {
    const url = `${NOMINATIM_URL}?q=${encodeURIComponent(query)}&countrycodes=mg&format=json&limit=5&addressdetails=1&accept-language=fr`;
    return fetch(url, { signal, headers: { Accept: 'application/json' } }).then((r) =>
        r.ok ? r.json() : []
    );
}

export function attachSearchBox(container, target) {
    const input = container.querySelector('.place-search-input');
    const list = container.querySelector('.place-suggestions');
    const clearBtn = container.querySelector('.place-search-clear');
    let debounceTimer = null;
    let currentCtrl = null;
    let activeIndex = -1;
    let currentResults = [];

    function closeList() {
        list.hidden = true;
        list.innerHTML = '';
        activeIndex = -1;
        currentResults = [];
    }

    function renderEmpty(msg) {
        list.hidden = false;
        list.innerHTML = `<li class="place-suggestions-empty">${msg}</li>`;
    }

    function renderResults(results) {
        currentResults = results;
        if (!results.length) return renderEmpty('Aucun résultat');
        list.hidden = false;
        list.innerHTML = '';
        results.forEach((item) => {
            const li = document.createElement('li');
            li.className = 'place-suggestion-item';
            li.setAttribute('role', 'option');
            const fmt = formatSuggestion(item);
            li.innerHTML =
                '<svg class="place-suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>' +
                '<div class="place-suggestion-text"><div class="place-suggestion-title"></div><div class="place-suggestion-sub"></div></div>';
            li.querySelector('.place-suggestion-title').textContent = fmt.title;
            li.querySelector('.place-suggestion-sub').textContent = fmt.sub;
            li.addEventListener('mousedown', (e) => {
                e.preventDefault();
                selectResult(item, fmt.title);
            });
            list.appendChild(li);
        });
    }

    function selectResult(item, title) {
        input.value = title;
        container.classList.add('has-value');
        closeList();
        if (navigator.vibrate) navigator.vibrate(20);
        const centerLat = item.lat ? parseFloat(item.lat) : null;
        const centerLon = item.lon ? parseFloat(item.lon) : null;
        const bb = item.boundingbox;
        if (bb && bb.length === 4) {
            const bounds = L.latLngBounds(
                [parseFloat(bb[0]), parseFloat(bb[2])],
                [parseFloat(bb[1]), parseFloat(bb[3])]
            );
            state.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 17, animate: false });
            if (state.map.getZoom() < 15) {
                if (centerLat !== null && centerLon !== null) {
                    state.map.setView([centerLat, centerLon], 15, { animate: false });
                } else {
                    state.map.setView(bounds.getCenter(), 15, { animate: false });
                }
            }
        } else if (centerLat !== null && centerLon !== null) {
            state.map.setView([centerLat, centerLon], 16);
        }
        activatePickMode(target);
    }

    function triggerSearch(query) {
        if (currentCtrl) currentCtrl.abort();
        currentCtrl = new AbortController();
        container.classList.add('is-loading');
        searchPlaces(query, currentCtrl.signal)
            .then((results) => {
                container.classList.remove('is-loading');
                renderResults(results);
            })
            .catch((err) => {
                if (err?.name === 'AbortError') return;
                container.classList.remove('is-loading');
                renderEmpty('Aucun résultat');
            });
    }

    input.addEventListener('input', () => {
        const v = input.value.trim();
        container.classList.toggle('has-value', v.length > 0);
        if (debounceTimer) clearTimeout(debounceTimer);
        if (v.length < 2) {
            closeList();
            container.classList.remove('is-loading');
            return;
        }
        debounceTimer = setTimeout(() => triggerSearch(v), 400);
    });

    input.addEventListener('focus', () => {
        if (currentResults.length) list.hidden = false;
    });

    input.addEventListener('blur', () => setTimeout(closeList, 180));

    input.addEventListener('keydown', (e) => {
        const items = list.querySelectorAll('.place-suggestion-item');
        if (e.key === 'ArrowDown' && items.length) {
            e.preventDefault();
            activeIndex = (activeIndex + 1) % items.length;
        } else if (e.key === 'ArrowUp' && items.length) {
            e.preventDefault();
            activeIndex = (activeIndex - 1 + items.length) % items.length;
        } else if (e.key === 'Enter' && activeIndex >= 0 && currentResults[activeIndex]) {
            e.preventDefault();
            const it = currentResults[activeIndex];
            selectResult(it, formatSuggestion(it).title);
            return;
        } else if (e.key === 'Escape') {
            closeList();
            input.blur();
            return;
        } else {
            return;
        }
        items.forEach((el, i) => el.classList.toggle('is-active', i === activeIndex));
        if (items[activeIndex]) items[activeIndex].scrollIntoView({ block: 'nearest' });
    });

    clearBtn.addEventListener('click', () => {
        input.value = '';
        container.classList.remove('has-value');
        closeList();
        input.focus();
    });
}

export function initSearch() {
    const startSearch = document.querySelector('.place-search[data-target="start"]');
    const endSearch = document.querySelector('.place-search[data-target="end"]');
    if (startSearch) attachSearchBox(startSearch, 'start');
    if (endSearch) attachSearchBox(endSearch, 'end');
}
