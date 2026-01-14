from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from config import *
from functools import wraps  # import necessario per login_required e ruolo_required
import socket
import qrcode
import io
import base64
from flask import Flask, render_template

from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from flask import abort

from datetime import date
from flask import request
from datetime import date, timedelta
import math
from collections import defaultdict

from fpdf import FPDF
from flask import make_response


def is_admin():
    return session.get("ruolo") == "Amministratore"



app = Flask(__name__)
app.secret_key = SECRET_KEY

# -------- DATABASE --------
def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

# -------- PROTEZIONE --------
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

def ruolo_required(*ruoli):
    def decorator(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            if session.get("ruolo") not in ruoli:
                flash("Accesso non autorizzato")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrap
    return decorator




@app.route("/qr")
#@login_required  # opzionale, puoi rimuoverlo se vuoi che sia accessibile a chiunque
def qr_code():
    import socket, io, base64, qrcode

    # Ottieni IP locale
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip_locale = s.getsockname()[0]
    finally:
        s.close()

    porta = 5000
    # Ora punta alla pagina di login
    url = f"http://{ip_locale}:{porta}/"

    # Genera QR code
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Converti immagine in base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return render_template("qr.html", qr_b64=qr_b64, url=url)


# -------- LOGIN --------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()
        cur.execute("""
            SELECT u.id, u.password_hash, r.nome
            FROM utenti u
            JOIN ruoli r ON u.ruolo_id = r.id
            WHERE username=%s AND attivo=TRUE
        """, (username,))
        user = cur.fetchone()
        db.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["ruolo"] = user[2]
            return redirect(url_for("dashboard"))
        else:
            flash("Credenziali non valide")

    return render_template("login.html")

# -------- LOGOUT --------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------- UTENTI --------
# GET + POST per visualizzare e aggiungere utenti
@app.route("/utenti", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore", "Manager")  # Admin e Manager possono accedere
def utenti_view():
    db = get_db()
    cur = db.cursor()
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        ruolo_id = int(request.form["ruolo"])  # Converti in intero

        # Recupera tutti i ruoli disponibili
        cur.execute("SELECT id, nome FROM ruoli ORDER BY id")
        tutti_ruoli = cur.fetchall()

        # Determina i ruoli consentiti in base all'utente loggato
        if session.get("ruolo") == "Amministratore":
            ruoli_consentiti = [r[0] for r in tutti_ruoli]  # tutti i ruoli
        elif session.get("ruolo") == "Manager":
            ruoli_consentiti = [r[0] for r in tutti_ruoli if r[1] == "Utente"]  # solo Utente
        else:
            ruoli_consentiti = []

        # Controlla se il ruolo selezionato è consentito
        if ruolo_id not in ruoli_consentiti:
            flash("Non puoi creare un utente con questo ruolo!")
            db.close()
            return redirect(url_for("utenti_view"))

        # Controllo se lo username esiste già
        cur.execute("SELECT id FROM utenti WHERE username=%s", (username,))
        if cur.fetchone():
            flash("Username già esistente")
        else:
            password_hash = generate_password_hash(password)
            cur.execute("""
                INSERT INTO utenti (username, password_hash, ruolo_id, attivo)
                VALUES (%s, %s, %s, TRUE)
            """, (username, password_hash, ruolo_id))
            db.commit()
            flash("Utente creato correttamente")

    # Lista utenti e ruoli
    cur.execute("SELECT u.id, u.username, r.nome, u.attivo FROM utenti u JOIN ruoli r ON u.ruolo_id = r.id ORDER BY u.username")
    utenti = cur.fetchall()
    cur.execute("SELECT id, nome FROM ruoli ORDER BY id")
    ruoli = cur.fetchall()
    
    db.close()
    return render_template("utenti.html", utenti=utenti, ruoli=ruoli)


@app.route("/lotti")
@login_required
@ruolo_required("Amministratore", "Manager", "Utente")
def lotti_view():
    conn = get_db()
    cur = conn.cursor()

    # 1. Recupero i dati dei lotti (il tuo codice originale)
    cur.execute("""
        SELECT
            l.id,
            p.nome,
            l.quantita,
            l.data_scadenza,
            p.posizione
        FROM lotti l
        JOIN prodotti p ON l.prodotto_id = p.id
        ORDER BY l.data_scadenza ASC
    """)
    lotti = cur.fetchall()

    # 2. AGGIUNTA: Recupero gli anni dai movimenti per il menu PDF
    # Usiamo DISTINCT per non avere doppioni e ORDER BY per l'anno più recente in alto
    cur.execute("""
        SELECT DISTINCT EXTRACT(YEAR FROM data_movimento)::int as anno 
        FROM movimenti 
        ORDER BY anno DESC
    """)
    anni_report = [r[0] for r in cur.fetchall()]

    # Ora posso chiudere la connessione
    conn.close()

    oggi = date.today()
    soglia_scadenza = oggi + timedelta(days=7)

    # 3. Invio tutto al template, inclusa la nuova lista anni_report
    return render_template(
        "lotti.html",
        lotti=lotti,
        anni_report=anni_report,  # <--- Passiamo i dati al template
        oggi=oggi,
        soglia_scadenza=soglia_scadenza
    )


@app.route("/lotti/carico", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore", "Manager")
def carico_lotto():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        prodotto_id = int(request.form["prodotto_id"])
        quantita = int(request.form["quantita"])
        data_scadenza = request.form.get("data_scadenza")

        # ✅ FIX DATE VUOTA
        if not data_scadenza:
            data_scadenza = None

        # 1️⃣ Controlla se esiste già un lotto con stessa scadenza
        cur.execute("""
            SELECT id
            FROM lotti
            WHERE prodotto_id = %s AND data_scadenza IS NOT DISTINCT FROM %s
        """, (prodotto_id, data_scadenza))
        lotto = cur.fetchone()

        if lotto:
            # Aggiorna quantità lotto esistente
            cur.execute("""
                UPDATE lotti
                SET quantita = quantita + %s
                WHERE id = %s
            """, (quantita, lotto[0]))
            lotto_id = lotto[0]
        else:
            # Crea nuovo lotto
            cur.execute("""
                INSERT INTO lotti (prodotto_id, quantita, data_scadenza)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (prodotto_id, quantita, data_scadenza))
            lotto_id = cur.fetchone()[0]

        # 2️⃣ Aggiorna quantità totale prodotto
        cur.execute("""
            UPDATE prodotti
            SET quantita = quantita + %s
            WHERE id = %s
        """, (quantita, prodotto_id))

        # 3️⃣ Registra movimento
        cur.execute("""
            INSERT INTO movimenti (
                prodotto_id,
                lotto_id,
                tipo_movimento,
                quantita,
                data_scadenza
            )
            VALUES (%s, %s, 'entrata', %s, %s)
        """, (prodotto_id, lotto_id, quantita, data_scadenza))

        conn.commit()
        conn.close()

        flash("✅ Carico lotto effettuato correttamente", "success")
        return redirect(url_for("lotti_view"))

    # GET → prodotti per select
    cur.execute("SELECT id, nome FROM prodotti ORDER BY nome")
    prodotti = cur.fetchall()
    conn.close()

    return render_template("carico_lotto.html", prodotti=prodotti)


@app.route("/lotti/uscita", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore", "Manager")
def uscita_lotto():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        prodotto_id = int(request.form["prodotto_id"])
        quantita_da_scaricare = int(request.form["quantita"])

        # 🔒 Controllo quantità totale prodotto (Backend)
        cur.execute("SELECT quantita FROM prodotti WHERE id = %s", (prodotto_id,))
        qta_totale = cur.fetchone()[0]

        if qta_totale < quantita_da_scaricare:
            conn.close()
            flash("❌ Quantità insufficiente a magazzino", "error")
            return redirect(url_for("uscita_lotto"))

        oggi = date.today()

        # 🔒 SOLO lotti NON scaduti (Logica FIFO)
        cur.execute("""
            SELECT id, quantita, data_scadenza
            FROM lotti
            WHERE prodotto_id = %s
              AND quantita > 0
              AND (data_scadenza IS NULL OR data_scadenza >= %s)
            ORDER BY data_scadenza ASC NULLS LAST
        """, (prodotto_id, oggi))

        lotti = cur.fetchall()
        restante = quantita_da_scaricare

        for lotto_id, qta_lotto, data_scadenza in lotti:
            if restante <= 0: break
            
            if qta_lotto <= restante:
                cur.execute("UPDATE lotti SET quantita = 0 WHERE id = %s", (lotto_id,))
                movimento_qta = qta_lotto
                restante -= qta_lotto
            else:
                cur.execute("UPDATE lotti SET quantita = quantita - %s WHERE id = %s", (restante, lotto_id))
                movimento_qta = restante
                restante = 0

            cur.execute("""
                INSERT INTO movimenti (prodotto_id, lotto_id, tipo_movimento, quantita)
                VALUES (%s, %s, 'uscita', %s)
            """, (prodotto_id, lotto_id, movimento_qta))

        if restante > 0:
            conn.rollback()
            conn.close()
            flash("❌ Quantità insufficiente nei lotti validi (scadenza futura)", "error")
            return redirect(url_for("uscita_lotto"))

        # 📉 Aggiorna quantità prodotto totale
        cur.execute("UPDATE prodotti SET quantita = quantita - %s WHERE id = %s", (quantita_da_scaricare, prodotto_id))
        cur.execute("DELETE FROM lotti WHERE quantita = 0")

        conn.commit()
        conn.close()
        flash("✅ Scarico effettuato correttamente", "success")
        return redirect(url_for("lotti_view"))

    # --- MODIFICA GET QUI ---
    cur.execute("SELECT id, nome, quantita FROM prodotti WHERE quantita > 0 ORDER BY nome")
    prodotti = cur.fetchall()
    conn.close()
    return render_template("uscita_lotto.html", prodotti=prodotti)


@app.route("/lotti/aggiorna_nota", methods=["POST"])
@ruolo_required("Amministratore", "Manager")
def aggiorna_nota():
    data = request.get_json()
    lotto_id = data.get("lotto_id")
    note = data.get("note")

    if not lotto_id:
        return "ID lotto mancante", 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE lotti SET note = %s WHERE id = %s", (note, lotto_id))
    conn.commit()
    conn.close()

    return "OK", 200



@app.route("/prodotti/note/<int:prodotto_id>", methods=["POST"])
@ruolo_required("Amministratore", "Manager")
def salva_note(prodotto_id):
    data = request.get_json()
    note = data.get("note", "")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE prodotti SET note = %s WHERE id = %s", (note, prodotto_id))
    conn.commit()
    conn.close()
    return "", 200



@app.route("/lotti/<int:lotto_id>/movimenti")
@login_required
@ruolo_required("Amministratore", "Manager", "Utente")
def storico_lotto(lotto_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT m.id, m.tipo_movimento, m.quantita, m.data_movimento, p.nome
        FROM movimenti m
        JOIN prodotti p ON m.prodotto_id = p.id
        WHERE m.lotto_id = %s
        ORDER BY m.data_movimento DESC
    """, (lotto_id,))

    movimenti = cur.fetchall()
    conn.close()

    return render_template("storico_lotto.html", movimenti=movimenti)


@app.route("/lotti/<int:lotto_id>/modifica", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore", "Manager")
def modifica_lotto(lotto_id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        quantita = int(request.form["quantita"])
        data_scadenza = request.form.get("data_scadenza")

        cur.execute("""
            UPDATE lotti
            SET quantita = %s,
                data_scadenza = %s
            WHERE id = %s
        """, (quantita, data_scadenza, lotto_id))

        conn.commit()
        conn.close()
        flash("✅ Lotto aggiornato correttamente", "success")
        return redirect(url_for("lotti_view"))

    # GET → carica dati lotto
    cur.execute("""
        SELECT l.id, p.nome, l.quantita, l.data_scadenza
        FROM lotti l
        JOIN prodotti p ON l.prodotto_id = p.id
        WHERE l.id = %s
    """, (lotto_id,))
    lotto = cur.fetchone()
    conn.close()

    return render_template("modifica_lotto.html", lotto=lotto)



@app.route("/lotti/<int:lotto_id>/elimina", methods=["POST", "GET"])
@login_required
@ruolo_required("Amministratore")
def elimina_lotto(lotto_id):
    conn = get_db()
    cur = conn.cursor()

    # Elimina prima i movimenti collegati (sicurezza)
    cur.execute("DELETE FROM movimenti WHERE lotto_id = %s", (lotto_id,))

    # Elimina il lotto
    cur.execute("DELETE FROM lotti WHERE id = %s", (lotto_id,))

    conn.commit()
    conn.close()

    flash("🗑️ Lotto eliminato correttamente", "success")
    return redirect(url_for("lotti_view"))



@app.route("/movimenti/elimina/<int:movimento_id>")
@ruolo_required("Amministratore", "Manager")
@login_required
def elimina_movimento(movimento_id):
    db = get_db()
    cur = db.cursor()
    # Cancella il movimento
    cur.execute("DELETE FROM movimenti WHERE id = %s", (movimento_id,))
    db.commit()
    db.close()
    return redirect(url_for("movimenti_view"))


# -------- ELIMINA UTENTE --------
@app.route("/utenti/elimina/<int:utente_id>")
@login_required
@ruolo_required("Amministratore", "Manager")  # Admin e Manager possono eliminare utenti
def elimina_utente(utente_id):
    db = get_db()
    cur = db.cursor()

    # Evita di eliminare l'utente admin principale
    cur.execute("SELECT username FROM utenti WHERE id=%s", (utente_id,))
    utente = cur.fetchone()
    if utente and utente[0].lower() == "admin":
        flash("Non puoi eliminare l'utente admin principale")
        db.close()
        return redirect(url_for("utenti_view"))

    cur.execute("DELETE FROM utenti WHERE id=%s", (utente_id,))
    db.commit()
    db.close()
    flash("Utente eliminato correttamente")
    return redirect(url_for("utenti_view"))



# -------- MODIFICA / ATTIVA / DISATTIVA UTENTE --------
@app.route("/utenti/modifica/<int:utente_id>", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore")
def modifica_utente(utente_id):
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        username = request.form.get("username")
        ruolo_id = request.form.get("ruolo")
        attivo = request.form.get("attivo") == "on"  # checkbox
        password = request.form.get("password")

        if password:
            password_hash = generate_password_hash(password)
            cur.execute("""
                UPDATE utenti
                SET username=%s, ruolo_id=%s, attivo=%s, password_hash=%s
                WHERE id=%s
            """, (username, ruolo_id, attivo, password_hash, utente_id))
        else:
            cur.execute("""
                UPDATE utenti
                SET username=%s, ruolo_id=%s, attivo=%s
                WHERE id=%s
            """, (username, ruolo_id, attivo, utente_id))
        
        db.commit()
        db.close()
        return redirect(url_for("utenti"))

    # GET: mostra form con dati dell'utente
    cur.execute("SELECT id, username, ruolo_id, attivo FROM utenti WHERE id=%s", (utente_id,))
    utente = cur.fetchone()
    cur.execute("SELECT id, nome FROM ruoli ORDER BY id")
    ruoli = cur.fetchall()
    db.close()

    return render_template("modifica_utente.html", utente=utente, ruoli=ruoli)


@app.route("/utenti/disattiva/<int:utente_id>")
@login_required
@ruolo_required("Amministratore")
def disattiva_utente(utente_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE utenti SET attivo=FALSE WHERE id=%s", (utente_id,))
    db.commit()
    db.close()
    return redirect(url_for("utenti"))


# -------- DASHBOARD --------

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    cur = conn.cursor()

    ruolo = session.get("ruolo")

    # =========================
    # CARD DATI
    # =========================
    cur.execute("SELECT COUNT(*) FROM prodotti")
    totale_prodotti = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM movimenti 
        WHERE DATE(data_movimento) = CURRENT_DATE
    """)
    movimenti_oggi = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM lotti 
        WHERE data_scadenza < CURRENT_DATE
    """)
    prodotti_scaduti = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM utenti 
        WHERE attivo = TRUE
    """)
    utenti_attivi = cur.fetchone()[0]

    # =========================
    # ALERT LOTTI IN SCADENZA (ADMIN)
    # =========================
    lotti_in_scadenza = []
    previsioni_esaurimento = []

    if ruolo == "Amministratore":
        oggi = date.today()
        soglia = oggi + timedelta(days=7)

        cur.execute("""
            SELECT l.id, p.nome, l.quantita, l.data_scadenza
            FROM lotti l
            JOIN prodotti p ON p.id = l.prodotto_id
            WHERE l.quantita > 0
              AND l.data_scadenza BETWEEN %s AND %s
            ORDER BY l.data_scadenza ASC
        """, (oggi, soglia))
        lotti_in_scadenza = cur.fetchall()

        # =========================
        # PREVISIONE ESAURIMENTO (SEMPLICE)
        # =========================
        cur.execute("""
            SELECT id, nome, quantita
            FROM prodotti
            WHERE quantita > 0
        """)

        for pid, nome, qta in cur.fetchall():
            # consumo medio stimato: 1 unità/giorno
            giorni = qta
            previsioni_esaurimento.append({
                "nome": nome,
                "quantita": qta,
                "giorni": giorni
            })

    # =========================
    # GRAFICO PRODOTTI PER CATEGORIA
    # =========================
    categorie_labels = []
    categorie_quantita = []

    cur.execute("""
        SELECT c.nome, COALESCE(SUM(p.quantita), 0)
        FROM categorie c
        LEFT JOIN prodotti p ON p.categoria_id = c.id
        GROUP BY c.nome
        ORDER BY c.nome
    """)

    for nome, qta in cur.fetchall():
        categorie_labels.append(nome)
        categorie_quantita.append(qta)

    # =========================
    # GRAFICO MOVIMENTI (ULTIMI 7 GIORNI)
    # =========================
    movimenti = defaultdict(lambda: {"entrata": 0, "uscita": 0})

    cur.execute("""
        SELECT DATE(data_movimento), tipo_movimento, SUM(quantita)
        FROM movimenti
        WHERE data_movimento >= CURRENT_DATE - INTERVAL '6 days'
        GROUP BY DATE(data_movimento), tipo_movimento
        ORDER BY DATE(data_movimento)
    """)

    for giorno, tipo, qta in cur.fetchall():
        movimenti[str(giorno)][tipo] += qta

    labels = sorted(movimenti.keys())
    movimenti_trend = {
        "labels": labels,
        "in_entrata": [movimenti[g]["entrata"] for g in labels],
        "in_uscita": [movimenti[g]["uscita"] for g in labels]
    }

    conn.close()

    return render_template(
        "dashboard.html",
        ruolo=ruolo,
        totale_prodotti=totale_prodotti,
        movimenti_oggi=movimenti_oggi,
        prodotti_scaduti=prodotti_scaduti,
        utenti_attivi=utenti_attivi,
        lotti_in_scadenza=lotti_in_scadenza,
        previsioni_esaurimento=previsioni_esaurimento,
        categorie_labels=categorie_labels,
        categorie_quantita=categorie_quantita,
        movimenti_trend=movimenti_trend
    )


def controlla_scadenze():
    conn = get_db()
    cur = conn.cursor()

    oggi = date.today()
    soglia = oggi + timedelta(days=3)

    cur.execute("""
        SELECT p.nome, l.data_scadenza
        FROM lotti l
        JOIN prodotti p ON l.prodotto_id = p.id
        WHERE l.data_scadenza <= %s
    """, (soglia,))

    alert = cur.fetchall()
    conn.close()
    return alert


# -------- PRODOTTI --------
@app.route("/prodotti")
@ruolo_required("Amministratore", "Manager", "Utente")
def prodotti_view():
    conn = get_db()
    cur = conn.cursor()

    filtro = request.args.get("filtro")
    oggi = date.today()

    sql = """
        SELECT
            p.id,
            p.nome,
            c.nome AS categoria,
            p.misura,
            COALESCE(SUM(l.quantita), 0) AS quantita,
            MIN(l.data_scadenza) AS prossima_scadenza,
            p.posizione,
            p.note
        FROM prodotti p
        LEFT JOIN categorie c ON p.categoria_id = c.id
        LEFT JOIN lotti l ON l.prodotto_id = p.id
    """

    if filtro == "scaduti":
        sql += """
            WHERE l.data_scadenza IS NOT NULL
              AND l.data_scadenza < %s
        """

    sql += """
        GROUP BY
            p.id, p.nome, c.nome, p.misura, p.posizione, p.note
        ORDER BY prossima_scadenza NULLS LAST
    """

    if filtro == "scaduti":
        cur.execute(sql, (oggi,))
    else:
        cur.execute(sql)

    prodotti = cur.fetchall()
    conn.close()

    return render_template(
        "prodotti.html",
        prodotti=prodotti,
        filtro_attivo=filtro,
        oggi=oggi
    )


@app.route("/prodotti/nuovo", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore", "Manager")
def nuovo_prodotto():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        categoria_id = request.form.get("categoria_id")
        misura = request.form.get("misura")
        posizione = request.form.get("posizione")
        quantita_minima = request.form.get("quantita_minima", 0)
        note = request.form.get("note")

        cur.execute("""
            INSERT INTO prodotti (
                nome,
                categoria_id,
                misura,
                posizione,
                quantita,
                quantita_minima,
                note,
                attivo
            )
            VALUES (%s, %s, %s, %s, 0, %s, %s, TRUE)
        """, (
            nome,
            categoria_id,
            misura,
            posizione,
            quantita_minima,
            note
        ))

        conn.commit()
        conn.close()

        flash("✅ Articolo creato correttamente", "success")
        return redirect(url_for("prodotti_view"))

    # GET
    cur.execute("SELECT id, nome FROM categorie ORDER BY nome")
    categorie = cur.fetchall()
    conn.close()

    return render_template("nuovo_prodotto.html", categorie=categorie)



@app.route("/prodotti/modifica/<int:prodotto_id>", methods=["GET", "POST"])
@login_required
def modifica_prodotto(prodotto_id):
    db = get_db()
    cur = db.cursor()

    # Controllo admin
    is_admin = session.get("ruolo") == "Amministratore"

    # Solo admin può salvare modifiche
    if request.method == "POST" and not is_admin:
        abort(403)

    if request.method == "POST" and is_admin:
        # Prelevo dati dal form
        nome = request.form["nome"]
        categoria_id = request.form["categoria_id"]
        misura = request.form["misura"]
        posizione = request.form["posizione"]

        # Aggiorno il prodotto
        cur.execute("""
            UPDATE prodotti
            SET nome=%s,
                categoria_id=%s,
                misura=%s,
                posizione=%s
            WHERE id=%s
        """, (nome, categoria_id, misura, posizione, prodotto_id))

        db.commit()
        return redirect(url_for("prodotti_view"))

    # GET: prendo i dati del prodotto
    cur.execute("""
        SELECT id, nome, categoria_id, misura, posizione
        FROM prodotti
        WHERE id=%s
    """, (prodotto_id,))
    r = cur.fetchone()
    if not r:
        abort(404)

    prodotto = {
        "id": r[0],
        "nome": r[1],
        "categoria_id": r[2],
        "misura": r[3],
        "posizione": r[4]
    }

    # Lista categorie
    cur.execute("SELECT id, nome FROM categorie ORDER BY nome")
    categorie = cur.fetchall()

    return render_template(
        "modifica_prodotto.html",
        prodotto=prodotto,
        categorie=categorie,
        is_admin=is_admin
    )


# -------- ELIMINA PRODOTTO --------
@app.route("/prodotti/elimina/<int:prodotto_id>")
@ruolo_required("Amministratore", "Manager")
@login_required
def elimina_prodotto(prodotto_id):
    db = get_db()
    cur = db.cursor()
    # Elimina il prodotto dal database
    cur.execute("DELETE FROM prodotti WHERE id = %s", (prodotto_id,))
    db.commit()
    db.close()
    return redirect(url_for("prodotti_view"))


# -------- CATEGORIE --------
@app.route("/categorie")
@login_required
def categorie_view():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, nome, descrizione FROM categorie ORDER BY nome")
    categorie = cur.fetchall()
    db.close()
    return render_template("categorie.html", categorie=categorie)

@app.route("/prodotti/categoria/<int:categoria_id>")
@login_required
def prodotti_per_categoria(categoria_id):
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT p.id,
               p.nome,
               c.nome,
               p.misura,
               p.quantita,
               p.data_scadenza,
               p.posizione
        FROM prodotti p
        LEFT JOIN categorie c ON p.categoria_id = c.id
        WHERE p.categoria_id = %s
        ORDER BY p.nome
    """, (categoria_id,))

    prodotti = cur.fetchall()

    cur.execute("SELECT nome FROM categorie WHERE id = %s", (categoria_id,))
    categoria_nome = cur.fetchone()[0]

    db.close()

    return render_template(
        "prodotti.html",
        prodotti=prodotti,
        categoria_nome=categoria_nome
    )


# -------- MOVIMENTI --------
@app.route("/movimenti", methods=["GET"])
@login_required
def movimenti_view():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            m.id,
            m.data_movimento,
            m.tipo_movimento,
            m.quantita,
            p.nome AS prodotto,
            COALESCE(l.data_scadenza, p.data_scadenza) AS data_scadenza,
            COALESCE(l.posizione, p.posizione, '-') AS posizione,
            m.note
        FROM movimenti m
        LEFT JOIN prodotti p ON m.prodotto_id = p.id
        LEFT JOIN lotti l ON m.lotto_id = l.id
        ORDER BY m.data_movimento DESC
    """)
    movimenti = cur.fetchall()

    conn.close()
    return render_template("movimenti.html", movimenti=movimenti)

# -------- AGGIUNGI MOVIMENTO --------
@app.route("/movimenti/aggiungi", methods=["GET", "POST"])
@ruolo_required("Amministratore", "Manager")
@login_required
def aggiungi_movimento():
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        prodotto_nome = request.form.get("nome")
        categoria_id = request.form.get("categoria_id")
        misura = request.form.get("misura")
        quantita = int(request.form.get("quantita"))
        tipo = request.form.get("tipo_movimento")
        posizione = request.form.get("posizione")
        descrizione = request.form.get("descrizione")
        lotto = request.form.get("lotto")
        data_scadenza = request.form.get("data_scadenza")

        # 1️⃣ Recupera o crea prodotto
        cur.execute("SELECT id FROM prodotti WHERE nome = %s", (prodotto_nome,))
        row = cur.fetchone()

        if row:
            prodotto_id = row[0]
            cur.execute("""
                UPDATE prodotti
                SET categoria_id = %s,
                    misura = %s,
                    posizione = %s,
                    descrizione = %s,
                    lotto = %s,
                    data_scadenza = %s
                WHERE id = %s
            """, (categoria_id, misura, posizione, descrizione, lotto, data_scadenza, prodotto_id))
        else:
            cur.execute("""
                INSERT INTO prodotti (
                    nome, categoria_id, misura, quantita,
                    posizione, descrizione, lotto, data_scadenza
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                prodotto_nome,
                categoria_id,
                misura,
                0,
                posizione,
                descrizione,
                lotto,
                data_scadenza
            ))
            prodotto_id = cur.fetchone()[0]

        # 2️⃣ 🔄 AGGIORNA QUANTITÀ (QUESTO È IL BLOCCO CHE CHIEDEVI)
        if tipo == "entrata":
            segno = 1
        else:
            segno = -1

        cur.execute("""
            UPDATE prodotti
            SET quantita = quantita + (%s * %s)
            WHERE id = %s
        """, (segno, quantita, prodotto_id))

        # 3️⃣ Inserisci movimento
        cur.execute("""
            INSERT INTO movimenti (
                prodotto_id,
                tipo_movimento,
                quantita,
                categoria_prodotto,
                misura_prodotto,
                note
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            prodotto_id,
            tipo,
            quantita,
            categoria_id,
            misura,
            None
        ))

        db.commit()
        db.close()
        return redirect(url_for("movimenti_view"))

    # GET
    cur.execute("SELECT id, nome FROM prodotti ORDER BY nome")
    prodotti = cur.fetchall()

    cur.execute("SELECT id, nome, descrizione FROM categorie ORDER BY nome")
    categorie = cur.fetchall()

    db.close()
    return render_template("aggiungi_movimento.html", prodotti=prodotti, categorie=categorie)

# -------- MODIFICA MOVIMENTO --------
@app.route("/movimenti/modifica/<int:id>", methods=["GET", "POST"])
@login_required
def modifica_movimento(id):
    db = get_db()
    cur = db.cursor()

    is_admin = session.get("ruolo") == "Amministratore"

    # Solo admin può modificare
    if request.method == "POST" and not is_admin:
        abort(403)

    if request.method == "POST" and is_admin:
        # DATI DAL FORM
        quantita = request.form["quantita"]
        data_movimento = request.form["data_movimento"]
        data_scadenza = request.form.get("data_scadenza")  # può essere None

        nome = request.form["nome"]
        categoria_id = request.form["categoria_id"]
        misura = request.form["misura"]
        posizione = request.form["posizione"]

        # 🔄 Aggiorna MOVIMENTO (solo campi esistenti in movimenti)
        cur.execute("""
            UPDATE movimenti
            SET quantita=%s,
                data_movimento=%s,
                data_scadenza=%s
            WHERE id=%s
        """, (quantita, data_movimento, data_scadenza, id))

        # 📦 Aggiorna PRODOTTO
        cur.execute("""
            UPDATE prodotti
            SET nome=%s,
                categoria_id=%s,
                misura=%s,
                posizione=%s
            WHERE id = (SELECT prodotto_id FROM movimenti WHERE id=%s)
        """, (nome, categoria_id, misura, posizione, id))

        db.commit()
        db.close()
        return redirect(url_for("movimenti_view"))

    # ===== GET =====
    cur.execute("""
        SELECT
            m.id,
            m.tipo_movimento,
            m.quantita,
            m.data_movimento,
            m.data_scadenza,
            p.id,
            p.nome,
            p.categoria_id,
            p.misura,
            p.posizione
        FROM movimenti m
        JOIN prodotti p ON p.id = m.prodotto_id
        WHERE m.id=%s
    """, (id,))

    r = cur.fetchone()
    if not r:
        abort(404)

    movimento = {
        "id": r[0],
        "tipo": r[1],
        "quantita": r[2],
        "data": r[3],
        "scadenza": r[4],
        "prodotto_id": r[5],
        "nome_prodotto": r[6],
        "categoria_id": r[7],
        "misura": r[8],
        "posizione": r[9]
    }

    # Lista categorie per il select
    cur.execute("SELECT id, nome FROM categorie ORDER BY nome")
    categorie = cur.fetchall()
    db.close()

    return render_template(
        "modifica_movimento.html",
        movimento=movimento,
        categorie=categorie,
        is_admin=is_admin
    )



# -------- UTENTI --------
@app.route("/utenti", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore")
def utenti():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        ruolo_id = request.form["ruolo"]
        cur.execute("""
            INSERT INTO utenti (username, password_hash, ruolo_id, attivo)
            VALUES (%s, %s, %s, TRUE)
        """, (username, password, ruolo_id))
        db.commit()

    cur.execute("""
        SELECT u.id, u.username, r.nome, u.attivo
        FROM utenti u
        JOIN ruoli r ON u.ruolo_id = r.id
    """)
    utenti = cur.fetchall()
    cur.execute("SELECT id, nome FROM ruoli")
    ruoli = cur.fetchall()
    db.close()
    return render_template("utenti.html", utenti=utenti, ruoli=ruoli)

@app.route("/prodotti/pdf")
@login_required
@ruolo_required("Amministratore")
def prodotti_pdf():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT p.id, p.nome, c.nome, p.misura, p.quantita, p.data_scadenza, p.posizione
        FROM prodotti p
        LEFT JOIN categorie c ON p.categoria_id = c.id
        ORDER BY p.nome
    """)
    prodotti = cur.fetchall()
    db.close()

    buffer = io.BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    elements = []

    # intestazione tabella
    data = [[
        "ID", "Nome", "Categoria", "Misura",
        "Quantità", "Scadenza", "Posizione"
    ]]

    for p in prodotti:
        data.append([
            p[0],
            p[1],
            p[2] or "—",
            p[3] or "—",
            p[4],
            p[5].strftime("%d/%m/%Y") if p[5] else "—",
            p[6] or "—"
        ])

    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))

    elements.append(table)
    pdf.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=False,
        download_name="prodotti_magazzino.pdf",
        mimetype="application/pdf"
    )



@app.route("/movimenti/pdf")
@login_required
def esporta_pdf():
    tipo_filtro = request.args.get('tipo', 'tutti')
    anno_filtro = request.args.get('anno') # Recupera l'anno (es. 2025)
    
    conn = get_db()
    cur = conn.cursor()

    # Query base
    query = """
        SELECT m.data_movimento, p.nome, m.tipo_movimento, m.quantita, l.data_scadenza
        FROM movimenti m
        JOIN prodotti p ON m.prodotto_id = p.id
        LEFT JOIN lotti l ON m.lotto_id = l.id
        WHERE 1=1
    """
    params = []

    # Filtro Tipo
    if tipo_filtro != 'tutti':
        query += " AND m.tipo_movimento = %s"
        params.append(tipo_filtro)
    
    # Filtro Anno
    if anno_filtro:
        query += " AND EXTRACT(YEAR FROM m.data_movimento) = %s"
        params.append(int(anno_filtro))
    
    query += " ORDER BY m.data_movimento DESC"
    cur.execute(query, params)
    movimenti = cur.fetchall()
    conn.close()

    # Generazione PDF (FPDF)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    titolo = f"Report Movimenti Protezione Civile Lungoni - {tipo_filtro.capitalize()}"
    if anno_filtro: titolo += f" Anno {anno_filtro}"
    
    pdf.cell(190, 10, titolo, ln=True, align="C")
    pdf.ln(10)

    # Intestazione Tabella
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(35, 10, "Data", 1, 0, "C", True)
    pdf.cell(65, 10, "Prodotto", 1, 0, "C", True)
    pdf.cell(25, 10, "Tipo", 1, 0, "C", True)
    pdf.cell(20, 10, "Qta", 1, 0, "C", True)
    pdf.cell(45, 10, "Scadenza Lotto", 1, 1, "C", True)

    # Dati
    pdf.set_font("Arial", "", 9)
    for m in movimenti:
        data_str = m[0].strftime('%d/%m/%Y %H:%M')
        scadenza_str = m[4].strftime('%d/%m/%Y') if m[4] else "-"
        
        pdf.cell(35, 8, data_str, 1)
        pdf.cell(65, 8, str(m[1])[:30], 1) # Tronca nomi troppo lunghi
        pdf.cell(25, 8, str(m[2]).upper(), 1, 0, "C")
        pdf.cell(20, 8, str(m[3]), 1, 0, "C")
        pdf.cell(45, 8, scadenza_str, 1, 1, "C")

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    filename = f"movimenti_{tipo_filtro}_{anno_filtro if anno_filtro else 'storico'}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
