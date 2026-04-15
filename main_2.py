""""""

import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from planilha import (
    carregar_planilha,
    mapear_cabecalhos,
    garantir_colunas_fipe,
    listar_linhas_sem_fipe,
    gravar_fipe,
    salvar_planilha,
)
from getrak import fazer_login, buscar_veiculo
from fipe import consultar_fipe

# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
load_dotenv()

ARQUIVO_PLANILHA = r"C:\Users\Luiz Gustavo\OneDrive - NEXCORP SER. TELECOMUNICAÇÕES S.A\Área de Trabalho\prog\planilhas_google\Recupera360_Novo.xlsx"  # ← ajuste o caminho


# ─────────────────────────────────────────────
# CHAVE DE CACHE
# A chave combina marca + modelo + ano para garantir que variações do mesmo
# modelo em anos diferentes sejam consultadas separadamente.
# Exemplo: "FORD|FIESTA 1.5 16V|2015" e "FORD|FIESTA 1.5 16V|2016"
#          são entradas distintas no cache.
# ─────────────────────────────────────────────
def _chave_cache(marca: str, modelo: str, ano: str) -> str:
    return f"{marca.upper()}|{modelo.upper()}|{ano}"


# ─────────────────────────────────────────────
# PROCESSAMENTO DE UMA PLACA
# ─────────────────────────────────────────────
def processar_placa(pendente: dict, page_getrak, page_fipe, cache: dict) -> dict:
    """
    Executa o fluxo completo para uma placa:
        1. Busca dados no Getrak
        2. Consulta FIPE (ou usa cache se modelo+ano já foi consultado)
        3. Retorna os dados para gravação

    Retorna:
        {
            "linha":      número da linha no Excel,
            "placa":      placa pesquisada,
            "preco":      float,
            "preco_str":  "R$ 41.202,00",
            "referencia": "abril de 2026",
        }
    """
    placa = pendente["placa"]
    linha = pendente["linha"]

    # ── GETRAK ───────────────────────────────────────────────────────────────
    dados_veiculo = buscar_veiculo(page_getrak, placa)
    marca = dados_veiculo["marca"]
    modelo = dados_veiculo["modelo"]
    ano = dados_veiculo["ano"]

    # ── CACHE ────────────────────────────────────────────────────────────────
    chave = _chave_cache(marca, modelo, ano)

    if chave in cache:
        print(f"  [cache] {marca} / {modelo} / {ano} — usando valor em cache")
        dados_fipe = cache[chave]
    else:
        dados_fipe = consultar_fipe(page_fipe, marca, modelo, ano)
        cache[chave] = dados_fipe

    return {
        "linha": linha,
        "placa": placa,
        "preco": dados_fipe["preco"],
        "preco_str": dados_fipe["preco_str"],
        "referencia": dados_fipe["referencia"],
    }


# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────
def executar(
    pendentes: list, page_getrak, page_fipe, wb, ws, cabecalhos: dict, cache: dict
) -> list:
    """
    Itera sobre a lista de pendentes, processa cada um e grava na planilha.
    Retorna a lista de erros ocorridos.

    Cada erro é um dicionário:
        {
            "linha":  número da linha no Excel,
            "placa":  placa que falhou,
            "motivo": mensagem de erro,
        }
    """
    erros = []

    total = len(pendentes)
    for i, pendente in enumerate(pendentes, start=1):
        placa = pendente["placa"]
        linha = pendente["linha"]
        print(f"\n[{i}/{total}] Placa: {placa} — linha {linha}")

        try:
            resultado = processar_placa(pendente, page_getrak, page_fipe, cache)

            gravar_fipe(
                ws,
                cabecalhos,
                resultado["linha"],
                resultado["preco"],
                resultado["referencia"],
            )

            # Salva após cada placa para não perder progresso em caso de falha
            salvar_planilha(wb, ARQUIVO_PLANILHA)

            print(
                f"  [✓] Gravado: {resultado['preco_str']} — {resultado['referencia']}"
            )

        except Exception as e:
            motivo = f"{type(e).__name__}: {e}"
            print(f"  [✗] Erro — {motivo}")
            erros.append(
                {
                    "linha": linha,
                    "placa": placa,
                    "motivo": motivo,
                }
            )

    return erros


