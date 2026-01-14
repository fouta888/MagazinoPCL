--
-- PostgreSQL database dump
--

\restrict GzlPQ9NDJyO5k7lloNr7cz1xkHfewCzg3Y0kGJzbbCbZNvLdpUOmMsiSfu2cbDg

-- Dumped from database version 17.7
-- Dumped by pg_dump version 17.7

-- Started on 2026-01-06 16:10:11

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 222 (class 1259 OID 24680)
-- Name: categorie; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.categorie (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    descrizione text
);


ALTER TABLE public.categorie OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 24679)
-- Name: categorie_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.categorie_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.categorie_id_seq OWNER TO postgres;

--
-- TOC entry 4970 (class 0 OID 0)
-- Dependencies: 221
-- Name: categorie_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.categorie_id_seq OWNED BY public.categorie.id;


--
-- TOC entry 228 (class 1259 OID 25312)
-- Name: lotti; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lotti (
    id integer NOT NULL,
    prodotto_id integer NOT NULL,
    quantita integer DEFAULT 0 NOT NULL,
    data_scadenza date,
    posizione character varying(200),
    note text,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT lotti_quantita_check CHECK ((quantita >= 0))
);


ALTER TABLE public.lotti OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 25311)
-- Name: lotti_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.lotti_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lotti_id_seq OWNER TO postgres;

--
-- TOC entry 4971 (class 0 OID 0)
-- Dependencies: 227
-- Name: lotti_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.lotti_id_seq OWNED BY public.lotti.id;


--
-- TOC entry 226 (class 1259 OID 24710)
-- Name: movimenti; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.movimenti (
    id integer NOT NULL,
    prodotto_id integer NOT NULL,
    data_movimento timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tipo_movimento character varying(10) NOT NULL,
    quantita integer NOT NULL,
    categoria_prodotto character varying(100),
    misura_prodotto character varying(50),
    note text,
    data_scadenza date,
    categoria character varying(100),
    misura character varying(50),
    posizione text,
    lotto_id integer,
    CONSTRAINT movimenti_quantita_check CHECK ((quantita > 0)),
    CONSTRAINT movimenti_tipo_movimento_check CHECK (((tipo_movimento)::text = ANY ((ARRAY['entrata'::character varying, 'uscita'::character varying])::text[])))
);


ALTER TABLE public.movimenti OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 24709)
-- Name: movimenti_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.movimenti_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.movimenti_id_seq OWNER TO postgres;

--
-- TOC entry 4972 (class 0 OID 0)
-- Dependencies: 225
-- Name: movimenti_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.movimenti_id_seq OWNED BY public.movimenti.id;


--
-- TOC entry 224 (class 1259 OID 24691)
-- Name: prodotti; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prodotti (
    id integer NOT NULL,
    nome character varying(150) NOT NULL,
    categoria_id integer,
    descrizione text,
    posizione character varying(200),
    misura character varying(50),
    quantita integer DEFAULT 0 NOT NULL,
    quantita_minima integer DEFAULT 0,
    lotto character varying(100),
    data_scadenza date,
    note text,
    attivo boolean DEFAULT true,
    categoria character varying(50),
    posizione_fisica character varying(200),
    CONSTRAINT prodotti_quantita_check CHECK ((quantita >= 0)),
    CONSTRAINT prodotti_quantita_minima_check CHECK ((quantita_minima >= 0))
);


ALTER TABLE public.prodotti OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 24690)
-- Name: prodotti_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.prodotti_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.prodotti_id_seq OWNER TO postgres;

--
-- TOC entry 4973 (class 0 OID 0)
-- Dependencies: 223
-- Name: prodotti_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.prodotti_id_seq OWNED BY public.prodotti.id;


--
-- TOC entry 218 (class 1259 OID 24654)
-- Name: ruoli; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ruoli (
    id integer NOT NULL,
    nome character varying(50) NOT NULL
);


ALTER TABLE public.ruoli OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 24653)
-- Name: ruoli_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ruoli_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ruoli_id_seq OWNER TO postgres;

--
-- TOC entry 4974 (class 0 OID 0)
-- Dependencies: 217
-- Name: ruoli_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ruoli_id_seq OWNED BY public.ruoli.id;


