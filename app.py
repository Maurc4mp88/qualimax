from flask import Flask, render_template, request, redirect, jsonify, session, url_for
import sqlite3
import os
import random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "chave_qualimax_secreta"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

CATEGORIAS = [
    {"nome": "Alimentos e bebidas", "icon": "ph-hamburger"},
    {"nome": "Casa, móveis e decoração", "icon": "ph-armchair"},
    {"nome": "Eletrodomésticos", "icon": "ph-plug"},
    {"nome": "Eletrônicos e tecnologia", "icon": "ph-desktop"},
    {"nome": "Celulares e acessórios", "icon": "ph-device-mobile"},
    {"nome": "Informática", "icon": "ph-laptop"},
    {"nome": "Roupas, calçados e acessórios", "icon": "ph-t-shirt"},
    {"nome": "Beleza e cuidados pessoais", "icon": "ph-sparkle"},
    {"nome": "Saúde e bem-estar", "icon": "ph-heartbeat"},
    {"nome": "Esportes e fitness", "icon": "ph-barbell"},
    {"nome": "Brinquedos e hobbies", "icon": "ph-game-controller"},
    {"nome": "Bebês e infantil", "icon": "ph-baby"},
    {"nome": "Pet shop", "icon": "ph-paw-print"},
    {"nome": "Automotivo", "icon": "ph-car"},
    {"nome": "Ferramentas e construção", "icon": "ph-wrench"},
    {"nome": "Indústria e comércio", "icon": "ph-factory"},
    {"nome": "Agro, jardim e exterior", "icon": "ph-plant"},
    {"nome": "Livros, papelaria e escritório", "icon": "ph-book"},
    {"nome": "Games e entretenimento", "icon": "ph-monitor-play"},
    {"nome": "Serviços e digitais", "icon": "ph-cloud-arrow-down"},
    {"nome": "Outro", "icon": "ph-package"}
]

def conectar():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def calcular_preco_dinamico(preco_base, estoque):
    if estoque <= 3: return preco_base * 1.15
    if estoque >= 20: return preco_base * 0.95
    return preco_base

def get_user_role():
    if "usuario" not in session: return None
    conn = conectar()
    user = conn.execute("SELECT role FROM usuarios WHERE nome=?", (session["usuario"],)).fetchone()
    conn.close()
    return user["role"] if user else None

@app.route("/")
def login():
    if "usuario" in session:
        role = get_user_role()
        if role in ['admin_A', 'admin_B', 'admin_C']: return redirect(url_for('admin'))
        return redirect(url_for('loja'))
    return render_template("login.html")

@app.route("/entrar", methods=["POST"])
def entrar():
    nome = request.form["nome"].strip().lower()
    if not nome: return redirect(url_for('login'))
    
    conn = conectar()
    user = conn.execute("SELECT * FROM usuarios WHERE nome = ?", (nome,)).fetchone()
    if not user:
        saldo_inicial = random.randint(100, 1700)
        conn.execute("INSERT INTO usuarios (nome, saldo, role) VALUES (?, ?, 'cliente')", (nome, saldo_inicial))
        conn.commit()
        role = 'cliente'
    else:
        role = user["role"]
    conn.close()
    
    session["usuario"] = nome
    if role in ['admin_A', 'admin_B', 'admin_C']: return redirect(url_for('admin_logistica' if role == 'admin_B' else 'admin'))
    return redirect(url_for('loja'))

@app.route("/sair")
def sair():
    session.pop("usuario", None)
    return redirect(url_for('login'))

