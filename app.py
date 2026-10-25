import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

import time
import psycopg2
from dotenv import load_dotenv
from ofxparse import OfxParser

load_dotenv()

# Palavras-chave para categorizar automaticamente

CATEGORIAS = {
    "Receitas": ["PIX CLIENTE", "SALARIO", "DEPOSITO", "RECEBIDO"],
    "Moradia": ["ENERGIA", "LUZ", "AGUA", "ALUGUEL", "CONDOMINIO"],
    "Internet/Telefone": ["INTERNET", "TELEFONE", "CLARO", "VIVO"],
    "Alimentação": ["MERCADO", "SUPERMERCADO", "IFOOD", "PADARIA"],
    "Transporte": ["UBER", "99", "COMBUSTIVEL", "POSTO", "ONIBUS"],
    "Saúde": ["FARMACIA", "DROGARIA", "CONSULTA", "PLANO DE SAUDE"],
    "Lazer": ["NETFLIX", "SPOTIFY", "CINEMA"],
}

# função para categorizar automaticamente com base na descrição da movimentação

def categorizar(descricao):
    texto = (descricao or "").upper()
    for categoria, palavras in CATEGORIAS.items():
        for palavra in palavras:
            if palavra in texto:
                return categoria
    return "Outros"


# função para conectar ao banco de dados

def conectar():
    for tentativa in range(3):
        try:
            return psycopg2.connect(os.getenv("DATABASE_URL"), connect_timeout=15)
        except psycopg2.OperationalError:
            if tentativa == 2:
                raise
            print("Conectando ao banco, aguarde...")
            time.sleep(3)

# função para importar arquivo OFX e inserir no banco de dados

def importar_ofx(conexao):
    try:
        with open("extrato.ofx", "rb") as arquivo:
            ofx = OfxParser.parse(arquivo)
    except FileNotFoundError:
        print("Arquivo extrato.ofx não encontrado na pasta.")
        return

    cursor = conexao.cursor()
    inseridas = 0
    duplicadas = 0

    for t in ofx.account.statement.transactions:
        descricao = t.memo or t.payee or "Sem descrição"
        cursor.execute(
            """
            INSERT INTO movimentacoes (data_movimentacao, valor, descricao, categoria)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (data_movimentacao, valor, descricao) DO NOTHING
            """,
            (t.date.date(), t.amount, descricao, categorizar(descricao)),
        )
        if cursor.rowcount == 1:
            inseridas += 1
        else:
            duplicadas += 1

    conexao.commit()
    cursor.close()
    print(f"Inseridas: {inseridas} | Duplicadas ignoradas: {duplicadas}")

# função para listar movimentações do banco de dados

def listar(conexao):
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT id, data_movimentacao, valor, categoria, descricao
        FROM movimentacoes
        ORDER BY data_movimentacao, id
        """
    )
    linhas = cursor.fetchall()
    cursor.close()

    if not linhas:
        print("Nenhuma movimentação cadastrada.")
        return

    print(f"\n{'ID':<4} {'DATA':<11} {'VALOR':>14}  {'CATEGORIA':<18} DESCRIÇÃO")
    print("-" * 70)
    for id_, data, valor, categoria, descricao in linhas:
        print(f"{id_:<4} {data:%d/%m/%Y}  R$ {valor:>10.2f}  {categoria:<18} {descricao}")
    print(f"\nTotal de movimentações: {len(linhas)}")

# função para gerar resumo por categoria

def resumo_por_categoria(conexao):
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT categoria, COUNT(*), SUM(valor)
        FROM movimentacoes
        GROUP BY categoria
        ORDER BY SUM(valor)
        """
    )
    linhas = cursor.fetchall()

    cursor.execute(
        """
        SELECT
            COALESCE(SUM(valor) FILTER (WHERE valor > 0), 0),
            COALESCE(SUM(valor) FILTER (WHERE valor < 0), 0)
        FROM movimentacoes
        """
    )
    entradas, saidas = cursor.fetchone()
    cursor.close()

    print(f"\n{'CATEGORIA':<20} {'QTD':>4} {'TOTAL':>14}")
    print("-" * 42)
    for categoria, qtd, total in linhas:
        print(f"{categoria:<20} {qtd:>4} R$ {total:>10.2f}")

    print("-" * 42)
    print(f"Entradas: R$ {entradas:.2f}")
    print(f"Saídas  : R$ {saidas:.2f}")
    print(f"Saldo   : R$ {entradas + saidas:.2f}")

