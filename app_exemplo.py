from flask import Flask, jsonify
from datetime import datetime, timedelta
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dados de exemplo para demonstração - com mais audiências por dia
DADOS_EXEMPLO = [
    # Dia 28/02/2026 (sexta-feira)
    {'data': '28/02/2026', 'horario': '8:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25228-23.2025'},
    {'data': '28/02/2026', 'horario': '8:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25229-08.2025'},
    {'data': '28/02/2026', 'horario': '9:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25230-90.2025'},
    {'data': '28/02/2026', 'horario': '9:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25231-75.2025'},
    {'data': '28/02/2026', 'horario': '9:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '24932-60.2025'},
    {'data': '28/02/2026', 'horario': '9:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '24937-23.2025'},
    {'data': '28/02/2026', 'horario': '10:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25233-45.2025'},
    {'data': '28/02/2026', 'horario': '10:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25234-30.2025'},
    {'data': '28/02/2026', 'horario': '10:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25235-15.2025'},
    {'data': '28/02/2026', 'horario': '10:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25236-00.2025'},
    
    # Dia 03/03/2026 (segunda-feira)
    {'data': '03/03/2026', 'horario': '8:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25228-23.2025'},
    {'data': '03/03/2026', 'horario': '8:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25229-08.2025'},
    {'data': '03/03/2026', 'horario': '9:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25230-90.2025'},
    {'data': '03/03/2026', 'horario': '9:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25231-75.2025'},
    {'data': '03/03/2026', 'horario': '9:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '24932-60.2025'},
    {'data': '03/03/2026', 'horario': '9:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '24937-23.2025'},
    {'data': '03/03/2026', 'horario': '10:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25233-45.2025'},
    {'data': '03/03/2026', 'horario': '10:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25234-30.2025'},
    {'data': '03/03/2026', 'horario': '10:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25235-15.2025'},
    {'data': '03/03/2026', 'horario': '10:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25236-00.2025'},
    {'data': '03/03/2026', 'horario': '14:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25237-85.2025'},
    {'data': '03/03/2026', 'horario': '14:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25238-70.2025'},
    
    # Dia 04/03/2026 (terça-feira)
    {'data': '04/03/2026', 'horario': '8:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25228-23.2025'},
    {'data': '04/03/2026', 'horario': '8:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25229-08.2025'},
    {'data': '04/03/2026', 'horario': '9:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25230-90.2025'},
    {'data': '04/03/2026', 'horario': '9:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25231-75.2025'},
    {'data': '04/03/2026', 'horario': '9:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '24932-60.2025'},
    {'data': '04/03/2026', 'horario': '9:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '24937-23.2025'},
    {'data': '04/03/2026', 'horario': '10:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25233-45.2025'},
    {'data': '04/03/2026', 'horario': '10:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25234-30.2025'},
    {'data': '04/03/2026', 'horario': '10:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25235-15.2025'},
    {'data': '04/03/2026', 'horario': '10:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25236-00.2025'},
    {'data': '04/03/2026', 'horario': '14:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25237-85.2025'},
    
    # Dia 05/03/2026 (quarta-feira)
    {'data': '05/03/2026', 'horario': '8:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25228-23.2025'},
    {'data': '05/03/2026', 'horario': '8:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25229-08.2025'},
    {'data': '05/03/2026', 'horario': '9:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25230-90.2025'},
    {'data': '05/03/2026', 'horario': '9:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25231-75.2025'},
    {'data': '05/03/2026', 'horario': '9:30', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '24932-60.2025'},
    {'data': '05/03/2026', 'horario': '9:45', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '24937-23.2025'},
    {'data': '05/03/2026', 'horario': '10:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25233-45.2025'},
    {'data': '05/03/2026', 'horario': '10:15', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25234-30.2025'},
    {'data': '05/03/2026', 'horario': '14:00', 'tipo': 'Conciliação em Conhecimento por videoconferência', 'processo': '25237-85.2025'},
]

def is_weekday(date):
    """Verifica se é dia útil (segunda a sexta)"""
    return date.weekday() < 5

def get_next_weekdays(num_days=3):
    """Retorna os próximos N dias úteis"""
    weekdays = []
    current_date = datetime.now()
    
    # Se hoje não é dia útil, começar pelo próximo
    if not is_weekday(current_date):
        current_date += timedelta(days=1)
        while not is_weekday(current_date):
            current_date += timedelta(days=1)
    
    while len(weekdays) < num_days:
        if is_weekday(current_date):
            weekdays.append(current_date)
        current_date += timedelta(days=1)
    
    return weekdays

def format_date(date):
    """Formata data para dd/mm/yyyy"""
    return date.strftime('%d/%m/%Y')

def buscar_pauta():
    """Busca a pauta de audiências dos próximos 3 dias"""
    try:
        # Obter os próximos 3 dias úteis
        weekdays = get_next_weekdays(3)
        datas_esperadas = [format_date(d) for d in weekdays]
        
        logger.info(f"Dias úteis esperados: {datas_esperadas}")
        
        # Filtrar dados de exemplo para os próximos 3 dias úteis
        pautas = []
        for pauta in DADOS_EXEMPLO:
            if pauta['data'] in datas_esperadas:
                # Verificar se o horário termina em 1
                horario = pauta['horario']
                if ':' in horario:
                    partes = horario.split(':')
                    if len(partes) > 1:
                        minutos = partes[1]
                        if minutos.endswith('1'):
                            logger.info(f"Horário {horario} excluído (termina em 1)")
                            continue
                
                pautas.append(pauta)
                logger.info(f"✓ Adicionado: {pauta['data']} {horario} - {pauta['processo']}")
        
        logger.info(f"Total de pautas encontradas: {len(pautas)}")
        return pautas
        
    except Exception as e:
        logger.error(f"Erro ao buscar pauta: {e}")
        return []

@app.route('/')
def index():
    """Serve a página principal"""
    with open('/home/ubuntu/vara-trabalho-paranaiba/index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/pauta')
def api_pauta():
    """API que retorna a pauta em JSON"""
    try:
        pautas = buscar_pauta()
        return jsonify({
            'sucesso': True,
            'data': datetime.now().isoformat(),
            'pautas': pautas,
            'total': len(pautas)
        })
    except Exception as e:
        logger.error(f"Erro na API: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'pautas': []
        }), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve arquivos estáticos"""
    import os
    file_path = os.path.join('/home/ubuntu/vara-trabalho-paranaiba', filename)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return f.read()
    return 'Not found', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
