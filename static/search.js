document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("searchInput");
    const checkbox = document.getElementById("filterScadenza");
    const rows = document.querySelectorAll("table tbody tr");

    function applyFilters() {
        const search = input ? input.value.toLowerCase() : "";
        const onlyScadenza = checkbox ? checkbox.checked : false;
        const today = new Date();

        rows.forEach(row => {
            const text = row.innerText.toLowerCase();

            // ---- FILTRO TESTO ----
            const matchText = text.includes(search);

            // ---- FILTRO SCADENZA ----
            let matchScadenza = true;

            if (onlyScadenza) {
                const scadenzaCell = row.children[5]; // colonna "Scadenza"
                if (!scadenzaCell) {
                    matchScadenza = false;
                } else {
                    const value = scadenzaCell.innerText.trim();
                    if (value === "—") {
                        matchScadenza = false;
                    } else {
                        const scadenza = new Date(value);
                        const diffDays = (scadenza - today) / (1000 * 60 * 60 * 24);
                        matchScadenza = diffDays >= 0 && diffDays <= 30;
                    }
                }
            }

            // ---- MOSTRA / NASCONDI ----
            row.style.display = matchText && matchScadenza ? "" : "none";
        });
    }

    if (input) input.addEventListener("input", applyFilters);
    if (checkbox) checkbox.addEventListener("change", applyFilters);
});
