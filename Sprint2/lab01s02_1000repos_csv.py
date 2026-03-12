# Importa módulos para manipulação do sistema operacional
import os

# Usado para controlar tempo de espera entre requisições
import time

# Biblioteca para leitura e escrita de arquivos CSV
import csv

# Biblioteca para leitura e escrita de arquivos JSON
import json

# Biblioteca usada para fazer requisições HTTP (API do GitHub)
import requests

# Utilizada para trabalhar com datas e fusos horários
from datetime import datetime, timezone

# Tipagem para deixar o código mais claro
from typing import List, Dict, Any, Optional, Tuple


# URL da API GraphQL do GitHub
API_URL = "https://api.github.com/graphql"


# =========================
# FASE A: Search LEVE (lista base de repos)
# =========================

# Query GraphQL que busca os repositórios mais populares do GitHub
# ordenados pelo número de estrelas
QUERY_SEARCH_25_LIGHT = """
query SearchTopReposLight($after: String) {
  search(
    query: "stars:>0 sort:stars-desc", # busca repos com mais estrelas
    type: REPOSITORY,
    first: 25,                         # retorna 25 repositórios por página
    after: $after                      # cursor de paginação
  ) {
    pageInfo { hasNextPage endCursor } # informações para continuar a paginação
    nodes {
      ... on Repository {
        nameWithOwner                  # nome completo do repo (owner/repo)
        url                            # URL do repositório
        stargazerCount                 # número de estrelas
        createdAt                      # data de criação
        updatedAt                      # data da última atualização
        primaryLanguage { name }       # linguagem principal
      }
    }
  }
}
"""


# Função que constrói dinamicamente uma query GraphQL para buscar
# detalhes de vários repositórios em uma única requisição
def build_details_query(batch: List[Tuple[str, str]]) -> str:

    parts = []

    # Percorre o lote de repositórios
    for i, (owner, name) in enumerate(batch):

        # Cria uma query com alias (r0, r1, r2...)
        parts.append(f"""
  r{i}: repository(owner: "{owner}", name: "{name}") {{
    mergedPRs: pullRequests(states: MERGED) {{ totalCount }}   # PRs mergeados
    releases {{ totalCount }}                                  # número de releases
    openIssues: issues(states: OPEN) {{ totalCount }}          # issues abertas
    closedIssues: issues(states: CLOSED) {{ totalCount }}      # issues fechadas
  }}
""")

    # Junta todas as queries em uma única requisição GraphQL
    return "query RepoDetailsBatch {\n" + "\n".join(parts) + "\n}\n"


# Nome do arquivo CSV que armazenará os dados finais
OUT_CSV = "top_1000_repos_github.csv"

# Arquivo de checkpoint que guarda o progresso do script
CHECKPOINT_FILE = "checkpoint_sprint2.json"

# Arquivo usado como lock para evitar execução duplicada
LOCK_FILE = ".run_lock_sprint2"


# Colunas que existirão no CSV
FIELDNAMES = [
    "nameWithOwner", "url", "stars",
    "createdAt", "updatedAt",
    "age_days", "since_update_days",
    "primary_language",
    "merged_prs", "releases",
    "open_issues", "closed_issues",
    "closed_issues_ratio"
]


# Função que cria um lock para impedir duas execuções simultâneas
def acquire_lock():

    # Se o arquivo de lock já existir, significa que o script já está rodando
    if os.path.exists(LOCK_FILE):
        raise SystemExit(
            f"ERRO: lock encontrado ({LOCK_FILE}).\n"
            "Provável execução duplicada. Pare outras execuções e apague o lock."
        )

    # Cria o arquivo de lock com o PID do processo
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(f"pid={os.getpid()}\n")


# Remove o arquivo de lock ao finalizar o script
def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


# Carrega o checkpoint salvo anteriormente
def load_checkpoint() -> Dict[str, Any]:

    # Estado padrão
    state = {
        "stage": "search",      # fase atual
        "after": None,          # cursor da paginação
        "collected_base": 0,    # quantos repos já foram coletados
        "details_index": 0      # índice para preencher detalhes
    }

    # Se não existir checkpoint, retorna estado padrão
    if not os.path.exists(CHECKPOINT_FILE):
        return state

    # Lê o checkpoint
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        old = json.load(f)

    # Compatibilidade com versões antigas
    if isinstance(old, dict):

        if "stage" in old and old["stage"] in ("search", "details"):
            state["stage"] = old["stage"]

        if "after" in old:
            state["after"] = old["after"]

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

        if "details_index" in old:
            try:
                state["details_index"] = int(old["details_index"])
            except Exception:
                state["details_index"] = 0

    return state


# Salva o checkpoint
def save_checkpoint(state: Dict[str, Any]):

    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# Cria o cabeçalho do CSV se ele ainda não existir
def ensure_csv_header_if_needed():

    if not os.path.exists(OUT_CSV) or os.path.getsize(OUT_CSV) == 0:

        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writeheader()


