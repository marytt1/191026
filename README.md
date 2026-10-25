# Projeto OFX: Leitura de Extratos Bancários com Python

Aplicação em Python que lê arquivos bancários no formato **OFX**, categoriza as movimentações automaticamente e as armazena em um banco **PostgreSQL**. Representa uma versão simplificada de um processo ETL (Extração, Transformação e Carga).

## Funcionalidades

- Leitura de arquivos OFX com a biblioteca `ofxparse`
- Exibição de data, valor, descrição, total de movimentações, entradas, saídas e saldo
- Gravação das movimentações no PostgreSQL
- Bloqueio de transações duplicadas
- Categorização automática por palavras-chave
- Resumo por categoria
- Cadastro manual de novas movimentações

## Estrutura do projeto

```
├── main.py            # Leitura do OFX e exibição do extrato com totais
├── importar.py        # Importação simples do OFX para o PostgreSQL
├── app.py             # Programa completo com menu (importar, listar, resumo, adicionar)
├── extrato.ofx        # Arquivo OFX
├── requirements.txt   # Dependências
├── .env.example       # Modelo do arquivo de configuração
└── .gitignore
```

## Como executar

### 1. Baixar o projeto

```
git clone https://github.com/marytt1/191026.git
cd 191026
```

### 2. Criar e ativar o ambiente virtual

```
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar as dependências

```
pip install -r requirements.txt
```

### 4. Executar a leitura do OFX (não precisa de banco)

```
python main.py
```

Mostra cada movimentação do `extrato.ofx` e, ao final, a quantidade de movimentações, o total de entradas, o total de saídas e o saldo.

### 5. Configurar o banco de dados

Para usar `importar.py` e `app.py`, é necessário um banco PostgreSQL.

**a) Crie um banco**

**b) Crie a tabela** executando o SQL abaixo no banco:

```sql
CREATE TABLE IF NOT EXISTS movimentacoes (
    id SERIAL PRIMARY KEY,
    data_movimentacao DATE,
    valor NUMERIC(15,2),
    descricao VARCHAR(255),
    categoria VARCHAR(50) DEFAULT 'Sem categoria',
    UNIQUE (data_movimentacao, valor, descricao)
);
```

**c) Crie o arquivo `.env`** na raiz do projeto, copiando o modelo:

```
copy .env.example .env
```

Abra o `.env` e substitua pelo endereço do seu banco:

```
DATABASE_URL=postgresql://usuario:senha@host/banco?sslmode=require
```

### 6. Importar o OFX para o banco

```
python importar.py
```

Saída esperada na primeira execução com o arquivo de exemplo:

```
Inseridas: 16 | Duplicadas ignoradas: 0
```

Executando novamente, nenhuma linha é duplicada:

```
Inseridas: 0 | Duplicadas ignoradas: 16
```

### 7. Usar o programa completo

```
python app.py
```

Menu disponível:

| Opção | Ação |
|-------|------|
| 1 | Importar arquivo OFX (`extrato.ofx`) |
| 2 | Listar movimentações |
| 3 | Resumo por categoria, com entradas, saídas e saldo |
| 4 | Adicionar movimentação manualmente |
| 5 | Categorizar movimentações antigas |
| 0 | Sair |

## Tecnologias

- Python
- ofxparse
- psycopg2
- python-dotenv
- PostgreSQL
