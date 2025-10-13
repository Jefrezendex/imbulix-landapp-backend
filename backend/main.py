from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import re
import csv
import os

app = FastAPI(title="Imbulix-LandApp CTR Verifier")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_FILE = "resultados.csv"
BASE_URL = "https://rcc-spregula.coletas.online/Transportador/CTR/ImprimeCTR.aspx?id="

# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Data de Envio", "Código", "Status"])

@app.get("/")
def root():
    return {"message": "Imbulix-LandApp CTR backend is running."}

@app.get("/buscar/{codigo}")
def buscar(codigo: str):
    if not codigo.isdigit() or len(codigo) != 8:
        raise HTTPException(status_code=400, detail="Código inválido. Deve ter 8 dígitos numéricos.")
    url = f"{BASE_URL}{codigo}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type','')
        html = resp.text

        # Try to extract "Data de Envio" via regex or BeautifulSoup text search
        # First try regex common patterns dd/mm/yyyy
        m = re.search(r"Data de Envio[:\s]*([0-9]{2}/[0-9]{2}/[0-9]{4})", html, re.IGNORECASE)
        data_envio = m.group(1) if m else None

        # fallback: search for text nodes containing 'Data de Envio'
        if not data_envio:
            try:
                soup = BeautifulSoup(html, "html.parser")
                matches = soup.find_all(string=re.compile(r"Data de Envio", re.IGNORECASE))
                for s in matches:
                    txt = s.strip()
                    # try to extract date from that string
                    m2 = re.search(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", txt)
                    if m2:
                        data_envio = m2.group(1)
                        break
            except Exception:
                pass

        if not data_envio:
            data_envio = "Não encontrada"

        # Return the original URL (so front can load via iframe) and the detected date
        return {"url": url, "data_envio": data_envio, "content_type": content_type}
    except requests.HTTPError as e:
        raise HTTPException(status_code=404, detail=f"Documento não encontrado: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/registrar")
def registrar(payload: dict):
    # expects: {"codigo": "...", "data_envio": "...", "status":"Aceito" }
    codigo = payload.get("codigo")
    data_envio = payload.get("data_envio")
    status = payload.get("status")
    if not codigo:
        raise HTTPException(status_code=400, detail="Campo codigo é obrigatório.")
    if status not in ("Aceito", "Aceito com restrição"):
        raise HTTPException(status_code=400, detail="Status inválido.")
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([data_envio or "", codigo, status])
    return {"message": "Registro salvo com sucesso."}

@app.get("/historico")
def historico():
    registros = []
    if os.path.exists(CSV_FILE):
        import csv
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                registros.append(r)
    return registros