--
-- TOC entry 220 (class 1259 OID 24663)
-- Name: utenti; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.utenti (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash text NOT NULL,
    ruolo_id integer,
    attivo boolean DEFAULT true
);


ALTER TABLE public.utenti OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 24662)
-- Name: utenti_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.utenti_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.utenti_id_seq OWNER TO postgres;

--
-- TOC entry 4975 (class 0 OID 0)
-- Dependencies: 219
-- Name: utenti_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.utenti_id_seq OWNED BY public.utenti.id;


--
-- TOC entry 4770 (class 2604 OID 24683)
-- Name: categorie id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categorie ALTER COLUMN id SET DEFAULT nextval('public.categorie_id_seq'::regclass);


--
-- TOC entry 4777 (class 2604 OID 25315)
-- Name: lotti id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lotti ALTER COLUMN id SET DEFAULT nextval('public.lotti_id_seq'::regclass);


--
-- TOC entry 4775 (class 2604 OID 24713)
-- Name: movimenti id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movimenti ALTER COLUMN id SET DEFAULT nextval('public.movimenti_id_seq'::regclass);


--
-- TOC entry 4771 (class 2604 OID 24694)
-- Name: prodotti id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prodotti ALTER COLUMN id SET DEFAULT nextval('public.prodotti_id_seq'::regclass);


--
-- TOC entry 4767 (class 2604 OID 24657)
-- Name: ruoli id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ruoli ALTER COLUMN id SET DEFAULT nextval('public.ruoli_id_seq'::regclass);


--
-- TOC entry 4768 (class 2604 OID 24666)
-- Name: utenti id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utenti ALTER COLUMN id SET DEFAULT nextval('public.utenti_id_seq'::regclass);


--
-- TOC entry 4958 (class 0 OID 24680)
-- Dependencies: 222
-- Data for Name: categorie; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.categorie (id, nome, descrizione) FROM stdin;
1	Sanitario	Materiale sanitario e primo soccorso
2	Antincendio	Attrezzature e dispositivi antincendio
3	DPI	Dispositivi di protezione individuale
\.


--
-- TOC entry 4964 (class 0 OID 25312)
-- Dependencies: 228
-- Data for Name: lotti; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.lotti (id, prodotto_id, quantita, data_scadenza, posizione, note, data_creazione) FROM stdin;
1	17	1	2026-05-31	\N	\N	2026-01-02 22:06:51.829774
\.


