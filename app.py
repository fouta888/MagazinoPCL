from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from config import *
from functools import wraps # import necessario per login_required e ruolo_required
import socket
import qrcode
import io
import base64
from flask import Flask, render_template
from io import BytesIO

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
import datetime


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
            session["username"] = username
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
# -------- UTENTI --------
@app.route("/utenti", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore", "Manager", "Utente")  # Ora anche l'Utente può entrare
def utenti_view():
    db = get_db()
    cur = db.cursor()
    
    # --- GESTIONE POST (Creazione Nuovi Utenti) ---
    if request.method == "POST":
        # Solo Admin e Manager possono creare utenti
        if session.get("ruolo") not in ["Amministratore", "Manager"]:
            flash("Non hai i permessi per creare utenti.")
            return redirect(url_for("utenti_view"))

        username = request.form["username"]
        password = request.form["password"]
        ruolo_id = int(request.form["ruolo"])

        cur.execute("SELECT id, nome FROM ruoli ORDER BY id")
        tutti_ruoli = cur.fetchall()

        # Logica permessi creazione
        if session.get("ruolo") == "Amministratore":
            ruoli_consentiti = [r[0] for r in tutti_ruoli]
        elif session.get("ruolo") == "Manager":
            ruoli_consentiti = [r[0] for r in tutti_ruoli if r[1] == "Utente"]
        else:
            ruoli_consentiti = []

        if ruolo_id not in ruoli_consentiti:
            flash("Non puoi creare un utente con questo ruolo!")
        else:
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

    # --- GESTIONE GET (Visualizzazione Lista) ---
    
    # Se è Amministratore, scarica TUTTI gli utenti
    if session.get("ruolo") == "Amministratore":
        cur.execute("""
            SELECT u.id, u.username, r.nome, u.attivo 
            FROM utenti u 
            JOIN ruoli r ON u.ruolo_id = r.id 
            ORDER BY u.username
        """)
    # Se è Manager o Utente, scarica SOLO i dati dell'utente loggato
    else:
        cur.execute("""
            SELECT u.id, u.username, r.nome, u.attivo 
            FROM utenti u 
            JOIN ruoli r ON u.ruolo_id = r.id 
            WHERE u.id = %s
        """, (session.get("user_id"),))
    
    utenti = cur.fetchall()
    
    # Scarica i ruoli per il form (servono solo all'Admin/Manager)
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
        
        # 1. GESTIONE CODICE LOTTO (Prima della ricerca nel DB)
        codice_lotto = request.form.get("codice_lotto", "").strip()
        if not codice_lotto:
            # Genera codice automatico: L-20260124-1530
            from datetime import datetime
            codice_lotto = datetime.now().strftime("L-%Y%m%d-%H%M")

        if not data_scadenza: 
            data_scadenza = None

        # Recupero nome prodotto per il log
        cur.execute("SELECT nome FROM prodotti WHERE id = %s", (prodotto_id,))
        nome_prodotto = cur.fetchone()[0]

        # 2. CONTROLLO ESISTENZA (Ora con il codice_lotto già definito)
        cur.execute("""
            SELECT id FROM lotti 
            WHERE prodotto_id = %s 
              AND data_scadenza IS NOT DISTINCT FROM %s 
              AND codice_lotto IS NOT DISTINCT FROM %s
        """, (prodotto_id, data_scadenza, codice_lotto))
        lotto = cur.fetchone()

        if lotto:
            # Aggiorna esistente
            cur.execute("UPDATE lotti SET quantita = quantita + %s WHERE id = %s", (quantita, lotto[0]))
            lotto_id = lotto[0]
        else:
            # Crea nuovo
            cur.execute("""
                INSERT INTO lotti (prodotto_id, quantita, data_scadenza, codice_lotto)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (prodotto_id, quantita, data_scadenza, codice_lotto))
            lotto_id = cur.fetchone()[0]

        # 3. AGGIORNA TOTALI E REGISTRA MOVIMENTO
        cur.execute("UPDATE prodotti SET quantita = quantita + %s WHERE id = %s", (quantita, prodotto_id))
        
        cur.execute("""
            INSERT INTO movimenti (prodotto_id, lotto_id, tipo_movimento, quantita, data_scadenza)
            VALUES (%s, %s, 'entrata', %s, %s)
        """, (prodotto_id, lotto_id, quantita, data_scadenza))

        # 4. LOG OPERAZIONE (Chi ha fatto cosa)
        cur.execute("""
            INSERT INTO log_operazioni (username, azione, dettaglio)
            VALUES (%s, %s, %s)
        """, (session.get('username'), 'CARICO', f"Caricati {quantita} pz di {nome_prodotto} (Lotto: {codice_lotto})"))

        conn.commit()
        conn.close()
        flash(f"✅ Carico effettuato correttamente (Lotto: {codice_lotto})", "success")
        return redirect(url_for("lotti_view"))

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

        cur.execute("SELECT nome, quantita FROM prodotti WHERE id = %s", (prodotto_id,))
        prod_data = cur.fetchone()
        nome_prodotto = prod_data[0]
        qta_totale = prod_data[1]

        if qta_totale < quantita_da_scaricare:
            conn.close()
            flash("❌ Quantità insufficiente", "error")
            return redirect(url_for("uscita_lotto"))

        cur.execute("""
            SELECT id, quantita, data_scadenza, codice_lotto FROM lotti
            WHERE prodotto_id = %s AND quantita > 0
            AND (data_scadenza IS NULL OR data_scadenza >= CURRENT_DATE)
            ORDER BY data_scadenza ASC NULLS LAST
        """, (prodotto_id,))
        
        lotti = cur.fetchall()
        restante = quantita_da_scaricare

        for lotto_id, qta_lotto, data_sca, cod_lotto in lotti:
            if restante <= 0: break
            mov_qta = qta_lotto if qta_lotto <= restante else restante
            
            cur.execute("UPDATE lotti SET quantita = quantita - %s WHERE id = %s", (mov_qta, lotto_id))
            cur.execute("INSERT INTO movimenti (prodotto_id, lotto_id, tipo_movimento, quantita) VALUES (%s, %s, 'uscita', %s)",
                       (prodotto_id, lotto_id, mov_qta))
            restante -= mov_qta

        if restante > 0:
            conn.rollback()
            flash("❌ Errore: lotti validi insufficienti", "error")
        else:
            cur.execute("UPDATE prodotti SET quantita = quantita - %s WHERE id = %s", (quantita_da_scaricare, prodotto_id))
            # LOG OPERAZIONE (Tracciabilità)
            cur.execute("""
                INSERT INTO log_operazioni (username, azione, dettaglio)
                VALUES (%s, %s, %s)
            """, (session.get('username'), 'SCARICO', f"Scaricati {quantita_da_scaricare} pz di {nome_prodotto}"))
            conn.commit()
            flash("✅ Scarico effettuato", "success")

        cur.execute("DELETE FROM lotti WHERE quantita = 0")
        conn.commit()
        conn.close()
        return redirect(url_for("lotti_view"))

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


# -------- MESSAGGI --------
@app.route("/messaggi")
@login_required
@ruolo_required("Amministratore", "Manager")
def messaggi():
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]

    # Prendi la lista utenti per la sidebar
    cur.execute("""
        SELECT u.id, u.username
        FROM utenti u
        JOIN ruoli r ON u.ruolo_id = r.id
        WHERE r.nome IN ('Amministratore', 'Manager')
          AND u.attivo=TRUE
          AND u.id != %s
    """, (user_id,))
    utenti = cur.fetchall()
    db.close()

    # Mostriamo la pagina senza messaggi e senza destinatario_id
    return render_template("messaggi.html", utenti=utenti)


@app.route("/messaggi/<int:dest_id>", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore", "Manager")
def chat_privata(dest_id):
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]

    if request.method == "POST":
        contenuto = request.form.get("contenuto")
        if contenuto:
            cur.execute("""
                INSERT INTO messaggi (mittente_id, destinatario_id, contenuto)
                VALUES (%s, %s, %s)
            """, (user_id, dest_id, contenuto))
            db.commit()

    # info destinatario
    cur.execute("SELECT username FROM utenti WHERE id=%s", (dest_id,))
    destinatario = cur.fetchone()

    # messaggi SOLO tra voi due
    cur.execute("""
        SELECT m.contenuto, m.data_creazione,
               mittente.username, destinatario.username
        FROM messaggi m
        JOIN utenti mittente ON m.mittente_id = mittente.id
        JOIN utenti destinatario ON m.destinatario_id = destinatario.id
        WHERE (m.mittente_id=%s AND m.destinatario_id=%s)
           OR (m.mittente_id=%s AND m.destinatario_id=%s)
        ORDER BY m.data_creazione
    """, (user_id, dest_id, dest_id, user_id))

    messaggi = cur.fetchall()

    # lista utenti (sidebar)
    cur.execute("""
        SELECT u.id, u.username
        FROM utenti u
        JOIN ruoli r ON u.ruolo_id = r.id
        WHERE r.nome IN ('Amministratore', 'Manager')
          AND u.attivo=TRUE
          AND u.id != %s
    """, (user_id,))
    utenti = cur.fetchall()

    db.close()

    return render_template(
        "chat_privata.html",
        utenti=utenti,
        messaggi=messaggi,
        destinatario=destinatario,
        dest_id=dest_id
    )


@app.route("/broadcast", methods=["POST"])
@login_required
@ruolo_required("Amministratore")
def broadcast():
    contenuto = request.form.get("contenuto")
    user_id = session["user_id"]
    
    if contenuto:
        db = get_db()
        cur = db.cursor()
        # Prendi tutti gli utenti Admin e Manager tranne te stesso
        cur.execute("""
            SELECT u.id FROM utenti u 
            JOIN ruoli r ON u.ruolo_id = r.id 
            WHERE r.nome IN ('Amministratore', 'Manager') AND u.id != %s
        """, (user_id,))
        destinatari = cur.fetchall()
        
        for dest in destinatari:
            cur.execute("""
                INSERT INTO messaggi (mittente_id, destinatario_id, contenuto)
                VALUES (%s, %s, %s)
            """, (user_id, dest[0], contenuto))
        
        db.commit()
        db.close()
        flash(f"Messaggio inviato a {len(destinatari)} utenti!")
    
    # Ritorna alla pagina precedente (o a 'messaggi' se non disponibile)
    return redirect(request.referrer or url_for('messaggi'))

@app.route("/api/get_messages/<int:dest_id>")
@login_required
def get_messages_ajax(dest_id):
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]

    cur.execute("""
        SELECT m.contenuto, m.data_creazione,
               mittente.username, destinatario.username
        FROM messaggi m
        JOIN utenti mittente ON m.mittente_id = mittente.id
        JOIN utenti destinatario ON m.destinatario_id = destinatario.id
        WHERE (m.mittente_id=%s AND m.destinatario_id=%s)
           OR (m.mittente_id=%s AND m.destinatario_id=%s)
        ORDER BY m.data_creazione
    """, (user_id, dest_id, dest_id, user_id))
    
    messaggi = cur.fetchall()
    db.close()
    
    # Restituiamo solo il pezzettino dei messaggi
    return render_template("partials/messages_list.html", messaggi=messaggi)


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



@app.route("/utenti/modifica/<int:utente_id>", methods=["GET", "POST"])
@login_required
# Rimosso @ruolo_required("Amministratore") per permettere l'accesso all'utente
def modifica_utente(utente_id):
    db = get_db()
    cur = db.cursor()

    # SICUREZZA: Se non è admin e prova a modificare un altro ID, lo blocchiamo
    if session.get("ruolo") != "Amministratore" and utente_id != session.get("user_id"):
        db.close()
        return "Accesso negato", 403

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Solo l'Admin può cambiare ruolo e stato attivo
        if session.get("ruolo") == "Amministratore":
            ruolo_id = request.form.get("ruolo")
            attivo = request.form.get("attivo") == "on"
        else:
            # Per l'utente normale, recuperiamo i dati attuali (non cambiano)
            cur.execute("SELECT ruolo_id, attivo FROM utenti WHERE id=%s", (utente_id,))
            res = cur.fetchone()
            ruolo_id, attivo = res[0], res[1]

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
        # Nota: assicurati che il nome della rotta sia 'utenti_view' o 'utenti'
        return redirect(url_for("utenti_view"))

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
    # Se vuoi vedere il totale dei pezzi (536) usa SUM(quantita), se vuoi i tipi di articoli (82) usa COUNT(*)
    cur.execute("SELECT COUNT(*) FROM prodotti")
    totale_prodotti = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) 
        FROM movimenti 
        WHERE DATE(data_movimento) = CURRENT_DATE
    """)
    movimenti_oggi = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM lotti WHERE data_scadenza < CURRENT_DATE")
    prodotti_scaduti = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM utenti WHERE attivo = TRUE")
    utenti_attivi = cur.fetchone()[0]
    # AGGIUNTA: Prendi l'orario dell'ultimo movimento (carico/scarico)
    cur.execute("SELECT data_movimento FROM movimenti ORDER BY data_movimento DESC LIMIT 1")
    ultimo_mov_row = cur.fetchone()
    # Formattiamo l'ora se esiste un movimento, altrimenti mettiamo un trattino
    ultimo_aggiornamento = ultimo_mov_row[0].strftime("%H:%M") if ultimo_mov_row else "--:--"

    # ==========================================
    # NOVITÀ: PRODOTTI SOTTO SOGLIA (LISTA SPESA)
    # ==========================================
    # Questa query recupera i prodotti dove la quantità attuale è inferiore alla minima impostata
    cur.execute("""
        SELECT nome, quantita, quantita_minima 
        FROM prodotti 
        WHERE quantita <= quantita_minima 
          AND quantita_minima > 0
          AND attivo = TRUE
        ORDER BY nome ASC
    """)
    prodotti_sotto_soglia = cur.fetchall()

    # =========================
    # ALERT E PREVISIONI (Admin e Manager)
    # =========================
    lotti_in_scadenza = []
    previsioni_esaurimento = []

    # Estendiamo la visibilità anche al Manager
    if ruolo in ["Amministratore", "Manager"]:
        oggi = date.today()
        soglia_scadenza = oggi + timedelta(days=7)

        cur.execute("""
            SELECT l.id, p.nome, l.quantita, l.data_scadenza
            FROM lotti l
            JOIN prodotti p ON p.id = l.prodotto_id
            WHERE l.quantita > 0
              AND l.data_scadenza BETWEEN %s AND %s
            ORDER BY l.data_scadenza ASC
        """, (oggi, soglia_scadenza))
        lotti_in_scadenza = cur.fetchall()

        # Previsione esaurimento
        cur.execute("SELECT id, nome, quantita FROM prodotti WHERE quantita > 0")
        for pid, nome, qta in cur.fetchall():
            giorni = qta # consumo stimato 1 unità/gg
            previsioni_esaurimento.append({
                "nome": nome,
                "quantita": qta,
                "giorni": giorni
            })

    # =========================
    # GRAFICI (Uguale a prima)
    # =========================
    categorie_labels = []
    categorie_quantita = []
    cur.execute("""
        SELECT c.nome, COALESCE(SUM(p.quantita), 0)
        FROM categorie c
        LEFT JOIN prodotti p ON p.categoria_id = c.id
        GROUP BY c.nome ORDER BY c.nome
    """)
    for nome, qta in cur.fetchall():
        categorie_labels.append(nome)
        categorie_quantita.append(qta)

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
        prodotti_sotto_soglia=prodotti_sotto_soglia, # <--- FONDAMENTALE PER IL DRAWER
        categorie_labels=categorie_labels,
        categorie_quantita=categorie_quantita,
        movimenti_trend=movimenti_trend,
        ultimo_aggiornamento=ultimo_aggiornamento,
        stato_db="Online" # Stato fisso a Online se la pagina carica
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

    is_admin = session.get("ruolo") == "Amministratore"

    if request.method == "POST" and not is_admin:
        abort(403)

    if request.method == "POST" and is_admin:
        nome = request.form["nome"]
        categoria_id = request.form["categoria_id"]
        misura = request.form["misura"]
        posizione = request.form["posizione"]
        quantita_minima = request.form["quantita_minima"] # <--- Prelevo la soglia

        cur.execute("""
            UPDATE prodotti
            SET nome=%s, categoria_id=%s, misura=%s, posizione=%s, quantita_minima=%s
            WHERE id=%s
        """, (nome, categoria_id, misura, posizione, quantita_minima, prodotto_id))

        db.commit()
        return redirect(url_for("prodotti_view"))

    # GET: prendo i dati includendo quantita_minima
    cur.execute("""
        SELECT id, nome, categoria_id, misura, posizione, quantita_minima
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
        "posizione": r[4],
        "quantita_minima": r[5] # <--- Aggiunto al dizionario
    }

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


@app.route("/lista_spesa")
@login_required
@ruolo_required("Amministratore", "Manager")
def lista_spesa():
    db = get_db()
    cur = db.cursor()
    
    # Cerchiamo i prodotti sotto soglia (escludendo quelli con minima a 0 se preferisci)
    cur.execute("""
        SELECT id, nome, quantita, quantita_minima, posizione
        FROM prodotti
        WHERE quantita <= quantita_minima 
          AND attivo = TRUE
        ORDER BY posizione ASC
    """)
    prodotti_bassi = cur.fetchall()
    db.close()
    
    return render_template("lista_spesa.html", prodotti=prodotti_bassi)

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
    # 1. Controllo Sicurezza
    if session.get("ruolo") != "Amministratore":
        return "Accesso negato: solo gli amministratori possono scaricare i report.", 403

    tipo_filtro = request.args.get('tipo', 'tutti')
    anno_filtro = request.args.get('anno')
    
    conn = get_db()
    cur = conn.cursor()

    # --- LOG DOWNLOAD ---
    try:
        cur.execute("""
            INSERT INTO log_download (username, tipo_report, anno_filtro, data_download)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """, (session.get("username"), tipo_filtro, anno_filtro))
        conn.commit()
    except Exception as e:
        print(f"Errore registrazione log: {e}")
        conn.rollback()

    # --- QUERY ---
    query = """
        SELECT m.data_movimento, p.nome, m.tipo_movimento, m.quantita, 
               l.codice_lotto, l.data_scadenza
        FROM movimenti m
        JOIN prodotti p ON m.prodotto_id = p.id
        LEFT JOIN lotti l ON m.lotto_id = l.id
        WHERE 1=1
    """
    params = []
    if tipo_filtro != 'tutti':
        query += " AND m.tipo_movimento = %s"
        params.append(tipo_filtro)
    if anno_filtro and anno_filtro not in ['None', '']:
        query += " AND EXTRACT(YEAR FROM m.data_movimento) = %s"
        params.append(int(anno_filtro))
    
    query += " ORDER BY m.data_movimento DESC"
    
    cur.execute(query, params)
    movimenti = cur.fetchall()
    conn.close()

    # --- GENERAZIONE PDF ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    
    testo_titolo = f"REPORT MOVIMENTI - {tipo_filtro.upper()}"
    if anno_filtro and anno_filtro != 'None':
        testo_titolo += f" ANNO {anno_filtro}"
    
    pdf.cell(190, 10, testo_titolo, ln=True, align="C")
    pdf.ln(5)

    # Intestazione Tabella
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(30, 8, "Data", 1, 0, "C", True)
    pdf.cell(50, 8, "Prodotto", 1, 0, "C", True)
    pdf.cell(30, 8, "Lotto", 1, 0, "C", True)
    pdf.cell(15, 8, "Tipo", 1, 0, "C", True)
    pdf.cell(15, 8, "Qta", 1, 0, "C", True)
    pdf.cell(50, 8, "Scadenza", 1, 1, "C", True)

    # Dati Tabella
    pdf.set_font("Arial", "", 8)
    for m in movimenti:
        # Colore riga basato sul tipo
        tipo_testo = str(m[2] or "").upper()
        if tipo_testo == 'USCITA':
            pdf.set_text_color(200, 0, 0) # Rosso
        elif tipo_testo == 'ENTRATA':
            pdf.set_text_color(0, 120, 0) # Verde
        else:
            pdf.set_text_color(0, 0, 0) # Nero

        pdf.cell(30, 7, m[0].strftime('%d/%m/%Y %H:%M') if m[0] else "-", 1)
        pdf.cell(50, 7, str(m[1] or "-")[:25].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(30, 7, str(m[4] or "-")[:15].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(15, 7, tipo_testo, 1, 0, "C")
        pdf.cell(15, 7, str(m[3] or "0"), 1, 0, "C")
        pdf.cell(50, 7, m[5].strftime('%d/%m/%Y') if m[5] else "-", 1, 1)
        
        pdf.set_text_color(0, 0, 0) # Reset colore per riga successiva

    # --- OUTPUT FINALE ---
    # Usiamo BytesIO per gestire il PDF in memoria
    pdf_stream = BytesIO()
    pdf_out = pdf.output(dest='S').encode('latin-1')
    pdf_stream.write(pdf_out)
    pdf_stream.seek(0)

    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"report_{tipo_filtro}.pdf"
    )


@app.route("/admin/esporta-audit-movimenti")
@login_required
@ruolo_required("Amministratore")
def esporta_pdf_audit():
    from fpdf import FPDF
    from io import BytesIO

    # 1. Recupero dati dal DB
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT data_operazione, username, azione, dettaglio FROM log_operazioni ORDER BY data_operazione DESC")
    logs = cur.fetchall()
    conn.close()

    # 2. Classe PDF con Header automatico e Footer
    class PDF_Audit(FPDF):
        def header(self):
            # Titolo Documento
            self.set_font("Arial", "B", 15)
            self.set_text_color(0, 0, 0)
            self.cell(190, 10, "REGISTRO MOVIMENTI MERCE (AUDIT)", ln=True, align="C")
            self.ln(5)
            
            # INTESTAZIONE TABELLA (Si ripete su ogni pagina)
            self.set_font("Arial", "B", 10)
            self.set_fill_color(50, 50, 50)  # Grigio scuro
            self.set_text_color(255, 255, 255) # Testo bianco
            
            self.cell(35, 10, "DATA", 1, 0, "C", True)
            self.cell(25, 10, "UTENTE", 1, 0, "C", True)
            self.cell(25, 10, "AZIONE", 1, 0, "C", True)
            self.cell(105, 10, "DETTAGLIO", 1, 1, "C", True)
            
            # Reset per i dati
            self.set_text_color(0, 0, 0)
            self.set_font("Arial", "", 9)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    # 3. Inizializzazione PDF
    pdf = PDF_Audit()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # 4. Ciclo dati con righe alternate
    fill = False # Variabile per alternare il colore
    for row in logs:
        data_f = row[0].strftime('%d/%m/%Y %H:%M') if row[0] else "-"
        utente = str(row[1])
        azione = str(row[2])
        dettaglio = str(row[3])
        
        # Pulizia testo
        testo_d = dettaglio.encode('latin-1', 'replace').decode('latin-1')

        # Imposta colore di sfondo per la riga alternata
        if fill:
            pdf.set_fill_color(240, 240, 240) # Grigio chiarissimo
        else:
            pdf.set_fill_color(255, 255, 255) # Bianco

        # Scrittura riga (l'ultimo parametro 'True' attiva il colore di sfondo)
        pdf.cell(35, 8, data_f, 1, 0, "C", True)
        pdf.cell(25, 8, utente, 1, 0, "C", True)
        pdf.cell(25, 8, azione, 1, 0, "C", True)
        pdf.cell(105, 8, testo_d, 1, 1, "L", True)
        
        fill = not fill # Inverte il colore per la riga successiva

    # 5. Ritorno del file
    pdf_out = pdf.output(dest='S').encode('latin-1', 'replace')
    return send_file(
        BytesIO(pdf_out), 
        mimetype='application/pdf', 
        as_attachment=True, 
        download_name="audit_movimenti_magazzino.pdf"
    )


@app.route("/admin/log_download")
@login_required
@ruolo_required("Amministratore")
def visualizza_log():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT username, tipo_report, anno_filtro, data_download FROM log_download ORDER BY data_download DESC")
        logs = cur.fetchall()
        cur.close()
        conn.close()
        
        # Debug nel terminale per sicurezza
        print(f"DEBUG LOGS CARICATI: {len(logs)} record trovati")
        
        return render_template("admin_logs.html", logs=logs)
    except Exception as e:
        print(f"ERRORE CRITICO LOG DOWNLOAD: {e}")
        return f"Errore durante il caricamento dei log: {str(e)}", 500


@app.route("/admin/audit-operazioni")
@login_required
@ruolo_required("Amministratore")
def audit_operazioni():
    conn = get_db()
    cur = conn.cursor()
    # Recuperiamo gli ultimi 200 movimenti registrati nella tabella log_operazioni
    cur.execute("""
        SELECT username, azione, dettaglio, data_operazione 
        FROM log_operazioni 
        ORDER BY data_operazione DESC 
        LIMIT 200
    """)
    logs_op = cur.fetchall()
    conn.close()
    return render_template("admin_audit.html", logs=logs_op)


@app.route("/admin/registri")
@login_required
@ruolo_required("Amministratore")
def visualizza_tutti_i_log():
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Log dei Download PDF
    cur.execute("""
    SELECT username, tipo_report, anno_filtro, data_download 
    FROM log_download 
    ORDER BY data_download DESC 
    LIMIT 50
""")
    logs_pdf = cur.fetchall()
    
    # 2. Log delle Operazioni (Carichi/Scarichi)
    cur.execute("SELECT username, azione, dettaglio, data_operazione FROM log_operazioni ORDER BY data_operazione DESC LIMIT 50")
    logs_op = cur.fetchall()
    
    conn.close()
    return render_template("admin_full_logs.html", logs_pdf=logs_pdf, logs_op=logs_op)


@app.route("/prestiti/nuovo", methods=["GET", "POST"])
@login_required
@ruolo_required("Amministratore")
def nuovo_prestito():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        # Usiamo getlist per recuperare tutti gli ID selezionati dai checkbox
        prodotti_selezionati = request.form.getlist("prodotto_id")
        beneficiario = request.form.get("beneficiario")
        telefono = request.form.get("telefono")
        indirizzo = request.form.get("indirizzo")
        note = request.form.get("note")
        utente_id = session.get("user_id")

        if not prodotti_selezionati:
            flash("❌ Errore: Seleziona almeno un oggetto!", "danger")
            # È fondamentale fare un return anche qui!
            return redirect(url_for('nuovo_prestito'))

        try:
            # Cicliamo su ogni prodotto selezionato
            for p_id in prodotti_selezionati:
                cur.execute("""
                    INSERT INTO prestiti (prodotto_id, beneficiario, telefono, indirizzo, note, utente_id, stato, data_inizio)
                    VALUES (%s, %s, %s, %s, %s, %s, 'ATTIVO', CURRENT_TIMESTAMP)
                """, (p_id, beneficiario, telefono, indirizzo, note, utente_id))
                
                # Scaliamo la giacenza per ogni oggetto
                cur.execute("UPDATE prodotti SET quantita = quantita - 1 WHERE id = %s", (p_id,))
            
            conn.commit()
            flash(f"✅ Registrati {len(prodotti_selezionati)} oggetti per {beneficiario}", "success")
            return redirect(url_for('elenco_prestiti'))
        
        except Exception as e:
            conn.rollback()
            flash(f"❌ Errore durante il salvataggio: {e}", "danger")
            return redirect(url_for('nuovo_prestito'))
        finally:
            conn.close()

    # --- CASO GET (Caricamento pagina) ---
    # Questa parte deve essere fuori dall'if POST
    cur.execute("SELECT id, nome, quantita FROM prodotti WHERE attivo=TRUE AND quantita > 0 ORDER BY nome")
    prodotti = cur.fetchall()
    conn.close()
    
    # Assicurati che questo return sia presente e allineato correttamente
    return render_template("nuovo_prestito.html", prodotti=prodotti)


@app.route("/prestiti")
@login_required
@ruolo_required("Amministratore")
def elenco_prestiti():
    conn = get_db()
    cur = conn.cursor()
    
    # Abbiamo aggiunto u.username nella clausola GROUP BY
    cur.execute("""
        SELECT 
            MIN(p.id), 
            u.username, 
            STRING_AGG(pr.nome, ', '), 
            p.beneficiario, 
            p.data_inizio, 
            p.stato, 
            p.indirizzo
        FROM prestiti p
        JOIN prodotti pr ON p.prodotto_id = pr.id
        LEFT JOIN utenti u ON p.utente_id = u.id
        GROUP BY u.username, p.beneficiario, p.data_inizio, p.stato, p.indirizzo
        ORDER BY p.data_inizio DESC
    """)
    lista_prestiti = cur.fetchall()
    conn.close()
    
    return render_template("elenco_prestiti.html", prestiti=lista_prestiti)


@app.route("/prestiti/ritorno/<int:prestito_id>")
@login_required
@ruolo_required("Amministratore")
def registra_ritorno(prestito_id):
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Recupera l'ID del prodotto prima di segnare come restituito
    cur.execute("SELECT prodotto_id, stato FROM prestiti WHERE id = %s", (prestito_id,))
    prestito = cur.fetchone()
    
    if prestito and prestito[1] == 'ATTIVO':
        # 2. Segna come RESTITUITO
        cur.execute("UPDATE prestiti SET stato = 'RESTITUITO' WHERE id = %s", (prestito_id,))
        # 3. Incrementa di nuovo la quantità in magazzino
        cur.execute("UPDATE prodotti SET quantita = quantita + 1 WHERE id = %s", (prestito[0],))
        conn.commit()
        flash("✅ Oggetto riportato in magazzino correttamente!", "success")
    
    conn.close()
    return redirect(url_for('elenco_prestiti'))



@app.route("/esporta-comodato/<int:prestito_id>")
@login_required
@ruolo_required("Amministratore")
def esporta_comodato(prestito_id):
    from datetime import datetime
    import os
    from io import BytesIO
    
    conn = get_db()
    cur = conn.cursor()
    # Recuperiamo i dati del singolo prestito
    cur.execute("""
        SELECT p.beneficiario, pr.nome, p.data_inizio, p.indirizzo, p.telefono, p.note
        FROM prestiti p
        JOIN prodotti pr ON p.prodotto_id = pr.id
        WHERE p.id = %s
    """, (prestito_id,))
    dati = cur.fetchone()
    conn.close()

    if not dati:
        flash("Prestito non trovato", "danger")
        return redirect(url_for('elenco_prestiti'))

    beneficiario, nome_prodotto, data_inizio, indirizzo, telefono, note = dati
    data_str = data_inizio.strftime("%d/%m/%Y") if data_inizio else datetime.now().strftime("%d/%m/%Y")

    pdf = FPDF()
    pdf.add_page()
    
    # --- LOGO E INTESTAZIONE ---
    logo_path = os.path.join('static', 'Magazzino.jpg')
    if os.path.exists(logo_path):
        pdf.image(logo_path, 12, 10, 28)
    
    pdf.set_font("Arial", "B", 14)
    pdf.set_x(45)
    pdf.cell(0, 8, 'Associazione Protezione Civile "LUNGONI" ODV', ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.set_x(45)
    pdf.cell(0, 5, 'Via La Funtana, sn - 07028 Santa Teresa Gallura (SS)', ln=True)
    pdf.ln(20)

    # --- TITOLO ---
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "COMODATO D'USO GRATUITO", ln=True, align="C")
    pdf.ln(10)
    
    # --- DATI BENEFICIARIO ---
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"In data {data_str}, l'Associazione concede al Sig./ra:", ln=True)
    
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, f"SOGGETTO: {beneficiario.upper()}", ln=True)
    
    pdf.set_font("Arial", "", 11)
    if indirizzo and indirizzo.strip():
        pdf.cell(0, 7, f"RESIDENTE IN: {indirizzo.strip()}", ln=True)
    if telefono and telefono.strip():
        pdf.cell(0, 7, f"RECAPITO TEL: {telefono.strip()}", ln=True)

    pdf.ln(15) 

    # --- OGGETTO ---
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "ATTREZZATURA CONSEGNATA:", ln=True)
    pdf.set_font("Arial", "B", 14)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(0, 12, f"  {nome_prodotto}", border=1, ln=True, fill=True)
    
    if note and note.strip():
        pdf.ln(5)
        pdf.set_font("Arial", "I", 10)
        pdf.multi_cell(0, 6, f"Note: {note.strip()}".encode('latin-1', 'replace').decode('latin-1'))

    # --- PRIVACY E FIRME ---
    pdf.set_y(-65)
    pdf.set_font("Arial", "I", 8)
    privacy = "Informativa Privacy: Trattamento dati conforme al GDPR UE 2016/679."
    pdf.multi_cell(0, 4, privacy.encode('latin-1', 'replace').decode('latin-1'), align="C")

    pdf.ln(10)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 10, "Firma del ricevente", 0, 0, "C")
    pdf.cell(95, 10, "Per l'Associazione", 0, 1, "C")
    
    pdf_out = pdf.output(dest='S').encode('latin-1', 'replace')
    return send_file(BytesIO(pdf_out), mimetype='application/pdf', as_attachment=False, download_name=f"Comodato_{beneficiario}.pdf")


@app.route("/esporta-comodato-multiplo/<string:beneficiario>")
@login_required
@ruolo_required("Amministratore")
def esporta_comodato_multiplo(beneficiario):
    from datetime import datetime
    import os
    from io import BytesIO
    
    conn = get_db()
    cur = conn.cursor()
    # Recuperiamo TUTTI i prodotti attivi per questo beneficiario
    cur.execute("""
        SELECT pr.nome, p.data_inizio, p.indirizzo, p.telefono, p.note
        FROM prestiti p
        JOIN prodotti pr ON p.prodotto_id = pr.id
        WHERE p.beneficiario = %s AND p.stato = 'ATTIVO'
        ORDER BY p.data_inizio DESC
    """, (beneficiario,))
    oggetti = cur.fetchall()
    conn.close()

    if not oggetti:
        flash(f"Nessun oggetto attivo trovato per {beneficiario}", "warning")
        return redirect(url_for('elenco_prestiti'))

    # Usiamo i dati comuni dal primo record (indirizzo e telefono sono uguali)
    nome_prodotto_primo, data_inizio, indirizzo, telefono, note_singola = oggetti[0]
    data_str = datetime.now().strftime("%d/%m/%Y") # Data di stampa del documento

    pdf = FPDF()
    pdf.add_page()
    
    # --- LOGO E INTESTAZIONE ---
    logo_path = os.path.join('static', 'Magazzino.jpg')
    if os.path.exists(logo_path):
        pdf.image(logo_path, 12, 10, 28)
    
    pdf.set_font("Arial", "B", 14)
    pdf.set_x(45)
    pdf.cell(0, 8, 'Associazione Protezione Civile "LUNGONI" ODV', ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.set_x(45)
    pdf.cell(0, 5, 'Via La Funtana, sn - 07028 Santa Teresa Gallura (SS)', ln=True)
    pdf.ln(20)

    # --- TITOLO ---
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "COMODATO D'USO GRATUITO - RIEPILOGO", ln=True, align="C")
    pdf.ln(10)
    
    # --- DATI BENEFICIARIO ---
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"In data odierna {data_str}, si conferma il prestito al Sig./ra:", ln=True)
    
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, f"SOGGETTO: {beneficiario.upper()}", ln=True)
    
    pdf.set_font("Arial", "", 11)
    if indirizzo and indirizzo.strip():
        pdf.cell(0, 7, f"RESIDENTE IN: {indirizzo.strip()}", ln=True)
    if telefono and telefono.strip():
        pdf.cell(0, 7, f"RECAPITO TEL: {telefono.strip()}", ln=True)

    pdf.ln(15) 

    # --- ELENCO ATTREZZATURE CONSEGNATE ---
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "ELENCO ATTREZZATURE IN CARICO:", ln=True)
    
    pdf.set_font("Arial", "", 12)
    pdf.set_fill_color(245, 245, 245)
    
    for obj in oggetti:
        # obj[0] è il nome del prodotto, obj[1] è la data inizio
        info_riga = f" - {obj[0]} (consegnato il {obj[1].strftime('%d/%m/%Y')})"
        pdf.cell(0, 10, info_riga.encode('latin-1', 'replace').decode('latin-1'), border='B', ln=True, fill=True)
    
    # --- NOTE CUMULATIVE ---
    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 5, "Note: Il beneficiario è responsabile della corretta conservazione di tutti gli oggetti elencati.", ln=True)

    # --- INFORMATIVA PRIVACY ---
    pdf.set_y(-65)
    pdf.set_font("Arial", "I", 8)
    privacy = ("Informativa Privacy: I dati personali raccolti sono trattati dall'Associazione esclusivamente per "
               "la gestione del presente comodato, in conformità al Regolamento UE 2016/679 (GDPR).")
    pdf.multi_cell(0, 4, privacy.encode('latin-1', 'replace').decode('latin-1'), align="C")

    # --- FIRME ---
    pdf.ln(10)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 10, "Firma del ricevente (Comodatario)", 0, 0, "C")
    pdf.cell(95, 10, "Per l'Associazione (Il Presidente/Delegato)", 0, 1, "C")
    
    pdf_out = pdf.output(dest='S').encode('latin-1', 'replace')
    return send_file(BytesIO(pdf_out), mimetype='application/pdf', as_attachment=False, download_name=f"Riepilogo_{beneficiario}.pdf")



@app.context_processor
def inject_globals():
    if "user_id" in session:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM prodotti WHERE quantita <= quantita_minima AND attivo = TRUE")
        count = cur.fetchone()[0]
        db.close()
        return dict(global_count_spesa=count)
    return dict(global_count_spesa=0)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
