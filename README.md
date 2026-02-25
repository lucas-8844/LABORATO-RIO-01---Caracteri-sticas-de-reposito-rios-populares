# LABORATO-RIO-01---Caracteri-sticas-de-reposito-rios-populares
Principais características de sistemas populares open-source. Vamos analisar como eles são desenvolvidos, com que frequência recebem contribuição externa, com qual frequência lançam releases, entre outras características.

# Lab01S01 – Consulta GraphQL para 100 Repositórios

Este script realiza uma consulta GraphQL na API do GitHub
para coletar 100 repositórios com maior número de estrelas,
incluindo todas as métricas necessárias para responder às RQs.

## Como executar

1. Configurar variável de ambiente:
   setx GITHUB_TOKEN "SEU_TOKEN"

2. Ativar venv:
   .\.venv\Scripts\Activate.ps1

3. Executar:
   python lab01s01_100repos.py

## Saída

- lab01s01_100_repos.json
