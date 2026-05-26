document.addEventListener('DOMContentLoaded', function() {
    // Initialisation de la carte Leaflet (Centrée sur Tana)
    const map = L.map('map').setView([-18.91, 47.52], 13);

    // Ajout du fond de carte OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    let routeLayer = null;
    let markersLayer = L.layerGroup().addTo(map);

    // Éléments du DOM
    const form = document.getElementById('route-form');
    const startSelect = document.getElementById('start-point');
    const endSelect = document.getElementById('end-point');
    const waypointsContainer = document.getElementById('waypoints-container');
    const addWaypointBtn = document.getElementById('add-waypoint-btn');
    const calculateBtn = document.getElementById('calculate-btn');
    const waypointTemplate = document.getElementById('waypoint-template');
    
    const resultsCard = document.getElementById('results-card');
    const mapLoader = document.getElementById('map-loader');
    
    // Valeurs de base
    const dailyPrice = parseFloat(document.getElementById('car-daily-price').dataset.price);

    // Gestion de l'ajout d'escale
    addWaypointBtn.addEventListener('click', () => {
        const clone = waypointTemplate.content.cloneNode(true);
        const item = clone.querySelector('.waypoint-item');
        
        // Bouton de suppression
        item.querySelector('.remove-waypoint-btn').addEventListener('click', () => {
            item.remove();
        });
        
        waypointsContainer.appendChild(item);
    });

    // Fonction de calcul de prix
    function updatePricing(distanceKm) {
        const consumption = parseFloat(document.getElementById('fuel-consumption').value) || 8;
        const fuelPrice = parseFloat(document.getElementById('fuel-price').value) || 4900;
        
        const fuelCost = (distanceKm / 100) * consumption * fuelPrice;
        const totalCost = dailyPrice + fuelCost;
        
        document.getElementById('res-distance').textContent = distanceKm.toFixed(1);
        document.getElementById('res-fuel-cost').textContent = fuelCost.toLocaleString('fr-MG', { maximumFractionDigits: 0 });
        document.getElementById('res-total-cost').textContent = totalCost.toLocaleString('fr-MG', { maximumFractionDigits: 0 });
        
        resultsCard.classList.remove('hidden');
    }

    // Calcul de l'itinéraire via BRouter
    calculateBtn.addEventListener('click', async () => {
        const start = startSelect.value;
        const end = endSelect.value;
        
        if (!start || !end) {
            alert("Veuillez sélectionner au minimum un point de départ et un point d'arrivée.");
            return;
        }

        // Récupérer toutes les coordonnées dans l'ordre
        const coords = [start];
        const waypoints = document.querySelectorAll('.waypoint-select');
        waypoints.forEach(wp => {
            if (wp.value) coords.push(wp.value);
        });
        coords.push(end);
        
        // Construction de l'URL BRouter
        // Profil standard car-eco (voiture)
        const lonlats = coords.join('|');
        const brouterUrl = `https://brouter.de/brouter?lonlats=${lonlats}&profile=car-eco&alternativeidx=0&format=geojson`;

        mapLoader.classList.remove('hidden');

        try {
            const response = await fetch(brouterUrl);
            if (!response.ok) throw new Error("Erreur lors de l'appel à BRouter");
            
            const geojson = await response.json();
            
            // Nettoyer la carte
            if (routeLayer) map.removeLayer(routeLayer);
            markersLayer.clearLayers();
            
            // Dessiner le trajet
            routeLayer = L.geoJSON(geojson, {
                style: {
                    color: '#4f46e5', // indigo-600
                    weight: 5,
                    opacity: 0.8
                }
            }).addTo(map);

            // Ajouter des marqueurs pour les points
            coords.forEach((coord, index) => {
                const [lon, lat] = coord.split(',');
                const isStart = index === 0;
                const isEnd = index === coords.length - 1;
                
                let color = '#3b82f6'; // bleu pour escales
                if (isStart) color = '#22c55e'; // vert pour départ
                if (isEnd) color = '#ef4444'; // rouge pour arrivée
                
                const markerHtml = `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`;
                const icon = L.divIcon({ html: markerHtml, className: 'custom-marker', iconSize: [14, 14], iconAnchor: [7, 7] });
                
                L.marker([lat, lon], { icon }).addTo(markersLayer);
            });

            // Ajuster la vue
            map.fitBounds(routeLayer.getBounds(), { padding: [30, 30] });

            // Extraire la distance totale des propriétés BRouter
            // distance en mètres
            const totalDistanceMeters = geojson.features[0].properties['track-length'];
            const distanceKm = totalDistanceMeters / 1000;
            
            // Mettre à jour le résumé
            updatePricing(distanceKm);

        } catch (error) {
            console.error(error);
            alert("Impossible de calculer l'itinéraire. L'API BRouter est peut-être indisponible.");
        } finally {
            mapLoader.classList.add('hidden');
        }
    });
});
