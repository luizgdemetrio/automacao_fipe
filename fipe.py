""" """

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
URL_FIPE = "https://veiculos.fipe.org.br/"
TIMEOUT = 20_000  # milissegundos

# ─────────────────────────────────────────────
# NOTAS SOBRE A ESTRUTURA DO SITE DA FIPE
# ─────────────────────────────────────────────
# O site usa a biblioteca "Chosen" que transforma <select> nativos em
# componentes visuais customizados. A estratégia correta é:
#   1. Selecionar o valor no <select> nativo via JavaScript (invisível)
#   2. Disparar o evento "change" para ativar a lógica do Chosen
#   3. Aguardar o próximo campo habilitar antes de continuar
#
# IDs dos selects nativos (confirmados pelo HTML):
#   Marca:   #selectMarcacarro
#   Modelo:  #selectAnoModelocarro
#   Ano:     #selectAnocarro
#   Botão:   #buttonPesquisarcarro
#
# Resultado na tabela (sem IDs, por posição de linha):
#   Linha 0: Mês de referência
#   Linha 1: Código Fipe
#   Linha 2: Marca
#   Linha 3: Modelo
#   Linha 4: Ano Modelo
#   Linha 5: Autenticação
#   Linha 6: Data da consulta
#   Linha 7: Preço Médio  ← o que queremos (última linha, classe "last")


# ─────────────────────────────────────────────
# FUNÇÃO AUXILIAR: selecionar opção via JS no select nativo
# ─────────────────────────────────────────────
def _selecionar_por_texto(
    page: Page, select_id: str, texto_busca: str, indice: int = 0
):
    """
    Seleciona uma opção no <select> nativo via JavaScript e dispara o evento
    'change' para que o Chosen e a lógica da página reconheçam a seleção.

    Parâmetros:
        page        — instância da página Playwright
        select_id   — id do select nativo, ex: "selectMarcacarro"
        texto_busca — texto parcial para filtrar as opções (case insensitive)
        indice      — qual das opções filtradas selecionar (0 = primeira)
    """
    # Aguarda o select estar disponível e habilitado
    page.wait_for_selector(f"#{select_id}", state="attached", timeout=TIMEOUT)

    # Encontra o valor (value) da opção cujo texto contenha texto_busca
    valor = page.evaluate(
        f"""
        () => {{
            const select = document.getElementById('{select_id}');
            const busca = '{texto_busca}'.toUpperCase();
            const opcoes = Array.from(select.options).filter(
                o => o.text.toUpperCase().includes(busca) && o.value !== ''
            );
            return opcoes.length > {indice} ? opcoes[{indice}].value : null;
        }}
    """
    )

    if valor is None:
        raise ValueError(
            f"Nenhuma opção contendo '{texto_busca}' encontrada em #{select_id}.\n"
            f"Verifique se a marca/modelo/ano está cadastrado na FIPE."
        )

    # Seleciona o valor e dispara o evento change para o Chosen reagir
    page.evaluate(
        f"""
        () => {{
            const select = document.getElementById('{select_id}');
            select.value = '{valor}';
            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
    """
    )

    # Aguarda a página processar o evento
    page.wait_for_timeout(1_500)