@app.route("/loja")
def loja():
    if get_user_role() != 'cliente': return redirect(url_for('admin'))

    busca, cat_busca, ordenar = request.args.get("q", ""), request.args.get("categoria", ""), request.args.get("ordenar", "relevancia")
    query, params = "SELECT * FROM produtos WHERE ativo = 1", []

    if busca:
        query += " AND nome LIKE ?"; params.append(f"%{busca}%")
    if cat_busca:
        query += " AND categoria = ?"; params.append(cat_busca)
    
    query += " ORDER BY preco_base ASC" if ordenar == "barato" else " ORDER BY vendas DESC" if ordenar == "vendidos" else " ORDER BY id DESC"

    conn = conectar()
    saldo = conn.execute("SELECT saldo FROM usuarios WHERE nome = ?", (session["usuario"],)).fetchone()["saldo"]
    produtos_raw = conn.execute(query, params).fetchall()
    
    produto_destaque_id = conn.execute("SELECT id FROM produtos WHERE ativo=1 ORDER BY vendas DESC LIMIT 1").fetchone()
    destaque_id = produto_destaque_id["id"] if produto_destaque_id else -1

    produtos = []
    for p in produtos_raw:
        pd = dict(p)
        pd["preco_final"] = calcular_preco_dinamico(p["preco_base"], p["estoque"])
        pd["is_destaque"] = (p["id"] == destaque_id)
        produtos.append(pd)

    conn.close()
    return render_template("loja.html", produtos=produtos, saldo=saldo, categorias=CATEGORIAS, busca=busca, cat_atual=cat_busca)

@app.route("/perfil")
def perfil():
    if get_user_role() != 'cliente': return redirect(url_for('login'))
    conn = conectar()
    saldo = conn.execute("SELECT saldo FROM usuarios WHERE nome = ?", (session["usuario"],)).fetchone()["saldo"]
    pedidos = conn.execute("""
        SELECT p.id, pr.nome, p.quantidade, p.valor_total_cliente, p.status, p.data, p.endereco, p.entregador_nome, p.entregador_info, pr.imagem 
        FROM pedidos p JOIN produtos pr ON p.produto_id = pr.id 
        WHERE p.usuario = ? ORDER BY p.data DESC
    """, (session["usuario"],)).fetchall()
    conn.close()
    return render_template("perfil.html", pedidos=pedidos, saldo=saldo, usuario=session["usuario"])

@app.route("/finalizar", methods=["POST"])
def finalizar():
    if get_user_role() != 'cliente': return jsonify({"msg": "Sessão inválida"})
    data = request.get_json()
    usuario, carrinho, endereco = session["usuario"], data.get("carrinho", []), data.get("endereco", "").strip()

    if not endereco or not carrinho: return jsonify({"msg": "Dados incompletos!"})

    conn = conectar()
    cursor = conn.cursor()
    
    valor_produtos = 0
    for item in carrinho:
        produto = cursor.execute("SELECT preco_base, estoque FROM produtos WHERE id=? AND ativo=1", (item["id"],)).fetchone()
        if not produto: return jsonify({"msg": f"Erro no item {item['id']}"})
        if item["qtd"] <= 0 or produto["estoque"] < item["qtd"]: 
            return jsonify({"msg": "Estoque insuficiente. Atualize a página."})
        preco_unitario = calcular_preco_dinamico(produto["preco_base"], produto["estoque"])
        valor_produtos += preco_unitario * item["qtd"]

    frete = max(12.00, valor_produtos * 0.08) if valor_produtos > 0 else 0
    total_cliente = valor_produtos + frete

    saldo_row = cursor.execute("SELECT saldo FROM usuarios WHERE nome=?", (usuario,)).fetchone()
    if not saldo_row or saldo_row["saldo"] < total_cliente: 
        return jsonify({"msg": "Saldo insuficiente para concluir a compra!"})

    cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE nome=?", (total_cliente, usuario))
    
    frete_fracionado = frete / len(carrinho) if len(carrinho) > 0 else 0

    for item in carrinho:
        produto = cursor.execute("SELECT custo, preco_base, estoque FROM produtos WHERE id=?", (item["id"],)).fetchone()
        preco_vendido = calcular_preco_dinamico(produto["preco_base"], produto["estoque"])
        
        # CORREÇÃO DE MATEMÁTICA: Adicionar a fração do frete como receita para cobrir o motoboy.
        receita_bruta = (preco_vendido * item["qtd"]) + frete_fracionado
        impostos = (preco_vendido * item["qtd"]) * 0.17
        custos = 0
        
        lucro_liquido_inicial = receita_bruta - impostos - custos
        
        cursor.execute("UPDATE produtos SET estoque = estoque - ?, vendas = vendas + ? WHERE id=?", (item["qtd"], item["qtd"], item["id"]))
        cursor.execute("""
            INSERT INTO pedidos (usuario, produto_id, quantidade, valor_total_cliente, imposto, custo_embalagem, lucro_liquido, status, endereco) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendente', ?)
        """, (usuario, item["id"], item["qtd"], receita_bruta, impostos, 3.50 * item["qtd"], lucro_liquido_inicial, endereco))

    conn.commit()
    conn.close()
    return jsonify({"msg": "sucesso"})

