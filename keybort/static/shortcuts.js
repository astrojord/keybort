// single-key shortcuts: an element with data-shortcut="n" gets clicked (or focused, for fields)
// when that key is pressed. data-shortcut-label names it in the "?" help dialog
(() => {
    const dialog = document.getElementById("shortcuts-dialog");
    const list = dialog?.querySelector("[data-shortcut-list]");

    const editable = (el) => el?.closest("input, textarea, select, [contenteditable]:not([contenteditable=false])");
    const visible = (el) => el.checkVisibility?.() ?? el.offsetParent !== null;
    const field = (el) => el.matches("input, textarea, select");
    const targets = (key) => [...document.querySelectorAll(`[data-shortcut="${CSS.escape(key)}"]`)].filter(visible);

    function kbd(key) {
        const el = document.createElement("kbd");
        el.className = "kbd";
        el.textContent = key.toUpperCase();
        return el;
    }

    function openHelp() {
        const seen = new Set();
        const rows = [];
        for (const el of document.querySelectorAll("[data-shortcut]")) {
            const key = el.dataset.shortcut;
            if (seen.has(key) || !visible(el)) continue;
            seen.add(key);
            rows.push([key, el.dataset.shortcutLabel ?? el.getAttribute("aria-label") ?? el.textContent.trim()]);
        }
        rows.push(["?", "Show shortcuts"], ["Esc", "Close dialog / leave a field"]);
        list.replaceChildren(
            ...rows.map(([key, label]) => {
                const li = document.createElement("li");
                const name = document.createElement("span");
                name.textContent = label;
                li.append(name, kbd(key));
                return li;
            })
        );
        dialog.showModal();
    }

    document.addEventListener("keydown", (event) => {
        if (event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return;

        const active = document.activeElement;
        if (event.key === "Escape" && active?.matches("[data-shortcut]") && field(active) && !active.value) {
            active.blur();
            return;
        }
        if (editable(event.target) || document.querySelector("dialog[open]")) return;

        if (event.key === "?" && dialog) {
            event.preventDefault();
            openHelp();
            return;
        }

        const target = targets(event.key.toLowerCase())[0];
        if (!target) return;
        event.preventDefault();
        if (field(target)) {
            target.focus();
            target.select?.();
        } else {
            target.click();
        }
    });
})();
