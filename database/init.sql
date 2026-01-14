-- RUOLI
CREATE TABLE ruoli (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) UNIQUE NOT NULL
);

-- UTENTI
CREATE TABLE utenti (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nome VARCHAR(100),
    attivo BOOLEAN DEFAULT TRUE,
    ruolo_id INT REFERENCES ruoli(id)
);

-- LOG ACCESSI
CREATE TABLE log_accessi (
    id SERIAL PRIMARY KEY,
    utente_id INT REFERENCES utenti(id),
    data_accesso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip VARCHAR(50)
);

-- CATEGORIE
CREATE TABLE categorie (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL
);

-- FORNITORI
CREATE TABLE fornitori (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    contatto TEXT
);

-- PRODOTTI
CREATE TABLE prodotti (
    id SERIAL PRIMARY KEY,
    codice VARCHAR(50) UNIQUE NOT NULL,
    nome VARCHAR(200) NOT NULL,
    categoria_id INT REFERENCES categorie(id),
    unita_misura VARCHAR(20),
    scorta_minima INT DEFAULT 0,
    fornitore_id INT REFERENCES fornitori(id),
    attivo BOOLEAN DEFAULT TRUE
);



-- LOTTI
CREATE TABLE lotti (
    id SERIAL PRIMARY KEY,
    prodotto_id INT REFERENCES prodotti(id),
    numero_lotto VARCHAR(100),
    data_scadenza DATE,
    quantita INT CHECK (quantita >= 0),
    validato BOOLEAN DEFAULT FALSE
);

-- MOVIMENTI
CREATE TABLE movimenti (
    id SERIAL PRIMARY KEY,
    lotto_id INT REFERENCES lotti(id),
    tipo VARCHAR(20) CHECK (tipo IN ('CARICO','SCARICO','SMALTIMENTO','STORNO')),
    quantita INT NOT NULL,
    data_movimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    utente_id INT REFERENCES utenti(id),
    note TEXT
);

-- DOCUMENTI
CREATE TABLE documenti (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(30),
    numero_progressivo INT,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creato_da INT REFERENCES utenti(id),
    file_pdf TEXT
);

-- CONFIGURAZIONI
CREATE TABLE configurazioni (
    chiave VARCHAR(50) PRIMARY KEY,
    valore TEXT
);

-- STORICO MODIFICHE (AUDIT)
CREATE TABLE storico_modifiche (
    id SERIAL PRIMARY KEY,
    tabella VARCHAR(50),
    record_id INT,
    operazione VARCHAR(20),
    utente_id INT REFERENCES utenti(id),
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dettaglio TEXT
);

