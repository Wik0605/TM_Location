import { state, events } from './state.js';
import { getCoord, getWaypointCoords } from './pick.js';
import { calcBackend } from './routing.js';
import { telechargerDevisPDF } from '../devis-pdf.js';

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

    const coords = [start, ...getWaypointCoords(), end];
    document.getElementById('map-loader').style.display = 'flex';
    calcInFlight = true;
    try {
        const result = await calcBackend(coords);
        if (!result) {
            alert('Impossible de calculer l\'itinéraire. Réessayez.');
            return;
        }
        if (result.quotaExceeded) {
            quotaModal.style.display = 'flex';
            return;
        }
        state.itineraryToken = result.token;
        try {
            localStorage.setItem(`itinerary_token_${state.CAR_ID}`, result.token);
        } catch { /* localStorage indisponible */ }
        showResults(result.distanceKm, result.isFallback);
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
    const rentalLabel = selectedOption?.value
        ? selectedOption.text.split('—')[0].trim()
        : 'Location';
    updateDevisPrint({
        distanceKm,
        rentalLabel,
        locationCost,
        fuelCost,
        total,
    });

    const labelEl = document.getElementById('res-rental-label');
    const costEl = document.getElementById('res-rental-cost');
    if (labelEl)
        labelEl.textContent = selectedOption?.value
            ? selectedOption.text.split('—')[0].trim()
            : 'Location';
    if (costEl) costEl.textContent = `${Math.round(locationCost).toLocaleString('fr-FR')} Ar`;

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

function textOfBadge(id) {
    const el = document.getElementById(id);
    if (!el || el.offsetParent === null) return '';
    return (el.textContent || '').replace(/[✕\s]+$/g, '').trim();
}

function collectWaypointNames() {
    const names = [];
    document.querySelectorAll('.waypoint-badge').forEach((badge) => {
        if (badge.style.display === 'none') return;
        const nameEl = badge.querySelector('.waypoint-badge-name');
        const txt = (nameEl?.textContent || '').trim();
        if (txt) names.push(txt);
    });
    return names;
}

function formatDateTime(value) {
    if (!value) return '—';
    const d = new Date(value);
    if (isNaN(d)) return '—';
    return d.toLocaleString('fr-FR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function updateDevisPrint({ distanceKm, rentalLabel, locationCost, fuelCost, total }) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };
    const nowFmt = new Date().toLocaleDateString('fr-FR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
    });
    const start = textOfBadge('start-badge-name') || 'Non renseigné';
    const end = textOfBadge('end-badge-name') || 'Non renseigné';
    const waypoints = collectWaypointNames();
    const carName = document.querySelector('h1.font-display')?.textContent?.trim() || '';

    set('devis-print-date', nowFmt);
    set('devis-print-start', start);
    set('devis-print-end', end);
    set('devis-print-waypoints', waypoints.length ? waypoints.join(' → ') : 'Aucune');
    set('devis-print-distance', `${distanceKm.toFixed(1)} km`);
    set('devis-print-dt-start', formatDateTime(dtStart?.value));
    set('devis-print-dt-end', formatDateTime(dtEnd?.value));
    set('devis-print-duration', document.getElementById('duration-display')?.textContent || '—');
    set('devis-print-rental', rentalLabel);
    set('devis-print-rental-label', rentalLabel);
    set('devis-print-rental-cost', `${Math.round(locationCost).toLocaleString('fr-FR')} Ar`);
    set('devis-print-fuel-cost', `${Math.round(fuelCost).toLocaleString('fr-FR')} Ar`);
    set('devis-print-total', Math.round(total).toLocaleString('fr-FR'));

    const wa = document.getElementById('devis-whatsapp-btn');
    if (wa) {
        const totalFmt = Math.round(total).toLocaleString('fr-FR');
        const lines = [
            `Devis TM Location — ${nowFmt}`,
            `Véhicule : ${carName}`,
            `Itinéraire : ${start}${waypoints.length ? ' → ' + waypoints.join(' → ') : ''} → ${end}`,
            `Distance : ${distanceKm.toFixed(1)} km`,
            `Période : ${formatDateTime(dtStart?.value)} → ${formatDateTime(dtEnd?.value)}`,
            `Forfait : ${rentalLabel}`,
            `Total estimé : ${totalFmt} Ar`,
            ``,
            `Devis indicatif, valable 7 jours.`,
        ];
        wa.href = `https://wa.me/?text=${encodeURIComponent(lines.join('\n'))}`;
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

    const printBtn = document.getElementById('devis-print-btn');
    if (printBtn) {
        printBtn.addEventListener('click', () => {
            const devis = document.getElementById('devis-print');
            const dateStr = new Date().toISOString().slice(0, 10);
            telechargerDevisPDF(devis, `devis-${dateStr}.pdf`);
        });
    }

    restoreDraft();
}
