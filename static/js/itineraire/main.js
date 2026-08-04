import { state } from './state.js';
import { initMap } from './map.js';
import { initPick } from './pick.js';
import { initSearch, attachSearchBox } from './search.js';
import { initResults } from './results.js';

const mapEl = document.getElementById('map');
state.DAILY_PRICE = parseFloat(mapEl.getAttribute('data-daily-price')) || 0;
state.CAR_ID = mapEl.getAttribute('data-car-id');
state.DRAFT_KEY = `itineraire-draft-${state.CAR_ID || window.location.pathname}`;

const map = initMap();
initPick({ attachSearch: attachSearchBox });
initSearch();
initResults();

map.whenReady(() => map.invalidateSize());