# ================= ADMIN =================
@app.route("/admin")
def admin():
    role = get_user_role()
    if role not in ['admin_A', 'admin_C']: return redirect(url_for('admin_logistica') if role == 'admin_B' else '/')
    
    conn = conectar()
    produtos = conn.execute("SELECT * FROM produtos").fetchall()
    funcionarios = conn.execute("SELECT nome, role FROM usuarios WHERE role LIKE 'admin_%' AND nome != 'qualimax_admin'").fetchall()
    
    lucro_total = conn.execute("SELECT SUM(lucro_liquido) as val FROM pedidos WHERE status='Entregue'").fetchone()["val"] or 0
    impostos = conn.execute("SELECT SUM(imposto) as val FROM pedidos WHERE status='Entregue'").fetchone()["val"] or 0
    
    grafico_dados = conn.execute("""
        SELECT date(data) as dia, SUM(lucro_liquido) as total 
        FROM pedidos WHERE status='Entregue' GROUP BY dia ORDER BY dia DESC LIMIT 7
    """).fetchall()
    
    grafico_dados = list(reversed(grafico_dados))
    datas = [linha["dia"] for linha in grafico_dados]
    valores = [linha["total"] for linha in grafico_dados]
    conn.close()
    
    return render_template("admin.html", produtos=produtos, funcionarios=funcionarios, lucro_total=lucro_total, impostos=impostos, categorias=CATEGORIAS, role=role, datas=datas, valores=valores)