--
-- TOC entry 4962 (class 0 OID 24710)
-- Dependencies: 226
-- Data for Name: movimenti; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.movimenti (id, prodotto_id, data_movimento, tipo_movimento, quantita, categoria_prodotto, misura_prodotto, note, data_scadenza, categoria, misura, posizione, lotto_id) FROM stdin;
1	1	2026-01-01 00:00:00	entrata	2	1	XL	\N	2027-04-01	\N	\N	Armadio A1 (R1)	\N
2	2	2026-01-01 23:49:54.869807	entrata	6	1	Adulti	\N	\N	\N	\N	\N	\N
3	3	2026-01-02 00:00:00	entrata	5	1	Adulti	\N	2026-01-04	\N	\N	\N	\N
4	4	2026-01-02 17:26:22.889033	entrata	3	1	Pediatrico	\N	\N	\N	\N	\N	\N
5	5	2026-01-02 17:27:18.658415	entrata	4	1	Adulti	\N	\N	\N	\N	\N	\N
6	6	2026-01-02 17:28:04.284622	entrata	2	1	Pediatrico	\N	\N	\N	\N	\N	\N
7	7	2026-01-02 17:29:18.81321	entrata	16	1	pezzi	\N	\N	\N	\N	\N	\N
8	8	2026-01-02 17:30:48.803406	entrata	6	1	pezzi	\N	\N	\N	\N	\N	\N
9	9	2026-01-02 17:32:12.220909	entrata	3	1	0	\N	\N	\N	\N	\N	\N
10	10	2026-01-02 17:33:13.015864	entrata	2	1	1	\N	\N	\N	\N	\N	\N
11	11	2026-01-02 17:34:01.600582	entrata	10	1	2	\N	\N	\N	\N	\N	\N
12	12	2026-01-02 17:34:55.03572	entrata	1	1	3	\N	\N	\N	\N	\N	\N
13	13	2026-01-02 17:35:35.416484	entrata	5	1	4	\N	\N	\N	\N	\N	\N
14	14	2026-01-02 17:36:19.715189	entrata	6	1	5	\N	\N	\N	\N	\N	\N
15	15	2026-01-02 17:37:02.809368	entrata	5	1	6	\N	\N	\N	\N	\N	\N
16	16	2026-01-02 17:38:31.65424	entrata	3	1	0	\N	\N	\N	\N	\N	\N
17	17	2026-01-02 17:39:28.080124	entrata	6	1	00	\N	\N	\N	\N	\N	\N
18	3	2026-01-02 17:40:19.038296	entrata	3	1	000	\N	\N	\N	\N	\N	\N
19	18	2026-01-02 17:41:01.110883	entrata	3	1	1	\N	\N	\N	\N	\N	\N
20	19	2026-01-02 17:41:48.484483	entrata	8	1	2	\N	\N	\N	\N	\N	\N
21	20	2026-01-02 17:42:35.726943	entrata	4	1	3	\N	\N	\N	\N	\N	\N
22	3	2026-01-02 17:43:33.722329	entrata	9	1	4	\N	\N	\N	\N	\N	\N
23	21	2026-01-02 17:44:25.51924	entrata	2	1	5	\N	\N	\N	\N	\N	\N
24	22	2026-01-02 17:45:23.311169	entrata	7	1	1 litro	\N	\N	\N	\N	\N	\N
25	23	2026-01-02 17:46:05.290487	entrata	5	1	1 litro	\N	\N	\N	\N	\N	\N
26	24	2026-01-02 17:46:47.18174	entrata	8	1	pezzi	\N	\N	\N	\N	\N	\N
27	25	2026-01-02 17:47:32.687336	entrata	7	1	pezzi	\N	\N	\N	\N	\N	\N
28	26	2026-01-02 17:48:57.650743	entrata	4	1	8	\N	\N	\N	\N	\N	\N
29	27	2026-01-02 17:50:11.316853	entrata	7	1	10	\N	\N	\N	\N	\N	\N
30	28	2026-01-02 17:50:47.680239	entrata	1	1	12	\N	\N	\N	\N	\N	\N
31	29	2026-01-02 17:51:31.145872	entrata	1	1	18	\N	\N	\N	\N	\N	\N
32	30	2026-01-02 17:52:18.608353	entrata	4	1	20	\N	\N	\N	\N	\N	\N
33	31	2026-01-02 17:53:11.014167	entrata	27	1	Adulti	\N	\N	\N	\N	\N	\N
34	32	2026-01-02 17:53:57.101992	entrata	15	1	Pediatrico	\N	\N	\N	\N	\N	\N
35	33	2026-01-02 17:54:42.598857	entrata	30	1	pezzi	\N	\N	\N	\N	\N	\N
36	34	2026-01-02 17:55:28.629438	entrata	5	1	pezzi	\N	\N	\N	\N	\N	\N
37	35	2026-01-02 17:56:50.751519	entrata	2	1	Scatole	\N	\N	\N	\N	\N	\N
38	36	2026-01-02 17:58:38.079155	entrata	1	1	Busta	\N	\N	\N	\N	\N	\N
39	37	2026-01-02 18:00:07.473768	entrata	1	1	Pacco	\N	\N	\N	\N	\N	\N
40	38	2026-01-02 18:01:18.763951	entrata	3	1	pezzi	\N	\N	\N	\N	\N	\N
41	39	2026-01-02 18:02:11.964184	entrata	2	1	pezzi	\N	\N	\N	\N	\N	\N
42	40	2026-01-02 18:06:00.456806	entrata	1	1	Pediatrico	\N	\N	\N	\N	\N	\N
43	41	2026-01-02 18:07:06.479151	entrata	11	1	XL	\N	\N	\N	\N	\N	\N
44	41	2026-01-02 18:07:53.045159	entrata	10	1	L	\N	\N	\N	\N	\N	\N
45	41	2026-01-02 18:08:31.547604	entrata	12	1	M	\N	\N	\N	\N	\N	\N
46	41	2026-01-02 18:09:13.934828	entrata	13	1	S	\N	\N	\N	\N	\N	\N
47	1	2026-01-02 18:09:56.668211	entrata	2	1	XL	\N	\N	\N	\N	\N	\N
48	1	2026-01-02 18:10:34.364455	entrata	2	1	L	\N	\N	\N	\N	\N	\N
49	1	2026-01-02 18:11:10.178232	entrata	2	1	M	\N	\N	\N	\N	\N	\N
50	1	2026-01-02 18:11:46.702825	entrata	2	1	S	\N	\N	\N	\N	\N	\N
51	17	2026-01-02 22:06:51.829774	entrata	1	\N	\N	\N	2026-05-31	\N	\N	\N	1
\.


