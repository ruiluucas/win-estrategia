"""Bookmap de eventos A7 — v3.

O heatmap anterior desenhava dois imshow sobrepostos (bid e ask) na mesma
extensao; o de cima cobria o de baixo. Aqui as duas matrizes viram UMA imagem
RGBA: verde para bid, vermelho para ask, preto onde nao ha nivel.

Uso:
    python bookmap_eventos.py 2026-11-16 10:15 10:30
    python bookmap_eventos.py 2026-11-16          (todos os blocos de 10min)
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

import db
import analise_a7 as a7

CUSTO = 7.5
OUT = '/home/rui/Projetos/win-estrategia/out'


def prepara(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.episodios(bk, tk, z)
    if len(ev):
        ev = a7.desenfeccoes(snaps, ev) if hasattr(a7, 'desenfeccoes') else a7.desfechos(snaps, ev)
        ev['classe'] = np.where(ev.def_queda > 0.10, 'consumo',
                         np.where(ev.def_queda < -0.10, 'reforco', 'neutro'))
        ev['desfecho'] = np.where(ev.passou, 'passou', 'segurou')
        ev['pnl_contra'] = -ev.av60 - CUSTO
    return bk, tk, snaps, z, ev


def matriz_rgb(bk, ini, fim, n_col=900):
    """Uma imagem RGBA: canal verde = volume bid, canal vermelho = volume ask."""
    j = bk[(bk.t >= ini) & (bk.t <= fim)]
    if not len(j):
        return None
    tempos = np.sort(j.t.unique())
    precos = np.sort(j.preco.unique())
    passo = max(1, len(tempos) // n_col)
    bordas = tempos[::passo]
    idx = np.clip(np.searchsorted(bordas, j.t.values, side='right') - 1, 0, len(bordas) - 1)

    grade = np.arange(precos.min(), precos.max() + 5, 5)
    ip = {p: i for i, p in enumerate(grade)}
    Mb = np.zeros((len(grade), len(bordas)))
    Ma = np.zeros((len(grade), len(bordas)))
    for r, c in zip(j.itertuples(), idx):
        p = ip.get(r.preco)
        if p is None:
            continue
        (Mb if r.lado == 2 else Ma)[p, c] += r.volume

    tot = Mb + Ma
    nz = tot[tot > 0]
    if not len(nz):
        return None
    teto = np.percentile(nz, 97)

    rgba = np.zeros((len(grade), len(bordas), 4), dtype=float)
    # normalizacao com raiz para levantar volumes baixos
    nb = np.sqrt(np.clip(Mb / teto, 0, 1))
    na = np.sqrt(np.clip(Ma / teto, 0, 1))
    rgba[..., 0] = na                      # vermelho = ask
    rgba[..., 1] = nb                      # verde    = bid
    rgba[..., 2] = 0.10 * (nb + na)        # leve azul para dar corpo
    rgba[..., 3] = np.clip((nb + na) * 1.6, 0, 1)   # alpha: so pinta onde tem book

    ext = (mdates.date2num(bordas[0]), mdates.date2num(tempos[-1]),
           grade[0] - 2.5, grade[-1] + 2.5)
    return rgba, ext


def desenha(dia, ini, fim, bk, snaps, z, ev, nome):
    m = snaps[(snaps.t >= ini) & (snaps.t <= fim)]
    if not len(m):
        print('sem dados'); return
    r = matriz_rgb(bk, ini, fim)
    if r is None:
        print('sem book'); return
    rgba, ext = r
    e = ev[(ev.t_fim >= ini) & (ev.t_fim <= fim)].sort_values('t_fim')

    fig = plt.figure(figsize=(18, 9.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[3.1, .95], hspace=.26)
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor('#07070a')
    ax.imshow(rgba, aspect='auto', origin='lower', extent=ext, interpolation='nearest')
    ax.plot(m.t, m.mid, color='white', lw=1.5, alpha=.95, zorder=4)

    zv = a7.zona_vigente(z, ini)
    if zv is not None:
        for _, zz in zv.iterrows():
            ax.axhline(zz.lo, color='#60a5fa', lw=.9, ls='--', alpha=.7, zorder=3)
            ax.axhline(zz.hi, color='#60a5fa', lw=.9, ls='--', alpha=.7, zorder=3)

    for k, row in enumerate(e.itertuples(), 1):
        cor = '#f59e0b' if row.classe == 'consumo' else ('#22d3ee' if row.classe == 'reforco' else '#9ca3af')
        ax.scatter([row.t_fim], [row.borda], s=230, c=cor, edgecolors='white',
                   linewidths=1.6, zorder=6, marker='o' if row.passou else 's')
        ax.annotate(str(k), (row.t_fim, row.borda), fontsize=7, color='black',
                    zorder=7, ha='center', va='center', fontweight='bold')

    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    ax.set_ylabel('preço')
    ax.tick_params(axis='x', labelsize=8)
    ax.set_title(f'{dia}   {ini:%H:%M}–{fim:%H:%M}   |   {len(e)} episódios   |   '
                 f'● rompeu   ■ segurou', fontsize=10)
    ax.legend(handles=[
        Patch(color='#22c55e', label='bid (compra)'),
        Patch(color='#ef4444', label='ask (venda)'),
        plt.Line2D([], [], color='white', lw=1.5, label='mid'),
        plt.Line2D([], [], color='#60a5fa', ls='--', lw=1, label='borda de zona'),
        plt.Line2D([], [], marker='o', ls='', color='#f59e0b', mec='white', ms=9, label='consumo'),
        plt.Line2D([], [], marker='o', ls='', color='#22d3ee', mec='white', ms=9, label='reforço'),
    ], loc='upper left', fontsize=8, ncol=3, framealpha=.9, facecolor='#111')

    axt = fig.add_subplot(gs[1])
    axt.axis('off')
    L = [f"{'#':>3s} {'hora':>9s} {'borda':>7s} {'nível':>5s} {'vol ini→fim':>14s} "
         f"{'def':>6s} {'comp':>5s} {'vend':>5s} {'classe':>8s} {'desf':>7s} "
         f"{'+60s':>5s} {'CONTRA':>7s}", '─' * 106]
    for k, row in enumerate(e.itertuples(), 1):
        L.append(f"{k:3d} {row.t_fim.strftime('%H:%M:%S'):>9s} {int(row.borda):7d} "
                 f"{row.lado_nivel:>5s} {row.v_ini:6.0f}→{row.v_fim:<5.0f} "
                 f"{row.def_queda*100:+5.0f}% {row.agride_compra:5.0f} {row.agride_venda:5.0f} "
                 f"{row.classe:>8s} {row.desfecho:>7s} {row.av60:+5.0f} {row.pnl_contra:+7.0f}")
    L.append('─' * 106)
    L.append(f"CONTRA o agressor: {(e.pnl_contra>0).sum()}/{len(e)} positivos | "
             f"total {e.pnl_contra.sum():+.0f} pts | mediana {e.pnl_contra.median():+.1f} | "
             f"custo {CUSTO} pts/trade")
    axt.text(0, 1, '\n'.join(L), family='monospace', fontsize=7.5, va='top',
             transform=axt.transAxes)

    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, nome)
    plt.savefig(p, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    print('salvo:', p, f'| {len(e)} eventos')
    return p


def main():
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    bk, tk, snaps, z, ev = prepara(dia)
    print(f'{dia}: {len(ev)} episodios')
    if len(sys.argv) >= 4:
        ini = pd.Timestamp(f'{dia} {sys.argv[2]}:00')
        fim = pd.Timestamp(f'{dia} {sys.argv[3]}:00')
        desenha(dia, ini, fim, bk, snaps, z, ev, 'bookmap_final.png')
    else:
        t0 = snaps.t.min().floor('10min')
        blocos = pd.date_range(t0, snaps.t.max(), freq='10min')
        for i in range(len(blocos) - 1):
            a, b = blocos[i], blocos[i + 1]
            if len(ev[(ev.t_fim >= a) & (ev.t_fim <= b)]):
                desenha(dia, a, b, bk, snaps, z, ev, f'bookmap_{a:%H%M}.png')


if __name__ == '__main__':
    main()
