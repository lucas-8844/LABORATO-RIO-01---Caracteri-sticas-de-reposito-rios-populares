# Características de Repositórios Populares no GitHub (Sprint 2)

## Autores
Lucas Carvalho e Matheus Pretti.

## Introdução
Este trabalho analisa características de desenvolvimento e manutenção dos 1.000 repositórios open-source com maior número de estrelas no GitHub, buscando entender padrões de maturidade, contribuição externa, releases, atualização, linguagens predominantes e fechamento de issues.

## Questões de Pesquisa e Hipóteses Informais

**RQ01. Sistemas populares são maduros/antigos?**  
- Métrica: idade do repositório (data atual - createdAt)  
- Hipótese: repositórios populares tendem a ser mais antigos/maduros.

**RQ02. Sistemas populares recebem muita contribuição externa?**  
- Métrica: total de pull requests aceitas (MERGED)  
- Hipótese: projetos populares recebem muitas PRs aceitas por terem grande comunidade.

**RQ03. Sistemas populares lançam releases com frequência?**  
- Métrica: total de releases  
- Hipótese: projetos populares tendem a ter vários releases ao longo do tempo.

**RQ04. Sistemas populares são atualizados com frequência?**  
- Métrica: tempo até a última atualização (data atual - updatedAt)  
- Hipótese: projetos populares são mantidos ativamente, então a última atualização tende a ser recente.

**RQ05. Sistemas populares são escritos nas linguagens mais populares?**  
- Métrica: linguagem primária (primaryLanguage)  
- Hipótese: JavaScript/TypeScript/Python (e outras linguagens comuns) devem ser predominantes.

**RQ06. Sistemas populares possuem alto percentual de issues fechadas?**  
- Métrica: closedIssues / (openIssues + closedIssues)  
- Hipótese: projetos populares tendem a fechar a maior parte das issues (razão > 0,5).

## Objetivo
Coletar dados via API GraphQL do GitHub para os 1.000 repositórios mais estrelados e preparar a base para análise estatística (medianas e contagens), permitindo responder às RQs.

## Metodologia
1. Foi utilizada a API GraphQL do GitHub com uma query manual contendo as métricas necessárias.
2. A coleta foi automatizada via script Python que realiza requisições HTTP POST, autenticação por token e paginação por cursor (endCursor).
3. Para reduzir instabilidades (ex.: erros 502), a coleta foi feita em páginas menores (25 repositórios por requisição).
4. Os dados foram armazenados em arquivo CSV contendo métricas brutas e métricas derivadas (idade em dias, dias desde atualização e razão de issues fechadas).

## Resultados (Sprint 2)
Nesta sprint foi gerado o dataset em CSV com 1.000 repositórios.  
(As medianas, contagens por linguagem e discussão detalhada serão feitas na próxima etapa/sprint.)

## Discussões (insights iniciais)
- A automação com paginação é necessária devido aos limites/instabilidades da API.
- O dataset em CSV viabiliza calcular medianas e contagens posteriormente de forma reprodutível.

## Conclusão
A Sprint 2 entregou a coleta automatizada dos 1.000 repositórios e a geração do arquivo CSV, além da primeira versão do relatório com hipóteses informais e metodologia.