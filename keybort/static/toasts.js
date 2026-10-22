const toastIcons = {
    success: "fa-circle-check",
    warning: "fa-triangle-exclamation",
    error: "fa-circle-exclamation",
    info: "fa-circle-info",
};

const escapeHtml = (text) => {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
};

document.addEventListener("messages", (event) => {
    const toaster = document.getElementById("toaster");
    if (!toaster?.toast) return;

    for (const { level, message } of event.detail.value) {
        const category = level in toastIcons ? level : "info";
        toaster.toast({
            category,
            description: escapeHtml(message),
            icon: `<i class="fas ${toastIcons[category]}"></i>`,
            cancel: { label: "Dismiss" },
        });
    }
});
