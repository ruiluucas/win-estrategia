"""Bookmap de operacoes — visual limpo.

Diferente do anterior (que era heatmap + tabela densa):

  - heatmap grande, com escala de cor legivel e paleta suave
  - cada trade desenhado como SETA de entrada -> saida no proprio preco
  - verde = trade vencedor, vermelho = perdedor
  - painel lateral com o P&L acumulado e as estatisticas
  - tooltip de legenda simples, sem jargao

Uso:
    python bookmap_trades.py 2026-11-16 10:15 10:30
    python bookmap_trades.py 2026-11-16 10:15 10:30 --contra
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, PowerNorm
from matplotlib.patches import FancyArrowPatch, Patch, Rectangle
import numpy as np
import pandas as pd

import db
import analise_a7 as a7
import simula_a7 as sim

OUT = '/home/rui/Projetos/win-estrategia/out'
CUSTO = 7.5

# paleta limpa: bid em verde-agua, ask em laranja-vermelho
CM_BID = LinearSegmentedColormap.from_list(
    'bid', ['#0b1220', '#0f3d3e', '#14b8a6', '#5eead4', '#ccfbf1'])
CM_ASK = LinearSegmentedColormap.from_list(
    'ask', ['#0b1220', '#4a1010', '#c2410c', '#f97316', '#fed7aa'])


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.episodios(bk, tk, z)
    ev = a7.desfechos(snaps, ev).sort_values('t_fim').reset_index(drop=True)
    ev['classe'] = np.where(ev.def_queda > .10, 'consumo',
                     np.where(ev.def_queda < -.10, 'reforco', 'neutro'))
    return bk, snaps, z, ev


def grade_rgb(bk, ini, fim, n_col=1100):
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
    teto = np.percentile(nz, 96)
    nb = np.sqrt(np.clip(Mb / teto, 0, 1))
    na = np.sqrt(np.clip(Ma / teto, 0, 1))
    rgba = np.zeros((len(grade), len(bordas), 4))
    rgba[..., 0] = na * 1.0
    rgba[..., 1] = nb * 0.95
    rgba[..., 2] = (na + nb) * 0.25
    rgba[..., 3] = np.clip((nb + na) * 2.2, 0, 1)
    ext = (mdates.date2num(bordas[0]), mdates.date2num(tempos[-1]),
           grade[0] - 2.5, grade[-1] + 2.5)
    return rgba, ext


def desenha(dia, ini, fim, contra=False, nome='trades.png',
            t_max=60, alvo=None, stop=None):
    bk, snaps, z, ev = carrega(dia)
    g = grade_rgb(bk, ini, fim)
    if g is None:
        print('sem book no intervalo'); return
    rgba, ext = g
    m = snaps[(snaps.t >= ini) & (snaps.t <= fim)]

    # trades do simulador (posicao unica)
    tr = sim.simula(snaps, ev, contra=contra, t_max=t_max, alvo=alvo, stop=stop)
    tr = tr[(tr.t_ent >= ini) & (tr.t_ent <= fim)].copy()

    fig = plt.figure(figsize=(19, 10), facecolor='#0b0f16')
    gs = fig.add_gridspec(1, 2, width_ratios=[4.6, 1], wspace=.03)
    ax = fig.add_subplot(gs[0])
    ap = fig.add_subplot(gs[1])
    ax.set_facecolor('#0b0f16')
    ap.set_facecolor('#0b0f16')

    ax.imshow(rgba, aspect='auto', origin='lower', extent=ext, interpolation='nearest')
    ax.plot(m.t, m.mid, color='white', lw=1.3, alpha=.9, zorder=4)

    zv = a7.zona_vigente(z, ini)
    if zv is not None and len(zv):
        for _, zz in zv.iterrows():
            ax.axhline(zz.lo, color='#93c5fd', lw=.8, ls=(0, (4, 4)), alpha=.5, zorder=3)
            ax.axhline(zz.hi, color='#93c5fd', lw=.8, ls=(0, (4, 4)), alpha=.5, zorder=3)

    # ----- trades: seta do preco de entrada ate o de saida
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values

    def px(t):
        j = np.searchsorted(mts, np.datetime64(pd.Timestamp(t)), side='right') - 1
        return mid[j] if 0 <= j < len(mid) else np.nan

    for k, r in enumerate(tr.itertuples(), 1):
        e = px(r.t_ent)
        s_ = px(r.t_ent + pd.Timedelta(seconds=t_max))
        if np.isnan(e) or np.isnan(s_):
            continue
        ganhou = r.pnl > 0
        cor = '#22c55e' if ganhou else '#ef4444'
        t0 = mdates.date2num(r.t_ent)
        t1 = mdates.date2num(r.t_ent + pd.Timedelta(seconds=t_max))
        # seta grossa: 60s e 6% da largura da tela, entao mutation_scale alto
        ax.add_patch(FancyArrowPatch(
            (t0, e), (t1, s_),
            arrowstyle='-|>,head_width=0.9,head_length=1.6',
            mutation_scale=22, lw=3.4, color=cor, alpha=.98,
            zorder=9, shrinkA=0, shrinkB=0))
        # marcador de entrada (circulo numerado) e de saida (X)
        ax.scatter([r.t_ent], [e], s=170, c=cor, edgecolors='white', linewidths=2,
                   zorder=10, marker='o')
        ax.annotate(f"{k}", (r.t_ent, e), fontsize=8, color='white', zorder=11,
                    ha='center', va='center', fontweight='bold')
        ax.scatter([r.t_ent + pd.Timedelta(seconds=t_max)], [s_], s=110, c=cor,
                   edgecolors='white', linewidths=1.6, zorder=10, marker='X')

    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.set_ylabel('preço', color='#cbd5e1', fontsize=10)
    ax.tick_params(colors='#94a3b8', labelsize=9)
    for sp in ax.spines.values():
        sp.set_color('#1e293b')
    ax.set_title(
        f'{dia}   {ini:%H:%M}–{fim:%H:%M}      '
        f'{"CONTRA" if contra else "A FAVOR"} do agressor   ·   '
        f'saída em {t_max}s' + (f' · alvo {alvo} / stop {stop}' if alvo or stop else ''),
        color='#e2e8f0', fontsize=12, pad=10, loc='left')
    ax.legend(handles=[
        Patch(color='#14b8a6', label='bid (compra)'),
        Patch(color='#f97316', label='ask (venda)'),
        plt.Line2D([], [], color='white', lw=1.3, label='mid'),
        plt.Line2D([], [], color='#22c55e', lw=2, label='trade vencedor'),
        plt.Line2D([], [], color='#ef4444', lw=2, label='trade perdedor'),
    ], loc='upper left', fontsize=8.5, ncol=5, framealpha=.25,
        facecolor='#111827', edgecolor='#1e293b', labelcolor='#e2e8f0')

    # ----- painel lateral: P&L e numeros
    ap.axis('off')
    if len(tr):
        cum = np.cumsum(tr.pnl.values)
        ap.plot(np.arange(1, len(cum) + 1), cum, color='#38bdf8', lw=2)
        ap.axhline(0, color='#334155', lw=1)
        ap.set_facecolor('#0b0f16')
        ap.tick_params(colors='#94a3b8', labelsize=8)
        for sp in ap.spines.values():
            sp.set_color('#1e293b')
        ap.set_title('P&L acumulado (pts)', color='#e2e8f0', fontsize=11, pad=8)
        ap.set_xlabel('trade', color='#94a3b8', fontsize=9)

        p = tr.pnl.values
        txt = (
            f"TRADES        {len(tr)}\n"
            f"───────────────\n"
            f"total         {p.sum():+8.0f}\n"
            f"mediana       {np.median(p):+8.1f}\n"
            f"acerto        {(p>0).sum():3d}/{len(p)} ({(p>0).mean()*100:.0f}%)\n"
            f"maior ganho   {p.max():+8.0f}\n"
            f"maior perda   {p.min():+8.0f}\n"
            f"custo         {CUSTO:8.1f}\n"
        )
        ap.text(0.02, -0.34, txt, transform=ap.transAxes, family='monospace',
                fontsize=9, color='#cbd5e1', va='top')
    else:
        ap.text(.5, .5, 'sem trades na janela', color='#94a3b8',
                ha='center', transform=ap.transAxes)

    os.makedirs(OUT, exist_ok=True)
    p_ = os.path.join(OUT, nome)
    plt.savefig(p_, dpi=150, bbox_inches='tight', facecolor='#0b0f16')
    plt.close()
    print('salvo:', p_, f'| {len(tr)} trades')
    return p_


def main():
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    args = [a for a in sys.argv[2:] if not a.startswith('--')]
    contra = '--contra' in sys.argv
    ini = pd.Timestamp(f'{dia} {args[0]}:00') if len(args) >= 1 else pd.Timestamp(f'{dia} 10:15:00')
    fim = pd.Timestamp(f'{dia} {args[1]}:00') if len(args) >= 2 else ini + pd.Timedelta(minutes=15)
    desenha(dia, ini, fim, contra=contra,
            nome=f'trades_{"contra" if contra else "afavor"}_{ini:%H%M}.png')


if __name__ == '__main__':
    main()
