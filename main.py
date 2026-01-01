from fastapi import FastAPI, HTTPException
import pandas as pd
from pathlib import Path
import re
import unicodedata

app = FastAPI(
    title="API Valor Oficial de Terrenos - MEF (2026)",
    version="1.0.0"
)

DATA_PATH = Path(__file__).parent / "data" / "resumen_distrito.csv"

# Carga al iniciar
df = pd.read_csv(DATA_PATH, dtype={"ubigeo": str})
df["ubigeo"] = df["ubigeo"].astype(str).str.zfill(6)

# ---------------------------
# Normalización de texto
# ---------------------------
def normalizar(texto: str) -> str:
    """Quita tildes, deja mayúsculas, reemplaza espacios por _, limpia dobles __."""
    if texto is None:
        return ""
    texto = str(texto).strip()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = texto.upper()
    texto = texto.replace(" ", "_")
    texto = re.sub(r"_+", "_", texto)
    return texto

def lista_departamentos_disponibles() -> list[str]:
    return sorted(df["departamento_folder"].dropna().unique().tolist())

def resolver_departamento(dep_input: str) -> str | None:
    """
    Convierte lo que escribe el usuario en un ID válido tipo '15_LIMA'.
    Acepta:
      - '15_LIMA'
      - 'Lima' / 'LÍMA' / 'lima'
      - 'LA LIBERTAD' / 'La Libertad' / 'LA_LIBERTAD'
    """
    deps = lista_departamentos_disponibles()
    dep_norm = normalizar(dep_input)

    # Caso 1: ya viene con código (ej: 15_LIMA)
    if re.match(r"^\d{2}_.+$", dep_norm):
        return dep_norm if dep_norm in deps else None

    # Caso 2: viene solo nombre (LIMA) -> buscamos *_LIMA
    for d in deps:
        # d es tipo 15_LIMA
        nombre = d.split("_", 1)[1]  # LIMA
        if normalizar(nombre) == dep_norm:
            return d

    return None

# ---------------------------
# Endpoints
# ---------------------------
@app.get("/")
def home():
    return {
        "mensaje": "API MEF - Valor oficial de terrenos (Reporte Rápido)",
        "docs": "/docs",
        "endpoints": ["/departamentos", "/distritos", "/distrito/{ubigeo}", "/valor-terreno"]
    }

@app.get("/departamentos")
def departamentos():
    """
    Devuelve lista lista para desplegable:
    [
      {"id":"15_LIMA","codigo":"15","nombre":"Lima"},
      ...
    ]
    """
    deps = lista_departamentos_disponibles()
    salida = []
    for d in deps:
        codigo, nombre = d.split("_", 1)
        salida.append({
            "id": d,
            "codigo": codigo,
            "nombre": nombre.replace("_", " ").title()
        })
    return {"departamentos": salida}

@app.get("/distritos")
def distritos(departamento: str):
    """
    Acepta:
      /distritos?departamento=15_LIMA
      /distritos?departamento=Lima
      /distritos?departamento=LÍMA
      /distritos?departamento=La Libertad
      /distritos?departamento=LA_LIBERTAD
    """
    dep_id = resolver_departamento(departamento)
    if not dep_id:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    sub = df[df["departamento_folder"] == dep_id]
    if sub.empty:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")

    # Puedes devolver solo ubigeo (como ahora), o ubigeo+nombre distrito.
    # Mantengo tu formato original:
    return sub[["ubigeo"]].drop_duplicates().sort_values("ubigeo").to_dict(orient="records")

@app.get("/distrito/{ubigeo}")
def distrito_info(ubigeo: str):
    ubigeo = str(ubigeo).zfill(6)
    row = df[df["ubigeo"] == ubigeo]
    if row.empty:
        raise HTTPException(status_code=404, detail="Ubigeo no encontrado")

    r = row.iloc[0].to_dict()

    return {
        "ubigeo": ubigeo,
        "departamento_folder": r.get("departamento_folder"),
        "dpto": r.get("dpto"),
        "prov": r.get("prov"),
        "dist": r.get("dist"),
        "urb_min_soles_m2": r.get("urb_min_soles_m2"),
        "urb_max_soles_m2": r.get("urb_max_soles_m2"),
        "rus_min_soles_ha": r.get("rus_min_soles_ha"),
        "rus_max_soles_ha": r.get("rus_max_soles_ha"),
        "urbano_pdf": r.get("urbano_pdf"),
        "rustico_pdf": r.get("rustico_pdf"),
        "fuente": "MEF – Valores Arancelarios Oficiales",
        "anio": 2026,
        "nota": "Valor oficial referencial (no es valor comercial)."
    }

@app.get("/valor-terreno")
def valor_terreno(ubigeo: str, tipo: str, area: float):
    ubigeo = str(ubigeo).zfill(6)
    row = df[df["ubigeo"] == ubigeo]
    if row.empty:
        raise HTTPException(status_code=404, detail="Ubigeo no encontrado")

    r = row.iloc[0]
    tipo = tipo.lower().strip()

    if tipo == "urbano":
        vmin = r.get("urb_min_soles_m2")
        vmax = r.get("urb_max_soles_m2")
        unidad = "S/ por m²"
    elif tipo == "rustico":
        vmin = r.get("rus_min_soles_ha")
        vmax = r.get("rus_max_soles_ha")
        unidad = "S/ por ha"
    else:
        raise HTTPException(status_code=400, detail="tipo debe ser 'urbano' o 'rustico'")

    if pd.isna(vmin) or pd.isna(vmax):
        raise HTTPException(status_code=404, detail="No hay valores para ese tipo en este ubigeo")

    vmin = float(vmin)
    vmax = float(vmax)

    return {
        "ubigeo": ubigeo,
        "tipo": tipo,
        "unidad": unidad,
        "valor_min": vmin,
        "valor_max": vmax,
        "area": area,
        "valor_total_min": round(area * vmin, 2),
        "valor_total_max": round(area * vmax, 2),
        "fuente": "MEF – Valores Arancelarios Oficiales",
        "anio": 2026,
        "nota": "Valor oficial referencial (no es valor comercial)."
    }
