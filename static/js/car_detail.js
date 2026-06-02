/* Carousel + Lightbox + Swipe — car_detail */
/* `photos` et `total` sont définis en inline dans le template */

let current = 0;

function carouselGoTo(index) {
    const prev = document.getElementById('slide-' + current);
    if (prev) prev.style.display = 'none';
    current = index;
    const next = document.getElementById('slide-' + current);
    if (next) next.style.display = 'block';

    const counter = document.getElementById('carousel-counter');
    if (counter) counter.textContent = current + 1;

    for (let i = 0; i < total; i++) {
        const dot   = document.getElementById('dot-'   + i);
        const thumb = document.getElementById('thumb-' + i);
        if (i === current) {
            if (dot)   { dot.classList.add('bg-white', 'scale-125'); dot.classList.remove('bg-white/50'); }
            if (thumb) { thumb.classList.add('border-primary'); thumb.classList.remove('border-transparent', 'opacity-60'); }
        } else {
            if (dot)   { dot.classList.remove('bg-white', 'scale-125'); dot.classList.add('bg-white/50'); }
            if (thumb) { thumb.classList.remove('border-primary'); thumb.classList.add('border-transparent', 'opacity-60'); }
        }
    }
}
function carouselNext() { carouselGoTo((current + 1) % total); }
function carouselPrev() { carouselGoTo((current - 1 + total) % total); }

/* Swipe tactile — carousel */
let touchStartX = 0;
document.addEventListener('DOMContentLoaded', () => {
    const carouselEl = document.getElementById('carousel');
    if (carouselEl) {
        carouselEl.addEventListener('touchstart', e => { touchStartX = e.changedTouches[0].screenX; }, { passive: true });
        carouselEl.addEventListener('touchend', e => {
            const diff = touchStartX - e.changedTouches[0].screenX;
            if (Math.abs(diff) > 40) diff > 0 ? carouselNext() : carouselPrev();
        }, { passive: true });
    }

    /* Swipe tactile — lightbox */
    const lb = document.getElementById('lightbox');
    if (lb) {
        let lbTouchStartX = 0;
        lb.addEventListener('touchstart', e => { lbTouchStartX = e.changedTouches[0].screenX; }, { passive: true });
        lb.addEventListener('touchend', e => {
            const diff = lbTouchStartX - e.changedTouches[0].screenX;
            if (Math.abs(diff) > 40) diff > 0 ? lightboxGoTo(lbCurrent + 1) : lightboxGoTo(lbCurrent - 1);
        }, { passive: true });
    }
});

/* Lightbox */
let lbCurrent = 0;

function openLightbox(index) {
    lbCurrent = index;
    const lb      = document.getElementById('lightbox');
    const lbImg   = document.getElementById('lightbox-img');
    const lbCount = document.getElementById('lightbox-counter');
    lbImg.src = photos[lbCurrent];
    if (lbCount) lbCount.textContent = lbCurrent + 1;
    lb.classList.remove('hidden');
    lb.classList.add('flex');
    document.body.style.overflow = 'hidden';
}
function closeLightbox() {
    const lb = document.getElementById('lightbox');
    lb.classList.add('hidden');
    lb.classList.remove('flex');
    document.body.style.overflow = '';
}
function closeLightboxOnBackdrop(e) {
    if (e.target === document.getElementById('lightbox')) closeLightbox();
}
function lightboxGoTo(index) {
    lbCurrent = (index + total) % total;
    document.getElementById('lightbox-img').src = photos[lbCurrent];
    const lbCount = document.getElementById('lightbox-counter');
    if (lbCount) lbCount.textContent = lbCurrent + 1;
}
function lightboxNext(e) { e.stopPropagation(); lightboxGoTo(lbCurrent + 1); }
function lightboxPrev(e) { e.stopPropagation(); lightboxGoTo(lbCurrent - 1); }

/* Navigation clavier */
document.addEventListener('keydown', e => {
    const lb = document.getElementById('lightbox');
    if (!lb || lb.classList.contains('hidden')) return;
    if (e.key === 'Escape')     closeLightbox();
    if (e.key === 'ArrowRight') lightboxGoTo(lbCurrent + 1);
    if (e.key === 'ArrowLeft')  lightboxGoTo(lbCurrent - 1);
});
