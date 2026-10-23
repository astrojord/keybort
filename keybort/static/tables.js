function setUrlParams(params) {
    const url = new URL(location);
    for (const [key, value] of Object.entries(params)) {
        url.searchParams.delete(key);
        for (const item of [value].flat()) if (item) url.searchParams.append(key, item);
    }
    history.replaceState(null, "", url);
}

function onRowsChanged(tbody, callback) {
    new MutationObserver(callback).observe(tbody, { childList: true });
}

function rowMatches(row, query) {
    return row.textContent.toLowerCase().includes(query.toLowerCase());
}

function updateEmpty(empty, title, filtered) {
    empty.querySelector("[data-empty-title]").textContent = title;
    for (const element of empty.querySelectorAll("[data-empty-action]")) element.hidden = filtered;
}

window.initTableSort = (table) => {
    const tbody = table.tBodies[0];
    const headers = [...table.tHead.rows[0].cells];
    const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
    const icons = { none: "fa-sort", ascending: "fa-sort-up", descending: "fa-sort-down" };
    let sort = new URLSearchParams(location.search).get("sort") ?? "";

    function sortRows() {
        const [key, direction] = sort.startsWith("-") ? [sort.slice(1), "descending"] : [sort, "ascending"];
        for (const th of headers.filter((th) => th.dataset.sort)) {
            const state = th.dataset.sort === key ? direction : "none";
            th.setAttribute("aria-sort", state);
            th.querySelector("i").className = `fas ${icons[state]} text-xs text-muted-foreground`;
        }

        const index = headers.findIndex((th) => th.dataset.sort === key);
        if (index < 0) return;
        const value = (row) => row.cells[index].dataset.sortValue ?? row.cells[index].textContent.trim();
        const sign = direction === "descending" ? -1 : 1;
        tbody.append(...[...tbody.rows].sort((a, b) => sign * collator.compare(value(a), value(b))));
    }

    table.tHead.addEventListener("click", (event) => {
        const th = event.target.closest("th[data-sort]");
        if (!th) return;
        sort = sort === th.dataset.sort ? `-${th.dataset.sort}` : th.dataset.sort;
        setUrlParams({ sort });
        sortRows();
    });
    document.body.addEventListener("htmx:afterSettle", sortRows);

    sortRows();
};
