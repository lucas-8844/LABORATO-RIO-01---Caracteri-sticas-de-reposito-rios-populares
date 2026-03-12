import os
import time
import csv
import json
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

API_URL = "https://api.github.com/graphql"

# =========================
# FASE A: Search LEVE (lista base de repos)
# =========================
QUERY_SEARCH_25_LIGHT = """
query SearchTopReposLight($after: String) {
  search(
    query: "stars:>0 sort:stars-desc",
    type: REPOSITORY,
    first: 25,
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
      }
    }
  }
}
"""

def build_details_query(batch: List[Tuple[str, str]]) -> str:
    parts = []
    for i, (owner, name) in enumerate(batch):
        parts.append(f"""
  r{i}: repository(owner: "{owner}", name: "{name}") {{
    mergedPRs: pullRequests(states: MERGED) {{ totalCount }}
    releases {{ totalCount }}
    openIssues: issues(states: OPEN) {{ totalCount }}
    closedIssues: issues(states: CLOSED) {{ totalCount }}
  }}
""")
    return "query RepoDetailsBatch {\n" + "\n".join(parts) + "\n}\n"

OUT_CSV = "top_1000_repos_github.csv"
CHECKPOINT_FILE = "checkpoint_sprint2.json"
LOCK_FILE = ".run_lock_sprint2"

FIELDNAMES = [
    "nameWithOwner", "url", "stars",
    "createdAt", "updatedAt",
    "age_days", "since_update_days",
    "primary_language",
    "merged_prs", "releases",
    "open_issues", "closed_issues",
    "closed_issues_ratio"
]

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        raise SystemExit(
            f"ERRO: lock encontrado ({LOCK_FILE}).\n"
            "Provável execução duplicada. Pare outras execuções e apague o lock."
        )
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(f"pid={os.getpid()}\n")

def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

def load_checkpoint() -> Dict[str, Any]:
    """
    Checkpoint compatível com versões antigas.
    Novo formato esperado:
      stage: 'search' | 'details'
      after: cursor para Search
      collected_base: quantos repos base já foram coletados (0..1000)
      details_index: índice para preencher detalhes (0..1000)
    """
    # formato padrão novo
    state = {
        "stage": "search",
        "after": None,
        "collected_base": 0,
        "details_index": 0
    }

    if not os.path.exists(CHECKPOINT_FILE):
        return state

    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        old = json.load(f)

    # migração / compatibilidade:
    # - se já for novo formato, só mescla
    # - se for antigo (ex.: {"after":..., "collected":...}), aproveita o que der
    if isinstance(old, dict):
        # stage
        if "stage" in old and old["stage"] in ("search", "details"):
            state["stage"] = old["stage"]

        # after (cursor)
        if "after" in old:
            state["after"] = old["after"]

        # collected_base (novo) OU collected (antigo)
        if "collected_base" in old:
            try:
                state["collected_base"] = int(old["collected_base"])
            except Exception:
                state["collected_base"] = 0
        elif "collected" in old:
            try:
                state["collected_base"] = int(old["collected"])
            except Exception:
                state["collected_base"] = 0

        # details_index
        if "details_index" in old:
            try:
                state["details_index"] = int(old["details_index"])
            except Exception:
                state["details_index"] = 0

    return state

def save_checkpoint(state: Dict[str, Any]):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def ensure_csv_header_if_needed():
    if not os.path.exists(OUT_CSV) or os.path.getsize(OUT_CSV) == 0:
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writeheader()

def read_csv_rows() -> List[Dict[str, Any]]:
    rows = []
    if not os.path.exists(OUT_CSV):
        return rows
    with open(OUT_CSV, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def write_csv_rows(rows: List[Dict[str, Any]]):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

def safe_ratio(open_count: int, closed_count: int) -> Optional[float]:
    total = open_count + closed_count
    return None if total == 0 else (closed_count / total)

def parse_iso(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

def graphql_post(session: requests.Session, token: str, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "lab01s02-script"
    }
    payload = {"query": query, "variables": variables or {}}

    max_tries = 25
    for attempt in range(1, max_tries + 1):
        try:
            r = session.post(API_URL, json=payload, headers=headers, timeout=90)

            if r.status_code in (502, 503, 504):
                wait = min(180, 10 * attempt)
                print(f"[{r.status_code}] Instabilidade. Esperando {wait}s (tentativa {attempt}/{max_tries})")
                time.sleep(wait)
                continue

            if r.status_code == 403:
                print("[403] Possível rate limit. Esperando 60s...")
                time.sleep(60)
                continue

            if r.status_code != 200:
                print("Erro HTTP:", r.status_code)
                print(r.text[:800])
                r.raise_for_status()

            data = r.json()
            if "errors" in data:
                wait = min(180, 10 * attempt)
                print("Erros GraphQL:", data["errors"])
                print(f"Esperando {wait}s...")
                time.sleep(wait)
                continue

            return data["data"]

        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            wait = min(180, 10 * attempt)
            print(f"Erro de conexão: {type(e).__name__}: {e}")
            print(f"Esperando {wait}s...")
            time.sleep(wait)

    raise RuntimeError("Falha após várias tentativas.")

def stage_search_base(session: requests.Session, token: str, state: Dict[str, Any]):
    ensure_csv_header_if_needed()

    after = state.get("after")
    collected = int(state.get("collected_base", 0))
    target = 1000

    now = datetime.now(timezone.utc)

    # Se o CSV já tem linhas e o checkpoint estiver zerado, sincroniza
    existing_rows = read_csv_rows()
    if collected == 0 and len(existing_rows) > 0:
        collected = len(existing_rows)
        state["collected_base"] = collected
        print(f"[FASE A] CSV já possui {collected} linhas. Sincronizando checkpoint...")
        save_checkpoint(state)

    while collected < target:
        page_number = (collected // 25) + 1
        print(f"\n[FASE A - SEARCH LEVE] Página {page_number}/40 (coletados: {collected}/{target})")

        data = graphql_post(session, token, QUERY_SEARCH_25_LIGHT, variables={"after": after})
        search = data["search"]

        batch_rows = []
        for repo in search["nodes"]:
            created = parse_iso(repo["createdAt"])
            updated = parse_iso(repo["updatedAt"])

            age_days = (now - created).days
            since_update_days = (now - updated).days

            lang = repo["primaryLanguage"]["name"] if repo["primaryLanguage"] else None

            batch_rows.append({
                "nameWithOwner": repo["nameWithOwner"],
                "url": repo["url"],
                "stars": repo["stargazerCount"],
                "createdAt": repo["createdAt"],
                "updatedAt": repo["updatedAt"],
                "age_days": age_days,
                "since_update_days": since_update_days,
                "primary_language": lang,
                "merged_prs": "",
                "releases": "",
                "open_issues": "",
                "closed_issues": "",
                "closed_issues_ratio": ""
            })

        # append no CSV
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writerows(batch_rows)

        collected += len(batch_rows)
        after = search["pageInfo"]["endCursor"]

        state["after"] = after
        state["collected_base"] = collected
        save_checkpoint(state)

        time.sleep(2)

    state["stage"] = "details"
    state["details_index"] = int(state.get("details_index", 0))
    save_checkpoint(state)
    print("\n✅ [FASE A] Base dos 1000 repos coletada e salva no CSV!")

