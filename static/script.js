let carrinho = [];
let valorFrete = 0;
let totalProdutosCarrinho = 0;

// CONTROLE DA ANIMAÇÃO DE TRANSIÇÃO (TELA DE CARREGAMENTO)
window.addEventListener('load', () => {
    const loader = document.getElementById('page-transition');
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => loader.style.display = 'none', 400);
    }
});

document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    // Verifica se é um link válido para página interna
    if (link && link.href && !link.href.includes('#') && !link.href.includes('javascript') && link.target !== '_blank') {
        e.preventDefault();
        const loader = document.getElementById('page-transition');
        if (loader) {
            loader.style.display = 'flex';
            setTimeout(() => loader.style.opacity = '1', 10);
        }
        setTimeout(() => window.location.href = link.href, 350); // Aguarda a animação antes de mudar
    }
});

function addCarrinho(id, nome, preco, estoqueMax) {
    let item = carrinho.find(i => i.id === id);
    if (item) {
        if (item.qtd < estoqueMax) { item.qtd++; mostrarToast("Adicionado mais um!", "sucesso"); }
        else { mostrarToast("Estoque máximo!", "erro"); }
    } else {
        carrinho.push({ id, nome, preco, qtd: 1, estoqueMax });
        mostrarToast(`${nome} no carrinho!`, "sucesso");
    }
    atualizarCarrinho();
}

function alterarQtd(id, delta) {
    let item = carrinho.find(i => i.id === id);
    if (item) {
        item.qtd += delta;
        if (item.qtd <= 0) carrinho = carrinho.filter(i => i.id !== id);
    }
    atualizarCarrinho();
}

function atualizarCarrinho() {
    const div = document.getElementById("carrinho-itens");
    if(!div) return; // Prevenção para caso não esteja na tela da loja

    div.innerHTML = "";
    totalProdutosCarrinho = 0;

    carrinho.forEach(item => {
        let sub = item.preco * item.qtd;
        totalProdutosCarrinho += sub;
        div.innerHTML += `
            <div style="display:flex; justify-content:space-between; margin-bottom:15px; border-bottom:1px solid var(--border); padding-bottom:10px;">
                <div style="font-size:1.1rem;"><b>${item.nome}</b> <br><span style="color:var(--success)">R$ ${item.preco.toFixed(2)}</span></div>
                <div style="display:flex; gap:15px; align-items:center; font-size:1.2rem; font-weight:bold;">
                    <button onclick="alterarQtd(${item.id}, -1)" style="padding:10px; width:45px; border-radius:50%; background:var(--border);">-</button>
                    ${item.qtd}
                    <button onclick="alterarQtd(${item.id}, 1)" style="padding:10px; width:45px; border-radius:50%; background:var(--primary);">+</button>
                </div>
            </div>`;
    });
    
    // Calcula o frete AUTOMATICAMENTE (8% do total, mínimo de R$ 12)
    if (carrinho.length > 0) {
        valorFrete = Math.max(12.00, totalProdutosCarrinho * 0.08);
    } else {
        valorFrete = 0;
    }

    document.getElementById("resultado-frete").innerHTML = `Entrega Padrão: R$ ${valorFrete.toFixed(2)}`;
    let totalFinal = totalProdutosCarrinho + valorFrete;
    document.getElementById("total-carrinho").innerText = totalFinal.toFixed(2);
}

function finalizar() {
    let endereco = document.getElementById("endereco").value.trim();
    if (carrinho.length === 0) return mostrarToast("Carrinho vazio!", "erro");
    if (!endereco) return mostrarToast("Digite o endereço de entrega!", "erro");

    let btn = document.getElementById("btn-finalizar");
    btn.disabled = true;
    btn.innerHTML = "Processando...";
    
    fetch("/finalizar", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ carrinho, endereco })
    }).then(r => r.json()).then(data => {
        if (data.msg === "sucesso") {
            // Animação de saída para a página de perfil
            const loader = document.getElementById('page-transition');
            if(loader){ loader.style.display = 'flex'; setTimeout(() => loader.style.opacity = '1', 10); }
            setTimeout(() => window.location.href = "/perfil", 350);
        } else {
            mostrarToast(data.msg, "erro");
            btn.disabled = false;
            btn.innerHTML = "Finalizar Compra";
        }
    });
}

function mostrarToast(msg, tipo) {
    let t = document.getElementById("toast");
    if(!t) return;
    t.innerText = msg;
    t.style.background = tipo === 'erro' ? 'var(--danger)' : 'var(--success)';
    t.style.opacity = "1";
    setTimeout(() => t.style.opacity = "0", 3000);
}