# ─────────────────────────────────────────────
# EXIBE O LOG DE ERROS
# ─────────────────────────────────────────────
def exibir_log_erros(erros: list, titulo: str = "LOG DE ERROS"):
    print(f"\n{'=' * 50}")
    print(f"{titulo} ({len(erros)} ocorrência(s))")
    print("=" * 50)
    for e in erros:
        print(f"  Linha {e['linha']:>4} | Placa: {e['placa']:<10} | {e['motivo']}")
    print("=" * 50)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":

    print("=" * 50)
    print("AUTOMAÇÃO FIPE — INÍCIO")
    print("=" * 50)

    # ── PLANILHA ─────────────────────────────────────────────────────────────
    print("\n[1] Carregando planilha...")
    wb, ws = carregar_planilha(ARQUIVO_PLANILHA)
    cabecalhos = mapear_cabecalhos(ws)
    cabecalhos = garantir_colunas_fipe(ws, cabecalhos)
    pendentes = listar_linhas_sem_fipe(ws, cabecalhos)

    print(f"  {len(pendentes)} placa(s) pendente(s) encontrada(s).")

    if not pendentes:
        print("\nNenhuma placa pendente. Encerrando.")
        exit()

    # ── NAVEGADORES ──────────────────────────────────────────────────────────
    print("\n[2] Iniciando navegadores...")

    with sync_playwright() as p:

        # Navegador 1 — Getrak
        navegador_getrak = p.chromium.launch(
            channel="msedge",
            headless=True,
            slow_mo=300,
        )
        page_getrak = navegador_getrak.new_page()

        # Navegador 2 — FIPE
        navegador_fipe = p.chromium.launch(
            channel="msedge",
            headless=True,
            slow_mo=300,
        )
        page_fipe = navegador_fipe.new_page()

        try:
            # Login no Getrak (feito uma única vez)
            print("\n[3] Fazendo login no Getrak...")
            fazer_login(page_getrak)

            # Cache compartilhado entre primeira rodada e retentativa
            cache = {}

            # ── PRIMEIRA RODADA ───────────────────────────────────────────────
            print(f"\n[4] Processando {len(pendentes)} placa(s)...\n")
            erros = executar(
                pendentes, page_getrak, page_fipe, wb, ws, cabecalhos, cache
            )

            # ── RETENTATIVA ───────────────────────────────────────────────────
            if erros:
                exibir_log_erros(erros, titulo="ERROS NA PRIMEIRA RODADA")

                print(f"\n[5] Tentando novamente {len(erros)} placa(s) com erro...")
                pendentes_retry = [
                    {"linha": e["linha"], "placa": e["placa"]} for e in erros
                ]
                erros_finais = executar(
                    pendentes_retry, page_getrak, page_fipe, wb, ws, cabecalhos, cache
                )

                if erros_finais:
                    exibir_log_erros(
                        erros_finais,
                        titulo="ERROS APÓS RETENTATIVA — INTERVENÇÃO MANUAL NECESSÁRIA",
                    )
                else:
                    print("\n[✓] Todas as retentativas foram bem-sucedidas!")
            else:
                erros_finais = []
                print("\n[✓] Nenhum erro encontrado!")

            # ── RESUMO FINAL ──────────────────────────────────────────────────
            total = len(pendentes)
            com_erro = len(erros_finais)
            sucesso = total - com_erro

            print(f"\n{'=' * 50}")
            print("RESUMO FINAL")
            print(f"{'=' * 50}")
            print(f"  Total processado : {total}")
            print(f"  Sucesso          : {sucesso}")
            print(f"  Erros finais     : {com_erro}")
            if cache:
                print(f"  Consultas em cache usadas: {len(cache)} chave(s)")
            print("=" * 50)

        finally:
            navegador_getrak.close()
            navegador_fipe.close()
            print("\nNavegadores encerrados.")
