// count numbers up from 0 on page load: put data-count-up on an element whose text is the number
(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const DURATION = 700;
    const ease = (t) => 1 - (1 - t) ** 3;
    const items = [];
    for (const el of document.querySelectorAll("[data-count-up]")) {
        const text = el.textContent.trim();
        const end = Number(text.replace(/[^\d.-]/g, ""));
        if (!Number.isFinite(end) || end <= 0) continue;
        // reserve the final width so surrounding text doesn't shift while digits are added
        el.style.display = "inline-block";
        el.style.minWidth = `${text.length}ch`;
        el.style.fontVariantNumeric = "tabular-nums";
        el.textContent = "0";
        items.push({ el, end, text });
    }
    if (!items.length) return;

    const start = performance.now();
    requestAnimationFrame(function tick(now) {
        const t = Math.min(1, (now - start) / DURATION);
        for (const { el, end, text } of items) el.textContent = t < 1 ? Math.round(end * ease(t)) : text;
        if (t < 1) requestAnimationFrame(tick);
    });
})();
