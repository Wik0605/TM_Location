export const state = {
    map: null,
    markersLayer: null,
    routeLayer: null,
    pickMarkers: { start: null, end: null },
    pickedCoords: { start: null, end: null },
    pickingMode: null,
    DAILY_PRICE: 0,
    DRAFT_KEY: '',
};

export const events = {
    _listeners: {},
    on(name, fn) {
        (this._listeners[name] = this._listeners[name] || []).push(fn);
    },
    emit(name, ...args) {
        (this._listeners[name] || []).forEach((fn) => fn(...args));
    },
};

const NAV_HEIGHT = 88;

export function scrollTo(el, offset) {
    const top = el.getBoundingClientRect().top + window.scrollY - (offset || NAV_HEIGHT);
    window.scrollTo({ top, behavior: 'smooth' });
}

export function makePickIcon(color) {
    const html = `<div style="background:${color};width:24px;height:24px;border-radius:50%;border:3px solid white;box-shadow:0 2px 10px rgba(0,0,0,0.5)"></div>`;
    return L.divIcon({ html, className: '', iconSize: [24, 24], iconAnchor: [12, 12] });
}
