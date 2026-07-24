/* JSON2CNAB750 — SPA de análise de retorno CNAB750.
 * Sem dependências externas. Servido pela própria API (mesma origem).
 */
(function () {
  "use strict";

  var API = "/api/v1";

  // Estado da aplicação
  var estado = {
    arquivo: null, // File original (para baixar o Excel sem reprocessar no cliente)
    dados: null, // resposta de /retorno-to-json
    recebimentos: [], // detalhes tipo "5" normalizados
    ordenacao: { campo: "data_movimento", asc: true },
  };

  // ---------------------------------------------------------------- //
  // Utilidades
  // ---------------------------------------------------------------- //
  function $(sel) { return document.querySelector(sel); }

  function num(v) {
    if (v === null || v === undefined || v === "") return 0;
    var n = typeof v === "number" ? v : parseFloat(v);
    return isNaN(n) ? 0 : n;
  }

  var fmtMoeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
  function moeda(v) { return fmtMoeda.format(num(v)); }

  function inteiro(v) { return new Intl.NumberFormat("pt-BR").format(v); }

  function dataBR(iso) {
    if (!iso) return "—";
    var p = String(iso).split("-");
    return p.length === 3 ? p[2] + "/" + p[1] + "/" + p[0] : iso;
  }

  function texto(v) { return v == null || v === "" ? "—" : String(v); }

  function escaparHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // ---------------------------------------------------------------- //
  // Upload
  // ---------------------------------------------------------------- //
  var inputArquivo = $("#input-arquivo");
  var dropzone = $("#dropzone");
  var btnAnalisar = $("#btn-analisar");
  var btnLimpar = $("#btn-limpar");

  function selecionarArquivo(file) {
    estado.arquivo = file || null;
    $("#dropzone-nome").textContent = file
      ? file.name
      : "Clique para selecionar ou arraste o arquivo aqui";
    btnAnalisar.disabled = !file;
    btnLimpar.hidden = !file;
  }

  inputArquivo.addEventListener("change", function (e) {
    selecionarArquivo(e.target.files[0]);
  });

  ["dragenter", "dragover"].forEach(function (ev) {
    dropzone.addEventListener(ev, function (e) {
      e.preventDefault(); dropzone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    dropzone.addEventListener(ev, function (e) {
      e.preventDefault(); dropzone.classList.remove("dragover");
    });
  });
  dropzone.addEventListener("drop", function (e) {
    if (e.dataTransfer.files.length) {
      inputArquivo.files = e.dataTransfer.files;
      selecionarArquivo(e.dataTransfer.files[0]);
    }
  });

  btnLimpar.addEventListener("click", function () {
    inputArquivo.value = "";
    selecionarArquivo(null);
    $("#secao-resultado").hidden = true;
    $("#erro").hidden = true;
  });

  btnAnalisar.addEventListener("click", analisar);

  function mostrarErro(msg) {
    var el = $("#erro");
    el.textContent = msg;
    el.hidden = false;
  }

  async function analisar() {
    if (!estado.arquivo) return;
    $("#erro").hidden = true;
    $("#loading").hidden = false;
    btnAnalisar.disabled = true;

    try {
      var fd = new FormData();
      fd.append("arquivo", estado.arquivo);
      var resp = await fetch(API + "/retorno-to-json", { method: "POST", body: fd });
      if (!resp.ok) {
        var detalhe = "Falha ao processar o arquivo.";
        try { var j = await resp.json(); if (j.detail) detalhe = j.detail; } catch (_) {}
        throw new Error(detalhe);
      }
      estado.dados = await resp.json();
      estado.recebimentos = (estado.dados.detalhes || [])
        .filter(function (d) { return d.tipo_registro === "5"; })
        .map(normalizarRecebimento);
      renderizar();
    } catch (err) {
      mostrarErro(err.message || "Erro inesperado.");
    } finally {
      $("#loading").hidden = true;
      btnAnalisar.disabled = false;
    }
  }

  function normalizarRecebimento(r) {
    return {
      identificador: r.identificador || "",
      data_movimento: r.data_movimento || "",
      chave_pix: r.chave_pix || "",
      nome_pagador_final: r.nome_pagador_final || "",
      cpf_cnpj_pagador_final: r.cpf_cnpj_pagador_final || "",
      valor_original: num(r.valor_original),
      valor_juros: num(r.valor_juros),
      valor_multa: num(r.valor_multa),
      valor_desconto: num(r.valor_desconto),
      valor_abatimento: num(r.valor_abatimento),
      valor_final: num(r.valor_final),
      valor_pago: num(r.valor_pago),
      tarifa_cobranca: num(r.tarifa_cobranca),
      get receita_liquida() { return this.valor_pago - this.tarifa_cobranca; },
      end_to_end_id: r.end_to_end_id || "",
      codigo_liquidacao: r.codigo_liquidacao || "",
    };
  }

  // ---------------------------------------------------------------- //
  // Filtros
  // ---------------------------------------------------------------- //
  var filtros = {
    dataInicio: $("#f-data-inicio"),
    dataFim: $("#f-data-fim"),
    busca: $("#f-busca"),
    valorMin: $("#f-valor-min"),
    valorMax: $("#f-valor-max"),
  };

  Object.keys(filtros).forEach(function (k) {
    filtros[k].addEventListener("input", renderizarResultado);
  });
  $("#btn-limpar-filtros").addEventListener("click", function () {
    Object.keys(filtros).forEach(function (k) { filtros[k].value = ""; });
    renderizarResultado();
  });

  function aplicarFiltros() {
    var di = filtros.dataInicio.value;
    var df = filtros.dataFim.value;
    var q = filtros.busca.value.trim().toLowerCase();
    var vMin = filtros.valorMin.value !== "" ? parseFloat(filtros.valorMin.value) : null;
    var vMax = filtros.valorMax.value !== "" ? parseFloat(filtros.valorMax.value) : null;

    return estado.recebimentos.filter(function (r) {
      if (di && r.data_movimento && r.data_movimento < di) return false;
      if (df && r.data_movimento && r.data_movimento > df) return false;
      if (vMin !== null && r.valor_pago < vMin) return false;
      if (vMax !== null && r.valor_pago > vMax) return false;
      if (q) {
        var alvo = (r.chave_pix + " " + r.nome_pagador_final + " " +
          r.identificador + " " + r.cpf_cnpj_pagador_final).toLowerCase();
        if (alvo.indexOf(q) === -1) return false;
      }
      return true;
    });
  }

  function ordenar(lista) {
    var campo = estado.ordenacao.campo;
    var dir = estado.ordenacao.asc ? 1 : -1;
    return lista.slice().sort(function (a, b) {
      var va = a[campo], vb = b[campo];
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb), "pt-BR") * dir;
    });
  }

  // ---------------------------------------------------------------- //
  // Renderização
  // ---------------------------------------------------------------- //
  function renderizar() {
    var h = estado.dados.header || {};
    $("#meta-recebedor").textContent = texto(h.nome_recebedor);
    $("#meta-ispb").textContent = texto(h.ispb_participante);
    $("#meta-data").textContent = dataBR(h.data_geracao);
    $("#meta-arquivo").textContent = estado.arquivo ? estado.arquivo.name : "—";
    $("#secao-resultado").hidden = false;
    renderizarResultado();
    $("#secao-resultado").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderizarResultado() {
    var visiveis = aplicarFiltros();
    renderizarKpis(visiveis);
    renderizarPorDia(visiveis);
    renderizarPorChave(visiveis);
    renderizarTabela(ordenar(visiveis));
    $("#contador").textContent = inteiro(visiveis.length);
  }

  function agregar(lista) {
    var a = { qtde: lista.length, original: 0, juros: 0, multa: 0, desconto: 0,
      abatimento: 0, pago: 0, tarifa: 0 };
    lista.forEach(function (r) {
      a.original += r.valor_original;
      a.juros += r.valor_juros;
      a.multa += r.valor_multa;
      a.desconto += r.valor_desconto;
      a.abatimento += r.valor_abatimento;
      a.pago += r.valor_pago;
      a.tarifa += r.tarifa_cobranca;
    });
    a.liquida = a.pago - a.tarifa;
    a.ticket = a.qtde ? a.pago / a.qtde : 0;
    return a;
  }

  function renderizarKpis(lista) {
    var a = agregar(lista);
    var cards = [
      { label: "Qtde. recebimentos", valor: inteiro(a.qtde) },
      { label: "Valor original", valor: moeda(a.original) },
      { label: "Juros", valor: moeda(a.juros) },
      { label: "Multa", valor: moeda(a.multa) },
      { label: "Descontos", valor: moeda(a.desconto) },
      { label: "Abatimentos", valor: moeda(a.abatimento) },
      { label: "Receita bruta", valor: moeda(a.pago), classe: "kpi--principal" },
      { label: "Tarifas", valor: moeda(a.tarifa) },
      { label: "Receita líquida", valor: moeda(a.liquida), classe: "kpi--destaque" },
      { label: "Ticket médio", valor: moeda(a.ticket) },
    ];
    $("#kpis").innerHTML = cards.map(function (c) {
      return '<div class="kpi ' + (c.classe || "") + '">' +
        '<div class="kpi__label">' + c.label + "</div>" +
        '<div class="kpi__value">' + c.valor + "</div></div>";
    }).join("");
  }

  function agruparPor(lista, chaveFn) {
    var mapa = {};
    lista.forEach(function (r) {
      var k = chaveFn(r) || "—";
      if (!mapa[k]) mapa[k] = { qtde: 0, pago: 0, tarifa: 0 };
      mapa[k].qtde += 1;
      mapa[k].pago += r.valor_pago;
      mapa[k].tarifa += r.tarifa_cobranca;
    });
    return Object.keys(mapa).sort().map(function (k) {
      var g = mapa[k];
      return { chave: k, qtde: g.qtde, pago: g.pago, tarifa: g.tarifa, liquida: g.pago - g.tarifa };
    });
  }

  function linhasAgrupadas(grupos) {
    if (!grupos.length) return '<tr><td colspan="4" class="vazio">Sem dados.</td></tr>';
    var corpo = grupos.map(function (g) {
      return "<tr><td>" + escaparHtml(g.chave) + '</td><td class="num">' + inteiro(g.qtde) +
        '</td><td class="num">' + moeda(g.pago) + '</td><td class="num col-verde">' + moeda(g.liquida) + "</td></tr>";
    }).join("");
    var tot = grupos.reduce(function (s, g) {
      s.qtde += g.qtde; s.pago += g.pago; s.liquida += g.liquida; return s;
    }, { qtde: 0, pago: 0, liquida: 0 });
    corpo += '<tr class="tfoot-total"><td>TOTAL</td><td class="num">' + inteiro(tot.qtde) +
      '</td><td class="num">' + moeda(tot.pago) + '</td><td class="num">' + moeda(tot.liquida) + "</td></tr>";
    return corpo;
  }

  function renderizarPorDia(lista) {
    var grupos = agruparPor(lista, function (r) { return r.data_movimento; })
      .map(function (g) { g.rotulo = dataBR(g.chave); return g; });
    $("#tab-dia").querySelector("tbody").innerHTML = linhasAgrupadas(
      grupos.map(function (g) { return { chave: g.rotulo, qtde: g.qtde, pago: g.pago, liquida: g.liquida }; })
    );
    renderizarChart(grupos);
  }

  function renderizarPorChave(lista) {
    var grupos = agruparPor(lista, function (r) { return r.chave_pix; });
    $("#tab-chave").querySelector("tbody").innerHTML = linhasAgrupadas(grupos);
  }

  // Gráfico de barras em SVG (receita paga por dia), sem libs externas.
  function renderizarChart(grupos) {
    var box = $("#chart-dia");
    if (!grupos.length) { box.innerHTML = ""; return; }
    var W = 100, H = 42, pad = 6, gap = 2;
    var max = Math.max.apply(null, grupos.map(function (g) { return g.pago; })) || 1;
    var n = grupos.length;
    var larg = (W - pad * 2 - gap * (n - 1)) / n;
    var barras = grupos.map(function (g, i) {
      var alt = (g.pago / max) * (H - 16);
      var x = pad + i * (larg + gap);
      var y = H - 6 - alt;
      var t = "<title>" + escaparHtml(g.rotulo) + ": " + moeda(g.pago) + "</title>";
      return '<rect class="barra" x="' + x.toFixed(2) + '" y="' + y.toFixed(2) +
        '" width="' + larg.toFixed(2) + '" height="' + Math.max(alt, 0.5).toFixed(2) +
        '" rx="0.6">' + t + "</rect>";
    }).join("");
    var rotulos = n <= 12 ? grupos.map(function (g, i) {
      var x = pad + i * (larg + gap) + larg / 2;
      return '<text class="rotulo" x="' + x.toFixed(2) + '" y="' + (H - 0.5) +
        '" text-anchor="middle">' + escaparHtml(g.rotulo.slice(0, 5)) + "</text>";
    }).join("") : "";
    box.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none" ' +
      'style="height:120px">' + barras + rotulos + "</svg>";
  }

  function renderizarTabela(lista) {
    var tbody = $("#tab-recebimentos").querySelector("tbody");
    var vazio = $("#tabela-vazia");
    if (!lista.length) {
      tbody.innerHTML = "";
      vazio.hidden = false;
      return;
    }
    vazio.hidden = true;
    var frag = lista.map(function (r) {
      return "<tr>" +
        "<td>" + escaparHtml(r.identificador) + "</td>" +
        "<td>" + dataBR(r.data_movimento) + "</td>" +
        "<td>" + escaparHtml(r.chave_pix) + "</td>" +
        "<td>" + escaparHtml(r.nome_pagador_final) + "</td>" +
        '<td class="num">' + moeda(r.valor_original) + "</td>" +
        '<td class="num">' + moeda(r.valor_juros) + "</td>" +
        '<td class="num">' + moeda(r.valor_multa) + "</td>" +
        '<td class="num">' + moeda(r.valor_desconto) + "</td>" +
        '<td class="num col-forte">' + moeda(r.valor_pago) + "</td>" +
        '<td class="num">' + moeda(r.tarifa_cobranca) + "</td>" +
        '<td class="num col-verde">' + moeda(r.receita_liquida) + "</td>" +
        "</tr>";
    }).join("");
    tbody.innerHTML = frag;
  }

  // Ordenação por clique no cabeçalho
  Array.prototype.forEach.call(
    document.querySelectorAll("#tab-recebimentos thead th[data-sort]"),
    function (th) {
      th.addEventListener("click", function () {
        var campo = th.getAttribute("data-sort");
        if (estado.ordenacao.campo === campo) {
          estado.ordenacao.asc = !estado.ordenacao.asc;
        } else {
          estado.ordenacao.campo = campo;
          estado.ordenacao.asc = true;
        }
        renderizarTabela(ordenar(aplicarFiltros()));
      });
    }
  );

  // ---------------------------------------------------------------- //
  // Download do Excel (reenvia o arquivo original para /retorno-to-excel)
  // ---------------------------------------------------------------- //
  $("#btn-excel").addEventListener("click", async function () {
    if (!estado.arquivo) return;
    var btn = this;
    var rotulo = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Gerando…";
    try {
      var fd = new FormData();
      fd.append("arquivo", estado.arquivo);
      var resp = await fetch(API + "/retorno-to-excel", { method: "POST", body: fd });
      if (!resp.ok) throw new Error("Falha ao gerar o Excel.");
      var blob = await resp.blob();
      var nome = "analise_" + (estado.arquivo.name.replace(/\.[^.]+$/, "") || "retorno") + ".xlsx";
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = nome;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      mostrarErro(err.message || "Erro ao gerar o Excel.");
    } finally {
      btn.disabled = false;
      btn.textContent = rotulo;
    }
  });
})();
