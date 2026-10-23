window.initTableFilter = ({ filter, table, search, empty, param }) => {
    const tbody = table.tBodies[0];
    const chip = (type) => filter.querySelector(`[data-filter="${CSS.escape(type)}"]`);
    const params = new URLSearchParams(location.search);
    const initial = params.get(param) ?? "";
    let active = chip(initial) ? initial : "";
    search.value = params.get("q") ?? "";

    function render() {
        const query = search.value.trim();
        const visible = (row, type) => (!type || row.dataset.type === type) && rowMatches(row, query);
        const rows = [...tbody.rows];

        for (const button of filter.querySelectorAll("[data-filter]")) {
            const type = button.dataset.filter;
            const count = rows.filter((row) => visible(row, type)).length;
            button.querySelector("[data-count]").textContent = count;
            button.dataset.variant = type === active ? "secondary" : "ghost";
            button.setAttribute("aria-pressed", type === active);
            button.toggleAttribute("data-empty", count === 0 && type !== active);
        }
        for (const row of rows) row.hidden = !visible(row, active);

        const label = chip(active).dataset.label;
        updateEmpty(empty, query ? `No ${label} match “${query}”` : `No ${label} yet`, Boolean(query));
        filter.dataset.active = active;
        setUrlParams({ [param]: active, q: query });
    }

    filter.addEventListener("click", (event) => {
        const button = event.target.closest("[data-filter]");
        if (!button) return;
        active = button.dataset.filter;
        render();
    });
    search.addEventListener("input", render);
    onRowsChanged(tbody, render);

    initTableSort(table);
    render();
};
