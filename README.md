# Automação FIPE — Consulta Automática de Tabela FIPE

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Playwright](https://img.shields.io/badge/Playwright-1.58+-brightgreen.svg)
![Status](https://img.shields.io/badge/Status-Em%20Andamento-yellow.svg)

![Capa do Projeto](https://img.shields.io/badge/Automa%C3%A7%C3%A3o%20FIPE-Consulta%20Autom%C3%A1tica%20de%20Pre%C3%A7os-blue?style=for-the-badge&logo=python&logoColor=white)

---

## Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Status](#status)
- [Funcionalidades](#funcionalidades)
- [Fluxo da Aplicação](#fluxo-da-aplicação)
- [Acesso ao Projeto](#acesso-ao-projeto)
  - [Pré-requisitos](#pré-requisitos)
  - [Instalação](#instalação)
  - [Configuração](#configuração)
  - [Execução](#execução)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Contribuidoras](#contribuidoras)
- [Licença](#licença)

---

## Sobre o Projeto

Automação de consulta à Tabela FIPE integrada à plataforma **Getrak**. O sistema lê uma planilha Excel com placas de veículos, busca no Getrak as informações de marca, modelo e ano de cada veículo, consulta o preço FIPE correspondente e grava os valores de volta na planilha — tudo de forma automatizada.

O projeto utiliza **Playwright** para automação de navegador, **openpyxl** para manipulação de planilhas e um sistema de **cache inteligente** para evitar consultas redundantes à FIPE quando marca, modelo e ano já foram consultados anteriormente.

---

## Status

**Em andamento** — versão `0.1.0`

Próximas melhorias planejadas:
- [ ] Paralelização de consultas FIPE (múltiplas abas simultâneas)
- [ ] Retry exponencial para consultas com falha
- [ ] Logging em arquivo com registro de erros
- [ ] Captura de screenshot em caso de falha para debug visual
- [ ] Testes unitários para funções auxiliares

---

## Funcionalidades

- **Leitura de planilha** — identifica automaticamente placas pendentes (sem valor FIPE preenchido)
- **Consulta Getrak** — login automático e busca de marca, modelo e ano pela placa do veículo
- **Consulta FIPE** — navegação automatizada no site `veiculos.fipe.org.br` com seleção inteligente de modelo/ano
- **Cache de consultas** — evita consultas redundantes combinando marca + modelo + ano como chave
- **Gravação automática** — preenche colunas "FIPE" (valor) e "FIPE REF" (mês de referência) na planilha
- **Salvamento incremental** — salva a planilha após cada placa, preservando progresso em caso de falha
- **Retentativa automática** — reprocessa automaticamente as placas que falharam na primeira rodada
- **Criação de colunas** — adiciona automaticamente as colunas FIPE caso ainda não existam na planilha
- **Relatório de erros** — log detalhado de todas as falhas com linha, placa e motivo

---

## Fluxo da Aplicação

```
Planilha Excel (.xlsx)
        │
        ▼
┌─────────────────┐
│  planilha.py    │  Identifica placas sem FIPE
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  getrak.py      │  Busca marca/modelo/ano pela placa (Playwright)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  fipe.py        │  Consulta preço no site FIPE (Playwright)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  planilha.py    │  Grava FIPE + referência na planilha
└─────────────────┘
```

### Demonstração do Fluxo

```
==================================================
AUTOMAÇÃO FIPE — INÍCIO
==================================================

[1] Carregando planilha...
  47 placa(s) pendente(s) encontrada(s).

[2] Iniciando navegadores...

[3] Fazendo login no Getrak...

[4] Processando 47 placa(s)...

[1/47] Placa: ABC1D23 — linha 2
  [→] Navegando para cadastro — placa: ABC1D23
  [✓] Dados capturados: {'placa': 'ABC1D23', 'marca': 'FORD', 'modelo': 'FIESTA 1.5 16V', 'ano': '2015'}
  [→] Acessando FIPE — FORD / FIESTA 1.5 16V / 2015
  [✓] Resultado FIPE: R$ 41.202,00 — ref: abril de 2026
  [✓] Planilha salva

...

==================================================
RESUMO FINAL
==================================================
  Total processado : 47
  Sucesso          : 45
  Erros finais     : 2
  Consultas em cache usadas: 12 chave(s)
==================================================
```

---

## Acesso ao Projeto

### Pré-requisitos

- Python **3.13+**
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes) ou pip
- [Playwright](https://playwright.dev/) (navegadores)
- Conta ativa no **Getrak** (sistema de rastreamento veicular)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/luizgdemetrio/automacao_fipe.git
cd automacao_fipe

# Instale as dependências com uv
uv sync

# Instale os navegadores do Playwright
uv run playwright install msedge
```

### Configuração

Crie um arquivo `.env` na raiz do projeto com as credenciais do Getrak:

```env
GETRAK_USUARIO=seu_usuario
GETRAK_SENHA=sua_senha
```

Edite o caminho da planilha no arquivo `main_2.py`:

```python
ARQUIVO_PLANILHA = r"C:\caminho\para\sua\planilha.xlsx"
```

A planilha deve possuir uma coluna chamada **"Placa"** na primeira linha (cabeçalho).

### Execução

```bash
uv run main_2.py
```

A planilha será atualizada automaticamente com os valores FIPE e mês de referência.

---

## Estrutura do Projeto

```
automacao_fipe/
├── main_2.py          # Orquestrador principal: integra todos os módulos
├── fipe.py            # Consulta ao site veiculos.fipe.org.br via Playwright
├── getrak.py          # Login e busca de dados do veículo no sistema Getrak
├── planilha.py        # Leitura, manipulação e gravação da planilha Excel
├── pyproject.toml     # Dependências e configuração do projeto
├── .env               # Credenciais (não versionado)
└── .gitignore
```

| Módulo | Responsabilidade |
|--------|-----------------|
| `planilha.py` | Abre o Excel, mapeia colunas, identifica pendências, grava resultados |
| `getrak.py` | Autentica no Getrak, busca marca/modelo/ano pela placa |
| `fipe.py` | Navega no site FIPE, seleciona marca/modelo/ano, captura preço |
| `main_2.py` | Coordena o fluxo completo com cache, retry e relatório de erros |

---

## Tecnologias Utilizadas

<div align="left">

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.58+-2EAD33?style=flat-square&logo=playwright&logoColor=white)
![openpyxl](https://img.shields.io/badge/openpyxl-3.1+-2563EB?style=flat-square&logo=excel&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-3.0+-150458?style=flat-square&logo=pandas&logoColor=white)
![dotenv](https://img.shields.io/badge/python--dotenv-ECD53F?style=flat-square&logo=python&logoColor=black)
![uv](https://img.shields.io/badge/uv-F7B731?style=flat-square&logo=python&logoColor=black)

</div>

---

## Contribuidoras

<!-- Adicione aqui as contribuidoras do projeto -->

| Nome | GitHub | Papel |
|------|--------|-------|
| Luiz Gustavo Demetrio de Sousa | [@luizgdemetrio](https://github.com/luizgdemetrio) | Desenvolvedor principal |

---

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

Copyright (c) 2026 Luiz Gustavo Demetrio de Sousa
