import os
import re
import traceback
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote
import requests
from flask import Flask, redirect, render_template_string, request, session, url_for
from gsheet_utils import append_to_sheet
ALLOWED_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9_.+-]+@((gmail|hotmail|outlook|yahoo)\.(com|com\.br))$",
    re.IGNORECASE,
)
NAME_PATTERN = re.compile(r"[A-Za-zÀ-ÿ '´`^~.-]+")
VALID_DDDS = {
    "11","12","13","14","15","16","17","18","19",
    "21","22","24","27","28",
    "31","32","33","34","35","37","38",
    "41","42","43","44","45","46","47","48","49",
    "51","53","54","55",
    "61","62","63","64","65","66","67","68","69",
    "71","73","74","75","77","79",
    "81","82","83","84","85","86","87","88","89",
    "91","92","93","94","95","96","97","98","99",
}
LOCAL_OPTIONS = [
    {"id": "5",  "nome": "CONSELHO COMUNITÁRIO DO PARQUE SÃO JOSÉ"},
    {"id": "6",  "nome": "INSTITUTO LOURDES VIANA"},
    {"id": "7",  "nome": "INSTITUTO NOVO RENASCER"},
    {"id": "11", "nome": "REGIONAL V - PROJETO AMIGOS DE DEUS (Projeto Tia Katia)"},
    {"id": "14", "nome": "REGIONAL II - INSTITUTO ESCOLHI AMAR"},
    {"id": "15", "nome": "REGIONAL I - INSTITUTO VIVA AGAPÊ"},
    {"id": "16", "nome": "IEQ JARDIM GUANABARA"},
    {"id": "17", "nome": "REGIONAL II - INSTITUTO LOURDES VIANA"},
    {"id": "18", "nome": "REGIONAL IV - INSTITUTO VIVA IDOSO"},
    {"id": "19", "nome": "REGIONAL V - PROJETO AMIGOS DE DEUS (Colégio Pequeno Aprendiz)"},
    {"id": "20", "nome": "REGIONAL V - CRECHE NOVO MUNDO PIONEIRO"},
    {"id": "22", "nome": "REGIONAL V - ESPAÇO DO PROJETO VIDA EM MOVIMENTO"},
    {"id": "23", "nome": "REGIONAL IX - CUCA JANGURUSSU"},
    {"id": "24", "nome": "REGIONAL VIII - CUCA JOSÉ WALTER"},
    {"id": "25", "nome": "REGIONAL V - SECRETARIA EXECUTIVA"},
    {"id": "26", "nome": "REGIONAL XI - CUCA PICI"},
    {"id": "27", "nome": "REGIONAL VIII - CAOF (CENTRO DE APOIO E ORIENTAÇÃO)"},
    {"id": "28", "nome": "CRE BOM JARDIM (CENTRO DE REFERÊNCIA DO EMPREENDEDOR)"},
    {"id": "29", "nome": "SINE MUNICIPAL PARQUELÂNDIA"},
    {"id": "30", "nome": "SINE MUNICIPAL ALDEOTA"},
    {"id": "31", "nome": "SINE MUNICIPAL SIQUEIRA"},
    {"id": "32", "nome": "SINE MUNICIPAL MARAPONGA"},
    {"id": "33", "nome": "SINE MUNICIPAL PANAMERICANO"},
    {"id": "34", "nome": "ATELIÊ CONJUNTO CEARÁ"},
    {"id": "35", "nome": "ATELIÊ CONJUNTO PALMEIRAS"},
    {"id": "36", "nome": "ATELIÊ BARRA DO CEARÁ"},
    {"id": "37", "nome": "ATELIÊ CANIDEZINHO (CENTRO CULTURAL)"},
    {"id": "38", "nome": "CRAS DA SERRINHA"},
    {"id": "39", "nome": "CENTRO DE REFERÊNCIA DO EMPREENDEDOR (CRE) DE MESSEJANA"},
]
COURSE_CATALOG = [
    {"id": "1",  "nome": "INTELIGÊNCIA ARTIFICIAL"},
    {"id": "2",  "nome": "MARKETING DIGITAL"},
    {"id": "3",  "nome": "OFICINA DE DANÇA"},
    {"id": "4",  "nome": "DESIGNER DE UNHAS"},
    {"id": "5",  "nome": "RECEPCIONISTA"},
    {"id": "6",  "nome": "MANICURE"},
    {"id": "7",  "nome": "EXTENSÃO DE CÍLIOS"},
    {"id": "8",  "nome": "SOCIAL MEDIA"},
    {"id": "9",  "nome": "TRANCISTA"},
    {"id": "10", "nome": "AUXILIAR ADMINISTRATIVO"},
    {"id": "11", "nome": "DESIGNER DE SOBRANCELHAS"},
    {"id": "12", "nome": "COSTURA"},
    {"id": "13", "nome": "ASSISTENTE DE LOGÍSTICA"},
    {"id": "14", "nome": "MONITOR LAZER E RECREAÇÃO"},
    {"id": "15", "nome": "PEDICURE"},
]
ADDRESS_OPTIONS = {
    "5":  "📍Rua Costa Freire, nº 2238, bairro Parangaba - Fortaleza, CE - CEP.: 60.730-255",
    "6":  "📍Rua Júlia Vasconcelos, nº 199 - Tatuapé - Fortaleza, CE - CEP.: 60125-150",
    "7":  "📍Travessa Ferreira dos Santos, nº 8b, bairro Álvaro Weyne - Fortaleza, CE - CEP.: 60.335-570",
    "11": "📍Rua Humberto Lomeu, nº 2074 - bairro Granja Portugal - Fortaleza, CE - CEP.: 60540-355",
    "14": "📍Rua Rosário, nº 38 - Bairro Aldeota. Fortaleza, CE - CEP.: 60.135-310",
    "15": "📍Rua Pedro Sampaio, nº 453 - bairro Vila Velha - Fortaleza, CE - CEP.: 60346-285",
    "16": "📍Rua Cariús, nº 669, bairro Jardim Guanabara - Fortaleza, CE - CEP.: 60.346-270",
    "18": "📍Rua Nove, nº 803, bairro Passaré - Fortaleza, CE - CEP.: 60.810-670",
    "19": "📍Rua Londrina, nº 1972 - bairro Granja Portugal - Fortaleza, CE - CEP.: 60540-485",
    "20": "📍Rua Pereira Barbosa, nº 1460 - bairro Siqueira - Fortaleza, CE - CEP.: 60732-382",
    "22": "📍Rua Barra Mansa, nº 478, bairro Bom Jardim - Fortaleza, CE - CEP.: 60.540-060",
    "23": "📍Avenida Governador Leonel Brizola, S/N, bairro Jangurussu - Fortaleza, CE - CEP.: 60.866-681",
    "24": "📍Rua 69, S/N, bairro Prefeito José Walter - Fortaleza, CE - CEP.: 60.810-670",
    "25": "📍Avenida Oscar Araripe, nº 1030, bairro Bom Jardim - Fortaleza, CE - CEP.: 60.543-452",
    "26": "📍Rua Coronel Matos Dourados, nº 1499, bairro Planalto Pici - Fortaleza, CE - CEP.: 60.360-561",
    "27": "📍Rua H, nº 61, bairro Parque Dois Irmãos - Fortaleza, CE - CEP.: 60810-670",
    "28": "📍Avenida Oscar Araripe, nº 1030, bairro Bom Jardim - Fortaleza, CE - CEP.: 60543-452",
    "29": "📍Rua Dom Lino, nº 546, bairro Parquelândia - Fortaleza, CE - CEP.: 60.450-285",
    "30": "📍Avenida Santos Dumont, nº 2500, bairro Aldeota - Fortaleza, CE - CEP.: 60.150-161",
    "31": "📍Avenida Augusto dos Anjos, nº 2466, bairro Bonsucesso (prédio da antiga Regional) - Fortaleza, CE - CEP.: 60542-164",
    "32": "📍Rua Francisco Glicério, nº 290, bairro Maraponga - Fortaleza, CE - CEP.: 60040-531",
    "33": "📍Rua Rio Grande do Sul, nº 860, bairro Panamericano - Fortaleza, CE - CEP.: 60440-131",
    "34": "📍Avenida Alanis Maria Laurindo de Oliveira, nº 461, bairro Conjunto Ceará - Fortaleza, CE - CEP.: 60533-603",
    "35": "📍Avenida Castelo de Castro, nº 2842, bairro Conjunto Palmeiras - Fortaleza, CE - CEP.: 60870-066",
    "36": "📍Avenida Presidente Castelo Branco, nº 6417, bairro Barra do Ceará - Fortaleza, CE - CEP.: 60334-105",
    "37": "📍Avenida General Osório de Paiva, nº 6061, bairro Canindezinho - Fortaleza, CE - CEP.: 60731-335",
    "38": "📍Rua Inácio Parente, nº 100, bairro Serrinha - Fortaleza, CE - CEP.: 60741-280",
    "39": "📍Rua Dr. Pergentino Maia, nº 379, bairro Messejana - Fortaleza, CE - CEP.: 60840-045",
}
# Turmas finalizadas removidas em 06/10/2026:
# 26/INAT-004, 26/MARK-006, 26/RECP-001, 26/SOMD-008, 26/MNCR-010
# Turmas removidas em 08/10/2026 (local REGIONAL V - CRECHE NOVO MUNDO PIONEIRO):
# 26/INAT-007 - Inteligência Artificial, 26/MARK-008 - Marketing Digital
# Turma removida em 15/10/2026:
# 26/TRNC-005 - Trancista (REGIONAL V - ESPAÇO DO PROJETO VIDA EM MOVIMENTO)
# Turmas encerradas removidas em 26/10/2026:
# 26/SOMD-009 - Social Media (REGIONAL II - INSTITUTO ESCOLHI AMAR) — enc. 21/10/2026
# 26/MARK-007 - Marketing Digital (REGIONAL I - INSTITUTO VIVA AGAPÊ) — enc. 08/10/2026
# 26/SOMD-010 - Social Media (REGIONAL IV - INSTITUTO VIVA IDOSO) — enc. 15/10/2026
# 26/INAT-005 - Inteligência Artificial (REGIONAL V - PROJETO AMIGOS DE DEUS - Colégio Pequeno Aprendiz) — enc. 08/10/2026
# 26/INAT-006 - Inteligência Artificial (REGIONAL V - PROJETO AMIGOS DE DEUS - Colégio Pequeno Aprendiz) — enc. 08/10/2026
# 26/ADMN-005 - Auxiliar Administrativo (REGIONAL V - CRECHE NOVO MUNDO PIONEIRO) — enc. 14/10/2026
# 26/COST-001 - Costura (REGIONAL IX - CUCA JANGURUSSU) — enc. 23/10/2026
# 26/COST-002 - Costura (REGIONAL VIII - CUCA JOSÉ WALTER) — enc. 23/10/2026
# 26/COST-003 - Costura (REGIONAL V - SECRETARIA EXECUTIVA) — enc. 23/10/2026
# 26/COST-004 - Costura (REGIONAL XI - CUCA PICI) — enc. 23/10/2026
# Turmas removidas em 28/10/2026:
# 26/ADMN-004 - Auxiliar Administrativo (REGIONAL II - INSTITUTO LOURDES VIANA) — enc. 05/11/2026
# 26/MARK-010 - Marketing Digital (IEQ JARDIM GUANABARA) — enc. 04/11/2026
# Turma removida em 30/10/2026:
# 26/MNCR-011 - Manicure (CRE BOM JARDIM) — enc. 11/11/2026
# Turma removida em 03/11/2026:
# 26/DSUN-007 - Designer de Unhas (REGIONAL VIII - CAOF) — enc. 13/11/2026
# Turmas removidas em 05/11/2026:
# 26/ADMN-007 - Auxiliar Administrativo (SINE MUNICIPAL PARQUELÂNDIA) — início 17/11/2026, encerramento 01/12/2026
# 26/MNCR-012 - Manicure (SINE MUNICIPAL PARQUELÂNDIA) — início 16/11/2026, encerramento 20/11/2026
# 26/ASLO-01 - Assistente de Logística (SINE MUNICIPAL ALDEOTA) — início 17/11/2026, encerramento 01/12/2026
# 26/RECP-003 - Recepcionista (SINE MUNICIPAL SIQUEIRA) — início 17/11/2026, encerramento 01/12/2026
# 26/MLRE-01 - Monitor Lazer e Recreação (SINE MUNICIPAL SIQUEIRA) — início 17/11/2026, encerramento 01/12/2026
# Turma removida em 05/11/2026:
# 26/TRNC-006 - Trancista (CRE BOM JARDIM) — início 16/11/2026, encerramento 20/11/2026
# Turma removida em 06/11/2026:
# 26/DSBR-013 - Designer de Sobrancelhas (REGIONAL VIII - CAOF) — início 09/11/2026, encerramento 13/11/2026
# Turmas atualizadas em 13/11/2026:
# 26/COST-005 - Costura (REGIONAL VIII - CUCA JOSÉ WALTER) — início 17/11/2026, encerramento 04/12/2026
# 26/COST-006 - Costura (REGIONAL V - SECRETARIA EXECUTIVA) — início 17/11/2026, encerramento 04/12/2026
# 26/COST-007 - Costura (REGIONAL XI - CUCA PICI) — início 17/11/2026, encerramento 04/12/2026
# Turmas removidas em 13/11/2026 (encerradas):
# 26/COST-005 - Costura (REGIONAL VIII - CUCA JOSÉ WALTER)
# 26/COST-006 - Costura (REGIONAL V - SECRETARIA EXECUTIVA)
# 26/COST-007 - Costura (REGIONAL XI - CUCA PICI)
# Turmas removidas em 19/11/2026:
# 26/ADMN-007 - Auxiliar Administrativo (SINE MUNICIPAL PARQUELÂNDIA) — início 17/11/2026, encerramento 01/12/2026
# 26/MNCR-012 - Manicure (SINE MUNICIPAL PARQUELÂNDIA) — início 16/11/2026, encerramento 20/11/2026
# 26/ASLO-001 - Assistente de Logística (SINE MUNICIPAL ALDEOTA) — início 17/11/2026, encerramento 01/12/2026
# 26/MLRE-001 - Monitor Lazer e Recreação (SINE MUNICIPAL SIQUEIRA) — início 17/11/2026, encerramento 01/12/2026
# Turma atualizada em 19/11/2026:
# 26/DSBR-014 - Designer de Sobrancelhas (SINE MUNICIPAL PARQUELÂNDIA) — dias de aula: "Terça e Quinta" -> "Segunda a Sexta"
# Turmas removidas em 23/11/2026:
# 26/COST-008 - Costura (ATELIÊ CONJUNTO CEARÁ) — horário 08h até 12h
# 26/COST-009 - Costura (ATELIÊ CONJUNTO PALMEIRAS) — horário 08h até 12h
# 26/COST-010 - Costura (ATELIÊ BARRA DO CEARÁ) — horário 08h até 12h
# 26/COST-012 - Costura (ATELIÊ BARRA DO CEARÁ) — horário 13h até 17h
# 26/EXTC-007 - Extensão de Cílios (SINE MUNICIPAL ALDEOTA)
# 26/INAT-009 - Inteligência Artificial (SINE MUNICIPAL MARAPONGA)
# Turmas adicionadas em 16/11/2026:
# Turmas adicionadas em 23/11/2026:
# 26/MNCR-013 - Manicure (CENTRO DE REFERÊNCIA DO EMPREENDEDOR (CRE) DE MESSEJANA)
TURMA_OPTIONS = [
    # OPÇÃO 1 — PEDICURE
    {"id": "1", "curso_id": "15", "local_id": "28", "turma_codigo": "26/PEDI-004",
     "dias_aula": "Segunda a Sexta", "horario": "13h até 17h", "vagas": 20,
     "data_inicio": "30/11/2026", "encerramento": "04/12/2026", "endereco_id": "28"},
    # OPÇÃO 2 — DESIGNER DE SOBRANCELHAS (dias alterados em 19/11/2026)
    {"id": "2", "curso_id": "11", "local_id": "29", "turma_codigo": "26/DSBR-014",
     "dias_aula": "Segunda a Sexta", "horario": "13h30 até 16h30", "vagas": 30,
     "data_inicio": "30/11/2026", "encerramento": "04/12/2026", "endereco_id": "29"},
    # OPÇÃO 5 — MARKETING DIGITAL
    {"id": "5", "curso_id": "2", "local_id": "33", "turma_codigo": "26/MARK-011",
     "dias_aula": "Terça e Quinta", "horario": "13h até 17h", "vagas": 30,
     "data_inicio": "01/12/2026", "encerramento": "15/12/2026", "endereco_id": "33"},
    # OPÇÃO 6 — ASSISTENTE DE LOGÍSTICA
    {"id": "6", "curso_id": "13", "local_id": "33", "turma_codigo": "26/ASLO-002",
     "dias_aula": "Terça e Quinta", "horario": "09h até 12h", "vagas": 30,
     "data_inicio": "01/12/2026", "encerramento": "15/12/2026", "endereco_id": "33"},
    # OPÇÃO 7 — SOCIAL MEDIA
    {"id": "7", "curso_id": "8", "local_id": "32", "turma_codigo": "26/SOMD-011",
     "dias_aula": "Terça e Quinta", "horario": "09h até 12h", "vagas": 30,
     "data_inicio": "01/12/2026", "encerramento": "15/12/2026", "endereco_id": "32"},
    # OPÇÃO 8 — DESIGNER DE UNHAS
    {"id": "8", "curso_id": "4", "local_id": "28", "turma_codigo": "26/DSUN-008",
     "dias_aula": "Segunda a Sexta", "horario": "13h até 17h", "vagas": 30,
     "data_inicio": "07/12/2026", "encerramento": "11/12/2026", "endereco_id": "28"},
    # OPÇÃO 9 — DESIGNER DE SOBRANCELHAS
    {"id": "9", "curso_id": "11", "local_id": "28", "turma_codigo": "26/DSBR-015",
     "dias_aula": "Segunda a Sexta", "horario": "13h até 17h", "vagas": 30,
     "data_inicio": "14/12/2026", "encerramento": "18/12/2026", "endereco_id": "28"},
    # ── Turmas adicionadas em 19/11/2026 ──
    # OPÇÃO 17 — COSTURA
    {"id": "17", "curso_id": "12", "local_id": "37", "turma_codigo": "26/COST-011",
     "dias_aula": "Terça a Sexta", "horario": "08h até 12h", "vagas": 30,
     "data_inicio": "01/12/2026", "encerramento": "18/12/2026", "endereco_id": "37"},
    # OPÇÃO 19 — COSTURA
    {"id": "19", "curso_id": "12", "local_id": "35", "turma_codigo": "26/COST-013",
     "dias_aula": "Segunda a Sexta", "horario": "13h até 17h", "vagas": 30,
     "data_inicio": "03/12/2026", "encerramento": "18/12/2026", "endereco_id": "35"},
    # OPÇÃO 20 — COSTURA
    {"id": "20", "curso_id": "12", "local_id": "38", "turma_codigo": "26/COST-014",
     "dias_aula": "Segunda a Sexta", "horario": "08h até 12h", "vagas": 30,
     "data_inicio": "03/12/2026", "encerramento": "18/12/2026", "endereco_id": "38"},
    # OPÇÃO 21 — COSTURA
    {"id": "21", "curso_id": "12", "local_id": "34", "turma_codigo": "26/COST-015",
     "dias_aula": "Segunda a Sexta", "horario": "13h até 17h", "vagas": 30,
     "data_inicio": "03/12/2026", "encerramento": "18/12/2026", "endereco_id": "34"},
    # OPÇÃO 22 — COSTURA
    {"id": "22", "curso_id": "12", "local_id": "38", "turma_codigo": "26/COST-016",
     "dias_aula": "Segunda a Sexta", "horario": "13h até 17h", "vagas": 30,
     "data_inicio": "03/12/2026", "encerramento": "18/12/2026", "endereco_id": "38"},
    # ── Turmas adicionadas em 23/11/2026 ──
    # OPÇÃO 23 — MANICURE
    {"id": "23", "curso_id": "6", "local_id": "39", "turma_codigo": "26/MNCR-013",
     "dias_aula": "Segunda a Sexta", "horario": "08h até 12h", "vagas": 30,
     "data_inicio": "07/12/2026", "encerramento": "11/12/2026", "endereco_id": "39"},
]
COMO_CONHECEU_OPCOES = ["Facebook", "Instagram", "Whatsapp", "Outros"]
def build_course_options():
    local_by_id  = {opt["id"]: opt for opt in LOCAL_OPTIONS}
    course_by_id = {opt["id"]: opt for opt in COURSE_CATALOG}
    options = []
    for t in TURMA_OPTIONS:
        local  = local_by_id[t["local_id"]]
        course = course_by_id[t["curso_id"]]
        options.append({
            "id":             t["id"],
            "curso_id":       t["curso_id"],
            "local_id":       t["local_id"],
            "local":          local["nome"],
            "curso":          course["nome"],
            "turma":          f"{t['turma_codigo']} - {course['nome']}",
            "dias_aula":      t["dias_aula"],
            "horario":        t["horario"],
            "data_inicio":    t["data_inicio"],
            "encerramento":   t["encerramento"],
            "endereco_curso": ADDRESS_OPTIONS[t["endereco_id"]],
        })
    return options
