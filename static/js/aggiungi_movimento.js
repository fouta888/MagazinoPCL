// Controllo campo "Data Scadenza" solo per entrata
const tipoSelect = document.querySelector('select[name="tipo_movimento"]');
const scadenzaContainer = document.getElementById("scadenza-container");
const dataScadenzaInput = document.getElementById("data_scadenza");

// Nasconde il campo inizialmente
scadenzaContainer.style.display = "none";

// Mostra solo se entrata
tipoSelect.addEventListener("change", () => {
  if (tipoSelect.value === "entrata") {
    scadenzaContainer.style.display = "block";
  } else {
    scadenzaContainer.style.display = "none";
    dataScadenzaInput.value = "";
  }
});