--
-- TOC entry 4960 (class 0 OID 24691)
-- Dependencies: 224
-- Data for Name: prodotti; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.prodotti (id, nome, categoria_id, descrizione, posizione, misura, quantita, quantita_minima, lotto, data_scadenza, note, attivo, categoria, posizione_fisica) FROM stdin;
2	Pallone Ambu	1	\N	Armadio A1 (R1)	Adulti	6	0	\N	2027-03-01	\N	t	\N	\N
33	Occhialini O2 	1	\N	Cassetto 7	pezzi	30	0	\N	2026-09-30	\N	t	\N	\N
34	Piastre DAE	1	\N	Cassetto 16	pezzi	5	0	\N	2028-06-02	\N	t	\N	\N
4	Pallone Ambu Pediatrico	1	\N	Armadio A1 (R1)	Pediatrico	3	0	\N	2027-07-02	\N	t	\N	\N
5	Resevoir Ambu Adulti	1	\N	Cassetto 5	Adulti	4	0	\N	2026-10-02	\N	t	\N	\N
6	Resevoir Ambu Pediatrico	1	\N	Cassetto 5	Pediatrico	2	0	\N	2026-09-30	\N	t	\N	\N
7	Filtro Ambu	1	\N	cassetto 6	pezzi	16	0	\N	2026-06-30	\N	t	\N	\N
8	Tubo Raccordo Ambu	1	\N	Cassetto 4	pezzi	6	0	\N	2027-08-02	\N	t	\N	\N
9	Maschere Ambu Bianca	1	\N	Cassetto 19	0	3	0	\N	2028-09-02	\N	t	\N	\N
10	Maschere Rosa Ambu	1	\N	Cassetto 10	1	2	0	\N	2026-11-02	\N	t	\N	\N
11	Maschere Ambu Gialla	1	\N	Cassetto 11	2	10	0	\N	2026-11-02	\N	t	\N	\N
12	Maschere Ambu Rosso	1	\N	Cassetto 12	3	1	0	\N	2027-05-02	\N	t	\N	\N
13	Maschere Ambu Verde	1	\N	Cassetto 13	4	5	0	\N	2029-09-02	\N	t	\N	\N
14	Maschere Ambu Azzurro	1	\N	Cassetto 14	5	6	0	\N	2028-09-02	\N	t	\N	\N
15	Maschere Ambu Blu	1	\N	Cassetto 15	6	5	0	\N	2028-05-02	\N	t	\N	\N
16	Cannule Guedel nero	1	\N	Cassetto 1	0	3	0	\N	2026-05-31	\N	t	\N	\N
17	Cannule Guedel Blu	1	\N	Cassetto 1	00	6	0	\N	2026-05-31	\N	t	\N	\N
35	Carta ECG	1	\N	Armadio A1 (R2)	Scatole	2	0	\N	2030-12-31	\N	t	\N	\N
18	Cannule Guedel Bianco	1	\N	Cassetto 2	1	3	0	\N	2026-05-31	\N	t	\N	\N
19	Cannule Guedel Verde	1	\N	Cassetto 2	2	8	0	\N	2027-02-28	\N	t	\N	\N
20	Cannule Guedel Giallo	1	\N	Cassetto A3	3	4	0	\N	2027-07-31	\N	t	\N	\N
3	Cannule Guedel Rosa	1	\N	Cassetto A3	4	17	0	\N	2027-10-31	\N	t	\N	\N
21	Cannule Guedel Azzorra	1	\N	Cassetto A3	5	2	0	\N	2026-11-30	\N	t	\N	\N
22	Sacca monouso aspiratore Rosa	1	\N	Armadio A1 (R4)	1 litro	7	0	\N	2029-04-30	\N	t	\N	\N
23	Sacca monouso aspiratore Verde	1	\N	Armadio A1 (R2)	1 litro	5	0	\N	2029-04-02	\N	t	\N	\N
24	Set aspirazione Yankauer con raccordo	1	\N	Armadio A1 (R2)	pezzi	8	0	\N	2029-01-31	\N	t	\N	\N
25	Raccordo finger typ	1	\N	Armadio A1 (R3)	pezzi	7	0	\N	2030-12-02	\N	t	\N	\N
26	Sondini aspirazione Blu	1	\N	Armadio A1 (R3)	8	4	0	\N	2026-05-31	\N	t	\N	\N
27	Sondini aspirazione Nero	1	\N	Armadio A1 (R3)	10	7	0	\N	2026-10-31	\N	t	\N	\N
28	Sondini aspirazione Bianco	1	\N	Armadio A1 (R3)	12	1	0	\N	2026-10-31	\N	t	\N	\N
29	Sondini aspirazione Roso	1	\N	Armadio A1 (R3)	18	1	0	\N	2026-05-31	\N	t	\N	\N
30	Sondini aspirazione Giallo	1	\N	Armadio A1 (R3)	20	4	0	\N	2026-05-31	\N	t	\N	\N
31	Maschere O2 Adulti	1	\N	Cassetto 22	Adulti	27	0	\N	2029-09-30	\N	t	\N	\N
32	Maschere O2 Pediatrico	1	\N	Cassetto 8	Pediatrico	15	0	\N	2027-06-30	\N	t	\N	\N
36	Elettrodi Per ECG	1	\N	Cassetto 18	Busta	1	0	\N	2027-02-28	\N	t	\N	\N
37	Maschere FFP2	1	\N	Armadio A1 (R3)	Pacco	1	0	\N	2026-08-31	\N	t	\N	\N
38	Valvola per Reservoir	1	\N	Armadio A1 (R4)	pezzi	3	0	\N	2029-03-31	\N	t	\N	\N
39	Cavi per ECG	1	\N	Cassetto 18	pezzi	2	0	\N	2030-12-31	\N	t	\N	\N
40	Sensore O2 Ped	1	\N	Armadio A1 (R2)	Pediatrico	1	0	\N	2030-12-31	\N	t	\N	\N
41	Guanti Non Sterili	1	\N	Scaffale A1	S	46	0	\N	2027-05-31	\N	t	\N	\N
1	Guanti Sterili	1	\N	Armadio A1 (R3)	S	10	0	\N	2027-06-30	\N	t	\N	\N
\.


