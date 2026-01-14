-- =============================
-- AGGIORNAMENTO SICURO FIFO
-- =============================

-- 1️⃣ Crea tabella lotti se non esiste
CREATE TABLE IF NOT EXISTS lotti (
    id SERIAL PRIMARY KEY,
    prodotto_id INT NOT NULL
        REFERENCES prodotti(id) ON DELETE CASCADE,
    quantita INT NOT NULL DEFAULT 0 CHECK (quantita >= 0),
    data_scadenza DATE,
    posizione VARCHAR(200),
    note TEXT,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2️⃣ Aggiunge lotto_id ai movimenti
ALTER TABLE movimenti
ADD COLUMN IF NOT EXISTS lotto_id INT
REFERENCES lotti(id) ON DELETE SET NULL;

-- 3️⃣ Popola lotti dai prodotti (solo se non esistono)
INSERT INTO lotti (prodotto_id, quantita, data_scadenza)
SELECT p.id, p.quantita, p.data_scadenza
FROM prodotti p
WHERE NOT EXISTS (
    SELECT 1 FROM lotti l WHERE l.prodotto_id = p.id
);

-- 4️⃣ Allinea quantità prodotti ai lotti
UPDATE prodotti p
SET quantita = sub.totale
FROM (
    SELECT prodotto_id, SUM(quantita) AS totale
    FROM lotti
    GROUP BY prodotto_id
) sub
WHERE p.id = sub.prodotto_id;

-- 5️⃣ Elimina lotti vuoti
DELETE FROM lotti WHERE quantita = 0;
