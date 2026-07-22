import { state, events } from './state.js';
import { getCoord, getWaypointCoords } from './pick.js';
import { firstValid, calcBRouter, calcOSRM, calcFallback } from './routing.js';

let dtStart, dtEnd, durationDisplay, rentalSelect, chipsContainer, quotaModal;
let calcTimer = null;
let calcInFlight = false;
let lastCalcKey = null;

function currentCalcKey() {
    return [
        state.pickedCoords.start,
        state.pickedCoords.end,
        getWaypointCoords().join('|'),
        rentalSelect?.value,
    ].join('#');
}

export function scheduleCalculation() {
    if (calcTimer) clearTimeout(calcTimer);
    calcTimer = setTimeout(runCalculation, 700);
}

async function runCalculation() {
    const start = getCoord('start');
    const end = getCoord('end');
    const hasType = rentalSelect?.value;
    if (!start || !end || !hasType) return;

    const key = currentCalcKey();
    if (calcInFlight || key === lastCalcKey) return;

    try {
        const quotaRes = await fetch(`${window.location.pathname}/quota`, { method: 'POST' });
        const quota = await quotaRes.json();
        if (!quota.allowed) {
            quotaModal.style.display = 'flex';
            return;
        }
    } catch {
        /* laisse passer */
    }

    const coords = [start, ...getWaypointCoords(), end];
    document.getElementById('map-loader').style.display = 'flex';
    calcInFlight = true;
    try {
        let distanceKm = await firstValid(calcBRouter(coords), calcOSRM(coords));
        let isFallback = false;
        if (distanceKm === null) {
            distanceKm = await calcFallback(coords);
            isFallback = true;
        }
        showResults(distanceKm, isFallback);
        lastCalcKey = key;
        const hint = document.getElementById('calc-hint');
        if (hint) hint.style.display = 'none';
    } catch (e) {
        console.error(e);
    } finally {
        document.getElementById('map-loader').style.display = 'none';
        calcInFlight = false;
    }
}

function showResults(distanceKm, isFallback) {
    const selectedOption = rentalSelect?.selectedOptions[0];
    const prixType = selectedOption ? parseFloat(selectedOption.getAttribute('data-prix')) : NaN;
    const locationCost = isNaN(prixType) || prixType === 0 ? state.DAILY_PRICE : prixType;
    const consoType = selectedOption ? parseFloat(selectedOption.getAttribute('data-conso')) : NaN;
    const conso = isNaN(consoType) || consoType === 0 ? 8 : consoType;
    const fuelPriceAttr = selectedOption ? parseFloat(selectedOption.getAttribute('data-fuel-price')) : NaN;
    const PRIX_LITRE = isNaN(fuelPriceAttr) || fuelPriceAttr === 0 ? 4900 : fuelPriceAttr;
    const fuelCost = (distanceKm / 100) * conso * PRIX_LITRE + 30000;
    const total = locationCost + fuelCost;

    const labelEl = document.getElementById('res-rental-label');
    const costEl = document.getElementById('res-rental-cost');
    if (labelEl)
        labelEl.textContent = selectedOption?.value
            ? selectedOption.text.split('—')[0].trim()
            : 'Location';
    if (costEl) costEl.textContent = `${Math.round(locationCost).toLocaleString('fr-FR')} Ar`;

    document.getElementById('res-distance').textContent = distanceKm.toFixed(1);
    document.getElementById('res-fuel-cost').textContent = Math.round(fuelCost).toLocaleString('fr-FR');
    document.getElementById('res-total-cost').textContent = Math.round(total).toLocaleString('fr-FR');
    const fallbackNote = document.querySelector('#results-card .fallback-note');
    if (fallbackNote) fallbackNote.style.display = isFallback ? 'block' : 'none';

    document.getElementById('results-card').style.display = 'block';

    const stickyTotal = document.getElementById('sticky-total');
    const stickyCta = document.getElementById('sticky-cta');
    if (stickyTotal) stickyTotal.textContent = Math.round(total).toLocaleString('fr-FR');
    if (stickyCta) {
        stickyCta.style.display = 'block';
        document.body.classList.add('has-sticky-cta');
    }
}