--
-- TOC entry 4954 (class 0 OID 24654)
-- Dependencies: 218
-- Data for Name: ruoli; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ruoli (id, nome) FROM stdin;
1	Amministratore
2	Manager
3	Utente
\.


--
-- TOC entry 4956 (class 0 OID 24663)
-- Dependencies: 220
-- Data for Name: utenti; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.utenti (id, username, password_hash, ruolo_id, attivo) FROM stdin;
1	admin	scrypt:32768:8:1$2PyHyLBdWeTbpGnH$b16a3794c74b12e74d7ec1e10c9f13f5434adf5b967a075b344d931273ebde41f7f0d9edc6c4bfb39d7e64c5388de88b789c4087d441c616a64767855691a80d	1	t
\.


--
-- TOC entry 4976 (class 0 OID 0)
-- Dependencies: 221
-- Name: categorie_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.categorie_id_seq', 3, true);


--
-- TOC entry 4977 (class 0 OID 0)
-- Dependencies: 227
-- Name: lotti_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.lotti_id_seq', 1, true);


--
-- TOC entry 4978 (class 0 OID 0)
-- Dependencies: 225
-- Name: movimenti_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.movimenti_id_seq', 51, true);


--
-- TOC entry 4979 (class 0 OID 0)
-- Dependencies: 223
-- Name: prodotti_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.prodotti_id_seq', 41, true);


