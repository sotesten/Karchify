// main.js — PaisaFlow brutalist interactions
// Animates mock-bar widths on view, reveals elements on scroll,
// adds micro-interactions (button shake, form focus effects).
// All UI changes are non-destructive: no markup or routes are altered.

(function () {
    'use strict';

    // ---------------------------------------------------------
    // Animate mock-bar widths when hero comes into view
    // ---------------------------------------------------------
    function animateBars() {
        const bars = document.querySelectorAll('.mock-bar');
        if (!bars.length) return;

        bars.forEach(bar => {
            const target = bar.dataset.width || bar.style.width || '0%';
            bar.dataset.width = target;
            bar.style.width = '0%';
        });

        const heroVisual = document.querySelector('.hero-visual');
        if (!heroVisual || !('IntersectionObserver' in window)) {
            bars.forEach(bar => { bar.style.width = bar.dataset.width; });
            return;
        }

        const obs = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    bars.forEach((bar, i) => {
                        setTimeout(() => {
                            bar.style.width = bar.dataset.width;
                        }, 200 + i * 120);
                    });
                    observer.disconnect();
                }
            });
        }, { threshold: 0.3 });

        obs.observe(heroVisual);
    }

    // ---------------------------------------------------------
    // Reveal-on-scroll
    // ---------------------------------------------------------
    function setupReveal() {
        const els = document.querySelectorAll('.reveal');
        if (!els.length || !('IntersectionObserver' in window)) {
            els.forEach(el => el.classList.add('is-in'));
            return;
        }

        const obs = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-in');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

        els.forEach(el => obs.observe(el));
    }

    // ---------------------------------------------------------
    // Form input micro-interaction: stamp the label chip on focus
    // ---------------------------------------------------------
    function setupFormInputs() {
        const inputs = document.querySelectorAll('.form-input');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                const label = input.closest('.form-group')?.querySelector('label span');
                if (label) {
                    label.style.background = 'var(--accent)';
                    label.style.color = 'var(--ink)';
                }
            });
            input.addEventListener('blur', () => {
                const label = input.closest('.form-group')?.querySelector('label span');
                if (label) {
                    label.style.background = '';
                    label.style.color = '';
                }
            });
        });
    }

    // ---------------------------------------------------------
    // Button ripple on click (visual only, no layout shift)
    // ---------------------------------------------------------
    function setupButtons() {
        const btns = document.querySelectorAll('.btn-primary, .btn-submit, .btn-secondary, .btn-ghost');
        btns.forEach(btn => {
            btn.addEventListener('click', e => {
                const rect = btn.getBoundingClientRect();
                const ripple = document.createElement('span');
                const size = Math.max(rect.width, rect.height);
                ripple.style.cssText = `
                    position: absolute;
                    width: ${size}px;
                    height: ${size}px;
                    left: ${e.clientX - rect.left - size / 2}px;
                    top: ${e.clientY - rect.top - size / 2}px;
                    background: var(--lime);
                    border-radius: 50%;
                    transform: scale(0);
                    pointer-events: none;
                    opacity: .55;
                    animation: ripple .55s ease-out;
                `;
                if (!document.getElementById('ripple-style')) {
                    const style = document.createElement('style');
                    style.id = 'ripple-style';
                    style.textContent = '@keyframes ripple { to { transform: scale(2.4); opacity: 0; } }';
                    document.head.appendChild(style);
                }
                btn.style.position = 'relative';
                btn.style.overflow = 'hidden';
                btn.appendChild(ripple);
                setTimeout(() => ripple.remove(), 600);
            });
        });
    }

    // ---------------------------------------------------------
    // Card tilt on hover (feature cards only)
    // ---------------------------------------------------------
    function setupCardTilt() {
        const cards = document.querySelectorAll('.feature-card, .mock-card');
        const supportsHover = window.matchMedia('(hover: hover)').matches;
        if (!supportsHover) return;

        cards.forEach(card => {
            card.addEventListener('mousemove', e => {
                const rect = card.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width - 0.5;
                const y = (e.clientY - rect.top) / rect.height - 0.5;
                card.style.transform = `translate(${x * 4}px, ${y * 4}px)`;
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    // ---------------------------------------------------------
    // Pause ticker on hover (accessibility — users can read it)
    // ---------------------------------------------------------
    function setupTicker() {
        const tickers = document.querySelectorAll('.ticker-track');
        tickers.forEach(t => {
            const parent = t.parentElement;
            if (!parent) return;
            parent.addEventListener('mouseenter', () => { t.style.animationPlayState = 'paused'; });
            parent.addEventListener('mouseleave', () => { t.style.animationPlayState = 'running'; });
        });
    }

    // ---------------------------------------------------------
    // Boot
    // ---------------------------------------------------------
    function init() {
        animateBars();
        setupReveal();
        setupFormInputs();
        setupButtons();
        setupCardTilt();
        setupTicker();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();