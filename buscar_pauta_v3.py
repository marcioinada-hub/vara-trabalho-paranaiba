#!/usr/bin/env python3
"""
Script para buscar a pauta de audiências da Vara do Trabalho de Paranaíba
dos próximos 5 dias úteis, excluindo horários terminados em 1.
Fluxo: 1° Grau -> Vara do Trabalho de Paranaíba -> Dia por dia
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import time
import logging
import json

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
        
        # PASSO 1: Clicar em "1° Grau" usando radio button
        logger.info("Selecionando 1° Grau...")
        try:
            # Tentar encontrar o input radio para 1° Grau
            primeiro_grau_radio = driver.find_element(By.XPATH, "//input[@type='radio' and @value='1']")
            if not primeiro_grau_radio.is_selected():
                primeiro_grau_radio.click()
                logger.info("1° Grau selecionado via radio button")
            else:
                logger.info("1° Grau já estava selecionado")
        except:
            logger.info("1° Grau já está selecionado por padrão")
        
        time.sleep(1)
        
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
                
                # Aguardar a tabela carregar
                time.sleep(3)
                
                # Extrair dados da tabela
                try:
                    rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
                    logger.info(f"Encontradas {len(rows)} linhas na tabela para {data_str}")
                    
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if len(cells) > 3:
                            horario = cells[1].text.strip() if len(cells) > 1 else ''
                            tipo = cells[2].text.strip() if len(cells) > 2 else ''
                            processo = cells[3].text.strip() if len(cells) > 3 else ''
                            sala = cells[5].text.strip() if len(cells) > 5 else ''
                            situacao = cells[6].text.strip() if len(cells) > 6 else ''
                            
                            # Filtrar horários terminados em 1
                            if horario and processo:
                                # Verificar se o horário termina em 1
                                minutos = horario.split(':')[-1] if ':' in horario else ''
                                if minutos.endswith('1'):
                                    logger.info(f"Horário {horario} excluído (termina em 1)")
                                    continue
                                
                                pauta_item = {
                                    'data': data_str,
                                    'horario': horario,
                                    'tipo': tipo,
                                    'processo': processo,
                                    'sala': sala,
                                    'situacao': situacao
                                }
                                todas_pautas.append(pauta_item)
                                logger.info(f"✓ Adicionado: {horario} - {processo}")
                except Exception as e:
                    logger.error(f"Erro ao extrair dados da tabela: {e}")
                
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
