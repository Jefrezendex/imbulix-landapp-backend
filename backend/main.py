from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests
from bs4 import BeautifulSoup
import re
import csv
import os
from io import BytesIO
from openpyxl import Workbook

app = FastAPI(title="Imbulix-LandApp CTR Verifier (Updated)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_FILE = "resultados.csv"
REL_DIR = "relatorios"
BASE_URL = "https://rcc-spregula.coletas.online/Transportador/CTR/ImprimeCTR.aspx?id="

os.makedirs(REL_DIR, exist_ok=True)

# Ensure CSV exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Envio", "Código", "Classe do Material", "Valor", "Status"])

@app.get("/")
def root():
    return {"message": "Imbulix-LandApp CTR backend is running."}

def extract_envio_and_classe(html):
    envio = None
    classe = None
    # Try regex for date after "Envio"
    m = re.search(r"Envio[:\s]*([0-9]{2}/[0-9]{2}/[0-9]{4})", html, re.IGNORECASE)
    if m:
        envio = m.group(1)
    else:
        try:
            soup = BeautifulSoup(html, "html.parser")
            matches = soup.find_all(string=re.compile(r"Envio", re.IGNORECASE))
            for s in matches:
                txt = s.strip()
                mm = re.search(r"([0-9]{2}/[0-9]{2}/[0-9]{4})", txt)
                if mm:
                    envio = mm.group(1)
                    break
        except Exception:
            pass

    # Extract 'Classe' value
    try:
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find(string=re.compile(r"\bClasse\b", re.IGNORECASE))
        if tag:
            parent = tag.parent
            # try pattern in parent text
            full = parent.get_text(separator=" ").strip()
            m2 = re.search(r"Classe[:\s]*([^\n\r]+)", full, re.IGNORECASE)
            if m2:
                candidate = m2.group(1).strip()
                classe = candidate.splitlines()[0].strip()
            if not classe:
                sib = parent.find_next_sibling()
                if sib and sib.get_text(strip=True):
                    classe = sib.get_text(strip=True)
                else:
                    ne = parent.find_next()
                    if ne and ne.get_text(strip=True) and ne is not parent:
                        classe = ne.get_text(strip=True).splitlines()[0].strip()
    except Exception:
        classe = None

    if not envio:
        envio = "Não encontrada"
    if not classe:
        classe = "Não encontrada"
    return envio, classe

@app.get("/buscar/{codigo}")
def buscar(codigo: str):
    if not codigo.isdigit() or len(codigo) != 8:
        raise HTTPException(status_code=400, detail="Código inválido. Deve ter 8 dígitos numéricos.")
    url = f"{BASE_URL}{codigo}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        html = resp.text
        envio, classe = extract_envio_and_classe(html)
        return {"url": url, "envio": envio, "classe": classe}
    except requests.HTTPError as e:
        raise HTTPException(status_code=404, detail=f"Documento não encontrado: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/registrar")
def registrar(payload: dict):
    codigo = payload.get("codigo")
    envio = payload.get("envio")
    classe = payload.get("classe")
    status = payload.get("status")
    valor = "R$ 0,00"
    if not codigo:
        raise HTTPException(status_code=400, detail="Campo codigo é obrigatório.")
    if status not in ("Aceito", "Aceito com restrição"):
        raise HTTPException(status_code=400, detail="Status inválido.")
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([envio or "", codigo, classe or "", valor, status])
    return {"message": "Registro salvo com sucesso."}

@app.get("/historico")
def historico():
    registros = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                registros.append(r)
    return registros

@app.get("/download")
def download_csv():
    if os.path.exists(CSV_FILE):
        return FileResponse(CSV_FILE, media_type='text/csv', filename='resultados.csv')
    else:
        raise HTTPException(status_code=404, detail="CSV não encontrado.")

@app.get("/download_excel")
def download_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Relatório"
    headers = ["Envio", "Código", "Classe do Material", "Valor", "Status"]
    ws.append(headers)
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                ws.append([r.get("Envio",""), r.get("Código",""), r.get("Classe do Material",""), r.get("Valor",""), r.get("Status","")])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return FileResponse(bio, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename='relatorio.xlsx')
