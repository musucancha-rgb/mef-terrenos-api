from fastapi import FastAPI, HTTPException
import pandas as pd
from pathlib import Path

app = FastAPI(
    title="API Valor Oficial de Terrenos - MEF (2026)",
    version="1.0.0"
)

DATA_PATH = Path(__file__).parent / "data" / "resumen_distrito.csv"

# Carga al iniciar
df = pd.read_csv(DATA_PATH, dtype={"ubigeo": str})
df["ubigeo"] = df["ubigeo"].astype(str).str.zfill(6)

@app.get("/")
def home():
    return {
        "mensaje": "API MEF - Valor oficial de terrenos (Reporte Rápido)",
        "docs": "/docs",
        "endpoints": ["/departamentos", "/distritos", "/distrito/{ubigeo}", "/valor-terreno"]
    }

@app.get("/departamentos")
def departamentos():
    deps = sorted(df["departamento_folder"].dropna().unique().tolist())
    return {"departamentos": deps}

@app.get("/distritos")
def distritos(departamento: str):
    sub = df[df["departamento_folder"] == departamento]
    if sub.empty:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
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
