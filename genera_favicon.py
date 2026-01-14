from PIL import Image
import os

# Percorso dell'immagine originale
img_path = "static/magazzino.jpg"  # sostituisci con il tuo file

# Controlla che l'immagine esista
if not os.path.exists(img_path):
    raise FileNotFoundError(f"L'immagine non esiste: {img_path}")

# Apri l'immagine
img = Image.open(img_path)

# Converti in RGBA (utile se c'è trasparenza)
img = img.convert("RGBA")

# Ridimensiona a diverse dimensioni (opzionale, ma consigliato per compatibilità)
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# Salva come favicon.ico
favicon_path = "static/favicon.ico"
img.save(favicon_path, format="ICO", sizes=sizes)

print(f"Favicon generato correttamente: {favicon_path}")
