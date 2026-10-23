window.initTableFilter = ({ filter, table, search, empty, param }) => {
    const tbody = table.tBodies[0];
    const headers = [...table.tHead.rows[0].cells];
    const sortable = headers.filter((th) => th.dataset.sort);
    const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
    const sortIcons = { none: "fa-sort", ascending: "fa-sort-up", descending: "fa-sort-down" };
    const chip = (type) => filter.querySelector(`[data-filter="${CSS.escape(type)}"]`);

    const params = new URLSearchParams(location.search);
    let active = params.get(param) ?? "";
    if (!chip(active)) active = "";
    let query = (params.get("q") ?? "").trim();
    let sort = params.get("sort") ?? "";
    search.value = query;

    const rows = () => [...tbody.querySelectorAll("tr[data-type]")];
    const matches = (row) => !query || row.textContent.toLowerCase().includes(query.toLowerCase());
    const visible = (row, type) => (!type || row.dataset.type === type) && matches(row);

    function sortRows() {
        const key = sort.replace(/^-/, "");
        const direction = sort.startsWith("-") ? "descending" : "ascending";
        for (const th of sortable) {
            const current = th.dataset.sort === key ? direction : "none";
            th.setAttribute("aria-sort", current);
            th.querySelector("i").className = `fas ${sortIcons[current]} text-xs text-muted-foreground`;
        }

        const index = headers.findIndex((th) => th.dataset.sort === key);
        if (index < 0) return;
        const value = (row) => row.cells[index].dataset.sortValue ?? row.cells[index].textContent.trim();
        const sign = direction === "descending" ? -1 : 1;
        tbody.append(...rows().sort((a, b) => sign * collator.compare(value(a), value(b))));
    }

    function filterRows() {
        const all = rows();
        for (const button of filter.querySelectorAll("[data-filter]")) {
            const type = button.dataset.filter;
            const count = all.filter((row) => visible(row, type)).length;
            button.querySelector("[data-count]").textContent = count;
            button.dataset.variant = type === active ? "secondary" : "ghost";
            button.setAttribute("aria-pressed", type === active);
            button.toggleAttribute("data-empty", count === 0 && type !== active);
        }
        for (const row of all) row.hidden = !visible(row, active);

        const label = chip(active).dataset.label;
        empty.querySelector("[data-empty-title]").textContent = query ? `No ${label} match “${query}”` : `No ${label} yet`;
        for (const element of empty.querySelectorAll("[data-empty-action]")) element.hidden = Boolean(query);
    }

    function render() {
        const url = new URL(location);
        for (const [key, value] of [[param, active], ["q", query], ["sort", sort]]) {
            if (value) url.searchParams.set(key, value);
            else url.searchParams.delete(key);
        }
        history.replaceState(null, "", url);
        filter.dataset.active = active;
        sortRows();
        filterRows();
    }

    filter.addEventListener("click", (event) => {
        const button = event.target.closest("[data-filter]");
        if (!button) return;
        active = button.dataset.filter;
        render();
    });
    search.addEventListener("input", () => {
        query = search.value.trim();
        render();
    });
    for (const th of sortable) {
        th.querySelector("button").addEventListener("click", () => {
            sort = sort === th.dataset.sort ? `-${th.dataset.sort}` : th.dataset.sort;
            render();
        });
    }
    document.body.addEventListener("htmx:afterSettle", render);

    render();
};
