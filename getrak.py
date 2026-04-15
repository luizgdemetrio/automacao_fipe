""""""

import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from playwright.sync_api import expect

# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
load_dotenv()

URL_LOGIN = "https://sis.getrak.com.br/gblocklocaliza/"
URL_CADASTRO = "https://sis.getrak.com.br/gblocklocaliza/mveiculo/cadastro/cadastrar"

USUARIO = os.getenv("GETRAK_USUARIO")
SENHA = os.getenv("GETRAK_SENHA")

TIMEOUT = 20_000  # milissegundos (Playwright usa ms, não segundos)


# ─────────────────────────────────────────────
# FUNÇÃO: fazer login no Getrak
# ─────────────────────────────────────────────
def fazer_login(page):
    """
    Acessa a página de login e realiza a autenticação.
    Seletores validados: input[name='login'], input[name='senha'], input[value='Entrar']
    """
    print("  [→] Acessando página de login...")
    page.goto(URL_LOGIN, wait_until="networkidle")

    page.locator("input[name='login']").fill(USUARIO)
    page.locator("input[name='senha']").fill(SENHA)
    page.locator('input[value="Entrar"]').click()

    page.wait_for_url(lambda url: url != URL_LOGIN, timeout=TIMEOUT)

    print(f"  [✓] Login realizado. URL atual: {page.url}")


# ─────────────────────────────────────────────
# FUNÇÃO: buscar dados do veículo pela placa
# ─────────────────────────────────────────────
def buscar_veiculo(page, placa: str) -> dict:
    """
    Acessa a tela de cadastro, insere a placa e captura
    Marca, Modelo e Ano do veículo.

    Seletores validados: #placa, #marca, #modelo, #anomodelo

    Parâmetros:
        page  — instância da página Playwright já logada
        placa — string da placa, ex: "QHF8A45"

    Retorna:
        {
            "placa":  "QHF8A45",
            "marca":  "FORD",
            "modelo": "FIESTA 1.5 16V",
            "ano":    "2015",
        }
    """
    print(f"  [→] Navegando para cadastro — placa: {placa}")
    page.goto(URL_CADASTRO)

    campo_placa = page.locator("#placa")
    campo_placa.wait_for(timeout=TIMEOUT)
    campo_placa.fill(placa)
    campo_placa.press("Tab")

    print("  [~] Aguardando carregamento dos dados do veículo...")

    # Aguarda cada campo ser preenchido automaticamente pela plataforma
    el_marca = page.locator("#marca")
    el_modelo = page.locator("#modelo")
    el_ano = page.locator("#anomodelo")

    expect(el_marca).not_to_have_value("", timeout=TIMEOUT)
    expect(el_modelo).not_to_have_value("", timeout=TIMEOUT)
    expect(el_ano).not_to_have_value("", timeout=TIMEOUT)

    dados = {
        "placa": placa,
        "marca": el_marca.input_value().strip().upper(),
        "modelo": el_modelo.input_value().strip().upper(),
        "ano": el_ano.input_value().strip(),
    }

    print(f"  [✓] Dados capturados: {dados}")
    return dados


# ─────────────────────────────────────────────
# EXECUÇÃO DIRETA — teste rápido do módulo
# ─────────────────────────────────────────────
if __name__ == "__main__":

    PLACA_TESTE = "QHF8A45"

    print("=" * 50)
    print("Testando getrak.py")
    print("=" * 50)

    if not USUARIO or not SENHA:
        print("\n[ERRO] Credenciais não encontradas.")
        print("Verifique se o arquivo .env está na mesma pasta com:")
        print("  GETRAK_USUARIO=seu_usuario")
        print("  GETRAK_SENHA=sua_senha")
    else:
        with sync_playwright() as p:
            navegador = p.chromium.launch(
                channel="msedge",
                headless=False,
                slow_mo=300,
            )
            page = navegador.new_page()

            try:
                fazer_login(page)
                dados = buscar_veiculo(page, PLACA_TESTE)

                print("\n" + "=" * 50)
                print("Resultado:")
                for chave, valor in dados.items():
                    print(f"  {chave:8}: {valor}")
                print("=" * 50)

            except PlaywrightTimeout as e:
                print(f"\n[ERRO] Timeout: {e}")

            except Exception as e:
                print(f"\n[ERRO] {type(e).__name__}: {e}")

            finally:
                input("\nPressione ENTER para fechar o navegador...")
                navegador.close()
