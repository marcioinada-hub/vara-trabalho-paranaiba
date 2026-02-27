# Vara do Trabalho de Paranaíba - Sistema de Inscrição em Audiências

Sistema web para que acadêmicos de Direito possam se inscrever para assistir audiências na Vara do Trabalho de Paranaíba.

## 🎯 Funcionalidades

- **Pauta Dinâmica:** Exibe audiências dos próximos 3 dias úteis
- **Inscrição em Audiências:** Acadêmicos podem se inscrever em até 3 audiências
- **Acesso via Zoom:** Informações de acesso à audiência por videoconferência
- **Painel Administrativo:** Visualização de relatórios de inscrições (protegido por senha)
- **Relatórios Automáticos:** Gerados automaticamente às 8h20 e 13h15 diariamente

## 📋 Requisitos

- Python 3.11+
- Flask
- SQLite (incluído no Python)

## 🚀 Como Instalar Localmente

1. Clone o repositório:
```bash
git clone https://github.com/marcioinada-hub/vara-trabalho-paranaiba.git
cd vara-trabalho-paranaiba
```

2. Crie um ambiente virtual:
```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute a aplicação:
```bash
python app.py
```

5. Acesse no navegador:
- Página principal: http://localhost:8000
- Painel admin: http://localhost:8000/admin
- Senha admin: `admin123`

## 🌐 Deploy no Render.com (Gratuito)

### Passo 1: Criar Conta no Render
1. Acesse https://render.com
2. Clique em "Sign up"
3. Conecte sua conta GitHub

### Passo 2: Conectar Repositório
1. No Render, clique em "New +"
2. Selecione "Web Service"
3. Conecte seu repositório GitHub
4. Selecione este repositório

### Passo 3: Configurar Deploy
1. **Name:** vara-trabalho-paranaiba
2. **Environment:** Python 3
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `python app.py`
5. **Plan:** Free

### Passo 4: Deploy
1. Clique em "Create Web Service"
2. Aguarde o deploy (2-3 minutos)
3. Seu site estará disponível em: `https://vara-trabalho-paranaiba.onrender.com`

## 📊 Estrutura do Projeto

```
vara-trabalho-paranaiba/
├── app.py                 # Aplicação Flask principal
├── index.html            # Página principal (HTML/CSS/JS)
├── requirements.txt      # Dependências Python
├── Procfile             # Configuração para deploy
├── render.yaml          # Configuração do Render
├── inscricoes.db        # Banco de dados SQLite
└── README.md            # Este arquivo
```

## 🔐 Segurança

- Senha do admin: `admin123` (altere em produção)
- Banco de dados SQLite armazenado localmente
- Sessões protegidas com chave secreta

## 📝 Notas Importantes

- A pauta é atualizada automaticamente a cada acesso
- Relatórios são gerados às 8h20 e 13h15 (horário do servidor)
- Acadêmicos podem se inscrever em até 3 audiências
- Inscrição deve ser feita 30 minutos antes da primeira audiência

## 👨‍💼 Contato

Para dúvidas ou sugestões, entre em contato com a administração da Vara do Trabalho de Paranaíba.

---

**Desenvolvido com ❤️ para facilitar o aprendizado prático de Direito**