--
-- TOC entry 4980 (class 0 OID 0)
-- Dependencies: 217
-- Name: ruoli_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ruoli_id_seq', 3, true);


--
-- TOC entry 4981 (class 0 OID 0)
-- Dependencies: 219
-- Name: utenti_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.utenti_id_seq', 1, true);


--
-- TOC entry 4794 (class 2606 OID 24689)
-- Name: categorie categorie_nome_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categorie
    ADD CONSTRAINT categorie_nome_key UNIQUE (nome);


--
-- TOC entry 4796 (class 2606 OID 24687)
-- Name: categorie categorie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categorie
    ADD CONSTRAINT categorie_pkey PRIMARY KEY (id);


--
-- TOC entry 4802 (class 2606 OID 25322)
-- Name: lotti lotti_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lotti
    ADD CONSTRAINT lotti_pkey PRIMARY KEY (id);


--
-- TOC entry 4800 (class 2606 OID 24720)
-- Name: movimenti movimenti_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movimenti
    ADD CONSTRAINT movimenti_pkey PRIMARY KEY (id);


--
-- TOC entry 4798 (class 2606 OID 24703)
-- Name: prodotti prodotti_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prodotti
    ADD CONSTRAINT prodotti_pkey PRIMARY KEY (id);


--
-- TOC entry 4786 (class 2606 OID 24661)
-- Name: ruoli ruoli_nome_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ruoli
    ADD CONSTRAINT ruoli_nome_key UNIQUE (nome);


--
-- TOC entry 4788 (class 2606 OID 24659)
-- Name: ruoli ruoli_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ruoli
    ADD CONSTRAINT ruoli_pkey PRIMARY KEY (id);


--
-- TOC entry 4790 (class 2606 OID 24671)
-- Name: utenti utenti_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utenti
    ADD CONSTRAINT utenti_pkey PRIMARY KEY (id);


--
-- TOC entry 4792 (class 2606 OID 24673)
-- Name: utenti utenti_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utenti
    ADD CONSTRAINT utenti_username_key UNIQUE (username);


--
-- TOC entry 4807 (class 2606 OID 25323)
-- Name: lotti lotti_prodotto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lotti
    ADD CONSTRAINT lotti_prodotto_id_fkey FOREIGN KEY (prodotto_id) REFERENCES public.prodotti(id) ON DELETE CASCADE;


--
-- TOC entry 4805 (class 2606 OID 25328)
-- Name: movimenti movimenti_lotto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movimenti
    ADD CONSTRAINT movimenti_lotto_id_fkey FOREIGN KEY (lotto_id) REFERENCES public.lotti(id) ON DELETE SET NULL;


--
-- TOC entry 4806 (class 2606 OID 24721)
-- Name: movimenti movimenti_prodotto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.movimenti
    ADD CONSTRAINT movimenti_prodotto_id_fkey FOREIGN KEY (prodotto_id) REFERENCES public.prodotti(id);


--
-- TOC entry 4804 (class 2606 OID 24704)
-- Name: prodotti prodotti_categoria_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prodotti
    ADD CONSTRAINT prodotti_categoria_id_fkey FOREIGN KEY (categoria_id) REFERENCES public.categorie(id);


--
-- TOC entry 4803 (class 2606 OID 24674)
-- Name: utenti utenti_ruolo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.utenti
    ADD CONSTRAINT utenti_ruolo_id_fkey FOREIGN KEY (ruolo_id) REFERENCES public.ruoli(id) ON DELETE SET NULL;


-- Completed on 2026-01-06 16:10:13

--
-- PostgreSQL database dump complete
--

\unrestrict GzlPQ9NDJyO5k7lloNr7cz1xkHfewCzg3Y0kGJzbbCbZNvLdpUOmMsiSfu2cbDg

