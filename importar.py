import os
import psycopg2
from dotenv import load_dotenv
from ofxparse import OfxParser

load_dotenv()

with open("extrato.ofx", "rb") as arquivo:
    ofx = OfxParser.parse(arquivo)

conexao = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conexao.cursor()

inseridas = 0
duplicadas = 0

for t in ofx.account.statement.transactions:
    cursor.execute(
        """
        INSERT INTO movimentacoes (data_movimentacao, valor, descricao)
        VALUES (%s, %s, %s)
        ON CONFLICT (data_movimentacao, valor, descricao) DO NOTHING
        """,
        (t.date.date(), t.amount, t.memo)
    )
    if cursor.rowcount == 1:
        inseridas += 1
    else:
        duplicadas += 1

conexao.commit()
cursor.close()
conexao.close()

print(f"Inseridas: {inseridas} | Duplicadas ignoradas: {duplicadas}")