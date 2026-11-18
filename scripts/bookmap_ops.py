"""Bookmap das operacoes A7: heatmap de profundidade + entradas marcadas.

Para cada episodio de beirada, desenha no heatmap:
  - seta na direcao do ataque
  - cor pela classe (consumo = azul, reforco = laranja)
  - preenchida se o desfecho foi 'passou', vazada se 'segurou'

Divide em blocos de 30 min para ficar legivel.

Uso: python bookmap_ops.py 2026-11-16 [inicio HH:MM] [fim HH:MM]
"""
import sys
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np
import pandas as pd

import db
import analise_a7 as a7

TICK = 5
CAMPO = 2 * TICK


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.episodios(bk, tk, z)
    ev = a7.desfechos(snaps, ev)
    ev['classe'] = np.where(ev.def_queda > 0.10, 'consumo',
                     np.where(ev.def_queda < -0.10, 'reforco', 'neutro'))
    ev['desfecho'] = np.where(ev.passou, 'passou', 'segurou')
    return bk, tk, snaps, ev


def heatmap(ax, bk, ini, fim, passo_preco=TICK, topo_pct=98):
    """Heatmap de profundidade: bid verde, ask vermelho."""
    d = bk[(bk.t >= ini) & (bk.t <= fim)]
    if not len(d):
        return None
    # agrupa por coluna de tempo (1s) e preco
    d = d.copy()
    d['col'] = (d.t - ini).dt.total_seconds().astype(int)
    d['prow'] = (d.preco // passo_preco * passo_preco).astype(int)
    grade = d.pivot_table(index='prow', columns='col', values='volume',
                          aggfunc='max').sort_index(ascending=False)
    grade = grade.fillna(0)
    if not grade.size:
        return None

    # fundo: cinza escuro
    ax.set_facecolor('#0d1117')
    veu = grade.values.astype(float)
    teto = np.percentile(veu[veu > 0], topo_pct) if (veu > 0).any() else 1
    norm = veu / max(teto, 1)

    # codifica lado medio por preco dentro da janela
    lado_preco = d.groupby('prow').lado.max()

    cmap_bid = colors.LinearSegmentedColormap.from_list(
        'b', ['#0d1117', '#1f4a3a', '#2f9e6f', '#7ee0a8', '#e8ff8f'])
    cmap_ask = colors.LinearSegmentedColormap.from_list(
        'a', ['#0d1117', '#4a1f1f', '#9e2f2f', '#e06060', '#ffd27f'])

    x0, x1 = 0, grade.shape[1]
    for i, prow in enumerate(grade.index):
        lado = lado_preco.get(prow, 1)
        cmap = cmap_bid if lado == 2 else cmap_ask
        linha = norm[i]
        for c in range(grade.shape[1]):
            v = linha[c]
            if v <= 0.02:
                continue
            ax.add_patch(plt.Rectangle(
                (x0 + c, i), 1, 1,
                facecolor=cmap(min(v, 1.0)), edgecolor='none'))

    ax.set_xlim(0, grade.shape[1])
    ax.set_ylim(0, grade.shape[0])

    # eixo de preco
    ys = np.linspace(0, grade.shape[0] - 1, 8).astype(int)
    ax.set_yticks(ys + .5)
    ax.set_yticklabels([f"{grade.index[y]:,}".replace(',', '.') for y in ys],
                       fontsize=7, color='#8b949e')
    xs = np.linspace(0, grade.shape[1] - 1, 8).astype(int)
    ax.set_xticks(xs + .5)
    ax.set_xticklabels([(ini + pd.Timedelta(seconds=int(x))).strftime('%H:%M')
                        for x in xs], fontsize=7, color='#8b949e')
    ax.tick_params(colors='#8b949e', length=2)
    for s in ax.spines.values():
        s.set_color('#30363d')
    return grade.index, ini


def marca_ops(ax, ev, grade_idx, ini, passo_preco=TICK):
    """Desenha cada episodio como uma seta no heatmap."""
    if grade_idx is None or not len(ev):
        return
    precos = list(grade_idx)                       # ordem decrescente
    linhas = {p: i for i, p in enumerate(precos)}

    def y_de(preco):
        p = int(preco // passo_preco * passo_preco)
        if p in linhas:
            return linhas[p] + .5
        return None

    for _, r in ev.iterrows():
        col = (r.t_fim - ini).total_seconds()
        y = y_de(r.borda)
        if y is None:
            continue
        cor = '#4cc9f0' if r.classe == 'consumo' else '#f7a35c'
        dy = 3.5 * (1 if r.nome == 'hi' else -1)
        cheio = r.desfecho == 'passou'
        ax.annotate('', xy=(col, y + dy), xytext=(col, y),
                    arrowprops=dict(arrowstyle='-|>' if cheio else '-|>',
                                    color=cor, lw=1.6 if cheio else 1.0,
                                    alpha=.95 if cheio else .55,
                                    linestyle='solid' if cheio else 'dashed',
                                    shrinkA=0, shrinkB=0))


def bloco(dia, ini_hhmm, fim_hhmm, saida):
    bk, tk, snaps, ev = carrega(dia)
    ini = pd.Timestamp(f'{dia} {ini_hhmm}:00')
    fim = pd.Timestamp(f'{dia} {fim_hhmm}:00')

    fig, ax = plt.subplots(figsize=(15, 8))
    fig.patch.set_facecolor('#0d1117')
    res = heatmap(ax, bk, ini, fim)
    if res:
        marca_ops(ax, ev[(ev.t_fim >= ini) & (ev.t_fim <= fim)], res[0], ini)

    sub = ev[(ev.t_fim >= ini) & (ev.t_fim <= fim)]
    n_cons = (sub.classe == 'consumo').sum()
    n_ref = (sub.classe == 'reforco').sum()
    n_pass = sub.passou.sum()
    ax.set_title(
        f'{dia} {ini_hhmm}–{fim_hhmm} | {len(sub)} episodios | '
        f'consumo {n_cons} (azul) · reforco {n_ref} (laranja) | '
        f'cheio = rompeu ({n_pass}), tracejado = segurou\n'
        f'seta aponta na direcao do ATAQUE medido por lado_inferido',
        fontsize=10, color='#c9d1d9', pad=10)

    # legenda manual
    from matplotlib.lines import Line2D
    leg = [
        Line2D([0], [0], color='#4cc9f0', lw=2, label='consumo (volume caiu)'),
        Line2D([0], [0], color='#f7a35c', lw=2, label='reforco (volume subiu)'),
        Line2D([0], [0], color='#8b949e', lw=2, ls='--', label='segurou'),
        Line2D([0], [0], color='#8b949e', lw=2, ls='-', label='rompeu'),
        Line2D([0], [0], color='#7ee0a8', lw=6, label='bid (compra)'),
        Line2D([0], [0], color='#e06060', lw=6, label='ask (venda)'),
    ]
    ax.legend(handles=leg, loc='upper left', fontsize=7, facecolor='#161b22',
              edgecolor='#30363d', labelcolor='#c9d1d9', ncol=3, framealpha=.9)

    plt.tight_layout()
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    plt.savefig(saida, dpi=130, facecolor='#0d1117', bbox_inches='tight')
    plt.close(fig)
    print('salvo:', saida, f'| {len(sub)} operacoes')
    return len(sub)


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    base = f'/home/rui/Projetos/win-estrategia/out'
    blocos = [('09:58', '10:28'), ('10:28', '10:58'), ('10:58', '11:28'),
              ('11:28', '11:58'), ('11:58', '12:15')]
    total = 0
    for i, (a, b) in enumerate(blocos, 1):
        total += bloco(dia, a, b, f'{base}/ops_{dia}_{i}.png')
    print(f'\ntotal de operacoes desenhadas: {total}')
