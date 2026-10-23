window.initBulkSelect = ({ table, bar, url }) => {
    const tbody = table.tBodies[0];
    const all = table.tHead.querySelector("[data-bulk-all]");
    const boxes = () => [...tbody.querySelectorAll("input[data-bulk]")];
    const visible = () => boxes().filter((box) => !box.closest("tr").hidden);
    const selected = () => boxes().filter((box) => box.checked);

    function sync() {
        for (const box of boxes()) if (box.closest("tr").hidden) box.checked = false;
        const count = selected().length;
        const shown = visible();
        all.checked = shown.length > 0 && shown.every((box) => box.checked);
        all.indeterminate = count > 0 && !all.checked;
        all.disabled = shown.length === 0;
        bar.querySelector("[data-bulk-count]").textContent = `${count} selected`;
        bar.hidden = count === 0;
    }

    function check(boxes, checked) {
        for (const box of boxes) box.checked = checked;
        sync();
    }

    all.addEventListener("change", () => check(visible(), all.checked));
    tbody.addEventListener("change", (event) => {
        if (event.target.matches("input[data-bulk]")) sync();
    });
    bar.querySelector("[data-bulk-clear]").addEventListener("click", () => check(boxes(), false));
    bar.querySelector("[data-bulk-delete]").addEventListener("click", () => {
        const target = new URL(url, location.href);
        for (const box of selected()) target.searchParams.append("ids", box.value);
        htmx.ajax("GET", target.href, { target: "#page-dialog" });
    });

    document.addEventListener("rows-deleted", (event) => {
        for (const id of event.detail.ids) document.getElementById(id)?.remove();
    });
    new MutationObserver(sync).observe(tbody, { childList: true, subtree: true, attributeFilter: ["hidden"] });

    sync();
};