COURSE_OPTIONS       = build_course_options()
COURSE_OPTIONS_BY_ID = {opt["id"]: opt for opt in COURSE_OPTIONS}
COURSE_CATALOG_BY_ID = {opt["id"]: opt for opt in COURSE_CATALOG}
LOCAL_OPTIONS_BY_ID  = {opt["id"]: opt for opt in LOCAL_OPTIONS}
_LOCAIS_COM_TURMA    = {t["local_id"] for t in TURMA_OPTIONS}
ACTIVE_LOCAL_OPTIONS = [opt for opt in LOCAL_OPTIONS if opt["id"] in _LOCAIS_COM_TURMA]
_CURSOS_ATIVOS_IDS   = {t["curso_id"] for t in TURMA_OPTIONS}
ACTIVE_COURSE_CATALOG = [c for c in COURSE_CATALOG if c["id"] in _CURSOS_ATIVOS_IDS]
COURSE_INFO          = COURSE_OPTIONS[0] if COURSE_OPTIONS else None
def build_whatsapp_share_url(home_url):
    message = ("Acabei de me inscrever em uma oportunidade de qualificacao profissional. Confira aqui: " + home_url)
    return f"https://wa.me/?text={quote(message)}"
def get_course_option(option_id):
    return COURSE_OPTIONS_BY_ID.get(str(option_id or ""))
