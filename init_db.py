import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        nome TEXT PRIMARY KEY,
        saldo REAL DEFAULT 1500.00,
        role TEXT DEFAULT 'cliente' -- Pode ser: cliente, admin_A, admin_B, admin_C
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT NOT NULL,
        custo REAL NOT NULL, 
        preco_base REAL NOT NULL,
        estoque INTEGER NOT NULL,
        imagem TEXT,
        ativo INTEGER DEFAULT 1,
        vendas INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        produto_id INTEGER,
        quantidade INTEGER,
        valor_total_cliente REAL,
        imposto REAL,
        custo_embalagem REAL,
        lucro_liquido REAL,
        status TEXT,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        endereco TEXT,
        entregador_nome TEXT,
        entregador_valor REAL,
        entregador_info TEXT,
        FOREIGN KEY(usuario) REFERENCES usuarios(nome),
        FOREIGN KEY(produto_id) REFERENCES produtos(id)
    )
    """)

    # Cria o Admin Supremo (Qualimax_Admin) com Nível A
    cursor.execute("INSERT OR IGNORE INTO usuarios (nome, saldo, role) VALUES ('qualimax_admin', 999999, 'admin_A')")
    
    conn.commit()
    conn.close()
    print("Banco Qualimax recriado com Sistema de Cargos e Entregadores!")

if __name__ == "__main__":
    init_db()