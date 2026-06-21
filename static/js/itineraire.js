(function () {
    var mapEl = document.getElementById('map');
    var DAILY_PRICE = parseFloat(mapEl.getAttribute('data-daily-price')) || 0;
    var NAV_HEIGHT = 88;

    function scrollTo(el, offset) {
        var top = el.getBoundingClientRect().top + window.scrollY - (offset || NAV_HEIGHT);
        window.scrollTo({ top: top, behavior: 'smooth' });
    }

    // ── Carte ──
    var map = L.map('map', {
        gestureHandling: true,
        gestureHandlingOptions: {
            text: {
                touch: 'Utilisez deux doigts pour déplacer la carte',
                scroll: 'Utilisez Ctrl + molette pour zoomer',
                scrollMac: 'Utilisez ⌘ + molette pour zoomer'
            },
            duration: 1000
        },
        zoomControl: false,
        tap: true,
        tapTolerance: 15
    }).setView([-18.91, 47.52], 13);

    // Contrôles zoom en bas à droite (plus ergonomiques sur mobile)
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Bouton "Me localiser"
    var LocateControl = L.Control.extend({
        options: { position: 'bottomright' },
        onAdd: function () {
            var btn = L.DomUtil.create('button', 'locate-btn');
            btn.title = 'Ma position';
            btn.innerHTML = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2a7 7 0 0 1 7 7c0 5-7 13-7 13S5 14 5 9a7 7 0 0 1 7-7zm0 4.5A2.5 2.5 0 1 0 12 11.5 2.5 2.5 0 0 0 12 6.5z"/></svg>';
            L.DomEvent.on(btn, 'click', function (e) {
                L.DomEvent.stopPropagation(e);
                map.locate({ setView: true, maxZoom: 15 });
            });
            return btn;
        }
    });
    new LocateControl().addTo(map);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    var routeLayer = null;
    var markersLayer = L.layerGroup().addTo(map);
    var pickMarkers = { start: null, end: null };
    var pickedCoords = { start: null, end: null };
    var pickingMode = null;       // 'start' | 'end' | DOM element (escale)
    var waypointPickMarkers = []; // marqueurs des escales pointées

    function makePickIcon(color) {
        var html = '<div style="background:' + color + ';width:24px;height:24px;border-radius:50%;border:3px solid white;box-shadow:0 2px 10px rgba(0,0,0,0.5)"></div>';
        return L.divIcon({ html: html, className: '', iconSize: [24, 24], iconAnchor: [12, 12] });
    }

    // ── Bannière flottante (hors carte = pas d'interférence touch) ──
    var banner = document.getElementById('pick-banner');

    function showBanner(target) {
        var icon = target === 'start' ? '🟢' : (target === 'end' ? '🔴' : '🔵');
        var text = target === 'start'
            ? 'Touche la carte pour poser le DÉPART'
            : (target === 'end' ? 'Touche la carte pour poser l\'ARRIVÉE' : 'Touche la carte pour poser l\'ESCALE');
        document.getElementById('pick-banner-icon').textContent = icon;
        document.getElementById('pick-banner-text').textContent = text;
        banner.style.display = 'flex';
    }
    function hideBanner() { banner.style.display = 'none'; }

    // ── Activer / désactiver mode pointage ──
    function activatePickMode(target) {
        pickingMode = target;
        document.getElementById('map').classList.add('picking-mode');
        document.getElementById('pick-start-btn').classList.toggle('is-active', target === 'start');
        document.getElementById('pick-end-btn').classList.toggle('is-active', target === 'end');
        // Désactiver les boutons escales non concernés
        document.querySelectorAll('.pick-waypoint-btn').forEach(function (b) {
            b.classList.toggle('is-active', b.closest('.waypoint-item') === target);
        });
        showBanner(target);
        if (window.innerWidth < 1024) {
            scrollTo(document.getElementById('map-col'));
        }
    }

    function deactivatePickMode() {
        pickingMode = null;
        document.getElementById('map').classList.remove('picking-mode');
        document.getElementById('pick-start-btn').classList.remove('is-active');
        document.getElementById('pick-end-btn').classList.remove('is-active');
        document.querySelectorAll('.pick-waypoint-btn').forEach(function (b) { b.classList.remove('is-active'); });
        hideBanner();
    }

    document.getElementById('pick-cancel-btn').addEventListener('click', deactivatePickMode);

    document.getElementById('pick-start-btn').addEventListener('click', function () {
        pickingMode === 'start' ? deactivatePickMode() : activatePickMode('start');
    });
    document.getElementById('pick-end-btn').addEventListener('click', function () {
        pickingMode === 'end' ? deactivatePickMode() : activatePickMode('end');
    });

    // ── Clic / tap sur la carte ──
    map.on('click', function (e) {
        if (!pickingMode) return;

        var lat = e.latlng.lat;
        var lng = e.latlng.lng;
        var target = pickingMode;
        var coordStr = lng.toFixed(6) + ',' + lat.toFixed(6);
        var isWaypoint = (target !== 'start' && target !== 'end');

        if (isWaypoint) {
            // --- Escale pointée ---
            var item = target; // élément DOM .waypoint-item
            var color = '#3b82f6';
            // Supprimer ancien marqueur de cette escale si existant
            var oldMarker = item._pickMarker;
            if (oldMarker) map.removeLayer(oldMarker);
            var marker = L.marker([lat, lng], { icon: makePickIcon(color) })
                .bindTooltip('Escale', { permanent: true, direction: 'top', offset: [0, -14] })
                .addTo(map);
            item._pickMarker = marker;
            item._pickedCoord = coordStr;
            // Afficher badge
            var badge = item.querySelector('.waypoint-badge');
            var badgeName = item.querySelector('.waypoint-badge-name');
            badgeName.textContent = 'Localisation...';
            badge.style.display = 'flex';
            // Effacer badge via bouton ✕
            item.querySelector('.waypoint-badge-clear').onclick = function () {
                badge.style.display = 'none';
                item._pickedCoord = null;
                if (item._pickMarker) { map.removeLayer(item._pickMarker); item._pickMarker = null; }
            };
        } else {
            // --- Départ / Arrivée ---
            var color = target === 'start' ? '#22c55e' : '#ef4444';
            if (pickMarkers[target]) map.removeLayer(pickMarkers[target]);
            pickMarkers[target] = L.marker([lat, lng], { icon: makePickIcon(color) })
                .bindTooltip(target === 'start' ? 'Départ' : 'Arrivée', { permanent: true, direction: 'top', offset: [0, -14] })
                .addTo(map);
            pickedCoords[target] = coordStr;
            var badgeEl = document.getElementById(target + '-badge');
            var badgeNameEl = document.getElementById(target + '-badge-name');
            badgeNameEl.textContent = 'Localisation...';
            badgeEl.style.display = 'flex';
            // Géocodage pour départ/arrivée
            reverseGeocode(lat, lng, badgeNameEl);
        }

        deactivatePickMode();
        if (navigator.vibrate) navigator.vibrate(40);
        if (window.innerWidth < 1024) {
            setTimeout(function () {
                scrollTo(document.getElementById('form-panel'));
            }, 400);
        }

        if (isWaypoint) {
            reverseGeocode(lat, lng, target.querySelector('.waypoint-badge-name'));
        }
    });

    function reverseGeocode(lat, lng, el) {
        fetch('https://nominatim.openstreetmap.org/reverse?lat=' + lat + '&lon=' + lng + '&format=json&accept-language=fr')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                el.textContent = data.display_name
                    ? data.display_name.split(',').slice(0, 2).join(', ')
                    : lat.toFixed(4) + ', ' + lng.toFixed(4);
            })
            .catch(function () { el.textContent = lat.toFixed(4) + ', ' + lng.toFixed(4); });
    }

    // ── Effacer badge ──
    document.getElementById('start-clear').addEventListener('click', function () {
        pickedCoords.start = null;
        if (pickMarkers.start) { map.removeLayer(pickMarkers.start); pickMarkers.start = null; }
        document.getElementById('start-badge').style.display = 'none';
    });
    document.getElementById('end-clear').addEventListener('click', function () {
        pickedCoords.end = null;
        if (pickMarkers.end) { map.removeLayer(pickMarkers.end); pickMarkers.end = null; }
        document.getElementById('end-badge').style.display = 'none';
    });

    // ── Escales ──
    document.getElementById('add-waypoint-btn').addEventListener('click', function () {
        var tmpl = document.getElementById('waypoint-template').content.cloneNode(true);
        var item = tmpl.querySelector('.waypoint-item');

        item.querySelector('.remove-waypoint-btn').addEventListener('click', function () {
            if (item._pickMarker) map.removeLayer(item._pickMarker);
            if (pickingMode === item) deactivatePickMode();
            item.remove();
        });

        item.querySelector('.pick-waypoint-btn').addEventListener('click', function () {
            if (pickingMode === item) { deactivatePickMode(); return; }
            activatePickMode(item);
        });

        document.getElementById('waypoints-container').appendChild(item);
    });

    function getCoord(target) {
        return pickedCoords[target] || null;
    }

    function getWaypointCoords() {
        var coords = [];
        document.querySelectorAll('.waypoint-item').forEach(function (item) {
            if (item._pickedCoord) coords.push(item._pickedCoord);
        });
        return coords;
    }

    // ── Résultats ──
    function showResults(distanceKm, isFallback) {
        var rentalSel = document.getElementById('rental-type');
        var selectedOption = rentalSel && rentalSel.selectedOptions[0];

        var prixType = selectedOption ? parseFloat(selectedOption.getAttribute('data-prix')) : NaN;
        var locationCost = isNaN(prixType) || prixType === 0 ? DAILY_PRICE : prixType;

        var consoType = selectedOption ? parseFloat(selectedOption.getAttribute('data-conso')) : NaN;
        var conso = isNaN(consoType) || consoType === 0 ? 8 : consoType;

        var fuelPriceAttr = selectedOption ? parseFloat(selectedOption.getAttribute('data-fuel-price')) : NaN;
        var PRIX_LITRE = isNaN(fuelPriceAttr) || fuelPriceAttr === 0 ? 4900 : fuelPriceAttr;
        var fuelCost = (distanceKm / 100) * conso * PRIX_LITRE;
        var total = locationCost + fuelCost;

        var labelEl = document.getElementById('res-rental-label');
        var costEl = document.getElementById('res-rental-cost');
        if (labelEl) labelEl.textContent = (selectedOption && selectedOption.value) ? selectedOption.text.split('—')[0].trim() : 'Location';
        if (costEl) costEl.textContent = Math.round(locationCost).toLocaleString('fr-FR') + ' Ar';

        document.getElementById('res-distance').textContent = distanceKm.toFixed(1);
        document.getElementById('res-fuel-cost').textContent = Math.round(fuelCost).toLocaleString('fr-FR');
        document.getElementById('res-total-cost').textContent = Math.round(total).toLocaleString('fr-FR');
        var fallbackNote = document.querySelector('#results-card .fallback-note');
        if (fallbackNote) fallbackNote.style.display = isFallback ? 'block' : 'none';

        var card = document.getElementById('results-card');
        card.style.display = 'block';
        if (window.innerWidth < 1024) {
            setTimeout(function () { scrollTo(card); }, 200);
        }
    }

    // ── Rendu de l'itinéraire sur la carte ──
    function drawRoute(geojson, coords) {
        if (routeLayer) map.removeLayer(routeLayer);
        markersLayer.clearLayers();
        routeLayer = L.geoJSON(geojson, { style: { color: '#4f46e5', weight: 5, opacity: 0.85 } }).addTo(map);
        coords.forEach(function (coord, i) {
            var parts = coord.split(',');
            var lon = parseFloat(parts[0]), lat = parseFloat(parts[1]);
            var color = i === 0 ? '#22c55e' : (i === coords.length - 1 ? '#ef4444' : '#3b82f6');
            var html = '<div style="background:' + color + ';width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4)"></div>';
            L.marker([lat, lon], { icon: L.divIcon({ html: html, className: '', iconSize: [16, 16], iconAnchor: [8, 8] }) }).addTo(markersLayer);
        });
        map.fitBounds(routeLayer.getBounds(), { padding: [30, 30] });
    }

    // Lance les deux requêtes en parallèle et retourne le premier résultat non-null
    function firstValid() {
        var promises = Array.prototype.slice.call(arguments);
        return new Promise(function (resolve) {
            var done = false;
            var pending = promises.length;
            promises.forEach(function (p) {
                p.then(function (v) {
                    if (!done && v !== null) { done = true; resolve(v); }
                }).finally(function () {
                    pending--;
                    if (pending === 0 && !done) resolve(null);
                });
            });
        });
    }

    // ── BRouter (meilleure qualité) ──
    async function calcBRouter(coords) {
        try {
            var url = 'https://brouter.de/brouter?lonlats=' + coords.join('|') + '&profile=car-eco&alternativeidx=0&format=geojson';
            var resp = await fetch(url);
            if (!resp.ok) return null;
            var geojson = await resp.json();
            if (!geojson.features || !geojson.features[0]) return null;
            drawRoute(geojson, coords);
            return parseFloat(geojson.features[0].properties['track-length']) / 1000;
        } catch (e) {
            return null;
        }
    }

    // ── Haversine (fallback local, sans appel réseau) ──
    function haversineKm(coord1, coord2) {
        var p1 = coord1.split(','), p2 = coord2.split(',');
        var lon1 = parseFloat(p1[0]), lat1 = parseFloat(p1[1]);
        var lon2 = parseFloat(p2[0]), lat2 = parseFloat(p2[1]);
        var R = 6371;
        var dLat = (lat2 - lat1) * Math.PI / 180;
        var dLon = (lon2 - lon1) * Math.PI / 180;
        var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    function calcFallback(coords) {
        var total = 0;
        for (var i = 0; i < coords.length - 1; i++) {
            total += haversineKm(coords[i], coords[i + 1]);
        }
        return Promise.resolve(total * 1.3);
    }

    // ── OSRM (fallback si BRouter échoue) ──
    async function calcOSRM(coords) {
        try {
            var waypoints = coords.join(';');
            var url = 'https://router.project-osrm.org/route/v1/driving/' + waypoints + '?overview=full&geometries=geojson';
            var resp = await fetch(url);
            if (!resp.ok) return null;
            var data = await resp.json();
            if (data.code !== 'Ok' || !data.routes || !data.routes[0]) return null;
            var geojson = {
                type: 'FeatureCollection',
                features: [{ type: 'Feature', geometry: data.routes[0].geometry, properties: {} }]
            };
            drawRoute(geojson, coords);
            return data.routes[0].distance / 1000;
        } catch (e) {
            return null;
        }
    }

    // ── Calculer ──
    document.getElementById('calculate-btn').addEventListener('click', async function () {
        var start = getCoord('start');
        var end = getCoord('end');
        if (!start || !end) {
            alert('Pointez ou sélectionnez un départ et une arrivée.');
            return;
        }
        var coords = [start].concat(getWaypointCoords()).concat([end]);

        document.getElementById('map-loader').style.display = 'flex';

        try {
            var distanceKm = await firstValid(calcBRouter(coords), calcOSRM(coords));
            var isFallback = false;
            if (distanceKm === null) {
                distanceKm = await calcFallback(coords);
                isFallback = true;
            }
            showResults(distanceKm, isFallback);
        } catch (e) {
            console.error(e);
            alert('Impossible de calculer l\'itinéraire. Vérifiez votre connexion ou réessayez.');
        } finally {
            document.getElementById('map-loader').style.display = 'none';
        }
    });

    // Forcer Leaflet à recalculer la taille après le rendu
    setTimeout(function () { map.invalidateSize(); }, 200);

})();
