/*
multi-step modal forms: each step is a <fieldset data-step>. steps with data-path only show when the radio
named by the form's data-path-input has that value, the rest always show. the modal templates call this
from an inline script after htmx swaps them in
*/
window.initStepForm = (form) => {
    const pathInput = form.dataset.pathInput;
    // editing starts with everything filled in, so any step can be jumped to and saved from
    const freeNav = form.hasAttribute("data-free-nav");
    const steps = [...form.querySelectorAll("[data-step]")];
    const labels = [...form.querySelectorAll("[data-step-label]")];
    const button = (action) => form.querySelector(`[data-action="${action}"]`);
    let current = form.dataset.initialStep;

    // steps on the chosen path
    const activeSteps = () => {
        const path = form.querySelector(`input[name="${pathInput}"]:checked`)?.value ?? form.dataset.defaultPath;
        return steps.filter((step) => !step.dataset.path || step.dataset.path === path);
    };

    function sync() {
        const active = activeSteps();
        if (!active.some((step) => step.dataset.step === current)) current = active[0].dataset.step;
        const index = active.findIndex((step) => step.dataset.step === current);

        // disabled fieldsets skip validation and aren't submitted, so the other path's fields stay out of the way
        for (const step of steps) {
            step.hidden = step.dataset.step !== current;
            step.disabled = !active.includes(step);
        }
        for (const block of form.querySelectorAll("[data-source]")) {
            const source = block.closest("[data-step]").querySelector('input[name$="-source"]:checked')?.value;
            block.hidden = block.disabled = block.dataset.source !== source;
        }
        // only asked when the part currently on the board is being swapped out
        for (const block of form.querySelectorAll("[data-removal]")) {
            const step = block.closest("[data-step]");
            const source = step.querySelector('input[name$="-source"]:checked')?.value;
            let unchanged = source === block.dataset.currentSource;
            if (unchanged && source === "stock") unchanged = step.querySelector('select[name$="-stock"]').value === block.dataset.currentStock;
            block.hidden = block.disabled = unchanged;
        }
        for (const label of labels) {
            label.hidden = !active.some((step) => step.dataset.step === label.dataset.stepLabel);
            if (label.dataset.stepLabel === current) label.setAttribute("aria-current", "step");
            else label.removeAttribute("aria-current");
        }

        button("back").hidden = index === 0;
        button("next").hidden = index === active.length - 1;
        button("save").hidden = !freeNav && index !== active.length - 1;
    }

    function go(delta) {
        const active = activeSteps();
        const index = active.findIndex((step) => step.dataset.step === current);
        if (!active[index + delta]) return;
        if (delta > 0) {
            const invalid = [...active[index].elements].find((el) => !el.checkValidity());
            if (invalid) return invalid.reportValidity();
        }
        show(active[index + delta].dataset.step);
    }

    function show(step) {
        current = step;
        sync();
        form.querySelector("section").scrollTop = 0;
    }

    form.addEventListener("change", (event) => {
        if (event.target.name === pathInput || /-(source|stock)$/.test(event.target.name)) sync();
    });
    button("back").addEventListener("click", () => go(-1));
    button("next").addEventListener("click", () => go(1));
    for (const link of form.querySelectorAll("[data-goto]")) {
        link.addEventListener("click", () => show(link.dataset.goto));
    }
    // a problem on a step that isn't showing can't be pointed at, so go there first
    button("save").addEventListener("click", (event) => {
        const invalid = [...form.elements].find((el) => el.willValidate && !el.checkValidity());
        if (!invalid) return;
        event.preventDefault();
        show(invalid.closest("[data-step]").dataset.step);
        invalid.reportValidity();
    });
    // enter in a text field moves forward instead of submitting the whole form early
    form.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" || event.target.tagName === "TEXTAREA" || event.target.type === "submit") return;
        if (!button("next").hidden) {
            event.preventDefault();
            go(1);
        }
    });

    sync();
};