def fill_form_data_from_option(form_data, option):
    form_data["local_id"]       = option["local_id"]
    form_data["curso_id"]       = option["curso_id"]
    form_data["opcao_id"]       = option["id"]
    form_data["local"]          = option["local"]
    form_data["curso"]          = option["curso"]
    form_data["turma"]          = option["turma"]
    form_data["dias_aula"]      = option["dias_aula"]
    form_data["horario"]        = option["horario"]
    form_data["data_inicio"]    = option["data_inicio"]
    form_data["encerramento"]   = option["encerramento"]
    form_data["endereco_curso"] = option["endereco_curso"]
def fill_form_data_from_selection(form_data):
    opcao_id = form_data.get("opcao_id")
    local_id = form_data.get("local_id")
    curso_id = form_data.get("curso_id")
    if opcao_id:
        matched = COURSE_OPTIONS_BY_ID.get(str(opcao_id))
        if matched:
            fill_form_data_from_option(form_data, matched)
            return
    if local_id and curso_id:
        matched = next((o for o in COURSE_OPTIONS if o["local_id"]==str(local_id) and o["curso_id"]==str(curso_id)), None)
        if matched:
            fill_form_data_from_option(form_data, matched)
            return
    for key in ("local","curso","turma","dias_aula","horario","data_inicio","encerramento","endereco_curso","opcao_id"):
        form_data.setdefault(key, "")

BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="inscricao")
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fortaleza-chave-secreta-padrao")
SUPABASE_URL     = "https://egpyhfzatabyftwajoad.supabase.co/functions/v1/fgm-fortaleza-register"
SUPABASE_API_KEY = os.environ.get("SUPABASE_API_KEY") or os.environ.get("FGM_FORTALEZA_API_KEY", "")

def _com_tentativas(nome, funcao, tentativas=3, espera=2):
    for n in range(1, tentativas + 1):
        try:
            return funcao()
        except Exception as exc:
            print(f"[{nome}] tentativa {n}/{tentativas} falhou: {exc}", flush=True)
            if n == tentativas:
                raise
            time.sleep(espera * n)

def send_registration_to_supabase(form_data):
    headers = {"Content-Type": "application/json", "apikey": SUPABASE_API_KEY}
    payload = {
        "nome":          form_data.get("nome", ""),
        "cpf":           form_data.get("cpf", ""),
        "email":         form_data.get("email", ""),
        "telefone":      form_data.get("telefone", ""),
        "bairro":        form_data.get("bairro", ""),
        "curso":         form_data.get("curso", ""),
        "local":         form_data.get("local", ""),
        "turma":         form_data.get("turma", ""),
        "dias_aula":     form_data.get("dias_aula", ""),
        "horario":       form_data.get("horario", ""),
        "data_inicio":   form_data.get("data_inicio", ""),
        "encerramento":  form_data.get("encerramento", ""),
        "como_conheceu": form_data.get("como_conheceu", ""),
        "protocolo":     form_data.get("protocolo", ""),
    }
    return requests.post(SUPABASE_URL, json=payload, headers=headers, timeout=(5, 15))

def processar_inscricao_em_segundo_plano(dados, form_data):
    protocolo = dados[0]
    try:
        _com_tentativas("Planilha", lambda: append_to_sheet(dados))
        print(f"[Planilha] inscricao {protocolo} salva", flush=True)
    except Exception:
        traceback.print_exc()
        print("INSCRICAO_NAO_SALVA_PLANILHA " + json.dumps(dados, ensure_ascii=False), flush=True)
    try:
        resp = _com_tentativas("Supabase", lambda: send_registration_to_supabase(form_data))
        print(f"[Supabase] inscricao {protocolo} enviada: {resp.status_code}", flush=True)
    except Exception:
        traceback.print_exc()
        print(f"INSCRICAO_NAO_ENVIADA_SUPABASE {protocolo}", flush=True)

