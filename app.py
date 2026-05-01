# app.py
from __future__ import annotations

import os
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

app = FastAPI(title="Calculadora de Fretes", version="3.0.0")

MELHOR_ENVIO_BASE_URL = os.getenv("MELHOR_ENVIO_BASE_URL", "https://www.melhorenvio.com.br")
MELHOR_ENVIO_TOKEN = os.getenv("MELHOR_ENVIO_TOKEN", "")
MELHOR_ENVIO_USER_AGENT = os.getenv(
    "MELHOR_ENVIO_USER_AGENT",
    "CalculadoraFretes/1.0 (suporte@suaempresa.com)",
)
DEFAULT_FROM_POSTAL_CODE = os.getenv("DEFAULT_FROM_POSTAL_CODE", "89228397")
DEFAULT_FROM_CITY = "JOINVILLE"
DEFAULT_FROM_UF = "SC"
VIACEP_BASE_URL = os.getenv("VIACEP_BASE_URL", "https://viacep.com.br/ws")
DISKTENHA_ENABLED = os.getenv("DISKTENHA_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
DISKTENHA_CUBIC_DIVISOR = float(os.getenv("DISKTENHA_CUBIC_DIVISOR", "6000"))
DISKTENHA_VOLUMINOUS_FEE = float(os.getenv("DISKTENHA_VOLUMINOUS_FEE", "3.0"))

BOXES: dict[str, dict[str, float | str]] = {
    "1": {
        "label": "Caixa 1",
        "width": 26.0,
        "height": 19.0,
        "length": 36.0,
    },
    "2": {
        "label": "Caixa 2",
        "width": 18.0,
        "height": 18.0,
        "length": 27.0,
    },
}

DISKTENHA_TABLE: dict[str, dict[str, Any]] = {
    "AGRONOMICA": {"price": 52.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "AGUAS MORNAS": {"price": 50.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "APIUNA": {"price": 56.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": "FLASH SERVICOS"},
    "ARAQUARI": {"price": 16.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "ARAUCARIA": {"price": 45.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "ASCURRA": {"price": 45.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": "FLASH SERVICOS"},
    "AURORA": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "BALNEARIO BARRA DO SUL": {"price": 16.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "BALNEARIO CAMBORIU": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "BALNEARIO PICARRAS": {"price": 33.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "BARRA VELHA": {"price": 33.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "BENEDITO NOVO": {"price": 45.0, "delivery_text": "2ª, 4ª e 6ª, até 12h", "partner": "FLASH SERVICOS"},
    "BIGUACU": {"price": 49.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "BLUMENAU": {"price": 37.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "BRACO DO TROMBUDO": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "BRUSQUE": {"price": 42.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "CAMBORIU": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "CAMPO ALEGRE": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "CANELINHA": {"price": 44.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "COLOMBO": {"price": 43.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "CORUPA": {"price": 37.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "CURITIBA": {"price": 43.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "DOUTOR PEDRINHO": {"price": 45.0, "delivery_text": "2ª, 4ª e 6ª, até 12h", "partner": "FLASH SERVICOS"},
    "FLORIANOPOLIS CONTINENTE": {"price": 49.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "FLORIANOPOLIS ILHA": {"price": 49.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "FLORIANOPOLIS": {"price": 49.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "GARUVA": {"price": 14.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "GASPAR": {"price": 42.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "GOVERNADOR CELSO RAMOS": {"price": 50.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "GUABIRUBA": {"price": 46.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "GUARAMIRIM": {"price": 32.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "IBIRAMA": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "ILHOTA": {"price": 42.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "INDAIAL": {"price": 40.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": "FLASH SERVICOS"},
    "ITAJAI": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "ITAPEMA": {"price": 42.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "ITAPOA": {"price": 14.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "ITUPORANGA": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "JARAGUA DO SUL": {"price": 32.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "JOINVILLE": {"price": 14.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "LAURENTINO": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "LONTRAS": {"price": 52.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "LUIZ ALVES": {"price": 42.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "MAFRA": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "MASSARANDUBA": {"price": 32.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "NAVEGANTES": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "NOVA TRENTO": {"price": 45.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "PALHOCA": {"price": 49.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "PENHA": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "PINHAIS": {"price": 43.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "POMERODE": {"price": 37.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "PORTO BELO": {"price": 43.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "POUSO REDONDO": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "PRESIDENTE GETULIO": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "RIO DO OESTE": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "RIO DO SUL": {"price": 52.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "RIO DOS CEDROS": {"price": 45.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": "FLASH SERVICOS"},
    "RIO NEGRINHO": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "RIO NEGRO": {"price": 41.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "RODEIO": {"price": 45.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": "FLASH SERVICOS"},
    "SANTO AMARO DA IMPERATRIZ": {"price": 50.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "SAO BENTO DO SUL": {"price": 39.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "SAO FRANCISCO DO SUL": {"price": 16.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "SAO JOAO BATISTA": {"price": 45.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "SAO JOAO DO ITAPERIU": {"price": 33.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "SAO JOSE": {"price": 49.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "SAO JOSE DOS PINHAIS": {"price": 43.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "SCHROEDER": {"price": 37.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": None},
    "TAIO": {"price": 57.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "TIJUCAS": {"price": 44.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
    "TIMBO": {"price": 40.0, "delivery_text": "8h as 12 para coletas feitas no dia anterior a tarde e 15h as 18h para coletas feitas no mesmo dia pela manhã", "partner": "FLASH SERVICOS"},
    "TROMBUDO CENTRAL": {"price": 58.0, "delivery_text": "Próximo dia útil após a coleta. Das 8h as 18h", "partner": None},
}

HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Calculadora de Fretes</title>
  <style>
    :root {
      --bg: #eef2f6;
      --card: #ffffff;
      --text: #183153;
      --muted: #5e718d;
      --border: #d7e0ea;
      --primary: #0b5cab;
      --primary-2: #0e6fd0;
      --success-bg: #eaf6ee;
      --success-border: #b8dfc1;
      --danger-bg: #fff0f0;
      --danger-border: #f0c4c4;
      --shadow: 0 10px 24px rgba(18, 38, 63, 0.08);
      --radius: 16px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: 24px;
      font-family: Inter, system-ui, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }

    .container {
      max-width: 1440px;
      margin: 0 auto;
    }

    .header {
      text-align: center;
      margin-bottom: 24px;
    }

    .header h1 {
      margin: 0;
      font-size: 36px;
      line-height: 1.1;
    }

    .header p {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 16px;
    }

    .grid {
      display: grid;
      grid-template-columns: 470px 1fr;
      gap: 24px;
      align-items: start;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }

    .form-card {
      padding: 24px;
      position: sticky;
      top: 24px;
      max-height: calc(100vh - 48px);
      overflow-y: auto;
    }

    .results-card {
      padding: 24px;
      min-height: 420px;
    }

    .section-title {
      margin: 0 0 18px;
      font-size: 22px;
    }

    .subtitle {
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 14px;
    }

    .field {
      margin-bottom: 16px;
    }

    .field label {
      display: block;
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 8px;
    }

    .field input,
    .field select {
      width: 100%;
      padding: 14px 14px;
      border: 1px solid var(--border);
      border-radius: 12px;
      font-size: 16px;
      outline: none;
      background: #fff;
    }

    .field input:focus,
    .field select:focus {
      border-color: var(--primary-2);
      box-shadow: 0 0 0 4px rgba(14, 111, 208, 0.08);
    }

    .hint {
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }

    .volumes-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 16px;
    }

    .volume-card {
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      background: #f8fbff;
    }

    .volume-card h3 {
      margin: 0 0 6px;
      font-size: 18px;
    }

    .volume-card .dims {
      color: var(--muted);
      font-size: 14px;
      margin-bottom: 12px;
    }

    .mini-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .custom-volume-card {
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 12px;
      background: #fbfdff;
    }

    .custom-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }

    .custom-head h4 {
      margin: 0;
      font-size: 16px;
    }

    .btn-remove {
      background: #f5d9d9;
      color: #8a2c2c;
      padding: 10px 12px;
      font-size: 14px;
      border: 0;
      border-radius: 10px;
      cursor: pointer;
    }

    .actions {
      display: flex;
      gap: 12px;
      margin-top: 16px;
      flex-wrap: wrap;
    }

    button {
      border: 0;
      border-radius: 12px;
      padding: 14px 18px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
    }

    .btn-primary {
      flex: 1;
      background: var(--primary);
      color: #fff;
    }

    .btn-primary:hover { background: var(--primary-2); }

    .btn-secondary {
      background: #e7eef6;
      color: var(--text);
    }

    .btn-add {
      background: #e8f1fb;
      color: var(--primary);
    }

    .status {
      display: none;
      margin-bottom: 16px;
      padding: 14px 16px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .status.show { display: block; }
    .status.error {
      background: var(--danger-bg);
      border: 1px solid var(--danger-border);
      color: #8a2c2c;
    }

    .status.info {
      background: #edf5ff;
      border: 1px solid #c9def8;
      color: #194f90;
    }

    .best-card {
      display: none;
      margin-bottom: 20px;
      padding: 18px;
      border-radius: 14px;
      background: var(--success-bg);
      border: 1px solid var(--success-border);
    }

    .best-card.show { display: block; }

    .best-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }

    .best-badge {
      background: #d5efdb;
      color: #245f31;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
    }

    .kpis {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }

    .kpi {
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid rgba(36, 95, 49, 0.12);
      border-radius: 12px;
      padding: 12px;
    }

    .kpi span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }

    .kpi strong {
      font-size: 18px;
    }

    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: #fff;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 980px;
    }

    th, td {
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      font-size: 14px;
      vertical-align: top;
    }

    th {
      background: #f6f9fc;
      font-size: 13px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    tr:last-child td { border-bottom: 0; }

    .price {
      font-weight: 800;
      color: #0b5cab;
    }

    .muted {
      color: var(--muted);
      font-size: 13px;
    }

    .empty {
      display: grid;
      place-items: center;
      min-height: 300px;
      text-align: center;
      color: var(--muted);
      border: 1px dashed var(--border);
      border-radius: 14px;
      background: #f8fbfe;
      padding: 24px;
    }

    .loading {
      display: none;
      margin-bottom: 16px;
      color: var(--muted);
      font-size: 14px;
      font-weight: 700;
    }

    .loading.show { display: block; }

    .summary-box {
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 16px;
      background: #f8fbff;
      color: var(--muted);
      font-size: 13px;
    }

    @media (max-width: 1120px) {
      .grid {
        grid-template-columns: 1fr;
      }

      .form-card {
        position: static;
        max-height: none;
      }
    }

    @media (max-width: 640px) {
      .volumes-grid,
      .mini-grid,
      .kpis {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Calculadora de fretes</h1>
      <p>Consulta rápida com Melhor Envio e Disk&Tenha.</p>
    </div>

    <div class="grid">
      <div class="card form-card">
        <h2 class="section-title">Consulta</h2>
        <p class="subtitle">Origem fixa em Joinville. Informe as quantidades das caixas padrão e adicione outros volumes se necessário.</p>

        <form id="quote-form">
          <div class="field">
            <label for="from_postal_code">CEP de origem</label>
            <input id="from_postal_code" name="from_postal_code" type="text" maxlength="9" value="{{FROM_POSTAL_CODE}}" />
            <span class="hint">Joinville fixo por padrão.</span>
          </div>

          <div class="field">
            <label for="to_postal_code">CEP de destino</label>
            <input id="to_postal_code" name="to_postal_code" type="text" maxlength="9" placeholder="00000-000" />
          </div>

          <div class="field">
            <label for="insurance_value">Valor da NF / valor declarado (R$)</label>
            <input id="insurance_value" name="insurance_value" type="number" step="0.01" min="0" value="0" />
          </div>

          <div class="summary-box">
            Preencha a quantidade e o peso unitário das caixas padrão. Se houver outro tamanho, use o botão <strong>Adicionar volume</strong>.
          </div>

          <div class="volumes-grid">
            <div class="volume-card">
              <h3>Caixa 1</h3>
              <div class="dims">26 x 19 x 36 cm</div>
              <div class="mini-grid">
                <div class="field">
                  <label for="box1_quantity">Quantidade</label>
                  <input id="box1_quantity" type="number" min="0" step="1" value="0" />
                </div>
                <div class="field">
                  <label for="box1_weight">Peso unitário (kg)</label>
                  <input id="box1_weight" type="number" min="0" step="0.001" value="0" />
                </div>
              </div>
            </div>

            <div class="volume-card">
              <h3>Caixa 2</h3>
              <div class="dims">18 x 18 x 27 cm</div>
              <div class="mini-grid">
                <div class="field">
                  <label for="box2_quantity">Quantidade</label>
                  <input id="box2_quantity" type="number" min="0" step="1" value="0" />
                </div>
                <div class="field">
                  <label for="box2_weight">Peso unitário (kg)</label>
                  <input id="box2_weight" type="number" min="0" step="0.001" value="0" />
                </div>
              </div>
            </div>
          </div>

          <h3 style="margin: 24px 0 12px; font-size: 18px;">Volumes adicionais</h3>
          <div id="custom-volumes"></div>

          <div class="actions">
            <button type="button" id="add-volume-btn" class="btn-add">Adicionar volume</button>
          </div>

          <div class="actions">
            <button type="submit" class="btn-primary">Calcular</button>
            <button type="button" id="reset-btn" class="btn-secondary">Limpar</button>
          </div>
        </form>
      </div>

      <div class="card results-card">
        <div id="status" class="status"></div>
        <div id="loading" class="loading">Consultando fretes...</div>

        <div id="best-card" class="best-card">
          <div class="best-head">
            <div>
              <div class="muted">Melhor opção encontrada</div>
              <h2 id="best-title" style="margin: 4px 0 0; font-size: 24px;"></h2>
            </div>
            <div class="best-badge">Menor preço</div>
          </div>
          <div id="best-company" class="muted"></div>
          <div class="kpis">
            <div class="kpi">
              <span>Provider</span>
              <strong id="best-provider">—</strong>
            </div>
            <div class="kpi">
              <span>Preço</span>
              <strong id="best-price">—</strong>
            </div>
            <div class="kpi">
              <span>Prazo</span>
              <strong id="best-days">—</strong>
            </div>
            <div class="kpi">
              <span>Total de volumes</span>
              <strong id="best-box">—</strong>
            </div>
          </div>
        </div>

        <div id="results-empty" class="empty">
          <div>
            <h3 style="margin: 0 0 8px;">Sem consulta ainda</h3>
            <p style="margin: 0;">Informe CEP destino e volumes para ver as opções de frete.</p>
          </div>
        </div>

        <div id="results-content" style="display: none;">
          <h2 class="section-title" style="margin-top: 0;">Opções retornadas</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Transportadora</th>
                  <th>Serviço</th>
                  <th>Tipo</th>
                  <th>Preço</th>
                  <th>Prazo</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="results-body"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const form = document.getElementById("quote-form");
    const resetBtn = document.getElementById("reset-btn");
    const addVolumeBtn = document.getElementById("add-volume-btn");
    const customVolumesContainer = document.getElementById("custom-volumes");
    const statusBox = document.getElementById("status");
    const loadingBox = document.getElementById("loading");
    const emptyBox = document.getElementById("results-empty");
    const contentBox = document.getElementById("results-content");
    const resultsBody = document.getElementById("results-body");
    const bestCard = document.getElementById("best-card");
    const bestTitle = document.getElementById("best-title");
    const bestCompany = document.getElementById("best-company");
    const bestProvider = document.getElementById("best-provider");
    const bestPrice = document.getElementById("best-price");
    const bestDays = document.getElementById("best-days");
    const bestBox = document.getElementById("best-box");

    let customVolumeIndex = 0;

    function onlyDigits(value) {
      return (value || "").replace(/\\D/g, "");
    }

    function formatCep(value) {
      const digits = onlyDigits(value).slice(0, 8);
      if (digits.length <= 5) return digits;
      return `${digits.slice(0, 5)}-${digits.slice(5)}`;
    }

    function formatBRL(value) {
      const numeric = Number(value || 0);
      return new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL"
      }).format(numeric);
    }

    function showStatus(message, type) {
      statusBox.textContent = message;
      statusBox.className = `status show ${type}`;
    }

    function hideStatus() {
      statusBox.textContent = "";
      statusBox.className = "status";
    }

    function setLoading(isLoading) {
      loadingBox.className = isLoading ? "loading show" : "loading";
    }

    function clearResults() {
      resultsBody.innerHTML = "";
      bestCard.classList.remove("show");
      contentBox.style.display = "none";
      emptyBox.style.display = "grid";
    }

    function fillBest(best, totalVolumes) {
      if (!best) {
        bestCard.classList.remove("show");
        return;
      }

      bestTitle.textContent = best.service_name || "Serviço sem nome";
      bestCompany.textContent = best.company_name || "Transportadora não informada";
      bestProvider.textContent = best.provider_label || best.provider || "-";
      bestPrice.textContent = formatBRL(best.price);
      bestDays.textContent = best.delivery_label || "Não informado";
      bestBox.textContent = `${totalVolumes} volume(s)`;
      bestCard.classList.add("show");
    }

    function renderRows(items) {
      const rows = [];

      for (const item of items) {
        const status = item.error ? (typeof item.error === "string" ? item.error : JSON.stringify(item.error)) : "Disponível";
        rows.push(`
          <tr>
            <td>${item.provider_label || item.provider || "-"}</td>
            <td>${item.company_name || "-"}</td>
            <td>${item.service_name || "-"}</td>
            <td>${item.service_type || "-"}</td>
            <td>${item.error ? "-" : `<span class="price">${formatBRL(item.price)}</span>`}</td>
            <td>${item.delivery_label || "-"}</td>
            <td>${status}</td>
          </tr>
        `);
      }

      resultsBody.innerHTML = rows.join("");
      contentBox.style.display = "block";
      emptyBox.style.display = "none";
    }

    async function parseResponse(response) {
      const rawText = await response.text();
      if (!rawText) {
        return {};
      }

      try {
        return JSON.parse(rawText);
      } catch {
        return { detail: rawText };
      }
    }

    function createCustomVolumeCard(index) {
      const wrapper = document.createElement("div");
      wrapper.className = "custom-volume-card";
      wrapper.dataset.index = index;
      wrapper.innerHTML = `
        <div class="custom-head">
          <h4>Volume adicional ${index + 1}</h4>
          <button type="button" class="btn-remove" data-remove-index="${index}">Remover</button>
        </div>
        <div class="mini-grid">
          <div class="field">
            <label>Largura (cm)</label>
            <input type="number" min="0.1" step="0.1" class="custom-width" />
          </div>
          <div class="field">
            <label>Altura (cm)</label>
            <input type="number" min="0.1" step="0.1" class="custom-height" />
          </div>
          <div class="field">
            <label>Comprimento (cm)</label>
            <input type="number" min="0.1" step="0.1" class="custom-length" />
          </div>
          <div class="field">
            <label>Peso unitário (kg)</label>
            <input type="number" min="0.001" step="0.001" class="custom-weight" />
          </div>
          <div class="field">
            <label>Quantidade</label>
            <input type="number" min="1" step="1" value="1" class="custom-quantity" />
          </div>
        </div>
      `;
      return wrapper;
    }

    function addCustomVolume() {
      const card = createCustomVolumeCard(customVolumeIndex);
      customVolumesContainer.appendChild(card);
      customVolumeIndex += 1;
    }

    function resetFormValues() {
      document.getElementById("from_postal_code").value = "{{FROM_POSTAL_CODE_FORMATTED}}";
      document.getElementById("to_postal_code").value = "";
      document.getElementById("insurance_value").value = "0";
      document.getElementById("box1_quantity").value = "0";
      document.getElementById("box1_weight").value = "0";
      document.getElementById("box2_quantity").value = "0";
      document.getElementById("box2_weight").value = "0";
      customVolumesContainer.innerHTML = "";
      customVolumeIndex = 0;
    }

    function buildStandardBoxes() {
      return [
        {
          box_type: "1",
          quantity: Number(document.getElementById("box1_quantity").value || 0),
          weight: Number(document.getElementById("box1_weight").value || 0)
        },
        {
          box_type: "2",
          quantity: Number(document.getElementById("box2_quantity").value || 0),
          weight: Number(document.getElementById("box2_weight").value || 0)
        }
      ];
    }

    function buildCustomVolumes() {
      const cards = Array.from(document.querySelectorAll(".custom-volume-card"));
      return cards.map((card) => ({
        width: Number(card.querySelector(".custom-width").value || 0),
        height: Number(card.querySelector(".custom-height").value || 0),
        length: Number(card.querySelector(".custom-length").value || 0),
        weight: Number(card.querySelector(".custom-weight").value || 0),
        quantity: Number(card.querySelector(".custom-quantity").value || 0)
      }));
    }

    function countTotalVolumes(standardBoxes, customVolumes) {
      const standard = standardBoxes.reduce((acc, item) => acc + (Number(item.quantity) || 0), 0);
      const custom = customVolumes.reduce((acc, item) => acc + (Number(item.quantity) || 0), 0);
      return standard + custom;
    }

    document.getElementById("from_postal_code").addEventListener("input", (e) => {
      e.target.value = formatCep(e.target.value);
    });

    document.getElementById("to_postal_code").addEventListener("input", (e) => {
      e.target.value = formatCep(e.target.value);
    });

    addVolumeBtn.addEventListener("click", () => {
      addCustomVolume();
    });

    customVolumesContainer.addEventListener("click", (event) => {
      const target = event.target;
      if (target.matches("[data-remove-index]")) {
        target.closest(".custom-volume-card").remove();
      }
    });

    resetBtn.addEventListener("click", () => {
      hideStatus();
      clearResults();
      resetFormValues();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideStatus();
      setLoading(true);

      const standard_boxes = buildStandardBoxes();
      const custom_volumes = buildCustomVolumes();
      const payload = {
        from_postal_code: onlyDigits(document.getElementById("from_postal_code").value),
        to_postal_code: onlyDigits(document.getElementById("to_postal_code").value),
        insurance_value: Number(document.getElementById("insurance_value").value || 0),
        standard_boxes,
        custom_volumes
      };

      if (payload.from_postal_code.length !== 8) {
        setLoading(false);
        showStatus("CEP de origem inválido.", "error");
        return;
      }

      if (payload.to_postal_code.length !== 8) {
        setLoading(false);
        showStatus("CEP de destino inválido.", "error");
        return;
      }

      const totalVolumes = countTotalVolumes(standard_boxes, custom_volumes);
      if (totalVolumes <= 0) {
        setLoading(false);
        showStatus("Informe ao menos 1 volume para cotação.", "error");
        return;
      }

      try {
        const response = await fetch("/api/quote", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        });

        const data = await parseResponse(response);

        if (!response.ok) {
          let detail = data?.detail ?? "Erro ao consultar a API.";
          if (typeof detail !== "string") {
            detail = JSON.stringify(detail, null, 2);
          }
          throw new Error(detail);
        }

        fillBest(data.best_option, data.total_volumes || totalVolumes);
        renderRows(data.all_options || []);

        if ((data.available_options || []).length === 0) {
          showStatus("Nenhuma opção disponível para esta consulta.", "info");
        }
      } catch (error) {
        clearResults();
        showStatus(error.message || "Falha ao consultar fretes.", "error");
      } finally {
        setLoading(false);
      }
    });

    resetFormValues();
  </script>
</body>
</html>
"""


class StandardBoxRequest(BaseModel):
    box_type: str = Field(..., description="Tipo de caixa padrão")
    quantity: int = Field(..., ge=0, description="Quantidade")
    weight: float = Field(..., ge=0, description="Peso unitário em kg")

    @field_validator("box_type")
    @classmethod
    def validate_box_type(cls, value: str) -> str:
        if value not in BOXES:
            raise ValueError("Tipo de caixa inválido.")
        return value


class CustomVolumeRequest(BaseModel):
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0)
    length: float = Field(..., gt=0)
    weight: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class QuoteRequest(BaseModel):
    from_postal_code: str = Field(..., description="CEP de origem")
    to_postal_code: str = Field(..., description="CEP de destino")
    insurance_value: float = Field(default=0.0, ge=0, description="Valor declarado em reais")
    standard_boxes: list[StandardBoxRequest] = Field(default_factory=list)
    custom_volumes: list[CustomVolumeRequest] = Field(default_factory=list)
    receipt: bool = Field(default=False)
    own_hand: bool = Field(default=False)
    collect: bool = Field(default=False)

    @field_validator("from_postal_code", "to_postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        digits = digits_only(value)
        if len(digits) != 8:
            raise ValueError("CEP deve conter 8 dígitos.")
        return digits

    @field_validator("insurance_value")
    @classmethod
    def validate_insurance_value(cls, value: float) -> float:
        try:
            normalized = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError("Valor de seguro inválido.") from exc
        if normalized < 0:
            raise ValueError("Valor de seguro não pode ser negativo.")
        return float(normalized)

    @model_validator(mode="after")
    def validate_has_volumes(self) -> "QuoteRequest":
        total_standard = sum(item.quantity for item in self.standard_boxes)
        total_custom = sum(item.quantity for item in self.custom_volumes)
        if total_standard + total_custom <= 0:
            raise ValueError("Informe ao menos 1 volume para cotação.")
        for item in self.standard_boxes:
            if item.quantity > 0 and item.weight <= 0:
                raise ValueError(f"Informe o peso unitário da {BOXES[item.box_type]['label']}.")
        return self


def digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def format_cep(value: str) -> str:
    digits = digits_only(value)
    if len(digits) != 8:
        return value
    return f"{digits[:5]}-{digits[5:]}"


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.upper())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).replace("(", " ").replace(")", " ").replace("-", " ").replace("/", " ").replace(".", " ").replace(",", " ").replace("  ", " ").strip()


def get_config_errors() -> list[str]:
    errors: list[str] = []

    if not MELHOR_ENVIO_TOKEN.strip():
        errors.append("MELHOR_ENVIO_TOKEN não configurado.")
    if not MELHOR_ENVIO_USER_AGENT.strip():
        errors.append("MELHOR_ENVIO_USER_AGENT não configurado.")
    elif "@" not in MELHOR_ENVIO_USER_AGENT:
        errors.append("MELHOR_ENVIO_USER_AGENT deve conter um e-mail de contato.")
    if len(digits_only(DEFAULT_FROM_POSTAL_CODE)) != 8:
        errors.append("DEFAULT_FROM_POSTAL_CODE inválido.")
    if DISKTENHA_CUBIC_DIVISOR <= 0:
        errors.append("DISKTENHA_CUBIC_DIVISOR inválido.")

    return errors


def build_volumes(req: QuoteRequest) -> list[dict[str, Any]]:
    volumes: list[dict[str, Any]] = []

    for item in req.standard_boxes:
        if item.quantity <= 0:
            continue
        box = BOXES[item.box_type]
        volumes.append(
            {
                "source": f"Caixa {item.box_type}",
                "width": float(box["width"]),
                "height": float(box["height"]),
                "length": float(box["length"]),
                "weight": item.weight,
                "insurance_value": 0.0,
                "quantity": item.quantity,
            }
        )

    for index, item in enumerate(req.custom_volumes, start=1):
        volumes.append(
            {
                "source": f"Volume adicional {index}",
                "width": item.width,
                "height": item.height,
                "length": item.length,
                "weight": item.weight,
                "insurance_value": 0.0,
                "quantity": item.quantity,
            }
        )

    total_units = sum(int(volume["quantity"]) for volume in volumes)
    if total_units <= 0:
        raise HTTPException(status_code=422, detail="Nenhum volume válido informado.")

    insurance_per_unit = round(req.insurance_value / total_units, 2) if req.insurance_value > 0 else 0.0

    for volume in volumes:
        volume["insurance_value"] = insurance_per_unit

    return volumes


def build_melhor_envio_payload(req: QuoteRequest, volumes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "from": {
            "postal_code": req.from_postal_code,
        },
        "to": {
            "postal_code": req.to_postal_code,
        },
        "volumes": [
            {
                "width": volume["width"],
                "height": volume["height"],
                "length": volume["length"],
                "weight": volume["weight"],
                "insurance_value": volume["insurance_value"],
                "quantity": volume["quantity"],
            }
            for volume in volumes
        ],
        "options": {
            "receipt": req.receipt,
            "own_hand": req.own_hand,
            "collect": req.collect,
        },
    }


def get_total_actual_weight(volumes: list[dict[str, Any]]) -> float:
    return round(sum(float(v["weight"]) * int(v["quantity"]) for v in volumes), 3)


def get_total_cubic_weight(volumes: list[dict[str, Any]], cubic_divisor: float) -> float:
    total = 0.0
    for volume in volumes:
        cubic_cm = float(volume["width"]) * float(volume["height"]) * float(volume["length"])
        total += (cubic_cm / cubic_divisor) * int(volume["quantity"])
    return round(total, 3)


def is_voluminous_load(volumes: list[dict[str, Any]], actual_weight: float) -> bool:
    if 50 <= actual_weight <= 150:
        return True
    for volume in volumes:
        if float(volume["height"]) > 112 or float(volume["width"]) > 105 or float(volume["length"]) > 155:
            return True
    return False


def parse_price(item: dict[str, Any]) -> float:
    raw = item.get("custom_price", item.get("price", "999999"))
    try:
        return float(str(raw).replace(",", "."))
    except (ValueError, TypeError):
        return 999999.0


def parse_delivery_days(item: dict[str, Any]) -> int | None:
    raw = item.get("custom_delivery_time", item.get("delivery_time"))
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def delivery_days_to_label(days: int | None) -> str:
    if days is None:
        return "-"
    return f"{days} dia(s)"


def classify_service(delivery_text: str, delivery_days: int | None) -> str:
    if "PROXIMO DIA UTIL" in normalize_text(delivery_text):
        return "expresso"
    if delivery_days is not None and delivery_days <= 1:
        return "expresso"
    return "programado"


class CepLookupClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "CalculadoraFretes/1.0"})

    def lookup(self, postal_code: str) -> dict[str, str]:
        url = f"{self.base_url}/{postal_code}/json/"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Falha ao consultar CEP: {exc}") from exc

        data = response.json()
        if data.get("erro"):
            raise HTTPException(status_code=422, detail="CEP de destino não encontrado.")
        city = str(data.get("localidade") or "").strip()
        uf = str(data.get("uf") or "").strip()
        if not city or not uf:
            raise HTTPException(status_code=422, detail="CEP sem cidade/UF válidos.")
        return {"city": city, "uf": uf}


class MelhorEnvioClient:
    def __init__(self, token: str, base_url: str, user_agent: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": user_agent,
            }
        )

    def calculate(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v2/me/shipment/calculate"
        try:
            response = self.session.post(url, json=payload, timeout=30)
        except requests.Timeout as exc:
            raise HTTPException(status_code=504, detail="Timeout ao consultar o Melhor Envio.") from exc
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Erro de conexão com o Melhor Envio: {exc}") from exc

        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Token inválido, expirado ou revogado.")
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail="Sem permissão para cotação na API do Melhor Envio.")
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text or "Erro desconhecido no Melhor Envio."
            raise HTTPException(status_code=response.status_code, detail=detail)

        try:
            data = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=f"Resposta inválida do Melhor Envio: {response.text[:500]}") from exc

        if not isinstance(data, list):
            raise HTTPException(status_code=502, detail="Resposta inesperada da API do Melhor Envio.")

        return data


class DiskTenhaProvider:
    def quote(self, destination_city: str, destination_uf: str, volumes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not DISKTENHA_ENABLED:
            return []

        normalized_city = normalize_text(destination_city)

        if destination_uf.upper() not in {"SC", "PR"}:
            return [
                {
                    "provider": "disktenha",
                    "provider_label": "Disk&Tenha",
                    "company_name": "Disk&Tenha",
                    "service_name": "Tabela Joinville",
                    "service_type": "expresso",
                    "price": None,
                    "delivery_days": None,
                    "delivery_label": "-",
                    "error": f"Disk&Tenha não atende a UF {destination_uf.upper()} pela tabela local.",
                    "metadata": {"city": destination_city, "uf": destination_uf},
                }
            ]

        matched_rule = DISKTENHA_TABLE.get(normalized_city)
        if matched_rule is None and normalized_city == "FLORIANOPOLIS":
            matched_rule = DISKTENHA_TABLE.get("FLORIANOPOLIS")

        if matched_rule is None:
            return [
                {
                    "provider": "disktenha",
                    "provider_label": "Disk&Tenha",
                    "company_name": "Disk&Tenha",
                    "service_name": "Tabela Joinville",
                    "service_type": "expresso",
                    "price": None,
                    "delivery_days": None,
                    "delivery_label": "-",
                    "error": f"Cidade {destination_city}/{destination_uf} não encontrada na tabela da Disk&Tenha.",
                    "metadata": {"city": destination_city, "uf": destination_uf},
                }
            ]

        actual_weight = get_total_actual_weight(volumes)
        cubic_weight = get_total_cubic_weight(volumes, DISKTENHA_CUBIC_DIVISOR)
        chargeable_weight = max(actual_weight, cubic_weight)
        price = float(matched_rule["price"])

        if chargeable_weight > 50:
            price += chargeable_weight - 50

        voluminous = is_voluminous_load(volumes, actual_weight)
        if voluminous:
            price += DISKTENHA_VOLUMINOUS_FEE

        delivery_text = str(matched_rule["delivery_text"])
        delivery_days = 1 if "PROXIMO DIA UTIL" in normalize_text(delivery_text) else None

        return [
            {
                "provider": "disktenha",
                "provider_label": "Disk&Tenha",
                "company_name": "Disk&Tenha",
                "service_name": "Tabela Joinville",
                "service_type": classify_service(delivery_text, delivery_days),
                "price": round(price, 2),
                "delivery_days": delivery_days,
                "delivery_label": delivery_text,
                "error": None,
                "metadata": {
                    "city": destination_city,
                    "uf": destination_uf,
                    "partner": matched_rule.get("partner"),
                    "actual_weight": actual_weight,
                    "cubic_weight": cubic_weight,
                    "chargeable_weight": round(chargeable_weight, 3),
                    "voluminous_fee_applied": voluminous,
                },
            }
        ]


def normalize_melhor_envio_result(item: dict[str, Any]) -> dict[str, Any]:
    company = item.get("company") or {}
    days = parse_delivery_days(item)
    return {
        "provider": "melhor_envio",
        "provider_label": "Melhor Envio",
        "company_name": company.get("name") or "Melhor Envio",
        "service_name": item.get("name"),
        "service_type": classify_service(item.get("name", ""), days),
        "price": parse_price(item),
        "delivery_days": days,
        "delivery_label": delivery_days_to_label(days),
        "error": item.get("error"),
        "metadata": item,
    }


def provider_error_result(provider: str, provider_label: str, detail: Any) -> dict[str, Any]:
    message = detail if isinstance(detail, str) else str(detail)
    return {
        "provider": provider,
        "provider_label": provider_label,
        "company_name": provider_label,
        "service_name": "-",
        "service_type": "-",
        "price": None,
        "delivery_days": None,
        "delivery_label": "-",
        "error": message,
        "metadata": {},
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": f"Erro interno: {str(exc)}"})


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (
        HTML_PAGE
        .replace("{{FROM_POSTAL_CODE}}", format_cep(DEFAULT_FROM_POSTAL_CODE))
        .replace("{{FROM_POSTAL_CODE_FORMATTED}}", format_cep(DEFAULT_FROM_POSTAL_CODE))
    )
    return HTMLResponse(content=html)


@app.get("/health")
def health() -> dict[str, Any]:
    config_errors = get_config_errors()
    return {
        "status": "ok" if not config_errors else "error",
        "config_ok": not config_errors,
        "config_errors": config_errors,
        "base_url": MELHOR_ENVIO_BASE_URL,
        "default_from_postal_code": format_cep(DEFAULT_FROM_POSTAL_CODE),
        "default_from_city": DEFAULT_FROM_CITY,
        "token_configured": bool(MELHOR_ENVIO_TOKEN.strip()),
        "user_agent_configured": bool(MELHOR_ENVIO_USER_AGENT.strip()),
        "disktenha_enabled": DISKTENHA_ENABLED,
        "disktenha_cubic_divisor": DISKTENHA_CUBIC_DIVISOR,
        "disktenha_cities_loaded": len(DISKTENHA_TABLE),
    }


@app.get("/api/boxes")
def get_boxes() -> dict[str, Any]:
    return {"boxes": BOXES}


@app.post("/api/quote")
def quote(req: QuoteRequest) -> dict[str, Any]:
    config_errors = get_config_errors()
    if config_errors:
        raise HTTPException(status_code=500, detail={"message": "Configuração inválida.", "errors": config_errors})

    volumes = build_volumes(req)
    cep_client = CepLookupClient(VIACEP_BASE_URL)
    destination = cep_client.lookup(req.to_postal_code)

    all_options: list[dict[str, Any]] = []

    try:
        melhor_envio_payload = build_melhor_envio_payload(req, volumes)
        melhor_envio_client = MelhorEnvioClient(
            token=MELHOR_ENVIO_TOKEN,
            base_url=MELHOR_ENVIO_BASE_URL,
            user_agent=MELHOR_ENVIO_USER_AGENT,
        )
        melhor_envio_raw = melhor_envio_client.calculate(melhor_envio_payload)
        all_options.extend(normalize_melhor_envio_result(item) for item in melhor_envio_raw)
    except HTTPException as exc:
        all_options.append(provider_error_result("melhor_envio", "Melhor Envio", exc.detail))

    disktenha_provider = DiskTenhaProvider()
    all_options.extend(disktenha_provider.quote(destination["city"], destination["uf"], volumes))

    available = [item for item in all_options if not item["error"] and item["price"] is not None]
    unavailable = [item for item in all_options if item["error"] or item["price"] is None]

    available.sort(key=lambda item: (float(item["price"]), item["delivery_days"] if item["delivery_days"] is not None else 999999))
    all_options_sorted = available + unavailable
    best_option = available[0] if available else None
    total_volumes = sum(int(volume["quantity"]) for volume in volumes)

    return {
        "input": {
            "from_postal_code": req.from_postal_code,
            "to_postal_code": req.to_postal_code,
            "insurance_value": req.insurance_value,
            "standard_boxes": [item.model_dump() for item in req.standard_boxes],
            "custom_volumes": [item.model_dump() for item in req.custom_volumes],
            "destination_city": destination["city"],
            "destination_uf": destination["uf"],
        },
        "total_volumes": total_volumes,
        "best_option": best_option,
        "available_options": available,
        "unavailable_options": unavailable,
        "all_options": all_options_sorted,
        "debug": {
            "actual_weight": get_total_actual_weight(volumes),
            "cubic_weight": get_total_cubic_weight(volumes, DISKTENHA_CUBIC_DIVISOR),
            "disktenha_cubic_divisor": DISKTENHA_CUBIC_DIVISOR,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000)