import os
import time
import json
import requests

# Endpoint da API GraphQL do GitHub
API_URL = "https://api.github.com/graphql"

# Query GraphQL:
# - Usa "search" para buscar repositórios ordenados por estrelas (mais populares primeiro)
# - first: 10  -> vamos paginar 10 páginas para totalizar 100 repositórios
# - after: cursor de paginação
# Métricas coletadas (para responder às RQs):
# - createdAt (idade)
# - updatedAt (tempo desde última atualização)
# - pullRequests MERGED (PRs aceitas)
# - releases (total de releases)
# - primaryLanguage (linguagem primária)
# - issues OPEN e CLOSED (razão de issues fechadas)
QUERY_10 = """
query TopStarredRepos10($after: String) {
  search(
    query: "stars:>0 sort:stars-desc",
    type: REPOSITORY,
    first: 10,
    after: $after
  ) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on Repository {
        nameWithOwner
        url
        stargazerCount
        createdAt
        updatedAt
        primaryLanguage { name }
        mergedPRs: pullRequests(states: MERGED) { totalCount }
        releases { totalCount }
        openIssues: issues(states: OPEN) { totalCount }
        closedIssues: issues(states: CLOSED) { totalCount }
      }
    }
  }
}
"""

def post_graphql(token, after):
    """
    Faz uma requisição HTTP POST para a API GraphQL do GitHub
    usando a query acima e o cursor de paginação (after).
    
    Inclui estratégia de retry para lidar com instabilidades (502/503/504)
    e possíveis rate limits (403).
    """
    # Cabeçalhos HTTP:
    # - Authorization com token (Bearer)
    # - Content-Type JSON
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "lab01s01-script"
    }

    # Corpo da requisição GraphQL:
    # - query: string GraphQL
    # - variables: dicionário com o cursor "after"
    payload = {"query": QUERY_10, "variables": {"after": after}}

    # Número máximo de tentativas em caso de falha
    max_tries = 12

    # Loop de tentativas (retry)
    for attempt in range(1, max_tries + 1):
        # Faz o POST para a API do GitHub
        r = requests.post(API_URL, json=payload, headers=headers, timeout=60)

        # 502/503/504: instabilidade do GitHub (Bad Gateway/Service Unavailable/Gateway Timeout)
        # Vamos esperar e tentar novamente com espera progressiva
        if r.status_code in (502, 503, 504):
            wait = min(60, 5 * attempt)  # 5s, 10s, 15s... até 60s
            print(f"[{r.status_code}] GitHub instável. Retry em {wait}s (tentativa {attempt}/{max_tries})")
            time.sleep(wait)
            continue

        # 403: pode ocorrer por rate limit
        # Esperamos 60s e tentamos novamente
        if r.status_code == 403:
            print("[403] Possível rate limit. Esperando 60s...")
            time.sleep(60)
            continue

        # Qualquer status diferente de 200 (OK) é tratado como erro
        if r.status_code != 200:
            print("Status:", r.status_code)
            print("Resposta:", r.text[:1000])  # mostra o começo do erro para debug
            r.raise_for_status()

        # Converte o JSON retornado pela API
        data = r.json()

        # Caso o GraphQL retorne "errors" mesmo com status 200
        if "errors" in data:
            wait = min(60, 5 * attempt)
            print("Erros GraphQL:", data["errors"])
            print(f"Retry em {wait}s...")
            time.sleep(wait)
            continue

        # Retorna somente o bloco "search" que contém pageInfo e nodes
        return data["data"]["search"]

    # Se todas as tentativas falharem, encerramos com erro
    raise RuntimeError("Falha após várias tentativas.")

def main():
    """
    Fluxo principal do Lab01S01:
    - Lê o token do ambiente (GITHUB_TOKEN)
    - Faz 10 requisições (10 repos por página) = 100 repositórios
    - Junta tudo e salva em JSON
    """
    # Lê o token configurado no sistema (variável de ambiente)
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN não encontrado. Configure a variável de ambiente e reabra o VSCode.")

    # Lista para armazenar os 100 repositórios coletados
    all_nodes = []

    # Cursor inicial (None = primeira página)
    after = None

    print("[Lab01S01] Coletando 100 repositórios (10x10) com todas as métricas...")

    # Coleta 10 páginas de 10 repositórios
    for page in range(10):  # 10 * 10 = 100
        print(f"[Lab01S01] Página {page+1}/10...")
        search = post_graphql(token, after)

        # Adiciona os 10 repositórios desta página na lista principal
        all_nodes.extend(search["nodes"])

        # Atualiza o cursor para a próxima página
        after = search["pageInfo"]["endCursor"]

        # Pausa pequena para reduzir chance de instabilidade/rate limit
        time.sleep(2)

    # Monta um objeto final para salvar em JSON
    output = {
        "total_repos": len(all_nodes),
        "query": "stars:>0 sort:stars-desc",
        "nodes": all_nodes
    }

    # Salva o arquivo resultado da Sprint1 (Lab01S01)
    out_file = "lab01s01_100_repos.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Concluído! Salvo em: {out_file}")

# Ponto de entrada do script
if __name__ == "__main__":
    main()
