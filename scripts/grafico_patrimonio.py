"""Curva de patrimonio da A7, com custo. Sessao 16/11.

IMPORTANTE: isto NAO e performance de estrategia validada. E o resultado de
uma hipotese nao replicada, numa sessao, in-sample. Serve para ver a FORMA da
distribuicao (se o resultado depende de poucos eventos), nao para estimar
retorno.

Gera 3 paineis:
  1. Curva de patrimonio, apostando A FAVOR do agressor (a hipotese original)
  2. Curva de patrimonio, apostando CONTRA o agressor (a hipotese invertida)
  3. Distribuicao dos resultados por evento

Uso: python grafico_patrimonio.py 2026-11-16
"""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import db
import analise_a7 as a7

CUSTO = 7.5          # round trip: 5 spread + 2.5 corretagem
HORIZONTE = 60       # segundos


def eventos(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.episodios(bk, tk, z)
    ev = a7.desfechos(snaps, ev)
    ev['classe'] = np.where(ev.def_queda > 0.10, 'consumo',
                     np.where(ev.def_queda < -0.10, 'reforco', 'neutro'))
    ev['desfecho'] = np.where(ev.passou, 'passou', 'segurou')
    return ev


def curva(ev, contra=False):
    """P&L acumulado, liquido de custo, na ordem cronologica."""
    e = ev.sort_values('t_fim').copy()
    mov = e[f'av{HORIZONTE}'].values          # avanco na direcao do ataque
    if contra:
        mov = -mov
    pnl = mov - CUSTO
    return e.t_fim.values, np.cumsum(pnl), pnl


def main(dia):
    ev = eventos(dia)
    if not len(ev):
        print('sem eventos'); return

    t_fav, cum_fav, pnl_fav = curva(ev, contra=False)
    t_con, cum_con, pnl_con = curva(ev, contra=True)

    fig, axes = plt.subplots(3, 1, figsize=(13, 11), sharex=False)
    fig.suptitle(f'A7 — absorcao/exaustao | {dia} | n={len(ev)} episodios | '
                 f'custo {CUSTO} pts/trade\n'
                 f'HIPOTESE NAO REPLICADA — in-sample, 1 sessao, sem valor preditivo',
                 fontsize=10)

    # 1 — a favor do agressor
    ax = axes[0]
    ax.plot(t_fav, cum_fav, lw=1.6, color='#2f7fc1')
    ax.axhline(0, color='#666', lw=.8, ls='--')
    ax.set_title(f'APOSTANDO A FAVOR do agressor — final {cum_fav[-1]:+.0f} pts '
                 f'| mediana/trade {np.median(pnl_fav):+.1f}', fontsize=9)
    ax.set_ylabel('P&L acumulado (pts)')
    ax.grid(alpha=.25)

    # 2 — contra o agressor
    ax = axes[1]
    ax.plot(t_con, cum_con, lw=1.6, color='#b5432f')
    ax.axhline(0, color='#666', lw=.8, ls='--')
    ax.set_title(f'APOSTANDO CONTRA o agressor — final {cum_con[-1]:+.0f} pts '
                 f'| mediana/trade {np.median(pnl_con):+.1f}', fontsize=9)
    ax.set_ylabel('P&L acumulado (pts)')
    ax.grid(alpha=.25)

    # 3 — distribuicao
    ax = axes[2]
    ax.hist(pnl_con, bins=30, color='#b5432f', alpha=.7, edgecolor='white')
    ax.axvline(0, color='#333', lw=1)
    ax.axvline(np.median(pnl_con), color='#000', lw=1.4, ls='--',
               label=f'mediana {np.median(pnl_con):+.0f}')
    ax.set_title(f'Distribuicao por evento (contra o agressor) — '
                 f'acertos {(pnl_con>0).sum()}/{len(pnl_con)} '
                 f'({(pnl_con>0).mean()*100:.0f}%)', fontsize=9)
    ax.set_xlabel('P&L por evento (pts, liquido de custo)')
    ax.set_ylabel('frequencia')
    ax.legend(fontsize=8)
    ax.grid(alpha=.25)

    for ax in axes[:2]:
        ax.tick_params(axis='x', labelsize=7)
    plt.tight_layout()
    out = f'/home/rui/Projetos/win-estrategia/out/patrimonio_{dia}.png'
    import os
    os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=140, bbox_inches='tight')
    print('salvo:', out)

    print(f"\n=== RESUMO ===")
    print(f"n eventos            : {len(ev)}")
    for nome, pnl in [('a favor', pnl_fav), ('contra', pnl_con)]:
        pos = pnl[pnl > 0]
        neg = pnl[pnl < 0]
        maior = pnl.max()
        print(f"\n{nome:8s}: total {pnl.sum():+8.0f} | mediana {np.median(pnl):+6.1f} "
              f"| acerto {(pnl>0).sum():3d}/{len(pnl)} ({(pnl>0).mean()*100:3.0f}%)")
        print(f"          maior ganho {maior:+6.0f} = {maior/pnl.sum()*100 if pnl.sum() else 0:5.1f}% do total"
              if pnl.sum() else "")
        if len(pos) and len(neg):
            print(f"          ganho medio {pos.mean():+6.1f} | perda media {neg.mean():+6.1f} "
                  f"| razao {abs(pos.mean()/neg.mean()):.2f}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '2026-11-16')
