"""Alvo e stop DINAMICOS: ATR e POC de volume.

Duas referencias de risco, em vez de pontos fixos:

  ATR  = average true range do mid em janela curta. Alvo e stop proporcionais
         a volatilidade corrente. Em mercado calmo, stop curto; em volatil, largo.

  POC  = preco de maior volume negociado ate o momento (point of control,
         janela movel). Stop posto na banda de preco de maior liquidez:
         se o preco atravessa o POC, a tese morreu.

Saida: alvo ou stop, sem tempo fixo. Uma posicao por vez.

Uso:
    python grade_atr_poc.py 2026-11-16
    python grade_atr_poc.py 2026-11-16 --contra
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7

CUSTO = 7.5
MULT_ALVO = [2.0, 3.0, 4.0, 5.0]
MULT_STOP = [0.5, 1.0, 1.5, 2.0]
JAN_ATR = 60          # segundos para o ATR
JAN_POC = 300         # segundos para o POC


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.desfechos(snaps, a7.episodios(bk, tk, z)).sort_values('t_fim').reset_index(drop=True)
    return snaps, tk, ev


def atr_series(snaps, jan=JAN_ATR):
    """Range medio do mid na janela, em pontos. Causal: usa so o passado."""
    m = snaps.set_index('t').mid
    # amplitude em janela: max - min dos ultimos jan segundos
    amp = m.rolling(f'{jan}s').apply(lambda s: s.max() - s.min(), raw=True)
    return amp.ffill().fillna(amp.median())


def poc_series(tk, snaps, jan=JAN_POC):
    """Preco com maior volume negociado na janela, causal."""
    tk = tk.copy()
    tk['b'] = tk.t.dt.floor('5s')
    # volume por preco a cada 5s
    v = tk.groupby(['b', 'last']).volume.sum().reset_index()
    out = {}
    for b, g in v.groupby('b'):
        out[b] = g.loc[g.volume.idxmax(), 'last']
    ser = pd.Series(out).sort_index()
    # propaga para cada timestamp do book
    idx = snaps.t.dt.floor('5s')
    poc = idx.map(ser).ffill()
    return poc.fillna(snaps.mid)


def simula(snaps, ev, atr, poc, m_alvo, m_stop, usar_poc=False, contra=False):
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values
    atr_v = atr.values
    poc_v = poc.values
    t_v = snaps.t.values

    def i_de(t):
        return int(np.searchsorted(mts, np.datetime64(pd.Timestamp(t)), side='right')) - 1

    trades = []
    livre = None
    for r in ev.itertuples():
        if livre is not None and r.t_fim < livre:
            continue
        i0 = i_de(r.t_fim)
        if i0 < 0 or i0 >= len(mid):
            continue
        ent = mid[i0]
        dirn = r.ataque if not contra else -r.ataque
        a = atr_v[i0]
        if not np.isfinite(a) or a <= 0:
            continue
        alvo = m_alvo * a
        stop = m_stop * a
        if usar_poc:
            # ancora o stop na distancia ao POC, na direcao contraria
            d_poc = abs(ent - poc_v[i0])
            if d_poc > 0:
                stop = max(min(d_poc, 4 * a), 0.3 * a)   # limita entre 0.3 e 4 ATR

        pnl, saida, k = None, None, None
        for k in range(i0 + 1, len(mid)):
            d = (mid[k] - ent) * dirn
            if d >= alvo:
                pnl, saida = alvo, 'alvo'
                break
            if d <= -stop:
                pnl, saida = -stop, 'stop'
                break
        if pnl is None:
            pnl, saida = (mid[-1] - ent) * dirn, 'fim'
            t_sai = snaps.t.iloc[-1]
        else:
            t_sai = pd.Timestamp(t_v[k])

        trades.append(dict(t=r.t_fim, pnl=pnl - CUSTO, saida=saida,
                           atr=a, alvo=alvo, stop=stop))
        livre = t_sai
    return pd.DataFrame(trades)


def imprime_grade(df_titulo, fn, alvos, stops):
    print(f"\n{df_titulo}")
    print(f"{'':>6s}" + "".join(f"{a:>9.1f}" for a in alvos) + "   <- alvo (x ATR)")
    print(f"{'stop':>6s}" + "".join("─" * 9 for _ in alvos))
    melhor = (-1e9, None, None)
    for s in stops:
        linha = f"{s:6.1f}"
        for a in alvos:
            df = fn(a, s)
            tot = df.pnl.sum() if len(df) else 0
            linha += f"{tot:+9.0f}"
            if tot > melhor[0]:
                melhor = (tot, a, s)
        print(linha)
    print(f"melhor: alvo {melhor[1]:.1f}x / stop {melhor[2]:.1f}x = {melhor[0]:+.0f}")
    return melhor


def main(dia, contra=False):
    snaps, tk, ev = carrega(dia)
    print(f"{dia} | {'CONTRA' if contra else 'A FAVOR'} | {len(ev)} episodios | custo {CUSTO}")

    atr = atr_series(snaps)
    poc = poc_series(tk, snaps)
    print(f"ATR mediano: {atr.median():.1f} pts (p10 {atr.quantile(.1):.1f}, p90 {atr.quantile(.9):.1f})")
    print(f"distancia media ao POC: {(snaps.mid - poc).abs().median():.1f} pts")

    m1 = imprime_grade(
        "=== ALVO/STOP EM MULTIPLOS DE ATR ===",
        lambda a, s: simula(snaps, ev, atr, poc, a, s, contra=contra),
        MULT_ALVO, MULT_STOP)

    m2 = imprime_grade(
        "=== STOP ANCORADO NO POC (alvo em ATR) ===",
        lambda a, s: simula(snaps, ev, atr, poc, a, s, usar_poc=True, contra=contra),
        MULT_ALVO, MULT_STOP)

    # detalhe dos dois melhores
    for rot, arg in [('ATR puro', False), ('ATR + POC', True)]:
        mult = m1 if not arg else m2
        df = simula(snaps, ev, atr, poc, mult[1], mult[2], usar_poc=arg, contra=contra)
        p = df.pnl.values
        print(f"\n--- {rot}: alvo {mult[1]:.1f}x / stop {mult[2]:.1f}x ---")
        print(f"trades {len(df)} | total {p.sum():+.0f} | mediana {np.median(p):+.1f} "
              f"| acerto {(p>0).sum()}/{len(p)} ({(p>0).mean()*100:.0f}%)")
        print(f"saidas: {df.saida.value_counts().to_dict()}")
        print(f"alvo medio {df.alvo.median():.0f} pts | stop medio {df.stop.median():.0f} pts")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    main(dia, contra='--contra' in sys.argv)
