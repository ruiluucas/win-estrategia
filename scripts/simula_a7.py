"""Simulador A7 com posicao unica e duracao configravel.

Regras novas em relacao ao script de episodios (que contava todo evento):

1. UMA OPERACAO POR VEZ. Se ha posicao aberta, novos gatilhos sao ignorados.
   Isso e o que um operador real faz — nao se empilha posicao no mesmo fluxo.

2. DURACAO DA OPERACAO configuravel: sai por tempo, por alvo ou por stop,
   o que vier primeiro. Testa 30/60/120/300 s de tempo maximo.

3. ALVO e STOP em pontos fixos, e também so por tempo (sem alvo/stop).

4. Custo de 7,5 pts por round trip, descontado no resultado.

Uso:
    python simula_a7.py 2026-11-16
    python simula_a7.py 2026-11-16 --contra
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7

CUSTO = 7.5


def episodios_ordenados(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.episodios(bk, tk, z)
    if not len(ev):
        return None, None, None
    ev = a7.desfechos(snaps, ev)
    ev = ev.sort_values('t_fim').reset_index(drop=True)
    return snaps, ev, bk


def simula(snaps, ev, contra=False, t_max=60, alvo=None, stop=None):
    """Uma posicao por vez. Sai por tempo, alvo ou stop — o que vier primeiro.

    contra=False -> aposta a favor do agressor
    contra=True  -> aposta contra o agressor
    """
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values

    def mid_em(t):
        j = np.searchsorted(mts, np.datetime64(pd.Timestamp(t)), side='right') - 1
        if j < 0 or j >= len(mid):
            return np.nan
        return mid[j]

    trades = []
    livre_em = None          # horario em que a posicao fica livre

    for r in ev.itertuples():
        if livre_em is not None and r.t_fim < livre_em:
            continue                                    # posicao ocupada

        ent = mid_em(r.t_fim)
        if np.isnan(ent):
            continue
        # direcao: a favor do ataque, ou contra ele
        dirn = r.ataque if not contra else -r.ataque

        saida_t = r.t_fim + pd.Timedelta(seconds=t_max)
        pnl = None
        saiu_por = 'tempo'

        # caminha ate t_max procurando alvo/stop
        if alvo is not None or stop is not None:
            ini = np.searchsorted(mts, np.datetime64(pd.Timestamp(r.t_fim)), side='right')
            fim = np.searchsorted(mts, np.datetime64(pd.Timestamp(saida_t)), side='right')
            for k in range(ini, min(fim, len(mid))):
                d = (mid[k] - ent) * dirn
                if alvo is not None and d >= alvo:
                    pnl = alvo
                    saiu_por = 'alvo'
                    break
                if stop is not None and d <= -stop:
                    pnl = -stop
                    saiu_por = 'stop'
                    break

        if pnl is None:
            mf = mid_em(saida_t)
            pnl = (mf - ent) * dirn if not np.isnan(mf) else np.nan

        if np.isnan(pnl):
            continue
        trades.append(dict(
            t_ent=r.t_fim, borda=r.borda, classe=(
                'consumo' if r.def_queda > .10 else
                'reforco' if r.def_queda < -.10 else 'neutro'),
            desfecho='passou' if r.passou else 'segurou',
            pnl_bruto=pnl, pnl=pnl - CUSTO, saida=saiu_por,
        ))
        livre_em = saida_t

    return pd.DataFrame(trades)


def relatorio(df, rotulo):
    if not len(df):
        print(f"{rotulo}: sem trades")
        return None
    p = df.pnl.values
    pos, neg = p[p > 0], p[p < 0]
    maior = p.max()
    total = p.sum()
    print(f"{rotulo:38s} n={len(df):3d} | total {total:+8.0f} | mediana {np.median(p):+6.1f} "
          f"| acerto {(p>0).sum():3d}/{len(p)} ({(p>0).mean()*100:3.0f}%) "
          f"| maior {maior:+6.0f}")
    return dict(n=len(df), total=total, mediana=np.median(p),
                acerto=(p > 0).mean(), pnl=p)


def main(dia, contra=False):
    snaps, ev, bk = episodios_ordenados(dia)
    if snaps is None:
        print('sem episodios'); return
    print(f"{dia}: {len(ev)} episodios totais | direcao: "
          f"{'CONTRA o agressor' if contra else 'A FAVOR do agressor'}")
    print(f"custo {CUSTO} pts/trade | uma posicao por vez\n")

    print("=== SO POR TEMPO (sem alvo/stop) ===")
    for t in [30, 60, 120, 300]:
        df = simula(snaps, ev, contra=contra, t_max=t)
        relatorio(df, f"  tempo max {t}s")

    print("\n=== TEMPO 60s + ALVO/STOP ===")
    for alvo, stop in [(None, None), (30, 30), (50, 25), (100, 50), (50, 50)]:
        df = simula(snaps, ev, contra=contra, t_max=60, alvo=alvo, stop=stop)
        rot = f"  alvo {alvo or '—'} / stop {stop or '—'}"
        relatorio(df, rot)

    print("\n=== TEMPO 300s + ALVO/STOP ===")
    for alvo, stop in [(50, 50), (100, 50), (150, 75)]:
        df = simula(snaps, ev, contra=contra, t_max=300, alvo=alvo, stop=stop)
        relatorio(df, f"  alvo {alvo} / stop {stop}")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    contra = '--contra' in sys.argv
    main(dia, contra)
