import os
import time
import json
import requests

API_URL = "https://api.github.com/graphql"

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
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "lab01s01-script"
    }
    payload = {"query": QUERY_10, "variables": {"after": after}}

    max_tries = 12
    for attempt in range(1, max_tries + 1):
        r = requests.post(API_URL, json=payload, headers=headers, timeout=60)

        if r.status_code in (502, 503, 504):
            wait = min(60, 5 * attempt)
            print(f"[{r.status_code}] GitHub instável. Retry em {wait}s (tentativa {attempt}/{max_tries})")
            time.sleep(wait)
            continue

        if r.status_code == 403:
            print("[403] Possível rate limit. Esperando 60s...")
            time.sleep(60)
            continue

        if r.status_code != 200:
            print("Status:", r.status_code)
            print("Resposta:", r.text[:1000])
            r.raise_for_status()

        data = r.json()

        if "errors" in data:
            wait = min(60, 5 * attempt)
            print("Erros GraphQL:", data["errors"])
            print(f"Retry em {wait}s...")
            time.sleep(wait)
            continue

        return data["data"]["search"]

    raise RuntimeError("Falha após várias tentativas.")

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN não encontrado. Configure a variável de ambiente e reabra o VSCode.")

    all_nodes = []
    after = None

    print("[Lab01S01] Coletando 100 repositórios (10x10) com todas as métricas...")

    for page in range(10):  # 10*10 = 100
        print(f"[Lab01S01] Página {page+1}/10...")
        search = post_graphql(token, after)
        all_nodes.extend(search["nodes"])
        after = search["pageInfo"]["endCursor"]
        time.sleep(2)

    output = {
        "total_repos": len(all_nodes),
        "query": "stars:>0 sort:stars-desc",
        "nodes": all_nodes
    }

    out_file = "lab01s01_100_repos.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Concluído! Salvo em: {out_file}")

if __name__ == "__main__":
    main()