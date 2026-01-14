-- ======================================================
-- Magazzino Sanitario e Antincendio – Schema completo
-- ======================================================

-- Elimina tabelle esistenti con dipendenze
DROP TABLE IF EXISTS movimenti CASCADE;
DROP TABLE IF EXISTS prodotti CASCADE;
DROP TABLE IF EXISTS categorie CASCADE;
DROP TABLE IF EXISTS utenti CASCADE;
DROP TABLE IF EXISTS ruoli CASCADE;

-- ========= RUOLI E UTENTI ==========

CREATE TABLE ruoli (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) UNIQUE NOT NULL
);

INSERT INTO ruoli (nome) VALUES 
('Amministratore'),
('Manager'),
('Utente');

CREATE TABLE utenti (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    ruolo_id INTEGER REFERENCES ruoli(id) ON DELETE SET NULL,
    attivo BOOLEAN DEFAULT TRUE
);

DELETE FROM utenti WHERE username='admin';
INSERT INTO utenti (username, password_hash, ruolo_id, attivo)
SELECT 
    'admin',
    'scrypt:32768:8:1$2PyHyLBdWeTbpGnH$b16a3794c74b12e74d7ec1e10c9f13f5434adf5b967a075b344d931273ebde41f7f0d9edc6c4bfb39d7e64c5388de88b789c4087d441c616a64767855691a80d',
    id,
    TRUE
FROM ruoli
WHERE nome='Amministratore';

-- ========= CATEGORIE PRODOTTI ==========

CREATE TABLE categorie (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    descrizione TEXT
);

INSERT INTO categorie (nome, descrizione) VALUES
('Sanitario', 'Materiale sanitario e primo soccorso'),
('Antincendio', 'Attrezzature e dispositivi antincendio'),
('DPI', 'Dispositivi di protezione individuale');

-- ========= PRODOTTI =========

CREATE TABLE prodotti (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,

    categoria_id INTEGER REFERENCES categorie(id),

    descrizione TEXT,

    posizione VARCHAR(200),   -- UN SOLO campo posizione

    misura VARCHAR(50),

    quantita INTEGER NOT NULL DEFAULT 0 CHECK (quantita >= 0),
    quantita_minima INTEGER DEFAULT 0 CHECK (quantita_minima >= 0),

    lotto VARCHAR(100),
    data_scadenza DATE,

    note TEXT,
    attivo BOOLEAN DEFAULT TRUE
);

-- ========= MOVIMENTI =========

CREATE TABLE movimenti (
    id SERIAL PRIMARY KEY,
    prodotto_id INTEGER NOT NULL REFERENCES prodotti(id),
    data_movimento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tipo_movimento VARCHAR(10) NOT NULL CHECK (tipo_movimento IN ('entrata', 'uscita')),
    quantita INTEGER NOT NULL CHECK (quantita > 0),

    categoria_prodotto VARCHAR(100),
    misura_prodotto VARCHAR(50),
    note TEXT
);

-- ======================================================
-- Fine dello schema
-- ======================================================
-- Aggiunge nuove colonne a prodotti
ALTER TABLE prodotti
ADD COLUMN IF NOT EXISTS categoria VARCHAR(50),
ADD COLUMN IF NOT EXISTS misura VARCHAR(50),
ADD COLUMN IF NOT EXISTS posizione_fisica VARCHAR(200);

-- Rende categoria_id nullable
ALTER TABLE prodotti
ALTER COLUMN categoria_id DROP NOT NULL;
UPDATE prodotti
SET categoria_id = 1
WHERE categoria_id IS NULL;



-- Aggiunge colonne alla tabella movimenti se non esistono già
ALTER TABLE movimenti
ADD COLUMN IF NOT EXISTS data_scadenza DATE,
ADD COLUMN IF NOT EXISTS posizione TEXT,
ADD COLUMN IF NOT EXISTS lotto_id INT REFERENCES lotti(id) ON DELETE SET NULL;

ALTER TABLE movimenti ADD COLUMN data_scadenza DATE;
ALTER TABLE movimenti ADD COLUMN posizione TEXT;



-- ======================================================
-- Creazione sicura della tabella Lotti
-- ======================================================

-- 1️⃣ Crea la tabella solo se non esiste
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


-- 2️⃣ Popola la tabella lotti dai prodotti esistenti
--    - Evita duplicati: inserisce solo prodotti che non hanno già un lotto
INSERT INTO lotti (prodotto_id, quantita, data_scadenza)
SELECT p.id, p.quantita, p.data_scadenza
FROM prodotti p
WHERE NOT EXISTS (
    SELECT 1 FROM lotti l WHERE l.prodotto_id = p.id
);

INSERT INTO lotti (prodotto_id, quantita, data_scadenza)
VALUES (%s, %s, %s);

INSERT INTO movimenti (prodotto_id, tipo_movimento, quantita, data_scadenza)
VALUES (%s, 'entrata', %s, %s);


SELECT id, quantita
FROM lotti
WHERE prodotto_id = %s
ORDER BY data_scadenza


INSERT INTO movimenti (prodotto_id, tipo_movimento, quantita)
VALUES (%s, 'uscita', %s);

SELECT
  p.id,
  p.nome,
  SUM(l.quantita) AS quantita_totale
FROM prodotti p
LEFT JOIN lotti l ON l.prodotto_id = p.id
GROUP BY p.id, p.nome;


SELECT
    p.id,
    p.nome,
    COALESCE(SUM(l.quantita), 0) AS quantita_totale,
    p.categoria_id,
    p.posizione,
    p.misura,
    p.quantita_minima
FROM prodotti p
LEFT JOIN lotti l ON l.prodotto_id = p.id
GROUP BY p.id;




-- ======================================================
-- Aggiornamento colonne prodotti e movimenti senza errori
-- ======================================================

-- Prodotti
ALTER TABLE prodotti
ADD COLUMN IF NOT EXISTS categoria VARCHAR(50),
ADD COLUMN IF NOT EXISTS posizione_fisica VARCHAR(200),
ADD COLUMN IF NOT EXISTS misura VARCHAR(50);

-- Movimenti
ALTER TABLE movimenti
ADD COLUMN IF NOT EXISTS data_scadenza DATE,
ADD COLUMN IF NOT EXISTS posizione TEXT,
ADD COLUMN IF NOT EXISTS categoria VARCHAR(100),
ADD COLUMN IF NOT EXISTS misura VARCHAR(50);

-- ======================================================
-- Controllo: mostra colonne e tipi
-- ======================================================

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'lotti';

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'prodotti';

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'movimenti';



ALTER TABLE movimenti
ADD COLUMN IF NOT EXISTS categoria VARCHAR(100),
ADD COLUMN IF NOT EXISTS misura VARCHAR(50);

ALTER TABLE prodotti
ADD COLUMN IF NOT EXISTS posizione VARCHAR(200);
UPDATE prodotti
SET quantita = quantita + 5
WHERE id = 1;

-- Controlla colonne della tabella movimenti
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'movimenti';

-- Controlla colonne della tabella prodotti
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'prodotti';






