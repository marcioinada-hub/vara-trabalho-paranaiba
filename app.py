from flask import Flask, jsonify, request, render_template_string, session, redirect, url_for
from datetime import datetime, timedelta, timezone
import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
import os
import hashlib
import pytz
import requests
from bs4 import BeautifulSoup
import json
import psycopg2
from psycopg2.extras import RealDictCursor

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

# Configuração do banco de dados PostgreSQL (Supabase)
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:VaraParanaiba2026!@db.hzocsqelyrrpsbhorabj.supabase.co:5432/postgres')

def get_db():
    """Retorna uma conexão com o banco de dados PostgreSQL"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Senha do administrador (hash SHA256)
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()

# Cache de dados do TRT-24
CACHE_DADOS = {
    'dados': [],
    'ultima_atualizacao': None,
    'ttl': 3600  # 1 hora
}

def buscar_audiencias_dia(data_iso):
    """
    Busca audiências de um dia específico na API do TRT-24.
    data_iso: string no formato 'YYYY-MM-DD'
    Retorna lista de dicionários com: data, horario, tipo, processo
    """
    try:
        url = f"https://pje.trt24.jus.br/pje-consulta-api/api/audiencias"
        headers = {
            'X-Grau-Instancia': '1',
            'Content-type': 'application/json'
        }
        params = {
            'pagina': 1,
            'tamanhoPagina': 200,
            'ordenacaoColuna': 'horario',
            'ordenacaoCrescente': 'true',
            'idOj': 95,  # ID da Vara do Trabalho de Paranaíba
            'data': data_iso
        }
        resp = requests.get(url, headers=headers, params=params, timeout=15, verify=False)
        resp.raise_for_status()
        dados_json = resp.json()
        
        if 'resultado' not in dados_json:
            return []
        
        audiencias = []
        # Converter data_iso para formato dd/mm/yyyy
        data_fmt = datetime.strptime(data_iso, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        for item in dados_json['resultado']:
            # Extrair horário do campo data (ex: '2026-03-05T08:21:00')
            dt = item.get('data', '')
            if 'T' in dt:
                horario = dt.split('T')[1][:5]  # 'HH:MM'
            else:
                horario = ''
            
            tipo = item.get('tipo', '')
            classe = item.get('classeProcesso', '')
            numero = item.get('numeroProcesso', '')
            processo = f"{classe} {numero}".strip() if classe else numero
            
            audiencias.append({
                'data': data_fmt,
                'horario': horario,
                'tipo': tipo,
                'processo': processo
            })
        
        return audiencias
    except Exception as e:
        logger.error(f"Erro ao buscar audiências do dia {data_iso}: {e}")
        return []


def buscar_dados_trt24():
    """
    Busca dados de audiências do TRT-24 de forma dinâmica via API REST.
    Busca os próximos 15 dias úteis para garantir 3 dias com audiências.
    Retorna uma lista de dicionários com: data, horario, tipo, processo
    """
    try:
        # Verificar se o cache ainda é válido
        agora = agora_gmt4()
        if CACHE_DADOS['ultima_atualizacao'] and \
           (agora - CACHE_DADOS['ultima_atualizacao']).total_seconds() < CACHE_DADOS['ttl']:
            logger.info("Usando cache de dados do TRT-24")
            return CACHE_DADOS['dados']
        
        logger.info("Buscando dados do TRT-24 via API REST...")
        
        # Suprimir warnings de SSL
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        todos_dados = []
        current = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Buscar os próximos 20 dias úteis
        dias_buscados = 0
        while dias_buscados < 20:
            if current.weekday() < 5:  # Segunda a Sexta
                data_iso = current.strftime('%Y-%m-%d')
                audiencias = buscar_audiencias_dia(data_iso)
                todos_dados.extend(audiencias)
                dias_buscados += 1
            current += timedelta(days=1)
        
        if todos_dados:
            # Atualizar cache
            CACHE_DADOS['dados'] = todos_dados
            CACHE_DADOS['ultima_atualizacao'] = agora
            logger.info(f"Dados carregados com sucesso via API. Total: {len(todos_dados)} audiências")
            return todos_dados
        else:
            logger.warning("API não retornou dados. Usando cache anterior se disponível.")
            if CACHE_DADOS['dados']:
                return CACHE_DADOS['dados']
            return []
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do TRT-24: {e}")
        if CACHE_DADOS['dados']:
            return CACHE_DADOS['dados']
        return []

def init_db():
    """Inicializa o banco de dados PostgreSQL"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inscricoes (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            data_audiencia TEXT NOT NULL,
            horario_audiencia TEXT NOT NULL,
            processo_audiencia TEXT NOT NULL,
            data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relatorios (
            id SERIAL PRIMARY KEY,
            conteudo TEXT NOT NULL,
            data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Banco de dados PostgreSQL (Supabase) inicializado com sucesso")

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

def filtrar_audiencias(dados):
    """Aplica os filtros padrão: remove horários terminados em 1 e não-videoconferência"""
    dados_filtrados = []
    for a in dados:
        horario = a.get('horario', '')
        if not horario or ':' not in horario:
            continue
        minuto = int(horario.split(':')[1])
        tipo = a.get('tipo', '')
        # Excluir se o minuto termina em 1 (01, 11, 21, 31, 41, 51)
        if minuto in [1, 11, 21, 31, 41, 51]:
            continue
        # Excluir se o tipo não contém 'videoconferência'
        if 'videoconfer' not in tipo.lower():
            continue
        dados_filtrados.append(a)
    return dados_filtrados


def buscar_pauta():
    """Retorna a pauta dos próximos 3 dias úteis com audiências de videoconferência.
    Avança para o próximo dia útil se não houver audiências em um dia."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    pautas_encontradas = []
    dias_com_audiencias = 0
    
    agora = agora_gmt4()
    current = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    dias_verificados = 0
    
    while dias_com_audiencias < 3 and dias_verificados < 30:
        if current.weekday() < 5:  # Segunda a Sexta
            data_iso = current.strftime('%Y-%m-%d')
            audiencias_dia = buscar_audiencias_dia(data_iso)
            audiencias_filtradas = filtrar_audiencias(audiencias_dia)
            
            if audiencias_filtradas:
                pautas_encontradas.extend(audiencias_filtradas)
                dias_com_audiencias += 1
            
            dias_verificados += 1
        
        current += timedelta(days=1)
    
    return pautas_encontradas

def determinar_periodo(horario):
    """Determina se o horário é matutino (antes de 12h) ou vespertino (12h ou depois)"""
    hora = int(horario.split(':')[0])
    return "MATUTINO" if hora < 12 else "VESPERTINO"

def gerar_relatorio_por_periodo(data, periodo):
    """Gera relatório para um dia e período específico"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Buscar todas as inscrições para este dia
        cursor.execute('''
            SELECT horario_audiencia, processo_audiencia, nome
            FROM inscricoes
            WHERE data_audiencia = %s
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
        conn = get_db()
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

def salvar_relatorio(data=None, periodo=None):
    """Salva o relatório no banco de dados para um dia e período específico.
    Se data e periodo forem None, gera relatório completo (uso manual)."""
    try:
        agora = agora_gmt4()
        
        if data is None or periodo is None:
            # Uso manual: gera relatório completo
            relatorio = gerar_relatorio()
        else:
            # Uso agendado: gera apenas para o dia e período especificado
            rel = gerar_relatorio_por_periodo(data, periodo)
            if not rel:
                logger.info(f"Nenhuma inscrição para {data} período {periodo}")
                return
            relatorio = "RELATÓRIO DE INSCRIÇÕES - VARA DO TRABALHO DE PARANAÍBA\n"
            relatorio += "=" * 80 + "\n"
            relatorio += f"Gerado em: {agora.strftime('%d/%m/%Y às %H:%M:%S')}\n"
            relatorio += "=" * 80 + "\n\n"
            relatorio += rel
        
        if not relatorio:
            logger.info("Nenhuma inscrição para salvar")
            return
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO relatorios (conteudo)
            VALUES (%s)
        ''', (relatorio,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Relatório salvo com sucesso: {data} {periodo}")
    except Exception as e:
        logger.error(f"Erro ao salvar relatório: {e}")

def gerar_relatorio_agendado(periodo):
    """Função chamada pelo agendador: gera relatório do dia atual e período informado"""
    data_hoje = agora_gmt4().strftime('%d/%m/%Y')
    logger.info(f"Gerando relatório agendado: {data_hoje} - {periodo}")
    salvar_relatorio(data=data_hoje, periodo=periodo)

def agendar_tarefas():
    """Agenda as tarefas de geração de relatórios usando APScheduler com timezone GMT-4"""
    scheduler = BackgroundScheduler(timezone=TZ_CAMPO_GRANDE)
    
    # Segunda-feira 13h45 (GMT-4) → período vespertino da segunda
    scheduler.add_job(gerar_relatorio_agendado, 'cron', day_of_week='mon', hour=13, minute=45,
                      kwargs={'periodo': 'VESPERTINO'})
    
    # Terça-feira 8h10 (GMT-4) → período matutino da terça
    scheduler.add_job(gerar_relatorio_agendado, 'cron', day_of_week='tue', hour=8, minute=10,
                      kwargs={'periodo': 'MATUTINO'})
    # Terça-feira 13h15 (GMT-4) → período vespertino da terça
    scheduler.add_job(gerar_relatorio_agendado, 'cron', day_of_week='tue', hour=13, minute=15,
                      kwargs={'periodo': 'VESPERTINO'})
    
    # Quarta-feira 8h10 (GMT-4) → período matutino da quarta
    scheduler.add_job(gerar_relatorio_agendado, 'cron', day_of_week='wed', hour=8, minute=10,
                      kwargs={'periodo': 'MATUTINO'})
    # Quarta-feira 13h15 (GMT-4) → período vespertino da quarta
    scheduler.add_job(gerar_relatorio_agendado, 'cron', day_of_week='wed', hour=13, minute=15,
                      kwargs={'periodo': 'VESPERTINO'})
     # Quinta-feira 8h10 (GMT-4) → período matutino da quinta
    scheduler.add_job(gerar_relatorio_agendado, 'cron', day_of_week='thu', hour=8, minute=10,
                      kwargs={'periodo': 'MATUTINO'})
    
    # Sexta-feira 13h15 (GMT-4) → período vespertino da sexta
    scheduler.add_job(gerar_relatorio_agendado, 'cron', day_of_week='fri', hour=13, minute=15,
                      kwargs={'periodo': 'VESPERTINO'})
    
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
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
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
        
        conn = get_db()
        cursor = conn.cursor()
        
        for aud in audiencias:
            cursor.execute('''
                INSERT INTO inscricoes (nome, data_audiencia, horario_audiencia, processo_audiencia)
                VALUES (%s, %s, %s, %s)
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
        conn = get_db()
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
