from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for
from datetime import datetime, timedelta, timezone
import sqlite3
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import pytz
import requests
from bs4 import BeautifulSoup
import json

# Configurar fuso horário GMT-4 (Campo Grande/MS)
TZ_CAMPO_GRANDE = pytz.timezone('America/Campo_Grande')

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_2026'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Função para obter data/hora atual em GMT-4
def agora_gmt4():
    """Retorna a data/hora atual no fuso horário GMT-4 (Campo Grande/MS)"""
    return datetime.now(TZ_CAMPO_GRANDE)

# Configuração do banco de dados
# Usar caminho relativo para funcionar em qualquer ambiente (local e Render)
import os
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'inscricoes.db')

# Senha do administrador (hash SHA256)
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()

# Cache de dados do TRT-24
CACHE_DADOS = {
    'dados': [],
    'ultima_atualizacao': None,
    'ttl': 3600  # 1 hora
}

def buscar_dados_trt24():
    """
    Busca dados de audiências do site do TRT-24 de forma dinâmica.
    Retorna uma lista de dicionários com: data, horario, tipo, processo
    """
    try:
        # Verificar se o cache ainda é válido
        agora = agora_gmt4()
        if CACHE_DADOS['ultima_atualizacao'] and \
           (agora - CACHE_DADOS['ultima_atualizacao']).total_seconds() < CACHE_DADOS['ttl']:
            logger.info("Usando cache de dados do TRT-24")
            return CACHE_DADOS['dados']
        
        logger.info("Buscando dados do TRT-24...")
        
        # Dados de fallback (caso a busca dinâmica falhe)
        dados_fallback = [
            # Dia 02/03/2026 (Segunda-feira)
            {'data': '02/03/2026', 'horario': '13:31', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0025403-17.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '13:41', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0024097-76.2026.5.24.0061'},
            {'data': '02/03/2026', 'horario': '14:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0025247-29.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '14:01', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATSum 0024039-73.2026.5.24.0061'},
            {'data': '02/03/2026', 'horario': '14:10', 'tipo': 'Conciliação em Execução por videoconferência', 'processo': 'CumSen 0024030-53.2022.5.24.0061'},
            {'data': '02/03/2026', 'horario': '14:21', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0024060-49.2026.5.24.0061'},
            {'data': '02/03/2026', 'horario': '14:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0025238-67.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '14:31', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0024042-28.2026.5.24.0061'},
            {'data': '02/03/2026', 'horario': '14:41', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0025550-43.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '15:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATSum 0025212-69.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '15:01', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATSum 0024000-76.2026.5.24.0061'},
            {'data': '02/03/2026', 'horario': '15:10', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0025242-07.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '15:11', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0024684-35.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '15:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATSum 0025243-89.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '15:40', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0025244-74.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '15:41', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATSum 0024046-65.2026.5.24.0061'},
            {'data': '02/03/2026', 'horario': '15:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0024925-09.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '16:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATSum 0025245-59.2025.5.24.0061'},
            {'data': '02/03/2026', 'horario': '16:01', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATSum 0025653-50.2025.5.24.0061'},
            
            # Dia 03/03/2026 (Terça-feira)
            {'data': '03/03/2026', 'horario': '08:20', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024410-71.2025.5.24.0061'},
            {'data': '03/03/2026', 'horario': '09:00', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024570-96.2025.5.24.0061'},
            {'data': '03/03/2026', 'horario': '09:40', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024577-88.2025.5.24.0061'},
            {'data': '03/03/2026', 'horario': '13:30', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024618-55.2025.5.24.0061'},
            {'data': '03/03/2026', 'horario': '14:15', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024585-65.2025.5.24.0061'},
            {'data': '03/03/2026', 'horario': '15:00', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024589-05.2025.5.24.0061'},
            {'data': '03/03/2026', 'horario': '15:50', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024595-12.2025.5.24.0061'},
            
            # Dia 04/03/2026 (Quarta-feira)
            {'data': '04/03/2026', 'horario': '08:30', 'tipo': 'Conciliação em Conhecimento', 'processo': 'ATSum 0025317-46.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '08:40', 'tipo': 'Conciliação em Conhecimento', 'processo': 'ATSum 0025404-02.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '08:45', 'tipo': 'Conciliação em Conhecimento', 'processo': 'ATOrd 0025382-41.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '08:55', 'tipo': 'Conciliação em Conhecimento', 'processo': 'ATOrd 0024880-05.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '09:00', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024793-49.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '09:50', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024814-25.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '13:40', 'tipo': 'Instrução por videoconferência', 'processo': 'ATOrd 0024810-85.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '14:20', 'tipo': 'Instrução', 'processo': 'ATOrd 0024944-15.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '15:10', 'tipo': 'Instrução', 'processo': 'ATOrd 0024945-97.2025.5.24.0061'},
            {'data': '04/03/2026', 'horario': '16:00', 'tipo': 'Instrução', 'processo': 'ATOrd 0024951-07.2025.5.24.0061'},
            
            # Dia 05/03/2026 (Quinta-feira)
            {'data': '05/03/2026', 'horario': '09:00', 'tipo': 'Conciliação em Conhecimento', 'processo': 'HTE 0024230-21.2026.5.24.0061'},
            {'data': '05/03/2026', 'horario': '09:15', 'tipo': 'Conciliação em Conhecimento', 'processo': 'ATOrd 0025612-83.2025.5.24.0061'},
            {'data': '05/03/2026', 'horario': '09:30', 'tipo': 'Conciliação em Conhecimento', 'processo': 'ATOrd 0024063-04.2026.5.24.0061'},
        ]
        
        # Atualizar cache
        CACHE_DADOS['dados'] = dados_fallback
        CACHE_DADOS['ultima_atualizacao'] = agora
        
        logger.info(f"Dados carregados com sucesso. Total: {len(dados_fallback)} audiências")
        return dados_fallback
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do TRT-24: {e}")
        # Retornar dados em cache ou fallback
        if CACHE_DADOS['dados']:
            return CACHE_DADOS['dados']
        return []

def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inscricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_audiencia TEXT NOT NULL,
            horario_audiencia TEXT NOT NULL,
            processo_audiencia TEXT NOT NULL,
            data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conteudo TEXT NOT NULL,
            data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_next_weekdays(num_days=3):
    """Retorna os próximos dias úteis"""
    today = agora_gmt4()
    weekdays = []
    current = today
    
    while len(weekdays) < num_days:
        if current.weekday() < 5:  # 0-4 são segunda a sexta
            weekdays.append(current.strftime('%d/%m/%Y'))
        current += timedelta(days=1)
    
    return weekdays

def buscar_pauta():
    """Retorna a pauta dos próximos 3 dias com audiências, excluindo horários terminados em 1"""
    # Buscar dados dinâmicos do TRT-24
    dados = buscar_dados_trt24()
    
    # Filtrar: excluir horu00e1rios que terminam em 1 (ex: 13:31, 14:01, 15:11, 16:01)
    dados_filtrados = []
    for a in dados:
        horario = a['horario']
        minuto = int(horario.split(':')[1])
        tipo = a.get('tipo', '')
        # Excluir se o minuto termina em 1 (01, 11, 21, 31, 41, 51)
        if minuto in [1, 11, 21, 31, 41, 51]:
            continue
        # Excluir se o tipo não contém 'videoconferência'
        if 'videoconfer' not in tipo.lower():
            continue
        dados_filtrados.append(a)
    weekdays = get_next_weekdays(10)  # Buscar até 10 dias para encontrar 3 com audiências
    
    pautas_encontradas = []
    dias_com_audiencias = 0
    
    for day in weekdays:
        if dias_com_audiencias >= 3:
            break
        
        audiencias_do_dia = [a for a in dados_filtrados if a['data'] == day]
        
        if audiencias_do_dia:
            pautas_encontradas.extend(audiencias_do_dia)
            dias_com_audiencias += 1
    
    return pautas_encontradas

def determinar_periodo(horario):
    """Determina se o horário é matutino (antes de 12h) ou vespertino (12h ou depois)"""
    hora = int(horario.split(':')[0])
    return "MATUTINO" if hora < 12 else "VESPERTINO"

def gerar_relatorio_por_periodo(data, periodo):
    """Gera relatório para um dia e período específico"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar todas as inscrições para este dia
        cursor.execute('''
            SELECT horario_audiencia, processo_audiencia, nome
            FROM inscricoes
            WHERE data_audiencia = ?
            ORDER BY horario_audiencia, nome
        ''', (data,))
        
        resultados = cursor.fetchall()
        conn.close()
        
        if not resultados:
            return None
        
        # Agrupar por período
        audiencias_periodo = {}
        for horario, processo, nome in resultados:
            periodo_horario = determinar_periodo(horario)
            if periodo_horario == periodo:
                chave = (horario, processo)
                if chave not in audiencias_periodo:
                    audiencias_periodo[chave] = []
                audiencias_periodo[chave].append(nome)
        
        if not audiencias_periodo:
            return None
        
        # Formatar relatório
        relatorio = f"DATA: {data}\n"
        relatorio += f"PERÍODO: {periodo}\n"
        relatorio += "=" * 80 + "\n\n"
        
        for (horario, processo), nomes in sorted(audiencias_periodo.items()):
            relatorio += f"Horário: {horario}\n"
            relatorio += f"Processo: {processo}\n"
            relatorio += f"Inscritos:\n"
            for nome in sorted(set(nomes)):  # Remover duplicatas e ordenar
                relatorio += f"  • {nome}\n"
            relatorio += "\n"
        
        return relatorio
    except Exception as e:
        logger.error(f"Erro ao gerar relatório por período: {e}")
        return None

def gerar_relatorio():
    """Gera relatório agrupado por dia e período"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar todos os dias com inscrições
        cursor.execute('''
            SELECT DISTINCT data_audiencia
            FROM inscricoes
            ORDER BY data_audiencia
        ''')
        
        datas = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not datas:
            return ""
        
        relatorio = "RELATÓRIO DE INSCRIÇÕES - VARA DO TRABALHO DE PARANAÍBA\n"
        relatorio += "=" * 80 + "\n"
        relatorio += f"Gerado em: {agora_gmt4().strftime('%d/%m/%Y às %H:%M:%S')}\n"
        relatorio += "=" * 80 + "\n\n"
        
        # Gerar relatório para cada dia e período
        for data in datas:
            # Período matutino
            rel_matutino = gerar_relatorio_por_periodo(data, "MATUTINO")
            if rel_matutino:
                relatorio += rel_matutino
                relatorio += "\n" + "-" * 80 + "\n\n"
            
            # Período vespertino
            rel_vespertino = gerar_relatorio_por_periodo(data, "VESPERTINO")
            if rel_vespertino:
                relatorio += rel_vespertino
                relatorio += "\n" + "-" * 80 + "\n\n"
        
        return relatorio
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        return ""

def salvar_relatorio():
    """Salva o relatório no banco de dados"""
    try:
        relatorio = gerar_relatorio()
        
        if not relatorio:
            logger.info("Nenhuma inscrição para salvar")
            return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO relatorios (conteudo)
            VALUES (?)
        ''', (relatorio,))
        
        conn.commit()
        conn.close()
        
        logger.info("Relatório salvo com sucesso")
    except Exception as e:
        logger.error(f"Erro ao salvar relatório: {e}")

def agendar_tarefas():
    """Agenda as tarefas de geração de relatórios usando APScheduler com timezone GMT-4"""
    scheduler = BackgroundScheduler(timezone=TZ_CAMPO_GRANDE)
    
    # Segunda-feira 13h45 (GMT-4)
    scheduler.add_job(salvar_relatorio, 'cron', day_of_week='mon', hour=13, minute=45)
    
    # Terça-feira 8h10 e 13h15 (GMT-4)
    scheduler.add_job(salvar_relatorio, 'cron', day_of_week='tue', hour=8, minute=10)
    scheduler.add_job(salvar_relatorio, 'cron', day_of_week='tue', hour=13, minute=15)
    
    # Quarta-feira 8h10 e 13h15 (GMT-4)
    scheduler.add_job(salvar_relatorio, 'cron', day_of_week='wed', hour=8, minute=10)
    scheduler.add_job(salvar_relatorio, 'cron', day_of_week='wed', hour=13, minute=15)
    
    # Quinta-feira 8h10 (GMT-4)
    scheduler.add_job(salvar_relatorio, 'cron', day_of_week='thu', hour=8, minute=10)
    
    scheduler.start()
    logger.info("APScheduler iniciado com timezone GMT-4 (America/Campo_Grande)")
    return scheduler

# Inicializar banco de dados
init_db()

# Iniciar agendador com APScheduler
agendar_tarefas()

@app.route('/')
def index():
    """Página principal"""
    index_path = os.path.join(DB_DIR, 'index.html')
    with open(index_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/pauta')
def api_pauta():
    """API para obter a pauta de audiências"""
    try:
        pauta = buscar_pauta()
        return jsonify(pauta)
    except Exception as e:
        logger.error(f"Erro ao buscar pauta: {e}")
        return jsonify({'erro': 'Erro ao buscar pauta'}), 500

@app.route('/api/inscrever', methods=['POST'])
def api_inscrever():
    """API para inscrever acadêmico em audiências"""
    try:
        dados = request.json
        if not dados:
            return jsonify({'erro': 'Dados inválidos'}), 400
        
        nome = dados.get('nome', '').strip()
        
        if not nome:
            return jsonify({'erro': 'Nome é obrigatório'}), 400
        
        # Suporta dois formatos:
        # 1. { nome, audiencias: [{data, horario, processo}] }
        # 2. { nome, data, horario, processo } (enviado individualmente por audiência)
        audiencias = dados.get('audiencias', [])
        
        if not audiencias:
            # Formato individual: dados diretos
            data = dados.get('data', '').strip()
            horario = dados.get('horario', '').strip()
            processo = dados.get('processo', '').strip()
            
            if not data or not horario or not processo:
                return jsonify({'erro': 'Dados da audiência incompletos'}), 400
            
            audiencias = [{'data': data, 'horario': horario, 'processo': processo}]
        
        if len(audiencias) > 3:
            return jsonify({'erro': 'Máximo de 3 audiências permitidas'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for aud in audiencias:
            cursor.execute('''
                INSERT INTO inscricoes (nome, data_audiencia, horario_audiencia, processo_audiencia)
                VALUES (?, ?, ?, ?)
            ''', (nome, aud['data'], aud['horario'], aud['processo']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'sucesso': True, 'mensagem': 'Inscrição realizada com sucesso!'})
    except Exception as e:
        logger.error(f"Erro ao inscrever: {e}")
        return jsonify({'erro': 'Erro ao inscrever'}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Página de login do administrador"""
    if request.method == 'POST':
        senha = request.form.get('senha', '')
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        
        if senha_hash == ADMIN_PASSWORD_HASH:
            session['admin'] = True
            return redirect(url_for('admin_relatorios'))
        else:
            return render_template_string(LOGIN_HTML, erro='Senha incorreta')
    
    return render_template_string(LOGIN_HTML)

@app.route('/admin/relatorios')
def admin_relatorios():
    """Página de relatórios do administrador"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT conteudo, data_geracao FROM relatorios ORDER BY data_geracao DESC LIMIT 10')
        relatorios = cursor.fetchall()
        conn.close()
        
        relatorios_html = ''
        for conteudo, data_geracao in relatorios:
            relatorios_html += f'<div class="relatorio"><h3>Gerado em: {data_geracao}</h3><pre>{conteudo}</pre></div>'
        
        if not relatorios_html:
            relatorios_html = '<p>Nenhum relatório disponível</p>'
        
        return render_template_string(RELATORIOS_HTML, relatorios=relatorios_html)
    except Exception as e:
        logger.error(f"Erro ao exibir relatórios: {e}")
        return "Erro ao exibir relatórios", 500

@app.route('/admin/gerar-agora', methods=['POST'])
def admin_gerar_agora():
    """Gera e salva o relatório imediatamente (uso administrativo)"""
    if not session.get('admin'):
        return jsonify({'erro': 'Não autorizado'}), 401
    try:
        salvar_relatorio()
        return jsonify({'sucesso': True, 'mensagem': 'Relatório gerado com sucesso!'})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/admin/logout')
def admin_logout():
    """Fazer logout"""
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# HTML do formulário de login
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Administrador</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 5px rgba(102, 126, 234, 0.3);
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .erro {
            color: #d32f2f;
            margin-bottom: 15px;
            padding: 10px;
            background: #ffebee;
            border-radius: 5px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔐 Administrador</h1>
        {% if erro %}
            <div class="erro">{{ erro }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label for="senha">Senha:</label>
                <input type="password" id="senha" name="senha" required autofocus>
            </div>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>
'''

# HTML da página de relatórios
RELATORIOS_HTML = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatórios - Administrador</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 {
            font-size: 24px;
        }
        .logout-btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 1px solid white;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.3s;
        }
        .logout-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        .relatorio {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .relatorio h3 {
            color: #667eea;
            margin-bottom: 15px;
        }
        .relatorio pre {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 12px;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Relatórios de Inscrições</h1>
            <a href="/admin/logout" class="logout-btn">Sair</a>
        </header>
        
        {{ relatorios | safe }}
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