TEMPLATE_WIZARD = r"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Cursos Gratuitos em Fortaleza | Qualificação Profissional</title>
    <meta name="description" content="Cursos gratuitos com certificado em Fortaleza. Inscrição em poucos minutos. Vagas limitadas.">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --background: 0 0% 97%;
            --foreground: 215 25% 15%;
            --card: 0 0% 100%;
            --primary: 0 100% 27%;
            --primary-light: 0 80% 40%;
            --primary-foreground: 0 0% 100%;
            --secondary: 0 10% 95%;
            --accent: 0 60% 95%;
            --muted: 0 10% 95%;
            --muted-foreground: 215 16% 47%;
            --destructive: 0 84% 60%;
            --success: 142 71% 45%;
            --warning: 38 92% 50%;
            --border: 0 10% 88%;
            --input: 0 10% 88%;
            --ring: 0 100% 27%;
            --radius: 1rem;
            --gradient-primary: linear-gradient(135deg, hsl(0 100% 27%) 0%, hsl(0 80% 40%) 100%);
            --gradient-hero: linear-gradient(135deg, hsl(0 100% 27%) 0%, hsl(0 70% 35%) 50%, hsl(0 100% 27%) 100%);
            --shadow-soft: 0 4px 6px rgba(139,0,0,.05);
            --shadow-md: 0 8px 16px rgba(139,0,0,.10);
            --shadow-hover: 0 8px 24px rgba(139,0,0,.12);
            --field-height: 38px;
        }
        * { box-sizing: border-box; }
        html, body { min-height: 100%; margin: 0; padding: 0; width: 100%; max-width: 100%; overflow-x: hidden; }
        body { min-height: 100vh; background: hsl(var(--background)); color: hsl(var(--foreground)); font-family: 'Inter', Arial, sans-serif; }
        .main-header { position: fixed; top: 0; left: 0; right: 0; z-index: 50; border-bottom: 1px solid hsl(var(--border)); background: hsl(var(--card) / 0.95); backdrop-filter: blur(8px); box-shadow: var(--shadow-soft); }
        .header-inner { display: flex; align-items: center; justify-content: center; gap: 16px; padding: 10px 16px; }
        .header-inner img { height: 44px; object-fit: contain; }
        .header-title { text-align: left; }
        .header-title .brand { margin: 0; font-size: 0.85rem; font-weight: 800; color: hsl(var(--primary)); line-height: 1.2; }
        .header-title .sub { margin: 0; font-size: 0.7rem; color: hsl(var(--muted-foreground)); }
        .wizard-page { width: min(900px, calc(100% - 16px)); margin: 0 auto; padding: 76px 0 18px; text-align: center; }
        .wizard-progress { margin: 18px auto 22px; padding: 18px 18px 20px; border-radius: calc(var(--radius) * 1.75); background: hsl(var(--card)); box-shadow: var(--shadow-md); }
        .progress-top-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
        .progress-step-label { font-size: 0.9rem; font-weight: 700; color: hsl(var(--foreground)); }
        .progress-percent { font-size: 0.9rem; font-weight: 700; color: hsl(var(--primary)); }
        .wizard-track { position: relative; width: 100%; height: 14px; background: hsl(var(--secondary)); border-radius: 999px; overflow: visible; }
        .wizard-fill { height: 100%; background: var(--gradient-primary); border-radius: 999px; transition: width 0.3s ease; }
        .wizard-labels { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-top: 14px; }
        .wizard-label { padding: 12px 10px; border: 1px solid hsl(var(--border)); border-radius: var(--radius); background: hsl(var(--card)); color: hsl(var(--primary)); font-size: 0.92rem; font-weight: 700; text-align: center; }
        .wizard-label.ativo { border-color: hsl(var(--primary)); background: hsl(var(--accent)); color: hsl(var(--primary)); }
        .wizard-shell { background: hsl(var(--card) / 0.96); border: 1px solid hsl(var(--border)); border-radius: calc(var(--radius) * 2); box-shadow: var(--shadow-hover); overflow: hidden; }
        .wizard-panel { padding: 18px 8px; }
        @keyframes surgir { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
        .wizard-panel { animation: surgir 0.28s ease; }
        .hero-grid { display: grid; grid-template-columns: minmax(0,1fr); gap: 14px; align-items: center; justify-items: center; }
        .hero-card { padding: 0; border-radius: 0; background: transparent; border: none; width: 100%; text-align: center; color: hsl(var(--foreground)); box-shadow: none; }
        .hero-pill { display: inline-flex; align-items: center; gap: 8px; padding: 7px 16px; border-radius: 999px; background: hsl(var(--primary) / 0.1); color: hsl(var(--primary)); font-size: 0.75rem; font-weight: 800; letter-spacing: 0.04em; text-transform: uppercase; animation: pulse-soft 2.4s ease-in-out infinite; }
        @keyframes pulse-soft { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }
        .hero-title-accent { color: hsl(var(--primary)); }
        .trust-badges { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 8px; margin-top: 14px; }
        .trust-badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border-radius: 999px; background: hsl(var(--secondary)); color: hsl(var(--foreground)); font-size: 0.75rem; font-weight: 700; }
        .hero-title { margin: 16px 0 10px; color: hsl(var(--foreground)); font-weight: 800; letter-spacing: -0.02em; font-size: clamp(1.5rem,3.4vw,2.4rem); line-height: 1.2; }
        .panel-title { margin: 18px 0 10px; color: hsl(var(--primary)); font-weight: 900; letter-spacing: -0.03em; font-size: clamp(1.7rem,3vw,2.4rem); }
        .hero-subtitle { margin: 0; color: hsl(var(--muted-foreground)); font-size: 0.95rem; line-height: 1.55; }
        .panel-subtitle { margin: 0; color: hsl(var(--muted-foreground)); font-size: 1.05rem; line-height: 1.55; }
        .hero-highlights { display: grid; gap: 10px; margin-top: 16px; }
        .hero-highlight { padding: 14px 14px; color: hsl(var(--foreground)); font-size: 0.95rem; font-weight: 700; border-radius: var(--radius); border: 2px solid transparent; background: hsl(var(--card)); box-shadow: var(--shadow-soft); }
        .hero-highlight strong { display: block; color: hsl(var(--primary)); font-size: 1.15rem; margin-bottom: 4px; }
        .course-accordion-wrap { margin-top: 22px; text-align: left; }
        .accordion-heading { margin: 0 0 12px; font-size: 1.05rem; font-weight: 800; color: hsl(var(--foreground)); text-align: center; }
        .course-accordion { display: grid; gap: 10px; }
        .accordion-item { border-radius: var(--radius); overflow: hidden; }
        .accordion-header { display: flex; align-items: center; gap: 12px; width: 100%; text-align: left; padding: 14px 16px; border: 2px solid transparent; border-radius: var(--radius); background: hsl(var(--card)); box-shadow: var(--shadow-soft); cursor: pointer; transition: all 0.2s ease; }
        .accordion-header:hover { border-color: hsl(var(--primary) / 0.3); }
        .accordion-item.aberto .accordion-header { border-color: hsl(var(--primary)); box-shadow: var(--shadow-md); }
        .accordion-icon { font-size: 1.5rem; flex-shrink: 0; }
        .accordion-header-text { flex: 1; min-width: 0; }
        .accordion-curso-nome { display: block; font-size: 1rem; font-weight: 800; color: hsl(var(--foreground)); }
        .accordion-curso-count { display: block; font-size: 0.78rem; color: hsl(var(--muted-foreground)); }
        .accordion-chevron { flex-shrink: 0; font-size: 1.3rem; font-weight: 900; color: hsl(var(--muted-foreground)); transition: transform 0.2s ease; }
        .accordion-item.aberto .accordion-chevron { transform: rotate(90deg); color: hsl(var(--primary)); }
        .accordion-panel { display: none; padding: 8px 4px 2px 6px; }
        .accordion-item.aberto .accordion-panel { display: grid; gap: 8px; margin-top: 6px; }
        .turma-card { background: hsl(var(--card)); border-radius: calc(var(--radius) * 0.9); box-shadow: var(--shadow-soft); padding: 14px; }
        .turma-info { display: grid; gap: 6px; font-size: 0.8rem; color: hsl(var(--muted-foreground)); margin-bottom: 10px; }
        .turma-local { display: flex; align-items: flex-start; gap: 6px; }
        .turma-local strong { color: hsl(var(--foreground)); font-weight: 700; }
        .turma-endereco { font-size: 0.74rem; }
        .turma-linha { display: flex; align-items: center; gap: 6px; }
        .turma-select-btn { width: 100%; height: 44px; font-size: 0.9rem; }
        .step-card { border-radius: calc(var(--radius) * 1.25); border: 2px solid transparent; background: hsl(var(--card)); box-shadow: var(--shadow-soft); padding: 18px 16px; width: 100%; margin: 0 auto; text-align: center; }
        .step-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 10px 12px; margin-top: 10px; align-items: start; }
        .step-grid.step-grid--stacked { grid-template-columns: minmax(0,1fr); max-width: 540px; margin-left: auto; margin-right: auto; }
        .form-group { display: flex; flex-direction: column; gap: 4px; width: 100%; align-self: start; align-items: center; text-align: center; }
        .form-group.full { grid-column: 1/-1; }
        .form-group label, .review-title { color: hsl(var(--primary)); font-size: 1rem; font-weight: 800; }
        .form-group input, .form-group select, .form-group textarea { display: block; width: 100% !important; max-width: 100% !important; min-width: 0 !important; margin: 0 !important; box-sizing: border-box; min-height: 38px; height: 38px; padding: 7px 10px; border: 1.5px solid hsl(var(--input)); border-radius: 0.65rem; background: hsl(var(--secondary)); color: hsl(var(--foreground)); font: inherit; line-height: 1.2; text-align: left; outline: none; transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease; }
        .form-group select { appearance: none; -webkit-appearance: none; -moz-appearance: none; background-image: url('data:image/svg+xml;utf8,<svg fill="%238b0000" height="20" viewBox="0 0 24 24" width="20" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5z"/></svg>'); background-repeat: no-repeat; background-position: right 14px center; background-size: 20px 20px; padding-right: 44px; }
        .form-group textarea { min-height: 60px; height: auto; resize: vertical; }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color: hsl(var(--ring)); background: hsl(var(--card)); box-shadow: 0 0 0 4px hsl(var(--ring) / 0.14); }
        .form-group { align-items: stretch; text-align: left; }
        .form-group label { width: 100%; text-align: left; }
        .balao-erro[hidden] { display: none; }
        .erro-campo { border-color: hsl(var(--destructive)) !important; box-shadow: 0 0 0 4px hsl(var(--destructive) / 0.14) !important; }
        .error-banner { background: hsl(var(--destructive) / 0.08); border: 1.5px solid hsl(var(--destructive) / 0.3); color: hsl(var(--destructive)); padding: 12px 16px; border-radius: var(--radius); margin-bottom: 16px; font-size: 0.9rem; font-weight: 600; text-align: left; }
        .info-note-box { margin-top: 16px; padding: 14px; border-radius: var(--radius); background: hsl(var(--secondary) / 0.6); text-align: left; }
        .info-note-box strong { display: block; margin-bottom: 8px; color: hsl(var(--foreground)); font-size: 0.92rem; }
        .info-note-box ul { margin: 0; padding-left: 18px; color: hsl(var(--muted-foreground)); font-size: 0.85rem; line-height: 1.6; }
        .review-layout { display: grid; grid-template-columns: 1fr; gap: 8px; margin-top: 10px; max-width: 540px; margin-left: auto; margin-right: auto; }
        .review-box { border-radius: calc(var(--radius) * 1.25); border: 2px solid transparent; background: hsl(var(--card)); box-shadow: var(--shadow-soft); padding: 10px; text-align: center; }
        .review-box.full { grid-column: 1/-1; }
        .review-list { display: grid; gap: 6px; margin-top: 8px; text-align: left; }
        .review-item { display: grid; grid-template-columns: auto 1fr; align-items: center; column-gap: 8px; padding: 7px 9px; border-radius: 0.65rem; background: hsl(var(--accent)); text-align: left; }
        .review-item strong { color: hsl(var(--primary)); font-size: 0.88rem; white-space: nowrap; }
        .review-item strong::after { content: ':'; }
        .review-item span { color: hsl(var(--foreground)); font-size: 0.94rem; word-break: break-word; text-align: left; }
        .review-check { display: flex; gap: 12px; align-items: flex-start; padding: 10px 12px; border-radius: var(--radius); background: hsl(var(--accent)); color: hsl(var(--foreground)); line-height: 1.45; text-align: left; }
        .review-check input { margin-top: 3px; width: 20px; min-width: 20px; height: 20px; flex: 0 0 20px; accent-color: hsl(var(--primary)); }
        .review-check span { flex: 1 1 auto; min-width: 0; }
        .elegibilidade-nota { margin-bottom: 10px; color: hsl(var(--muted-foreground)); font-size: 0.98rem; text-align: left; }
        .elegibilidade-nota strong { color: hsl(var(--primary)); }
        .review-declaracao { margin-top: 10px; text-align: left; color: hsl(var(--foreground)); }
        .review-declaracao strong { color: hsl(var(--primary)); }
        .review-box .form-group { align-items: stretch; text-align: left; }
        .review-box .form-group label { width: 100%; text-align: left; }
        .panel-actions { display: flex; flex-direction: row; align-items: center; gap: 16px; justify-content: space-between; margin-top: 28px; padding-top: 20px; border-top: 1px solid hsl(var(--border)); max-width: 420px; margin-left: auto; margin-right: auto; }
        .panel-actions > * { flex: 1; }
        .cta-button, .submit-button, .secondary-button { border: none; border-radius: 999px; font: inherit; font-weight: 700; cursor: pointer; transition: transform 0.16s ease, box-shadow 0.16s ease, background 0.16s ease, filter 0.16s ease; }
        .cta-button, .submit-button { background: var(--gradient-primary); color: hsl(var(--primary-foreground)); box-shadow: var(--shadow-soft); min-height: 48px; padding: 12px 22px; letter-spacing: 0.01em; width: 100%; font-size: 1rem; }
        .cta-button:hover, .submit-button:hover { filter: brightness(1.1); transform: scale(1.03); }
        .cta-button:active, .submit-button:active { transform: scale(0.97); }
        .secondary-button { background: hsl(var(--card)); color: hsl(var(--foreground)); border: 1.5px solid hsl(var(--border)); min-height: 48px; padding: 12px 22px; letter-spacing: 0.01em; width: 100%; font-size: 1rem; }
        .secondary-button:hover { transform: scale(1.03); }
        .opcao-radio-group { display: grid; gap: 10px; margin-top: 10px; }
        .opcao-card { border: 2px solid hsl(var(--border)); border-radius: var(--radius); padding: 14px 16px; cursor: pointer; transition: all 0.2s; display: flex; align-items: flex-start; gap: 12px; background: hsl(var(--card)); box-shadow: var(--shadow-soft); }
        .opcao-card:hover { border-color: hsl(var(--primary) / 0.4); }
        .opcao-card.selected { border-color: hsl(var(--primary)); background: hsl(var(--accent)); }
        .opcao-card input[type=radio] { margin-top: 4px; accent-color: hsl(var(--primary)); flex-shrink: 0; }
        .opcao-card label { cursor: pointer; flex: 1; text-align: left; }
        .opcao-titulo { font-weight: 800; font-size: 0.95rem; color: hsl(var(--primary)); }
        .opcao-detalhe { font-size: 0.82rem; color: hsl(var(--muted-foreground)); margin-top: 4px; }
        @media (max-width: 860px) { .hero-grid, .review-layout { grid-template-columns: 1fr; } .step-grid { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; } .step-grid.step-grid--stacked { grid-template-columns: minmax(0,1fr); max-width: 540px; } }
        @media (max-width: 640px) {
            :root { --field-height: 32px; }
            html,body { width:100%!important; max-width:100%!important; overflow-x:hidden!important; } body * { min-width: 0; } body { overflow-x: hidden; }
            .main-header { padding: 0; } .header-inner { padding: 8px 12px; gap: 10px; } .header-inner img { height: 36px; }
            .wizard-page { width:calc(100% - 8px)!important; max-width:100%!important; padding:68px 0 10px !important; } .wizard-progress, .wizard-panel { width:100%!important; max-width:100%!important; padding:8px; } .wizard-labels { grid-template-columns: 1fr; gap: 6px; }
            .hero-card, .step-card, .review-box { width:100%!important; max-width:100%!important; padding:8px; }
            .panel-actions > * { width: 100%; }
            .step-grid { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 6px; } .step-grid.step-grid--stacked { grid-template-columns: minmax(0,1fr); max-width: 100%; } .review-layout { grid-template-columns: 1fr; max-width: 100%; gap: 10px; }
            .review-item, .form-group, .form-group input, .form-group select, .form-group textarea, .wizard-shell, .panel-actions, .review-check, .balao-erro { width:100%!important; max-width:100%!important; }
            .form-group label, .review-title, .review-item span, .review-check { word-break: break-word; } img, svg { max-width:100%!important; height:auto!important; }
            .form-group input, .form-group select, .form-group textarea { min-height:32px; height:32px; font-size:0.98em; } .form-group textarea { min-height:60px; height:auto; }
            .hero-title, .panel-title { font-size: 1.3rem; } .hero-subtitle, .panel-subtitle { font-size: 0.92rem; } .wizard-shell { border-radius: 1.1rem; } .form-group.full { grid-column: auto; }
        }
    </style>