@app.route("/admin/logistica")
def admin_logistica():
    role = get_user_role()
    if role not in ['admin_A', 'admin_B', 'admin_C']: return redirect("/")
    conn = conectar()
    pedidos = conn.execute("""
        SELECT p.id, p.usuario, p.endereco, pr.nome, p.quantidade, p.lucro_liquido, p.status, p.data, p.entregador_nome, p.valor_total_cliente
        FROM pedidos p JOIN produtos pr ON p.produto_id = pr.id ORDER BY p.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_logistica.html", pedidos=pedidos, role=role)

@app.route("/admin/rankings")
def admin_rankings():
    role = get_user_role()
    if role not in ['admin_A', 'admin_B', 'admin_C']: return redirect("/")
    conn = conectar()
    top_produtos = conn.execute("SELECT pr.nome, pr.imagem, SUM(p.quantidade) as qtd FROM pedidos p JOIN produtos pr ON p.produto_id = pr.id GROUP BY p.produto_id ORDER BY qtd DESC LIMIT 5").fetchall()
    top_categorias = conn.execute("SELECT pr.categoria, SUM(p.lucro_liquido) as lucro FROM pedidos p JOIN produtos pr ON p.produto_id = pr.id WHERE p.status='Entregue' GROUP BY pr.categoria ORDER BY lucro DESC LIMIT 5").fetchall()
    top_entregadores = conn.execute("SELECT entregador_nome, COUNT(id) as entregas, SUM(entregador_valor) as recebido FROM pedidos WHERE status='Entregue' GROUP BY entregador_nome ORDER BY entregas DESC LIMIT 5").fetchall()
    conn.close()
    return render_template("admin_rankings.html", top_produtos=top_produtos, top_categorias=top_categorias, top_entregadores=top_entregadores, role=role)

@app.route("/salvar_produto", methods=["POST"])
def salvar_produto():
    if get_user_role() != 'admin_A': return redirect("/")
    conn = conectar()
    id_p, nome, cat, custo, preco, estoque = request.form.get("id"), request.form["nome"], request.form["categoria"], float(request.form["custo"]), float(request.form["preco"]), int(request.form["estoque"])
    file = request.files.get("imagem")
    
    img_path = ""
    if file and file.filename:
        img_path = f"/static/uploads/{secure_filename(file.filename)}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename)))

    if id_p:
        if img_path: conn.execute("UPDATE produtos SET nome=?, categoria=?, custo=?, preco_base=?, estoque=?, imagem=? WHERE id=?", (nome, cat, custo, preco, estoque, img_path, id_p))
        else: conn.execute("UPDATE produtos SET nome=?, categoria=?, custo=?, preco_base=?, estoque=? WHERE id=?", (nome, cat, custo, preco, estoque, id_p))
    else:
        conn.execute("INSERT INTO produtos (nome, categoria, custo, preco_base, estoque, imagem) VALUES (?, ?, ?, ?, ?, ?)", (nome, cat, custo, preco, estoque, img_path))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route("/deletar_produto/<int:id>", methods=["POST"])
def deletar_produto(id):
    if get_user_role() != 'admin_A': return redirect("/")
    conn = conectar()
    conn.execute("DELETE FROM produtos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route("/mudar_status_pedido", methods=["POST"])
def mudar_status_pedido():
    if get_user_role() not in ['admin_A', 'admin_B']: return redirect("/")
    id_pedido, novo_status = request.form["id"], request.form["status"]
    
    conn = conectar()
    pedido = conn.execute("SELECT status, usuario, valor_total_cliente, produto_id, quantidade, lucro_liquido FROM pedidos WHERE id=?", (id_pedido,)).fetchone()
    
    if not pedido or pedido["status"] in ["Entregue", "Cancelado"]:
        conn.close(); return redirect(url_for('admin_logistica'))

    if novo_status == "Cancelado":
        motivo = request.form.get("motivo", "Nenhum motivo.")
        conn.execute("UPDATE usuarios SET saldo = saldo + ? WHERE nome=?", (pedido["valor_total_cliente"], pedido["usuario"]))
        conn.execute("UPDATE produtos SET estoque = estoque + ?, vendas = vendas - ? WHERE id=?", (pedido["quantidade"], pedido["quantidade"], pedido["produto_id"]))
        conn.execute("UPDATE pedidos SET status=?, entregador_info=? WHERE id=?", ("Cancelado", f"Cancelado: {motivo}", id_pedido))
        
    elif novo_status == "Entregue":
        # CORREÇÃO DE NOMES DUPLICADOS: Limpa espaços e coloca primeira letra maiúscula (Ex: "joao " -> "Joao")
        entregador_nome = request.form.get("entregador_nome", "Não informado").strip().title()
        entregador_valor = float(request.form.get("entregador_valor", 0))
        
        lucro_final = pedido["lucro_liquido"] - entregador_valor
        conn.execute("UPDATE pedidos SET status=?, entregador_nome=?, entregador_valor=?, lucro_liquido=? WHERE id=?", (novo_status, entregador_nome, entregador_valor, lucro_final, id_pedido))
        
    else:
        conn.execute("UPDATE pedidos SET status=? WHERE id=?", (novo_status, id_pedido))
        
    conn.commit()
    conn.close()
    return redirect(url_for('admin_logistica'))

@app.route("/salvar_funcionario", methods=["POST"])
def salvar_funcionario():
    if get_user_role() != 'admin_A': return redirect("/")
    nome, role = request.form["nome"].strip().lower(), request.form["role"]
    conn = conectar()
    if conn.execute("SELECT * FROM usuarios WHERE nome=?", (nome,)).fetchone(): conn.execute("UPDATE usuarios SET role=? WHERE nome=?", (role, nome))
    else: conn.execute("INSERT INTO usuarios (nome, saldo, role) VALUES (?, 0, ?)", (nome, role))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route("/deletar_funcionario/<nome>", methods=["POST"])
def deletar_funcionario(nome):
    if get_user_role() != 'admin_A' or nome == 'qualimax_admin': return redirect("/")
    conn = conectar()
    conn.execute("UPDATE usuarios SET role='cliente' WHERE nome=?", (nome,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')