# ─────────────────────────────────────────────
# FUNÇÃO AUXILIAR: selecionar os modelos e ver qual possui o ano correto
# ─────────────────────────────────────────────
def _selecionar_modelo_inteligente(page: Page, modelo: str, ano: str):
    """
    Testa múltiplas variações do modelo até encontrar uma que contenha o ano desejado.
    """

    # Aguarda o select de modelo
    page.wait_for_selector("#selectAnoModelocarro", state="attached", timeout=TIMEOUT)

    # Busca todas as opções que contenham o modelo completo
    opcoes = page.evaluate(
        f"""
        () => {{
            const select = document.getElementById('selectAnoModelocarro');
            const busca = '{modelo}'.toUpperCase();

            return Array.from(select.options)
                .filter(o => o.text.toUpperCase().includes(busca) && o.value !== '')
                .map(o => ({{ value: o.value, text: o.text }}));
        }}
    """
    )

    if not opcoes:
        raise ValueError(f"Nenhuma opção encontrada para modelo: {modelo}")

    print(f"  [info] {len(opcoes)} variação(ões) encontrada(s)")

    # Testa uma por uma
    for i, opcao in enumerate(opcoes, start=1):
        print(f"  [teste {i}] {opcao['text']}")

        # Seleciona o modelo
        page.evaluate(
            f"""
            () => {{
                const select = document.getElementById('selectAnoModelocarro');
                select.value = '{opcao["value"]}';
                select.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """
        )

        page.wait_for_timeout(1500)

        # Verifica se o ano existe nas opções
        ano_existe = page.evaluate(
            f"""
            () => {{
                const select = document.getElementById('selectAnocarro');
                if (!select) return false;

                return Array.from(select.options)
                    .some(o => o.text.includes('{ano}'));
            }}
        """
        )

        if ano_existe:
            print(f"  [✓] Modelo válido encontrado: {opcao['text']}")
            return

    raise ValueError(f"Nenhuma variação do modelo '{modelo}' possui o ano '{ano}'")


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL: consultar valor FIPE
# ─────────────────────────────────────────────
def consultar_fipe(page: Page, marca: str, modelo: str, ano: str) -> dict:
    """
    Acessa o site da FIPE, preenche os campos de marca, modelo e ano,
    clica em pesquisar e retorna o preço médio e o mês de referência.

    Parâmetros:
        page   — instância da página Playwright já aberta
        marca  — ex: "FORD"
        modelo — ex: "FIESTA 1.5 16V"
        ano    — ex: "2015"

    Retorna:
        {
            "preco":      41202.00,           (float)
            "preco_str":  "R$ 41.202,00",     (string original do site)
            "referencia": "abril de 2026",    (string do mês de referência)
        }
    """
    print(f"  [→] Acessando FIPE — {marca} / {modelo} / {ano}")
    page.goto(URL_FIPE, wait_until="networkidle")

    # Clica na aba "Consulta de Carros e Utilitários Pequenos"
    # A aba já vem aberta por padrão (class="open"), mas garantimos o clique
    page.locator("a[data-label='carro']").first.click()
    page.wait_for_timeout(1_000)

    # ── CAMPO 1: MARCA ────────────────────────────────────────────────────────
    print(f"  [~] Selecionando marca: {marca}")
    _selecionar_por_texto(page, "selectMarcacarro", marca)

    # ── CAMPO 2: MODELO ───────────────────────────────────────────────────────
    print(f"  [~] Selecionando modelo: {modelo}")
    # Usa apenas a primeira palavra do modelo para aumentar a chance de match
    # Ex: "FIESTA 1.5 16V" → busca por "FIESTA"
    # palavra_modelo = modelo.split()[0]
    _selecionar_modelo_inteligente(page, modelo, ano)
    # _selecionar_por_texto(page, "selectAnoModelocarro", modelo)

    # ── CAMPO 3: ANO ──────────────────────────────────────────────────────────
    print(f"  [~] Selecionando ano: {ano}")
    _selecionar_por_texto(page, "selectAnocarro", ano)

    # ── BOTÃO PESQUISAR ───────────────────────────────────────────────────────
    print("  [~] Clicando em Pesquisar...")
    page.locator("#buttonPesquisarcarro").click()

    # Aguarda a tabela de resultado aparecer
    tabela = page.locator("#resultadoConsultacarroFiltros table")
    tabela.wait_for(timeout=TIMEOUT)

    # ── CAPTURA DO RESULTADO ──────────────────────────────────────────────────
    # A tabela tem linhas fixas — Preço Médio é a última (classe "last")
    # Mês de referência é a primeira linha (índice 0)
    linhas = page.locator("#resultadoConsultacarroFiltros table tr")

    referencia = linhas.nth(0).locator("td").nth(1).inner_text().strip()
    preco_str = linhas.last.locator("td").nth(1).inner_text().strip()

    # Limpa o preço — remove "R$", pontos de milhar, troca vírgula por ponto
    preco_float = float(
        preco_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
    )

    dados = {
        "preco": preco_float,
        "preco_str": preco_str,
        "referencia": referencia,
    }

    print(f"  [✓] Resultado FIPE: {preco_str} — ref: {referencia}")
    return dados


# ─────────────────────────────────────────────
# EXECUÇÃO DIRETA — teste rápido do módulo
# ─────────────────────────────────────────────
if __name__ == "__main__":
    from playwright.sync_api import sync_playwright

    MARCA_TESTE = "FORD"
    MODELO_TESTE = "FIESTA 1.5 16V"
    ANO_TESTE = "2015"

    print("=" * 50)
    print("Testando fipe.py")
    print("=" * 50)

    with sync_playwright() as p:
        navegador = p.chromium.launch(
            channel="msedge",
            headless=False,
            slow_mo=300,
        )
        page = navegador.new_page()

        try:
            dados = consultar_fipe(page, MARCA_TESTE, MODELO_TESTE, ANO_TESTE)

            print("\n" + "=" * 50)
            print("Resultado:")
            print(f"  Preço:      {dados['preco_str']}")
            print(f"  Valor float:{dados['preco']}")
            print(f"  Referência: {dados['referencia']}")
            print("=" * 50)

        except PlaywrightTimeout as e:
            print(f"\n[ERRO] Timeout: {e}")

        except ValueError as e:
            print(f"\n[ERRO] Valor não encontrado: {e}")

        except Exception as e:
            print(f"\n[ERRO] {type(e).__name__}: {e}")

        finally:
            input("\nPressione ENTER para fechar o navegador...")
            navegador.close()
