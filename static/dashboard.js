// Leggi i dati JSON incorporati nell'HTML
const data = JSON.parse(document.getElementById("dashboard-data").textContent);

// 🥧 Grafico Prodotti per Categoria (Torta)
new Chart(document.getElementById("prodottiChart"), {
  type: "pie",
  data: {
    labels: data.categorie_labels,
    datasets: [{
      data: data.categorie_quantita,
      backgroundColor: [
        "#6366f1", "#22c55e", "#f97316", "#ef4444", "#0ea5e9"
      ]
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false
  }
});

// 📊 Grafico Movimenti Entrate/Uscite (Bar)
new Chart(document.getElementById("movimentiChart"), {
  type: "bar",
  data: {
    labels: data.movimenti_labels,
    datasets: [
      {
        label: "Entrate",
        data: data.movimenti_entrata,
        backgroundColor: "#22c55e"
      },
      {
        label: "Uscite",
        data: data.movimenti_uscita,
        backgroundColor: "#ef4444"
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top"
      }
    }
  }
});
