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
    const text = [...row.cells].filter((cell) => cell.dataset.role !== "toggle").map((cell) => cell.textContent).join(" ");
    return text.toLowerCase().includes(query.toLowerCase());
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

        table.dispatchEvent(new CustomEvent("table-sorted", { detail: { sort } }));
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
    table.addEventListener("table-sort", (event) => {
        sort = event.detail.sort;
        setUrlParams({ sort });
        sortRows();
    });
    document.body.addEventListener("htmx:afterSettle", sortRows);

    sortRows();
};

window.initTableStack = (table) => {
    const tbody = table.tBodies[0];
    const headers = [...table.tHead.rows[0].cells];
    const labels = headers.map((th) => th.textContent.trim());

    // Only write when something changed, so the observer below doesn't retrigger itself
    function label() {
        for (const row of tbody.rows) {
            [...row.cells].forEach((td, i) => {
                if (td.dataset.role) return;
                const text = labels[i] ?? "";
                if (td.dataset.label !== text) td.dataset.label = text;
                const empty = !td.textContent.trim() && !td.querySelector("i, input, img");
                if (td.hasAttribute("data-empty") !== empty) td.toggleAttribute("data-empty", empty);
            });
            const toggle = row.querySelector("[data-row-toggle]");
            if (!toggle) continue;
            const count = row.querySelectorAll("td[data-secondary]:not([data-empty]):not([hidden])").length;
            if (toggle.hidden !== (count === 0)) toggle.hidden = count === 0;
            const counter = toggle.querySelector("[data-row-toggle-count]");
            if (counter.textContent !== ` · ${count}`) counter.textContent = ` · ${count}`;
        }
    }

    tbody.addEventListener("click", (event) => {
        const toggle = event.target.closest("[data-row-toggle]");
        if (toggle) {
            const expanded = toggle.closest("tr").toggleAttribute("data-expanded");
            toggle.setAttribute("aria-expanded", expanded);
            return;
        }
        const step = event.target.closest("[data-step]");
        if (step) {
            const input = step.closest("td").querySelector("input[type=number]");
            const before = input.value;
            Number(step.dataset.step) > 0 ? input.stepUp() : input.stepDown();
            if (input.value !== before) input.dispatchEvent(new Event("change", { bubbles: true }));
        }
    });

    const select = table.querySelector("[data-stack-sort]");
    if (select) {
        let current = new URLSearchParams(location.search).get("sort") ?? "";
        const buildOptions = () => {
            const options = [new Option("Default", "")];
            for (const th of headers.filter((th) => th.dataset.sort && !th.hidden)) {
                const name = th.textContent.trim();
                options.push(new Option(`${name} A→Z`, th.dataset.sort), new Option(`${name} Z→A`, `-${th.dataset.sort}`));
            }
            select.replaceChildren(...options);
            select.value = current;
        };
        select.addEventListener("change", () => {
            table.dispatchEvent(new CustomEvent("table-sort", { detail: { sort: select.value } }));
        });
        table.addEventListener("table-sorted", (event) => {
            current = event.detail.sort;
            select.value = current;
        });
        new MutationObserver(buildOptions).observe(table.tHead.rows[0], { subtree: true, attributeFilter: ["hidden"] });
        buildOptions();
    }

    new MutationObserver(label).observe(tbody, { childList: true, subtree: true, attributeFilter: ["hidden"] });
    label();
};
