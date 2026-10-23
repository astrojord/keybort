window.initFilterCard = ({ card, table, empty, noun }) => {
    const tbody = table.tBodies[0];
    const search = card.querySelector("[data-filter-search]");
    const comboboxes = [...card.querySelectorAll(".combobox[data-filter-key]")];
    const clear = card.querySelector("[data-filter-clear]");
    const summary = card.querySelector("[data-filter-summary]");

    const chosen = (box) => [...box.querySelectorAll('[role="option"][aria-selected="true"]')].map((option) => option.dataset.value);
    const facetValues = (row, key) => (row.getAttribute(`data-facet-${key}`) ?? "").split("|");

    function render() {
        const query = search.value.trim();
        const filters = Object.fromEntries(comboboxes.map((box) => [box.dataset.filterKey, chosen(box)]));
        const active = Object.entries(filters).filter(([, values]) => values.length);
        const visible = (row) =>
            rowMatches(row, query) && active.every(([key, values]) => facetValues(row, key).some((value) => values.includes(value)));

        const rows = [...tbody.rows];
        for (const row of rows) row.hidden = !visible(row);
        const shown = rows.filter((row) => !row.hidden).length;
        const filtered = Boolean(query || active.length);

        summary.textContent = filtered ? `Showing ${shown} of ${rows.length} ${noun}` : `${rows.length} ${noun}`;
        clear.hidden = !filtered;
        updateEmpty(empty, filtered ? `No ${noun} match these filters` : `No ${noun} yet`, filtered);
        setUrlParams({ q: query, ...filters });
    }

    search.addEventListener("input", render);
    card.addEventListener("change", (event) => {
        if (comboboxes.includes(event.target)) render();
    });
    clear.addEventListener("click", () => {
        search.value = "";
        for (const box of comboboxes) box.selectNone?.();
        render();
    });
    onRowsChanged(tbody, render);

    initTableSort(table);
    render();
};
