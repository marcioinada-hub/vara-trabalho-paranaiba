from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for
from datetime import datetime, timedelta, timezone
import sqlite3
import logging
import schedule
import threading
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import pytz

# Configurar fuso horário GMT-4 (Brasília)
TZ_BRASILIA = pytz.timezone('America/Sao_Paulo')

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_2026'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Função para obter data/hora atual em GMT-4
def agora_brasilia():
    """Retorna a data/hora atual no fuso horário de Brasília (GMT-4)"""
    return datetime.now(TZ_BRASILIA)

# Configuração do banco de dados
DB_PATH = '/home/ubuntu/vara-trabalho-paranaiba/inscricoes.db'

# Senha do administrador (hash SHA256)
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()

# Dados REAIS extraídos do sistema TRT24
DADOS_REAIS = [
    # Dia 02/03/2026 (Segunda-feira)
    {'data': '02/03/2026', 'horario': '14:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': 'ATOrd 0025247-29.2025.5.24.0061'},
    {'data': '02/03/2026', 'horario': '14:10', 'tipo': 'Conciliação em Execução por videoconferência', 'processo': 'CumSen 0024030-53.2022.5.24.0061'},
    
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
    today = datetime.now()
    weekdays = []
    current = today
    
    while len(weekdays) < num_days:
        if current.weekday() < 5:  # 0-4 são segunda a sexta
            weekdays.append(current.strftime('%d/%m/%Y'))
        current += timedelta(days=1)
    
    return weekdays

def buscar_pauta():
    """Retorna a pauta dos próximos 3 dias com audiências"""
    weekdays = get_next_weekdays(10)  # Buscar até 10 dias para encontrar 3 com audiências
    
    pautas_encontradas = []
    dias_com_audiencias = 0
    
    for day in weekdays:
        if dias_com_audiencias >= 3:
            break
        
        audiencias_do_dia = [a for a in DADOS_REAIS if a['data'] == day]
        
        # Filtrar audiências com horários terminados em 1
        audiencias_filtradas = []
        for aud in audiencias_do_dia:
            hora = int(aud['horario'].split(':')[1])
            if hora % 10 != 1:  # Excluir horários terminados em 1
                audiencias_filtradas.append(aud)
        
        if audiencias_filtradas:
            pautas_encontradas.extend(audiencias_filtradas)
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
        relatorio += f"Gerado em: {agora_brasilia().strftime('%d/%m/%Y às %H:%M:%S')}\n"
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
    """Agenda as tarefas de geração de relatórios (GMT-4 / Brasília)"""
    # Segunda-feira às 13h45
    schedule.every().monday.at("13:45").do(salvar_relatorio)
    
    # Terça-feira às 8h10 e 13h15
    schedule.every().tuesday.at("08:10").do(salvar_relatorio)
    schedule.every().tuesday.at("13:15").do(salvar_relatorio)
    
    # Quarta-feira às 8h10 e 13h15
    schedule.every().wednesday.at("08:10").do(salvar_relatorio)
    schedule.every().wednesday.at("13:15").do(salvar_relatorio)
    
    # Quinta-feira às 8h10
    schedule.every().thursday.at("08:10").do(salvar_relatorio)
    
    def executar_agendador():
        while True:
            schedule.run_pending()
            import time
            time.sleep(60)
    
    logger.info("Tarefas agendadas com sucesso (fuso horário: GMT-4 / Brasília)")
    
    thread = threading.Thread(target=executar_agendador, daemon=True)
    thread.start()

@app.route('/api/pauta', methods=['GET'])
def api_pauta():
    """API para retornar a pauta"""
    try:
        pautas = buscar_pauta()
        return jsonify(pautas)
    except Exception as e:
        logger.error(f"Erro ao buscar pauta: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/inscrever', methods=['POST'])
def api_inscrever():
    """API para registrar inscrição em uma audiência"""
    try:
        data = request.get_json()
        logger.info(f"Dados recebidos: {data}")
        nome = data.get('nome')
        data_audiencia = data.get('data')
        horario_audiencia = data.get('horario')
        processo_audiencia = data.get('processo')
        
        logger.info(f"Nome: {nome}, Data: {data_audiencia}, Horário: {horario_audiencia}, Processo: {processo_audiencia}")
        
        if not nome or not data_audiencia or not horario_audiencia or not processo_audiencia:
            return jsonify({'sucesso': False, 'mensagem': 'Campos obrigatórios faltando'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO inscricoes (nome, data_audiencia, horario_audiencia, processo_audiencia)
            VALUES (?, ?, ?, ?)
        ''', (nome, data_audiencia, horario_audiencia, processo_audiencia))
        
        conn.commit()
        conn.close()
        
        return jsonify({'sucesso': True, 'mensagem': 'Inscrição realizada com sucesso!'})
    except Exception as e:
        logger.error(f"Erro ao inscrever: {e}")
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

@app.route('/admin')
def admin_redirect():
    """Redireciona para a página de login"""
    return redirect(url_for('admin_login'))

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
    """Página de visualização de relatórios"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, conteudo, data_geracao
            FROM relatorios
            ORDER BY data_geracao DESC
        ''')
        
        relatorios = cursor.fetchall()
        conn.close()
        
        return render_template_string(RELATORIOS_HTML, relatorios=relatorios)
    except Exception as e:
        logger.error(f"Erro ao buscar relatórios: {e}")
        return "Erro ao buscar relatórios", 500

@app.route('/admin/logout')
def admin_logout():
    """Fazer logout"""
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/')
def index():
    """Página principal"""
    with open('/home/ubuntu/vara-trabalho-paranaiba/index.html', 'r', encoding='utf-8') as f:
        return f.read()

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
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 24px;
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
            transition: border-color 0.3s;
        }
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
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
            text-align: center;
            margin-bottom: 20px;
            padding: 10px;
            background: #ffebee;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔐 Acesso Restrito</h1>
        {% if erro %}
            <div class="erro">{{ erro }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label for="senha">Senha de Administrador:</label>
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
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 28px;
        }
        .logout-btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 10px 20px;
            border: none;
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
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        .relatorio-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        .relatorio-data {
            font-size: 14px;
            color: #666;
            font-weight: 600;
        }
        .relatorio-conteudo {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 600px;
            overflow-y: auto;
        }
        .vazio {
            text-align: center;
            padding: 40px;
            color: #999;
            background: white;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Relatórios de Inscrições</h1>
            <a href="/admin/logout" class="logout-btn">Sair</a>
        </div>
        
        {% if relatorios %}
            {% for relatorio in relatorios %}
                <div class="relatorio">
                    <div class="relatorio-header">
                        <span class="relatorio-data">{{ relatorio[2] }}</span>
                    </div>
                    <div class="relatorio-conteudo">{{ relatorio[1] }}</div>
                </div>
            {% endfor %}
        {% else %}
            <div class="vazio">
                <p>Nenhum relatório disponível ainda.</p>
                <p style="font-size: 12px; margin-top: 10px;">Os relatórios serão gerados automaticamente nos horários agendados.</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    agendar_tarefas()
    app.run(host='0.0.0.0', port=8000, debug=False)