function hideStickyIfIncomplete() {
    if (!state.pickedCoords.start || !state.pickedCoords.end) {
        const stickyCta = document.getElementById('sticky-cta');
        if (stickyCta) {
            stickyCta.style.display = 'none';
            document.body.classList.remove('has-sticky-cta');
        }
        const card = document.getElementById('results-card');
        if (card) card.style.display = 'none';
        lastCalcKey = null;
    }
}

function updateDuration() {
    if (!dtStart?.value || !dtEnd?.value) {
        if (durationDisplay) durationDisplay.style.display = 'none';
        return;
    }
    const diffMs = new Date(dtEnd.value) - new Date(dtStart.value);
    if (isNaN(diffMs) || diffMs <= 0) {
        if (durationDisplay) durationDisplay.style.display = 'none';
        return;
    }
    const totalHours = diffMs / 3600000;
    const days = Math.floor(totalHours / 24);
    const hours = Math.round(totalHours - days * 24);
    let txt = '';
    if (days > 0) txt += `${days} j`;
    if (hours > 0) txt += `${txt ? ' ' : ''}${hours} h`;
    if (!txt) txt = `${Math.round(diffMs / 60000)} min`;
    durationDisplay.textContent = txt;
    durationDisplay.style.display = 'inline';
}

function saveDraft() {
    try {
        const draft = {
            dtStart: dtStart?.value || '',
            dtEnd: dtEnd?.value || '',
            rentalType: rentalSelect?.value || '',
            start: state.pickedCoords.start,
            end: state.pickedCoords.end,
        };
        localStorage.setItem(state.DRAFT_KEY, JSON.stringify(draft));
    } catch {
        /* localStorage indisponible */
    }
}

function restoreDraft() {
    try {
        const raw = localStorage.getItem(state.DRAFT_KEY);
        if (!raw) return;
        const d = JSON.parse(raw);
        if (d.dtStart && dtStart) dtStart.value = d.dtStart;
        if (d.dtEnd && dtEnd) dtEnd.value = d.dtEnd;
        if (d.rentalType && rentalSelect) {
            rentalSelect.value = d.rentalType;
            const chip = chipsContainer?.querySelector(
                `.rental-chip[data-value="${d.rentalType}"]`
            );
            if (chip) chip.classList.add('is-selected');
        }
        updateDuration();
    } catch {
        /* JSON invalide */
    }
}

export function initResults() {
    quotaModal = document.getElementById('quota-modal');
    document.getElementById('quota-backdrop').addEventListener('click', () => {
        quotaModal.style.display = 'none';
    });
    document.getElementById('quota-close').addEventListener('click', () => {
        quotaModal.style.display = 'none';
    });

    rentalSelect = document.getElementById('rental-type');
    chipsContainer = document.getElementById('rental-type-chips');
    dtStart = document.getElementById('datetime-start');
    dtEnd = document.getElementById('datetime-end');
    durationDisplay = document.getElementById('duration-display');

    if (chipsContainer) {
        chipsContainer.querySelectorAll('.rental-chip').forEach((chip) => {
            chip.addEventListener('click', () => {
                chipsContainer
                    .querySelectorAll('.rental-chip')
                    .forEach((c) => c.classList.remove('is-selected'));
                chip.classList.add('is-selected');
                if (rentalSelect) rentalSelect.value = chip.getAttribute('data-value');
                saveDraft();
                scheduleCalculation();
            });
        });
    }

    dtStart?.addEventListener('change', () => {
        updateDuration();
        saveDraft();
        scheduleCalculation();
    });
    dtEnd?.addEventListener('change', () => {
        updateDuration();
        saveDraft();
        scheduleCalculation();
    });

    events.on('coordChange', () => {
        saveDraft();
        hideStickyIfIncomplete();
        scheduleCalculation();
    });

    restoreDraft();
}