</head>
<body>
    <header class="main-header">
        <div class="header-inner">
            <img src="/static/logo-prefeitura.png" alt="Prefeitura de Fortaleza" loading="eager">
            <div class="header-title">
                <p class="brand">QUALIFICAÇÃO PROFISSIONAL</p>
                <p class="sub">Prefeitura de Fortaleza &bull; SMTE</p>
            </div>
        </div>
    </header>
    <main>
    <div class="wizard-page">
        <div class="wizard-progress">
            <div class="progress-top-row">
                <span class="progress-step-label">
                    {% if etapa == "inicio" %}Passo 1 de 4
                    {% elif etapa == "dados" %}Passo 2 de 4
                    {% elif etapa == "escolher" %}Passo 3 de 4
                    {% elif etapa == "revisao" %}Passo 4 de 4
                    {% else %}Passo 1 de 4{% endif %}
                </span>
                <span class="progress-percent">{{ progresso }}%</span>
            </div>
            <div class="wizard-track">
                <div class="wizard-fill" style="width: {{ progresso }}%;"></div>
            </div>
            <div class="wizard-labels">
                <div class="wizard-label {% if etapa == 'inicio' %}ativo{% endif %}">1. In&#237;cio</div>
                <div class="wizard-label {% if etapa == 'dados' %}ativo{% endif %}">2. Dados pessoais</div>
                <div class="wizard-label {% if etapa == 'escolher' %}ativo{% endif %}">3. Escolher</div>
                <div class="wizard-label {% if etapa == 'revisao' %}ativo{% endif %}">4. Revis&#227;o</div>
            </div>
        </div>
        <div class="wizard-shell">

        {% if etapa == "inicio" %}
        <div class="wizard-panel">
            <div class="hero-grid"><div class="hero-card">
                <span class="hero-pill">&#x1F525; INSCRI&#199;&#213;ES ABERTAS &mdash; INSCREVA-SE J&#193;</span>
                <h1 class="hero-title">CURSOS <span class="hero-title-accent">GRATUITOS</span> EM FORTALEZA</h1>
                <p class="hero-subtitle">Programa de Qualifica&#231;&#227;o Profissional &bull; Prefeitura de Fortaleza</p>
                <div class="trust-badges">
                    <span class="trust-badge">&#10024; 100% Gratuito</span>
                    <span class="trust-badge">&#127942; Certificado</span>
                    <span class="trust-badge">&#127891; Qualifica&#231;&#227;o Profissional</span>
                </div>
                <div class="hero-highlights">
                    <div class="hero-highlight">
                        <strong>BENEF&#205;CIOS</strong>
                        Curso 100% gratuito com certificado de conclus&#227;o e material did&#225;tico incluso.
                    </div>
                    <div class="hero-highlight">
                        <strong>QUALIFICA&#199;&#195;O PROFISSIONAL</strong>
                        Amplie suas oportunidades e fortale&#231;a sua entrada no mercado de trabalho com capacita&#231;&#227;o gratuita.
                    </div>
                </div>
            </div></div>
            <div class="course-accordion-wrap">
                <h2 class="accordion-heading">Escolha seu curso ({{ cursos_ativos|length }} op&#231;&#245;es dispon&#237;veis):</h2>
                <div class="course-accordion" id="course-accordion">
                    {% set ns = namespace(cursos_vistos=[]) %}
                    {% for op in opcoes %}
                    {% if op.curso_id not in ns.cursos_vistos %}
                    {% set ns.cursos_vistos = ns.cursos_vistos + [op.curso_id] %}
                    {% set turmas_do_curso = opcoes | selectattr("curso_id", "equalto", op.curso_id) | list %}
                    <div class="accordion-item" id="accordion-{{ op.curso_id }}">
                        <button type="button" class="accordion-header" onclick="toggleAccordion('{{ op.curso_id }}')">
                            <span class="accordion-icon">&#127891;</span>
                            <span class="accordion-header-text">
                                <span class="accordion-curso-nome">{{ op.curso }}</span>
                                <span class="accordion-curso-count">{{ turmas_do_curso|length }} turma{{ 's' if turmas_do_curso|length > 1 else '' }} dispon&#237;ve{{ 'is' if turmas_do_curso|length > 1 else 'l' }}</span>
                            </span>
                            <span class="accordion-chevron" id="chevron-{{ op.curso_id }}">&#8250;</span>
                        </button>
                        <div class="accordion-panel" id="panel-{{ op.curso_id }}">
                            {% for turma in turmas_do_curso %}
                            <div class="turma-card">
                                <div class="turma-info">
                                    <div class="turma-local">
                                        <span>&#128205;</span>
                                        <span><strong>{{ turma.local }}</strong><br><span class="turma-endereco">{{ turma.endereco_curso }}</span></span>
                                    </div>
                                    <div class="turma-linha"><span>&#128197;</span> {{ turma.dias_aula }} &bull; {{ turma.data_inicio }} a {{ turma.encerramento }}</div>
                                    <div class="turma-linha"><span>&#128337;</span> {{ turma.horario }}</div>
                                </div>
                                <form method="post" action="{{ url_for('inscricao_unica') }}">
                                    <input type="hidden" name="etapa" value="inicio">
                                    <input type="hidden" name="opcao_id_inicio" value="{{ turma.id }}">
                                    <button type="submit" class="cta-button turma-select-btn">QUERO ME INSCREVER &#8594;</button>
                                </form>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                    {% endfor %}
                </div>
            </div>
        </div>

        {% elif etapa == "dados" %}
        <div class="wizard-panel">
            <div class="step-card">
                <h2 class="panel-title">Dados pessoais</h2>
                {% if erro %}<div class="error-banner">&#9888;&#65039; {{ erro }}</div>{% endif %}
                <form method="post" action="{{ url_for('inscricao_unica') }}">
                    <input type="hidden" name="etapa" value="dados">
                    <div class="step-grid step-grid--stacked">
                        <div class="form-group full"><label for="nome">Nome completo *</label><input type="text" id="nome" name="nome" maxlength="50" placeholder="Digite seu nome completo" value="{{ form.nome or '' }}"></div>
                        <div class="form-group"><label for="cpf">CPF *</label><input type="text" id="cpf" name="cpf" maxlength="14" placeholder="000.000.000-00" value="{{ form.cpf or '' }}"></div>
                        <div class="form-group"><label for="telefone">WhatsApp *</label><input type="text" id="telefone" name="telefone" maxlength="15" placeholder="(00) 00000-0000" value="{{ form.telefone or '' }}"></div>
                        <div class="form-group"><label for="nascimento">Data de nascimento *</label><input type="text" id="nascimento" name="nascimento" maxlength="10" placeholder="dd/mm/aaaa" value="{{ form.nascimento or '' }}"></div>
                        <div class="form-group"><label for="email">E-mail *</label><input type="email" id="email" name="email" maxlength="60" placeholder="seuemail@gmail.com" value="{{ form.email or '' }}"></div>
                        <div class="form-group"><label for="cep">CEP *</label><input type="text" id="cep" name="cep" maxlength="9" placeholder="00000-000" value="{{ form.cep or '' }}"></div>
                        <div class="form-group"><label for="bairro">Bairro *</label><input type="text" id="bairro" name="bairro" maxlength="40" placeholder="Nome do bairro" value="{{ form.bairro or '' }}"></div>
                        <div class="form-group"><label for="genero">G&#234;nero *</label><select id="genero" name="genero"><option value="">Selecione</option><option value="Feminino" {{ 'selected' if form.genero=='Feminino' else '' }}>Feminino</option><option value="Masculino" {{ 'selected' if form.genero=='Masculino' else '' }}>Masculino</option><option value="Outro" {{ 'selected' if form.genero=='Outro' else '' }}>Outro</option><option value="Prefiro não dizer" {{ 'selected' if form.genero=='Prefiro não dizer' else '' }}>Prefiro n&#227;o dizer</option></select></div>
                    </div>
                    <div class="panel-actions">
                        <button type="submit" name="voltar" value="1" class="secondary-button">&#8249; Voltar</button>
                        <button type="submit" class="cta-button">Pr&#243;ximo &#8250;</button>
                    </div>
                </form>
            </div>
        </div>

        {% elif etapa == "escolher" %}
        <div class="wizard-panel">
            <div class="step-card">
                <h2 class="panel-title">Escolha sua turma</h2>
                <p class="panel-subtitle">Selecione uma das turmas dispon&#237;veis abaixo.</p>
                {% if erro %}<div class="error-banner">&#9888;&#65039; {{ erro }}</div>{% endif %}
                <form method="post" action="{{ url_for('inscricao_unica') }}">
                    <input type="hidden" name="etapa" value="escolher">
                    <div class="opcao-radio-group">
                        {% for op in opcoes %}
                        <div class="opcao-card {{ 'selected' if form.opcao_id==op.id else '' }}" onclick="this.querySelector('input').checked=true;document.querySelectorAll('.opcao-card').forEach(c=>c.classList.remove('selected'));this.classList.add('selected');">
                            <input type="radio" name="opcao_id" value="{{ op.id }}" {{ 'checked' if form.opcao_id==op.id else '' }}>
                            <label>
                                <div class="opcao-titulo">{{ op.curso }} &mdash; {{ op.local }}</div>
                                <div class="opcao-detalhe">&#128197; {{ op.dias_aula }} &nbsp;|&nbsp; &#9200; {{ op.horario }} &nbsp;|&nbsp; {{ op.data_inicio }} a {{ op.encerramento }}</div>
                                <div class="opcao-detalhe" style="margin-top:4px;">{{ op.endereco_curso }}</div>
                            </label>
                        </div>
                        {% endfor %}
                    </div>
                    <div class="panel-actions">
                        <button type="submit" name="voltar" value="1" class="secondary-button">&#8249; Voltar</button>
                        <button type="submit" class="cta-button">Ir para revis&#227;o &#8250;</button>
                    </div>
                </form>
            </div>
        </div>

        {% elif etapa == "revisao" %}
        <div class="wizard-panel">
            <div class="step-card">
                <h2 class="panel-title">Revise antes de finalizar</h2>
                <p class="panel-subtitle">Confira os dados preenchidos e confirme sua participa&#231;&#227;o.</p>
                {% if erro %}<div class="error-banner">&#9888;&#65039; {{ erro }}</div>{% endif %}
                <div class="review-layout">
                    <div class="review-box"><div class="review-title">Dados pessoais</div><div class="review-list">
                        <div class="review-item"><strong>Nome</strong><span>{{ form.nome }}</span></div>
                        <div class="review-item"><strong>CPF</strong><span>{{ form.cpf }}</span></div>
                        <div class="review-item"><strong>Nascimento</strong><span>{{ form.nascimento }}</span></div>
                        <div class="review-item"><strong>G&#234;nero</strong><span>{{ form.genero }}</span></div>
                        <div class="review-item"><strong>WhatsApp</strong><span>{{ form.telefone }}</span></div>
                        <div class="review-item"><strong>CEP</strong><span>{{ form.cep }}</span></div>
                        <div class="review-item"><strong>Bairro</strong><span>{{ form.bairro }}</span></div>
                        <div class="review-item"><strong>E-mail</strong><span>{{ form.email }}</span></div>
                    </div></div>
                    <div class="review-box"><div class="review-title">Informa&#231;&#245;es do curso</div><div class="review-list">
                        <div class="review-item"><strong>Curso</strong><span>{{ form.curso }}</span></div>
                        <div class="review-item"><strong>Local</strong><span>{{ form.local }}</span></div>
                        <div class="review-item"><strong>Dia</strong><span>{{ form.dias_aula }}</span></div>
                        <div class="review-item"><strong>Hor&#225;rio</strong><span>{{ form.horario }}</span></div>
                        <div class="review-item"><strong>In&#237;cio</strong><span>{{ form.data_inicio }}</span></div>
                        <div class="review-item"><strong>Encerramento</strong><span>{{ form.encerramento }}</span></div>
                        <div class="review-item"><strong>Endere&#231;o</strong><span>{{ form.endereco_curso }}</span></div>
                    </div></div>
                    <div class="review-box full">
                        <div class="form-group"><label for="como_conheceu">Como conheceu (opcional)</label><select id="como_conheceu" name="como_conheceu_tmp" form="form-revisao"><option value="">Selecione...</option>{% for op in como_conheceu_opcoes %}<option value="{{ op }}" {{ 'selected' if form.como_conheceu==op else '' }}>{{ op }}</option>{% endfor %}</select></div>
                    </div>
                    <div class="review-box full">
                        <div class="elegibilidade-nota"><strong>Elegibilidade:</strong> Este curso &#233; destinado a pessoas com 16 anos ou mais.</div>
                        <label class="review-check" for="confirma_termos">
                            <input type="checkbox" id="confirma_termos" name="confirma_termos_tmp" value="sim" form="form-revisao">
                            <span>Confirmo que tenho 16 anos ou mais e tenho interesse em participar do curso selecionado.<br>Todas as informa&#231;&#245;es s&#227;o verdadeiras e estou de acordo com os termos de participa&#231;&#227;o.<br>Autorizo o uso dos meus dados para inscri&#231;&#227;o e contato relacionado ao curso.</span>
                        </label>
                        <div class="review-declaracao" style="margin-top:10px;"><strong>Ao confirmar voc&#234; declara que:</strong><ul><li>O curso &#233; totalmente gratuito</li><li>Os dados ser&#227;o usados apenas para inscri&#231;&#227;o</li></ul></div>
                    </div>
                </div>
                <form method="post" action="{{ url_for('inscricao_unica') }}" id="form-revisao">
                    <input type="hidden" name="etapa" value="revisao">
                    <div class="panel-actions">
                        <button type="submit" name="voltar" value="1" class="secondary-button">&#8249; Voltar</button>
                        <button type="submit" class="submit-button">Finalizar inscri&#231;&#227;o &#10003;</button>
                    </div>
                </form>
            </div>
        </div>
        {% endif %}

        </div><!-- .wizard-shell -->
    </div><!-- .wizard-page -->
    </main>
    <script>
        function toggleAccordion(cursoId) {
            var item = document.getElementById('accordion-' + cursoId);
            var panel = document.getElementById('panel-' + cursoId);
            var chevron = document.getElementById('chevron-' + cursoId);
            var isOpen = item.classList.contains('aberto');
            document.querySelectorAll('.accordion-item.aberto').forEach(function(i) { i.classList.remove('aberto'); });
            if (!isOpen) { item.classList.add('aberto'); }
        }
        function cpfMask(v) {
            v = v.replace(/\D/g,'');
            if(v.length>3) v = v.slice(0,3)+'.'+v.slice(3);
            if(v.length>7) v = v.slice(0,7)+'.'+v.slice(7);
            if(v.length>11) v = v.slice(0,11)+'-'+v.slice(11);
            return v.slice(0,14);
        }
        function telMask(v) {
            v = v.replace(/\D/g,'');
            if(v.length>2) v = '('+v.slice(0,2)+') '+v.slice(2);
            if(v.length>9) v = v.slice(0,10)+'-'+v.slice(10);
            return v.slice(0,15);
        }
        function nascMask(v) {
            v = v.replace(/\D/g,'');
            if(v.length>2) v = v.slice(0,2)+'/'+v.slice(2);
            if(v.length>5) v = v.slice(0,5)+'/'+v.slice(5);
            return v.slice(0,10);
        }
        function cepMask(v) {
            v = v.replace(/\D/g,'');
            if(v.length>5) v = v.slice(0,5)+'-'+v.slice(5);
            return v.slice(0,9);
        }
        function mascara(id, fn) {
            var el = document.getElementById(id);
            if(el) el.addEventListener('input', function() { this.value = fn(this.value); });
        }
        mascara('cpf', cpfMask);
        mascara('telefone', telMask);
        mascara('nascimento', nascMask);
        mascara('cep', cepMask);
    </script>
</body>
</html>
"""

TEMPLATE_CONFIRMACAO = r"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Inscri&#231;&#227;o confirmada | Qualifica&#231;&#227;o Profissional Fortaleza</title>
    <meta name="robots" content="noindex, nofollow">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --background: 0 0% 97%;
            --foreground: 215 25% 15%;
            --card: 0 0% 100%;
            --primary: 0 100% 27%;
            --primary-light: 0 80% 40%;
            --primary-foreground: 0 0% 100%;
            --secondary: 0 10% 95%;
            --accent: 0 60% 95%;
            --muted-foreground: 215 16% 47%;
            --success: 142 71% 45%;
            --border: 0 10% 88%;
            --radius: 1rem;
            --gradient-primary: linear-gradient(135deg, hsl(0 100% 27%) 0%, hsl(0 80% 40%) 100%);
            --gradient-soft: linear-gradient(180deg, hsl(0 0% 97%) 0%, hsl(0 10% 95%) 100%);
            --shadow-soft: 0 4px 6px rgba(139,0,0,.05);
            --shadow-md: 0 8px 16px rgba(139,0,0,.10);
            --shadow-hover: 0 8px 24px rgba(139,0,0,.12);
        }
        html { overflow-x: hidden; }
        body { min-height:100vh; margin:0; width:100%; max-width:100%; overflow-x:hidden; background: var(--gradient-soft); font-family:'Inter',Arial,sans-serif; color: hsl(var(--foreground)); }
        .main-header { position: fixed; top:0; left:0; right:0; z-index:50; border-bottom:1px solid hsl(var(--border)); background:hsl(var(--card) / 0.95); backdrop-filter: blur(8px); box-shadow: var(--shadow-soft); }
        .header-inner { display:flex; align-items:center; justify-content:center; gap:16px; padding:10px 16px; }
        .header-inner img { height:44px; object-fit:contain; }
        .header-title { text-align:left; }
        .header-title .brand { margin:0; font-size:0.85rem; font-weight:800; color:hsl(var(--primary)); line-height:1.2; }
        .header-title .sub { margin:0; font-size:0.7rem; color:hsl(var(--muted-foreground)); }
        .confirm-page { width:min(560px,calc(100% - 16px)); margin:0 auto; padding:92px 0 32px; text-align:center; }
        .confirm-card { background:hsl(var(--card)); border-radius:calc(var(--radius) * 1.25); box-shadow: var(--shadow-hover); padding:28px 20px; text-align:center; }
        .checkmark-circle { width:64px; height:64px; margin:0 auto 16px; border-radius:999px; background:hsl(var(--success) / 0.12); display:flex; align-items:center; justify-content:center; }
        .checkmark-circle svg { width:36px; height:36px; stroke:hsl(var(--success)); fill:none; }
        .confirm-card h1 { margin:0 0 6px; color:hsl(var(--foreground)); font-weight:800; font-size:clamp(1.5rem,4vw,1.9rem); }
        .confirm-lead { margin:0; color:hsl(var(--muted-foreground)); font-size:0.92rem; }
        .confirm-note { margin:14px auto 0; color:hsl(var(--muted-foreground)); font-size:0.88rem; max-width:420px; }
        .protocol-badge { display:inline-flex; flex-direction:column; gap:2px; margin:16px auto 0; padding:10px 20px; border-radius:var(--radius); background:hsl(var(--accent)); }
        .protocol-badge .label { font-size:0.72rem; font-weight:700; color:hsl(var(--primary)); text-transform:uppercase; letter-spacing:0.04em; }
        .protocol-badge .value { font-size:1.1rem; font-weight:900; color:hsl(var(--primary)); letter-spacing:0.06em; }
        .review-list { display:grid; gap:6px; margin:16px 0 0; text-align:left; }
        .review-item { display:grid; grid-template-columns:auto 1fr; align-items:center; column-gap:8px; padding:7px 9px; border-radius:0.65rem; background:hsl(var(--accent)); text-align:left; }
        .review-item strong { color:hsl(var(--primary)); font-size:0.88rem; white-space:nowrap; }
        .review-item strong::after { content:':'; }
        .review-item span { color:hsl(var(--foreground)); font-size:0.94rem; word-break:break-word; text-align:left; }
        .actions { display:flex; flex-direction:column; gap:10px; margin-top:20px; }
        .action-button { display:flex; align-items:center; justify-content:center; gap:8px; min-height:46px; padding:10px 16px; border-radius:999px; text-decoration:none; font-weight:700; font-size:0.95rem; transition:transform 0.16s ease, filter 0.16s ease; }
        .action-button.primary { background: var(--gradient-primary); color:hsl(var(--primary-foreground)); }
        .action-button.primary:hover { filter:brightness(1.1); }
        .action-button.secondary { background:hsl(var(--card)); color:hsl(var(--foreground)); border:1.5px solid hsl(var(--border)); }
        .action-button:hover { transform:scale(1.02); }
        .info-card { margin-top:16px; text-align:left; background:hsl(var(--card)); border-radius:calc(var(--radius) * 1.1); box-shadow: var(--shadow-soft); padding:16px 18px; }
        .info-card h3 { margin:0 0 10px; color:hsl(var(--foreground)); font-size:0.95rem; font-weight:800; }
        .info-card ol, .info-card ul { margin:0; padding-left:18px; color:hsl(var(--muted-foreground)); font-size:0.86rem; line-height:1.6; }
        .info-card.muted { background:hsl(var(--secondary) / 0.6); box-shadow:none; }
        @media (max-width:640px) {
            html,body{width:100%!important;max-width:100%!important;overflow-x:hidden!important;}body*{min-width:0;}
            .header-inner{padding:8px 12px;gap:10px;} .header-inner img{height:36px;}
            .confirm-page{width:calc(100% - 8px)!important;max-width:100%!important;padding:76px 0 20px;}
            .confirm-card{width:100%!important;max-width:100%!important;padding:20px 14px;}
            img,svg{max-width:100%!important;height:auto!important;}
        }
    </style>
</head>
<body>
    <header class="main-header">
        <div class="header-inner">
            <img src="/static/logo-prefeitura.png" alt="Prefeitura de Fortaleza" loading="eager">
            <div class="header-title">
                <p class="brand">QUALIFICAÇÃO PROFISSIONAL</p>
                <p class="sub">Prefeitura de Fortaleza &bull; SMTE</p>
            </div>
        </div>
    </header>
    <main>
    <div class="confirm-page">
        <div class="confirm-card">
            <div class="checkmark-circle"><svg viewBox="0 0 24 24"><path d="M20 6L9 17l-5-5" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5"/></svg></div>
            <h1>Inscri&#231;&#227;o realizada! &#127881;</h1>
            <p class="confirm-lead">Sua vaga foi garantida no Programa de Qualifica&#231;&#227;o Profissional!</p>
            <p class="confirm-note">Em breve entraremos em contato via WhatsApp com mais informa&#231;&#245;es.</p>
            <div class="protocol-badge">
                <span class="label">N&#250;mero de protocolo</span>
                <span class="value">{{ protocolo }}</span>
            </div>
            <div class="review-list">
                <div class="review-item"><strong>Nome</strong><span>{{ nome }}</span></div>
                <div class="review-item"><strong>Curso</strong><span>{{ curso }}</span></div>
                <div class="review-item"><strong>Local</strong><span>{{ local }}</span></div>
                <div class="review-item"><strong>Dias</strong><span>{{ dias_aula }}</span></div>
                <div class="review-item"><strong>Hor&#225;rio</strong><span>{{ horario }}</span></div>
                <div class="review-item"><strong>Per&#237;odo</strong><span>{{ data_inicio }} a {{ encerramento }}</span></div>
                <div class="review-item"><strong>Endere&#231;o</strong><span>{{ endereco_curso }}</span></div>
            </div>
            <div class="actions">
                <a class="action-button secondary" href="{{ whatsapp_url }}" target="_blank" rel="noopener noreferrer">&#128172; Compartilhar no WhatsApp</a>
                <a class="action-button primary" href="{{ url_for('inicio') }}">&#127968; Voltar ao In&#237;cio</a>
            </div>
        </div>
        <div class="info-card muted">
            <h3>Pr&#243;ximos Passos:</h3>
            <ol>
                <li>Aguarde nosso contato via WhatsApp</li>
                <li>Prepare RG, CPF e comprovante de resid&#234;ncia</li>
                <li>Compare&#231;a no primeiro dia de aula no local indicado</li>
                <li>N&#227;o se esque&#231;a de levar documento com foto!</li>
            </ol>
        </div>
    </div>
    </main>
</body>
</html>
"""

def validar_nome(nome):
    if not nome or len(nome.strip()) < 5:
        return "Nome deve ter pelo menos 5 caracteres."
    partes = [p for p in nome.strip().split() if p]
    if len(partes) < 2:
        return "Informe nome e sobrenome."
    for p in partes:
        if not NAME_PATTERN.fullmatch(p):
            return "Nome contém caracteres inválidos."
    return None

def validar_cpf(cpf):
    nums = re.sub(r'\D', '', cpf or "")
    if len(nums) != 11 or len(set(nums)) == 1:
        return "CPF inválido."
    for i in range(2):
        total = sum(int(nums[j]) * (10 + i - j) for j in range(9 + i))
        esperado = 0 if (total * 10 % 11) >= 10 else (total * 10 % 11)
        if esperado != int(nums[9 + i]):
            return "CPF inválido."
    return None

def validar_telefone(tel):
    nums = re.sub(r'\D', '', tel or "")
    if len(nums) < 10 or len(nums) > 11:
        return "Telefone inválido."
    ddd = nums[:2]
    if ddd not in VALID_DDDS:
        return f"DDD {ddd} inválido."
    return None

def validar_email(email):
    if not ALLOWED_EMAIL_PATTERN.match(email or ""):
        return "Use um e-mail Gmail, Hotmail, Outlook ou Yahoo."
    return None

def validar_nascimento(nascimento):
    try:
        dn = datetime.strptime(nascimento or "", "%d/%m/%Y")
    except ValueError:
        return "Data de nascimento inválida. Use o formato dd/mm/aaaa."
    hoje = datetime.today()
    idade = hoje.year - dn.year
    if (hoje.month, hoje.day) < (dn.month, dn.day):
        idade -= 1
    if idade < 16 or idade > 90:
        return "Idade permitida: de 16 até 90 anos."
    return None

def validar_cep(cep):
    if not re.fullmatch(r"\d{5}-\d{3}", cep or ""):
        return "CEP inválido. Formato: 00000-000."
    return None

def validar_dados_pessoais(form):
    erros = []
    e = validar_nome(form.get("nome", ""))
    if e: erros.append(e)
    e = validar_cpf(form.get("cpf", ""))
    if e: erros.append(e)
    e = validar_telefone(form.get("telefone", ""))
    if e: erros.append(e)
    e = validar_nascimento(form.get("nascimento", ""))
    if e: erros.append(e)
    e = validar_email(form.get("email", ""))
    if e: erros.append(e)
    e = validar_cep(form.get("cep", ""))
    if e: erros.append(e)
    if not form.get("bairro", "").strip():
        erros.append("Informe seu bairro.")
    if not form.get("genero", ""):
        erros.append("Selecione o gênero.")
    return erros

@app.route("/", methods=["GET"])
def inicio():
    session.clear()
    return render_template_string(
        TEMPLATE_WIZARD,
        etapa="inicio",
        progresso=5,
        form={},
        erro=None,
        opcoes=COURSE_OPTIONS,
        como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
        cursos_ativos=ACTIVE_COURSE_CATALOG,
    )

@app.route("/inscricao", methods=["GET","POST"])
def inscricao_unica():
    if request.method == "GET":
        return redirect(url_for("inicio"))

    etapa_atual = request.form.get("etapa", "inicio")
    form_data   = dict(session.get("form_data", {}))
    erro        = None

    # ── VOLTAR ──────────────────────────────────────────────
    if request.form.get("voltar"):
        if etapa_atual == "dados":
            return render_template_string(
                TEMPLATE_WIZARD, etapa="inicio", progresso=5,
                form=form_data, erro=None,
                opcoes=COURSE_OPTIONS,
                como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
                cursos_ativos=ACTIVE_COURSE_CATALOG,
            )
        if etapa_atual == "escolher":
            return render_template_string(
                TEMPLATE_WIZARD, etapa="dados", progresso=35,
                form=form_data, erro=None,
                opcoes=COURSE_OPTIONS,
                como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
                cursos_ativos=ACTIVE_COURSE_CATALOG,
            )
        if etapa_atual == "revisao":
            return render_template_string(
                TEMPLATE_WIZARD, etapa="escolher", progresso=65,
                form=form_data, erro=None,
                opcoes=COURSE_OPTIONS,
                como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
                cursos_ativos=ACTIVE_COURSE_CATALOG,
            )

    # ── ETAPA: INICIO (turma selecionada pelo accordion) ──────
    if etapa_atual == "inicio":
        opcao_id_inicio = request.form.get("opcao_id_inicio", "").strip()
        if opcao_id_inicio:
            form_data["opcao_id"] = opcao_id_inicio
            fill_form_data_from_selection(form_data)
            session["form_data"] = form_data
        return render_template_string(
            TEMPLATE_WIZARD, etapa="dados", progresso=35,
            form=form_data, erro=None,
            opcoes=COURSE_OPTIONS,
            como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
            cursos_ativos=ACTIVE_COURSE_CATALOG,
        )

    # ── ETAPA: DADOS PESSOAIS ────────────────────────────────
    if etapa_atual == "dados":
        for campo in ("nome","cpf","telefone","nascimento","email","cep","bairro","genero"):
            form_data[campo] = request.form.get(campo, "").strip()
        erros = validar_dados_pessoais(form_data)
        if erros:
            erro = " | ".join(erros)
            return render_template_string(
                TEMPLATE_WIZARD, etapa="dados", progresso=35,
                form=form_data, erro=erro,
                opcoes=COURSE_OPTIONS,
                como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
                cursos_ativos=ACTIVE_COURSE_CATALOG,
            )
        session["form_data"] = form_data
        return render_template_string(
            TEMPLATE_WIZARD, etapa="escolher", progresso=65,
            form=form_data, erro=None,
            opcoes=COURSE_OPTIONS,
            como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
            cursos_ativos=ACTIVE_COURSE_CATALOG,
        )

    # ── ETAPA: ESCOLHER CURSO ────────────────────────────────
    if etapa_atual == "escolher":
        opcao_id = request.form.get("opcao_id", "").strip()
        if not opcao_id:
            erro = "Selecione uma turma."
            return render_template_string(
                TEMPLATE_WIZARD, etapa="escolher", progresso=65,
                form=form_data, erro=erro,
                opcoes=COURSE_OPTIONS,
                como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
                cursos_ativos=ACTIVE_COURSE_CATALOG,
            )
        form_data["opcao_id"] = opcao_id
        fill_form_data_from_selection(form_data)
        session["form_data"] = form_data
        return render_template_string(
            TEMPLATE_WIZARD, etapa="revisao", progresso=90,
            form=form_data, erro=None,
            opcoes=COURSE_OPTIONS,
            como_conheceu_opcoes=COMO_CONHECEU_OPCOES,
            cursos_ativos=ACTIVE_COURSE_CATALOG,
        )

    # ── ETAPA: REVISAO / CONFIRMAR ───────────────────────────
    if etapa_atual == "revisao":
        form_data["como_conheceu"] = request.form.get("como_conheceu_tmp", "").strip()
        fill_form_data_from_selection(form_data)
        agora     = datetime.now(timezone.utc)
        protocolo = agora.strftime("%Y%m%d%H%M%S") + "-" + str(uuid.uuid4())[:6].upper()
        form_data["protocolo"] = protocolo
        cpf_limpo  = re.sub(r'\D', '', form_data.get("cpf", ""))
        tel_limpo  = re.sub(r'\D', '', form_data.get("telefone", ""))
        dados = [
            protocolo,
            agora.strftime("%d/%m/%Y %H:%M:%S"),
            form_data.get("nome", ""),
            cpf_limpo,
            tel_limpo,
            form_data.get("email", ""),
            form_data.get("nascimento", ""),
            form_data.get("cep", ""),
            form_data.get("bairro", ""),
            form_data.get("genero", ""),
            form_data.get("como_conheceu", ""),
            form_data.get("curso", ""),
            form_data.get("local", ""),
            form_data.get("turma", ""),
            form_data.get("dias_aula", ""),
            form_data.get("horario", ""),
            form_data.get("data_inicio", ""),
            form_data.get("encerramento", ""),
        ]
        session["confirmacao"] = {
            "protocolo":     protocolo,
            "nome":          form_data.get("nome", ""),
            "curso":         form_data.get("curso", ""),
            "local":         form_data.get("local", ""),
            "turma":         form_data.get("turma", ""),
            "dias_aula":     form_data.get("dias_aula", ""),
            "horario":       form_data.get("horario", ""),
            "data_inicio":   form_data.get("data_inicio", ""),
            "encerramento":  form_data.get("encerramento", ""),
            "endereco_curso":form_data.get("endereco_curso", ""),
        }
        BACKGROUND_EXECUTOR.submit(
            processar_inscricao_em_segundo_plano, dados, dict(form_data)
        )
        return redirect(url_for("confirmacao"))

    return redirect(url_for("inicio"))

@app.route("/confirmacao")
def confirmacao():
    conf = session.get("confirmacao")
    if not conf:
        return redirect(url_for("inicio"))
    home_url     = request.host_url.rstrip("/")
    whatsapp_url = build_whatsapp_share_url(home_url)
    return render_template_string(
        TEMPLATE_CONFIRMACAO,
        protocolo=conf["protocolo"],
        nome=conf["nome"],
        curso=conf["curso"],
        local=conf["local"],
        turma=conf["turma"],
        dias_aula=conf["dias_aula"],
        horario=conf["horario"],
        data_inicio=conf["data_inicio"],
        encerramento=conf["encerramento"],
        endereco_curso=conf["endereco_curso"],
        whatsapp_url=whatsapp_url,
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