# Lê todas as linhas do CSV
def read_csv_rows() -> List[Dict[str, Any]]:

    rows = []

    if not os.path.exists(OUT_CSV):
        return rows

    with open(OUT_CSV, "r", newline="", encoding="utf-8") as f:

        r = csv.DictReader(f)

        for row in r:
            rows.append(row)

    return rows


# Reescreve todas as linhas no CSV
def write_csv_rows(rows: List[Dict[str, Any]]):

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:

        w = csv.DictWriter(f, fieldnames=FIELDNAMES)

        w.writeheader()
        w.writerows(rows)


# Calcula a proporção de issues fechadas
def safe_ratio(open_count: int, closed_count: int) -> Optional[float]:

    total = open_count + closed_count

    return None if total == 0 else (closed_count / total)


# Converte uma string ISO para objeto datetime
def parse_iso(date_str: str) -> datetime:

    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


# Função responsável por enviar requisições para a API GraphQL
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

            # Tratamento de erros temporários da API
            if r.status_code in (502, 503, 504):
                wait = min(180, 10 * attempt)
                print(f"[{r.status_code}] Instabilidade. Esperando {wait}s")
                time.sleep(wait)
                continue

            # Tratamento de rate limit
            if r.status_code == 403:
                print("[403] Possível rate limit. Esperando 60s...")
                time.sleep(60)
                continue

            if r.status_code != 200:
                print("Erro HTTP:", r.status_code)
                r.raise_for_status()

            data = r.json()

            # Caso a API retorne erros GraphQL
            if "errors" in data:
                wait = min(180, 10 * attempt)
                print("Erros GraphQL:", data["errors"])
                time.sleep(wait)
                continue

            return data["data"]

        except requests.exceptions.RequestException as e:

            wait = min(180, 10 * attempt)
            print(f"Erro de conexão: {e}")
            time.sleep(wait)

    raise RuntimeError("Falha após várias tentativas.")


# =========================
# FASE A - Coleta dos 1000 repositórios
# =========================
def stage_search_base(session: requests.Session, token: str, state: Dict[str, Any]):

    ensure_csv_header_if_needed()

    after = state.get("after")
    collected = int(state.get("collected_base", 0))

    target = 1000

    now = datetime.now(timezone.utc)

    while collected < target:

        print(f"Coletados {collected}/{target}")

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

        # adiciona no CSV
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:

            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writerows(batch_rows)

        collected += len(batch_rows)
        after = search["pageInfo"]["endCursor"]

        state["after"] = after
        state["collected_base"] = collected

        save_checkpoint(state)

        time.sleep(2)


# =========================
# FASE B - Coleta métricas detalhadas
# =========================
def stage_fill_details(session: requests.Session, token: str, state: Dict[str, Any]):

    rows = read_csv_rows()

    total = len(rows)

    idx = int(state.get("details_index", 0))

    while idx < total:

        batch_rows = rows[idx:idx+10]

        batch_repos = []

        for r in batch_rows:

            if "/" not in r["nameWithOwner"]:
                continue

            owner, name = r["nameWithOwner"].split("/", 1)

            batch_repos.append((owner, name))

        q = build_details_query(batch_repos)

        data = graphql_post(session, token, q)

        for i in range(len(batch_repos)):

            key = f"r{i}"

            details = data.get(key)

            if details is None:
                continue

            merged_prs = details["mergedPRs"]["totalCount"]
            releases = details["releases"]["totalCount"]
            open_issues = details["openIssues"]["totalCount"]
            closed_issues = details["closedIssues"]["totalCount"]

            ratio = safe_ratio(open_issues, closed_issues)

            rows[idx + i]["merged_prs"] = merged_prs
            rows[idx + i]["releases"] = releases
            rows[idx + i]["open_issues"] = open_issues
            rows[idx + i]["closed_issues"] = closed_issues
            rows[idx + i]["closed_issues_ratio"] = "" if ratio is None else ratio

        idx += len(batch_rows)

        state["details_index"] = idx

        save_checkpoint(state)

        write_csv_rows(rows)

        time.sleep(2)


# Função principal do programa
def main():

    acquire_lock()

    try:

        print("Sprint2 iniciado")

        # Obtém o token da variável de ambiente
        token = os.getenv("GITHUB_TOKEN")

        if not token:
            print("ERRO: GITHUB_TOKEN não encontrado.")
            return

        state = load_checkpoint()

        save_checkpoint(state)

        session = requests.Session()

        # executa fase A
        if state.get("stage") == "search":
            stage_search_base(session, token, state)
            state = load_checkpoint()

        # executa fase B
        if state.get("stage") == "details":
            stage_fill_details(session, token, state)

        print("Sprint2 finalizada")

    finally:

        release_lock()


# Executa o script se for chamado diretamente
if __name__ == "__main__":
    main()