# função para adicionar uma nova movimentação manualmente

def adicionar():
    print("\n Nova movimentação")

    # Data
    while True:
        texto = input("Data (dd/mm/aaaa): ").strip()
        if texto == "":
            data = datetime.today().date()
            break
        for formato in ("%d/%m/%Y", "%d/%m/%y"):
            try:
                data = datetime.strptime(texto, formato).date()
                break
            except ValueError:
                data = None
        if data:
            break
        print("Data inválida. Use o formato dd/mm/aaaa.")

    # Tipo
    while True:
        tipo = input("Tipo (1 = Entrada, 2 = Saída): ").strip()
        if tipo in ("1", "2"):
            break
        print("Digite 1 ou 2.")

    # Valor
    while True:
        texto = input("Valor (ex: 150,00): ").strip().replace(",", ".")
        try:
            valor = abs(Decimal(texto))
            if valor == 0:
                print("O valor deve ser maior que zero.")
                continue
            break
        except InvalidOperation:
            print("Valor inválido.")

    if tipo == "2":
        valor = -valor

    # Descrição e categoria
    descricao = input("Descrição: ").strip() or "Sem descrição"
    sugestao = categorizar(descricao)
    categoria = input(f"Categoria [Enter = {sugestao}]: ").strip() or sugestao

    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            INSERT INTO movimentacoes (data_movimentacao, valor, descricao, categoria)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (data_movimentacao, valor, descricao) DO NOTHING
            """,
            (data, valor, descricao, categoria),
        )
        gravou = cursor.rowcount == 1
        conexao.commit()
        cursor.close()
    finally:
        conexao.close()

    if gravou:
        print("Movimentação adicionada com sucesso!")
    else:
        print("Já existe uma movimentação igual (mesma data, valor e descrição).")

# função para recategorizar movimentações antigas com categoria "Sem categoria"
def recategorizar(conexao):
    cursor = conexao.cursor()
    cursor.execute(
        "SELECT id, descricao FROM movimentacoes WHERE categoria = 'Sem categoria'"
    )
    pendentes = cursor.fetchall()

    for id_, descricao in pendentes:
        cursor.execute(
            "UPDATE movimentacoes SET categoria = %s WHERE id = %s",
            (categorizar(descricao), id_),
        )

    conexao.commit()
    cursor.close()
    print(f"{len(pendentes)} movimentações categorizadas.")

# função para exibir o menu principal e tratar as opções do usuário

def menu():
    while True:
        print("\n===== CONTROLE FINANCEIRO =====")
        print("1 - Importar arquivo OFX")
        print("2 - Listar movimentações")
        print("3 - Resumo por categoria")
        print("4 - Adicionar movimentação")
        print("5 - Categorizar movimentações antigas")
        print("0 - Sair")

        opcao = input("Escolha: ").strip()

        if opcao == "0":
            break

        if opcao == "4":
            adicionar()
            continue
        acoes = {
            "1": importar_ofx,
            "2": listar,
            "3": resumo_por_categoria,
            "5": recategorizar,
        }

        if opcao not in acoes:
            print("Opção inválida.")
            continue

        conexao = conectar()
        try:
            acoes[opcao](conexao)
        finally:
            conexao.close()

    print("Até logo!")


if __name__ == "__main__":
    menu()