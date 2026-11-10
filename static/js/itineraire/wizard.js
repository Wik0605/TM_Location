import { state, events } from './state.js';

const wizard = document.getElementById('wizard');
let _currentStep = 1;

function showPanel(n) {
    if (!wizard) return;
    wizard.querySelectorAll('.step-panel').forEach((panel) => {
        const s = parseInt(panel.dataset.step, 10);
        panel.style.display = s === n ? 'flex' : 'none';
        panel.style.flexDirection = s === n ? 'column' : '';
        panel.style.gap = s === n ? '1rem' : '';
    });
}

function goToStep(n) {
    if (!wizard) return;
    _currentStep = n;
    wizard.dataset.step = n;
    showPanel(n);
    updateDots(n);
    wizard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    const stickyCta = document.getElementById('sticky-cta');
    if (stickyCta && n !== 3) {
        stickyCta.style.display = 'none';
        document.body.classList.remove('has-sticky-cta');
    }

    events.emit('stepChange', n);
}

function updateDots(activeStep) {
    wizard.querySelectorAll('.wizard-step-dot').forEach((dot) => {
        const s = parseInt(dot.dataset.step, 10);
        dot.classList.toggle('active', s === activeStep);
        dot.classList.toggle('done', s < activeStep);
    });
    wizard.querySelectorAll('.wizard-step-line').forEach((line, i) => {
        line.classList.toggle('done', i + 1 < activeStep);
    });
}

function flashError(el) {
    if (!el) return;
    el.classList.add('wizard-error-shake');
    setTimeout(() => el.classList.remove('wizard-error-shake'), 600);
}

function validateStep1() {
    const hasStart = !!state.pickedCoords.start;
    const hasEnd = !!state.pickedCoords.end;
    if (!hasStart) flashError(document.getElementById('start-search'));
    if (!hasEnd) flashError(document.getElementById('end-search'));
    return hasStart && hasEnd;
}

function validateStep2() {
    const dtStart = document.getElementById('datetime-start');
    const dtEnd = document.getElementById('datetime-end');
    const rentalType = document.getElementById('rental-type');
    const ok = dtStart?.value && dtEnd?.value && rentalType?.value;
    if (!dtStart?.value) flashError(dtStart);
    if (!dtEnd?.value) flashError(dtEnd);
    if (!rentalType?.value) flashError(document.getElementById('rental-type-chips'));
    return !!ok;
}

export function initWizard() {
    if (!wizard) return;
    showPanel(1);

    window.addEventListener('pageshow', (e) => {
        if (e.persisted) showPanel(_currentStep);
    });

    document.getElementById('wizard-next-1')?.addEventListener('click', () => {
        if (validateStep1()) goToStep(2);
    });

    document.getElementById('wizard-next-2')?.addEventListener('click', () => {
        if (validateStep2()) goToStep(3);
    });

    document.getElementById('wizard-prev-2')?.addEventListener('click', () => goToStep(1));
    document.getElementById('wizard-prev-3')?.addEventListener('click', () => goToStep(2));
}

export function currentStep() {
    return _currentStep;
}
