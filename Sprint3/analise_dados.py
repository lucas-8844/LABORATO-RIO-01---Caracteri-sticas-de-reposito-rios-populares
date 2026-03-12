import os
import pandas as pd
import matplotlib.pyplot as plt

def main():
    print("=== Script de análise iniciado ===")

    # Caminho absoluto baseado na pasta do arquivo atual
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(base_dir, "..", "Sprint2", "top_1000_repos_github.csv")

    print(f"Arquivo CSV esperado em: {csv_file}")

    if not os.path.exists(csv_file):
        print("ERRO: CSV não encontrado nesse caminho.")
        return

    df = pd.read_csv(csv_file)

    print(f"Total de linhas no CSV: {len(df)}")
    print("Colunas encontradas:")
    print(list(df.columns))
    print()

    # Converter colunas numéricas, se necessário
    numeric_cols = [
        "age_days",
        "since_update_days",
        "merged_prs",
        "releases",
        "open_issues",
        "closed_issues",
        "closed_issues_ratio"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =========================
    # RQ01 - Idade
    # =========================
    idade_mediana = df["age_days"].median()
    print("Mediana da idade (dias):", idade_mediana)

    # =========================
    # RQ02 - PRs aceitas
    # =========================
    prs_mediana = df["merged_prs"].median()
    print("Mediana PRs aceitas:", prs_mediana)

    # =========================
    # RQ03 - Releases
    # =========================
    releases_mediana = df["releases"].median()
    print("Mediana releases:", releases_mediana)

    # =========================
    # RQ04 - Última atualização
    # =========================
    update_mediana = df["since_update_days"].median()
    print("Mediana dias desde atualização:", update_mediana)

    # =========================
    # RQ06 - Issues
    # =========================
    issues_ratio_mediana = df["closed_issues_ratio"].median()
    print("Mediana razão issues fechadas:", issues_ratio_mediana)

    # =========================
    # RQ05 - Linguagens
    # =========================
    linguagens = df["primary_language"].value_counts(dropna=False)

    print("\nTop 10 linguagens:")
    print(linguagens.head(10))

    # =========================
    # GRÁFICO 1 - Linguagens
    # =========================
    plt.figure(figsize=(10, 6))
    linguagens.head(10).plot(kind="bar")
    plt.title("Top 10 Linguagens nos Repositórios Populares")
    plt.xlabel("Linguagem")
    plt.ylabel("Quantidade")
    plt.tight_layout()

    linguagens_path = os.path.join(base_dir, "linguagens.png")
    plt.savefig(linguagens_path)
    plt.close()

    # =========================
    # GRÁFICO 2 - Idade
    # =========================
    plt.figure(figsize=(10, 6))
    df["age_days"].dropna().hist(bins=30)
    plt.title("Distribuição da idade dos repositórios")
    plt.xlabel("Dias")
    plt.ylabel("Quantidade")
    plt.tight_layout()

    idade_path = os.path.join(base_dir, "idade_repos.png")
    plt.savefig(idade_path)
    plt.close()

    print("\nGráficos gerados com sucesso:")
    print(f"- {linguagens_path}")
    print(f"- {idade_path}")

    # Salvar resumo em txt para facilitar o relatório
    resumo_path = os.path.join(base_dir, "resumo_analise.txt")
    with open(resumo_path, "w", encoding="utf-8") as f:
        f.write("=== RESULTADOS DA ANÁLISE ===\n\n")
        f.write(f"Total de repositórios: {len(df)}\n")
        f.write(f"Mediana da idade (dias): {idade_mediana}\n")
        f.write(f"Mediana PRs aceitas: {prs_mediana}\n")
        f.write(f"Mediana releases: {releases_mediana}\n")
        f.write(f"Mediana dias desde atualização: {update_mediana}\n")
        f.write(f"Mediana razão issues fechadas: {issues_ratio_mediana}\n\n")
        f.write("Top 10 linguagens:\n")
        for lang, qtd in linguagens.head(10).items():
            f.write(f"{lang}: {qtd}\n")

    print(f"\nResumo salvo em: {resumo_path}")
    print("=== Script finalizado ===")

if __name__ == "__main__":
    main()