#!/usr/bin/env python3
"""
Script para buscar a pauta de audiências da Vara do Trabalho de Paranaíba
dos próximos 5 dias úteis, excluindo horários terminados em 1.
Extrai dados dos CARDS de audiência, não de tabelas.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import time
import logging
import json
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_weekday(date):
    """Verifica se a data é um dia útil (segunda a sexta)"""
    return date.weekday() < 5  # 0-4 = segunda a sexta

def get_next_weekdays(num_days=5):
    """Retorna os próximos N dias úteis"""
    weekdays = []
    current_date = datetime.now()
    
    while len(weekdays) < num_days:
        if is_weekday(current_date):
            weekdays.append(current_date)
        current_date += timedelta(days=1)
    
    return weekdays

def extrair_dados_cards(driver, data_str):
    """Extrai dados dos cards de audiência"""
    try:
        logger.info(f"Extraindo dados dos cards para {data_str}...")
        
        pautas_dia = []
        
        # Procurar por elementos que contêm "Índice" (indicador de um card)
        # Os cards parecem ter a estrutura: Índice, Horário, Tipo, Processo, Sala, Situação
        
        # Tentar encontrar todos os divs que contêm os dados
        page_source = driver.page_source
        
        # Procurar por padrões de Índice seguido de dados
        # Padrão: "Índice\nHorário\n<horario>\nTipo\n<tipo>\nProcesso\n<processo>"
        
        # Usar regex para encontrar os cards
        # Procurar por "Índice" seguido de números
        indices = re.findall(r'Índice\s*(\d+)', page_source)
        logger.info(f"Encontrados {len(indices)} cards de audiência")
        
        if len(indices) == 0:
            logger.info("Nenhum card encontrado, tentando extrair via JavaScript...")
            # Tentar extrair via JavaScript
            result = driver.execute_script("""
                const cards = [];
                const pageText = document.body.innerText;
                const lines = pageText.split('\\n');
                
                let currentCard = null;
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    
                    if (line.startsWith('Índice') && !isNaN(lines[i+1]?.trim())) {
                        if (currentCard) {
                            cards.push(currentCard);
                        }
                        currentCard = {
                            indice: lines[i+1]?.trim(),
                            horario: '',
                            tipo: '',
                            processo: '',
                            sala: '',
                            situacao: ''
                        };
                    } else if (currentCard) {
                        if (line.startsWith('Horário') && lines[i+1]) {
                            currentCard.horario = lines[i+1].trim();
                        } else if (line.startsWith('Tipo') && lines[i+1]) {
                            currentCard.tipo = lines[i+1].trim();
                        } else if (line.startsWith('Processo') && lines[i+1]) {
                            currentCard.processo = lines[i+1].trim();
                        } else if (line.startsWith('Sala') && lines[i+1]) {
                            currentCard.sala = lines[i+1].trim();
                        } else if (line.startsWith('Situação') && lines[i+1]) {
                            currentCard.situacao = lines[i+1].trim();
                        }
                    }
                }
                
                if (currentCard) {
                    cards.push(currentCard);
                }
                
                return cards;
            """)
            
            logger.info(f"JavaScript extraiu {len(result)} cards")
            
            for card in result:
                horario = card.get('horario', '')
                tipo = card.get('tipo', '')
                processo = card.get('processo', '')
                sala = card.get('sala', '')
                situacao = card.get('situacao', '')
                
                # Filtrar horários terminados em 1
                if horario:
                    minutos = horario.split(':')[-1] if ':' in horario else ''
                    if minutos.endswith('1'):
                        logger.info(f"Horário {horario} excluído (termina em 1)")
                        continue
                
                if horario and processo:
                    pauta_item = {
                        'data': data_str,
                        'horario': horario,
                        'tipo': tipo,
                        'processo': processo,
                        'sala': sala,
                        'situacao': situacao
                    }
                    pautas_dia.append(pauta_item)
                    logger.info(f"✓ Adicionado: {horario} - {processo}")
        
        return pautas_dia
        
    except Exception as e:
        logger.error(f"Erro ao extrair dados dos cards: {e}")
        import traceback
        traceback.print_exc()
        return []

def buscar_pauta_completa():
    """Busca a pauta completa para os próximos 5 dias úteis"""
    try:
        # Configurar opções do Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=options)
        logger.info("Navegador iniciado")
        
        driver.get('https://pje.trt24.jus.br/consultaprocessual/pautas')
        logger.info("Página carregada")
        
        # Aguardar carregamento da página
        wait = WebDriverWait(driver, 10)
        time.sleep(2)
        
        # PASSO 1: 1° Grau já está selecionado por padrão
        logger.info("1° Grau já está selecionado por padrão")
        
        # PASSO 2: Selecionar a Vara do Trabalho de Paranaíba
        logger.info("Selecionando Vara do Trabalho de Paranaíba...")
        select_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[role="combobox"]')))
        select_field.click()
        time.sleep(1)
        
        # Procurar e clicar na opção Paranaíba
        options_list = driver.find_elements(By.CSS_SELECTOR, '[role="option"]')
        logger.info(f"Encontradas {len(options_list)} opções")
        
        paranaiba_encontrada = False
        for option in options_list:
            option_text = option.text
            if 'Paranaíba' in option_text:
                logger.info(f"Selecionando: {option_text}")
                option.click()
                paranaiba_encontrada = True
                break
        
        if not paranaiba_encontrada:
            logger.error("Vara do Trabalho de Paranaíba não encontrada!")
            driver.quit()
            return []
        
        time.sleep(1)
        
        # PASSO 3: Obter os próximos 5 dias úteis
        weekdays = get_next_weekdays(5)
        logger.info(f"Dias úteis para buscar: {[d.strftime('%d/%m/%Y') for d in weekdays]}")
        
        # PASSO 4: Buscar pauta para cada dia útil
        todas_pautas = []
        
        for dia in weekdays:
            data_str = dia.strftime('%d/%m/%Y')
            logger.info(f"\n=== Buscando pauta para {data_str} ===")
            
            try:
                # Limpar o campo de data
                input_field = driver.find_element(By.ID, 'mat-input-0')
                input_field.clear()
                time.sleep(0.5)
                
                # Digitar a data
                input_field.send_keys(data_str)
                logger.info(f"Data digitada: {data_str}")
                time.sleep(1)
                
                # Clicar em Pesquisar
                search_button = driver.find_element(By.ID, 'btnPesquisar')
                search_button.click()
                logger.info("Botão Pesquisar clicado")
                
                # Aguardar a página carregar
                time.sleep(3)
                
                # Extrair dados dos cards
                pautas_dia = extrair_dados_cards(driver, data_str)
                todas_pautas.extend(pautas_dia)
                
            except Exception as e:
                logger.error(f"Erro ao buscar pauta para {data_str}: {e}")
        
        driver.quit()
        logger.info(f"\n=== RESUMO ===")
        logger.info(f"Total de pautas encontradas: {len(todas_pautas)}")
        
        return todas_pautas
        
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    pautas = buscar_pauta_completa()
    print(json.dumps(pautas, indent=2, ensure_ascii=False))
