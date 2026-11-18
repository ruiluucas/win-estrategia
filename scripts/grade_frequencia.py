"""Alvo e stop ancorados na FREQUENCIA do mercado (metodo A: historica).

Ideia do pesquisador: o preco anda em pernadas de tamanho parecido. Entao:
  - alvo = tamanho tipico da pernada a frente
  - stop = abaixo/acima do tamanho minimo que ainda e "pernada"

Implementacao causal:
  - calcula o zigzag do mid ATE o instante da entrada (nunca depois)
  - pega as amplitudes das pernadas concluidas
  - alvo = percentil ALVO_PCT dessas amplitudes
  - stop = percentil STOP_PCT
  - se houver menos de MIN_PERNADAS amostradas, usa fallback em ATR

Saida por alvo ou stop. Uma posicao por vez.

Uso:
    python grade_frequencia.py 2026-11-16
    python grade_frequencia.py 2026-11-16 --contra
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7
import mede_frequencia as mf

CUSTO = 7.5
JAN_ATR = 20
MIN_PERNADAS = 8            # minimo de pernadas para confiar no percentil
FILTRO_ZIG = 48             # pontos minimos de oscilacao para contar pernada
ALVO_PCT = [40, 50, 60, 70, 80]
STOP_PCT = [10, 20, 25, 30, 40]


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.desfechos(snaps, a7.episodios(bk, tk, z)).sort_values('t_fim').reset_index(drop=True)
    return tk, snaps, ev


def atr_series(snaps, jan=JAN_ATR):
    m = snaps.set_index('t').mid
    return m.rolling(f'{jan}s').apply(lambda s: s.max() - s.min(), raw=True).ffill()


def amplitudes_causais(mid, filtro=FILTRO_ZIG, passo=60):
    """Para cada indice, as amplitudes das pernadas concluidas ate ali.

    Recalcula o zigzag a cada `passo` snapshots (custo controlado) e devolve
    um array de listas.
    """
    n = len(mid)
    out = [None] * n
    cache = np.array([])
    ultimo = -passo
    for i in range(n):
        if i - ultimo >= passo and i > 200:
            pts = mf.zigzag(mid[:i], filtro)
            amps = [abs(pts[k][1] - pts[k - 1][1]) for k in range(1, len(pts))]
            cache = np.array(amps) if amps else np.array([])
            ultimo = i
        out[i] = cache
    return out


def simula(snaps, ev, atr, amps, alvo_pct, stop_pct, contra=False):
    mts = snaps.t.values.astype('datetime64[ns]')
    mid = snaps.mid.values
    atr_v = atr.values

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
        a = atr_v[i0]
        if not np.isfinite(a) or a <= 0:
            continue
        dirn = r.ataque if not contra else -r.ataque

        am = amps[i0]
        if am is None or len(am) < MIN_PERNADAS:
            dist = 1.5 * a                 # fallback
            stop = 0.5 * a
        else:
            dist = float(np.percentile(am, alvo_pct))
            stop = float(np.percentile(am, stop_pct))

        # sanidade: alvo e stop tem que ser viaveis
        if dist <= stop or dist < 15 or stop < 8:
            continue
        if dist > 6 * a:
            continue

        pnl, saida, k = None, None, None
        for k in range(i0 + 1, len(mid)):
            d = (mid[k] - ent) * dirn
            if d >= dist:
                pnl, saida = dist, 'alvo'
                break
            if d <= -stop:
                pnl, saida = -stop, 'stop'
                break
        if pnl is None:
            pnl, saida = (mid[-1] - ent) * dirn, 'fim'
            t_sai = snaps.t.iloc[-1]
        else:
            t_sai = pd.Timestamp(mts[k])

        trades.append(dict(t=r.t_fim, pnl=pnl - CUSTO, saida=saida,
                           alvo=dist, stop=stop, n_pernadas=len(am) if am is not None else 0))
        livre = t_sai
    return pd.DataFrame(trades)


def main(dia, contra=False):
    tk, snaps, ev = carrega(dia)
    atr = atr_series(snaps)
    mid = snaps.mid.values
    print(f"{dia} | {'CONTRA' if contra else 'A FAVOR'} | {len(ev)} episodios | custo {CUSTO}")
    print(f"calculando frequencia causal (zigzag a cada 60 snapshots)...")
    amps = amplitudes_causais(mid)
    n_med = np.median([len(a) for a in amps if a is not None and len(a)])
    print(f"pernadas disponiveis (mediana ao longo do dia): {n_med:.0f}\n")

    print(f"{'':>8s}" + "".join(f"alvo_p{a:<4d}" for a in ALVO_PCT))
    print(f"{'stop_p':>8s}" + "".join("─" * 9 for _ in ALVO_PCT))
    res = []
    for sp in STOP_PCT:
        linha = f"{sp:8d}"
        for ap in ALVO_PCT:
            df = simula(snaps, ev, atr, amps, ap, sp, contra)
            tot = df.pnl.sum() if len(df) else 0
            linha += f"{tot:+9.0f}"
            res.append(dict(alvo_pct=ap, stop_pct=sp, total=tot,
                            acerto=(df.pnl > 0).mean() * 100 if len(df) else 0,
                            n=len(df),
                            mediana=df.pnl.median() if len(df) else np.nan))
        print(linha)

    r = pd.DataFrame(res)
    print(f"\n=== TOP 5 POR P&L ===")
    for _, x in r.sort_values('total', ascending=False).head(5).iterrows():
        print(f"  alvo p{x.alvo_pct:.0f} / stop p{x.stop_pct:.0f} → {x.total:+8.0f} pts "
              f"| acerto {x.acerto:4.0f}% | n={x.n:3.0f} | mediana {x.mediana:+6.1f}")

    pos = r[r.total > 0].sort_values('acerto', ascending=False).head(5)
    print(f"\n=== TOP 5 POR ACERTO (total positivo) ===")
    if len(pos):
        for _, x in pos.iterrows():
            print(f"  alvo p{x.alvo_pct:.0f} / stop p{x.stop_pct:.0f} → acerto {x.acerto:4.0f}% "
                  f"| {x.total:+8.0f} pts | n={x.n:3.0f} | mediana {x.mediana:+6.1f}")
    else:
        print("  nenhuma celula positiva")

    m = r.sort_values('total', ascending=False).iloc[0]
    df = simula(snaps, ev, atr, amps, m.alvo_pct, m.stop_pct, contra)
    if len(df):
        p = df.pnl.values
        print(f"\n--- detalhe: alvo p{m.alvo_pct:.0f} / stop p{m.stop_pct:.0f} ---")
        print(f"trades {len(df)} | total {p.sum():+.0f} | mediana {np.median(p):+.1f} "
              f"| acerto {(p>0).sum()}/{len(p)} ({(p>0).mean()*100:.0f}%)")
        print(f"saidas: {df.saida.value_counts().to_dict()}")
        print(f"alvo mediano {df.alvo.median():.0f} | stop mediano {df.stop.median():.0f} "
              f"| R:R {df.alvo.median()/df.stop.median():.2f}")
        top5 = np.sort(p)[::-1][:5].sum()
        print(f"concentracao: top5 = {top5/p.sum()*100:.0f}% do total | "
              f"sem top5 = {p.sum()-top5:+.0f}")
        print(f"\n{len(r)} celulas testadas, 1 sessao — o maximo e overfit.")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    main(dia, contra='--contra' in sys.argv)
