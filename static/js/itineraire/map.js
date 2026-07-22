import { state } from './state.js';

export function initMap() {
    const map = L.map('map', {
        gestureHandling: true,
        gestureHandlingOptions: {
            text: {
                touch: 'Utilisez deux doigts pour déplacer la carte',
                scroll: 'Utilisez Ctrl + molette pour zoomer',
                scrollMac: 'Utilisez ⌘ + molette pour zoomer',
            },
            duration: 1000,
        },
        zoomControl: false,
        tap: true,
        tapTolerance: 15,
    }).setView([-18.91, 47.52], 15);

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    const LocateControl = L.Control.extend({
        options: { position: 'bottomright' },
        onAdd() {
            const btn = L.DomUtil.create('button', 'locate-btn');
            btn.title = 'Ma position';
            btn.innerHTML =
                '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7zm0 4.5A2.5 2.5 0 1 0 12 11.5 2.5 2.5 0 0 0 12 6.5z"/></svg>';
            L.DomEvent.on(btn, 'click', (e) => {
                L.DomEvent.stopPropagation(e);
                map.locate({ setView: true, maxZoom: 15 });
            });
            return btn;
        },
    });
    new LocateControl().addTo(map);

    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    });
    const esriImagery = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics',
            maxZoom: 19,
        }
    );
    const osmLabels = L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png',
        {
            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19,
            pane: 'shadowPane',
        }
    );
    const satelliteLayer = L.layerGroup([esriImagery, osmLabels]);
    osmLayer.addTo(map);

    L.control
        .layers({ Plan: osmLayer, Satellite: satelliteLayer }, null, {
            position: 'topright',
            collapsed: false,
        })
        .addTo(map);

    state.map = map;
    state.markersLayer = L.layerGroup().addTo(map);
    return map;
}
