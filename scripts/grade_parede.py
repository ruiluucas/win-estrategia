"""Alvo = PROXIMA PAREDE DE VOLUME a frente do preco. Stop em ATR.

Correcao do pedido: o alvo NAO e o POC do dia. O alvo e o proximo nivel de
preco, a frente da entrada, que concentrou volume relevante — a parede que o
preco vai encontrar no caminho.

Como calcula (tudo causal, so com dados ate o instante da entrada):

  1. Perfil de volume do dia ate agora: volume negociado por preco
     (dos ticks), mais o volume parado no book (snapshots).
  2. Filtra os precos "fortes": volume acima do percentil 80 do perfil.
  3. Se a entrada e de compra, o alvo e o proximo preco forte ACIMA;
     se e de venda, o proximo preco forte ABAIXO.
  4. Se nao houver parede a frente dentro de um limite, usa fallback em ATR.
  5. Stop proporcional ao ATR da janela.

Saida: alvo ou stop. Uma posicao por vez. Sem tempo fixo.

Uso:
    python grade_parede.py 2026-11-16
    python grade_parede.py 2026-11-16 --contra
"""
import sys

import numpy as np
import pandas as pd

import db
import analise_a7 as a7

CUSTO = 7.5
# malha fina de stop, de curto a muito largo
MULT_STOP = [0.25, 0.35, 0.5, 0.65, 0.75, 0.9, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0]
FRACAO_ALVO = [0.25, 0.4, 0.5, 0.65, 0.75, 1.0]
JAN_ATR = 20                        # 60s pegava a queda inteira e dava ATR=120
JAN_POC = 300
PCT_FORTE = 96                      # 80 deixava 50 "paredes" por instante
MIN_SEPARACAO = 2                   # paredes tem que estar a >=2 ticks uma da outra
MAX_ALVO_ATR = 8.0


def carrega(dia):
    bk = db.carrega_book(dia)
    tk = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    z = a7.zonas_expansivas(snaps)
    ev = a7.desfechos(snaps, a7.episodios(bk, tk, z)).sort_values('t_fim').reset_index(drop=True)
    return bk, tk, snaps, ev


def atr_series(snaps, jan=JAN_ATR):
    m = snaps.set_index('t').mid
    amp = m.rolling(f'{jan}s').apply(lambda s: s.max() - s.min(), raw=True)
    return amp.ffill().fillna(amp.median())


def perfil_volume(tk, snaps, tick=5):
    """Volume acumulado por preco, reconstruido por timestamp.

    Devolve lista de (t, {preco: volume_acumulado_ate_ali}).
    Construcao incremental: O(n) e causal.
    """
    tk = tk.sort_values('t')
    precos_t = tk.t.values
    precos_p = (np.round(tk['last'].values / tick) * tick).astype(int)
    vol = tk.volume.values

    # para cada timestamp do book, o perfil ate ali
    mts = snaps.t.values
    idx = np.searchsorted(precos_t, mts, side='right')

    perfis = []
    acum = {}
    cursor = 0
    for n in idx:
        while cursor < n:
            p = precos_p[cursor]
            acum[p] = acum.get(p, 0.0) + vol[cursor]
            cursor += 1
        perfis.append(dict(acum))
    return perfis


def paredes(perfil, pct=PCT_FORTE, minimo_precos=8):
    """Precos com volume acima do percentil indicado, separados entre si.

    PCT_FORTE=96 sobre ~158 precos deixa ~6 paredes, nao 50. A separacao
    minima evita contar 3 ticks vizinhos como 3 paredes distintas.
    """
    if len(perfil) < minimo_precos:
        return np.array([])
    precos = np.array(sorted(perfil.keys()))
    vols = np.array([perfil[p] for p in precos])
    if len(vols) < minimo_precos:
        return np.array([])
    corte = np.percentile(vols, pct)
    fortes = precos[vols >= corte]
    if not len(fortes):
        return np.array([])
    # agrupa vizinhos e fica com o de maior volume de cada grupo
    grupos, atual = [], [fortes[0]]
    for p in fortes[1:]:
        if p - atual[-1] <= MIN_SEPARACAO * 5:
            atual.append(p)
        else:
            grupos.append(atual)
            atual = [p]
    grupos.append(atual)
    return np.array([max(g, key=lambda x: perfil[x]) for g in grupos])


def simula(snaps, ev, atr, perfis, m_stop, frac, contra=False, teto_atr=MAX_ALVO_ATR):
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
        stop = m_stop * a

        # ---- a parede a frente
        par = paredes(perfis[i0])
        alvo = None
        if len(par):
            if dirn > 0:
                acima = par[par > ent]
                if len(acima):
                    alvo = float(acima.min())
            else:
                abaixo = par[par < ent]
                if len(abaixo):
                    alvo = float(abaixo.max())
        if alvo is None:
            alvo = ent + dirn * (frac * 3.0 * a)     # fallback
        dist = abs(alvo - ent) * frac
        if dist > teto_atr * a:
            dist = teto_atr * a
        alvo = ent + dirn * dist
        if dist < 0.3 * a:
            continue                                  # parede colada: sem espaco

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
                           atr=a, alvo=dist, stop=stop,
                           rr=dist / stop if stop else np.nan))
        livre = t_sai
    return pd.DataFrame(trades)


def main(dia, contra=False):
    bk, tk, snaps, ev = carrega(dia)
    atr = atr_series(snaps)
    perfis = perfil_volume(tk, snaps)
    print(f"{dia} | {'CONTRA' if contra else 'A FAVOR'} | {len(ev)} episodios | custo {CUSTO}")
    print(f"ATR mediano {atr.median():.1f} pts")

    n_par = np.mean([len(paredes(p)) for p in perfis[::50]])
    print(f"paredes detectadas (media): {n_par:.0f} precos fortes por instante\n")

    # grade com P&L E acerto por celula
    print(f"{'':>6s}" + "".join(f"f={f:<6.2f}" for f in FRACAO_ALVO) + "  <- fracao da parede")
    print(f"{'stop':>6s}" + "".join("─" * 9 for _ in FRACAO_ALVO))
    res = []
    for s in MULT_STOP:
        linha = f"{s:6.2f}"
        for f in FRACAO_ALVO:
            df = simula(snaps, ev, atr, perfis, s, f, contra)
            tot = df.pnl.sum() if len(df) else 0
            ac = (df.pnl > 0).mean() * 100 if len(df) else 0
            n = len(df)
            res.append(dict(stop=s, frac=f, total=tot, acerto=ac, n=n,
                            mediana=df.pnl.median() if n else np.nan))
            linha += f"{tot:+9.0f}"
        print(linha)

    r = pd.DataFrame(res)

    print(f"\n=== TOP 5 POR P&L ===")
    for _, x in r.sort_values('total', ascending=False).head(5).iterrows():
        print(f"  stop {x.stop:.2f}x · frac {x.frac:.2f} → {x.total:+8.0f} pts "
              f"| acerto {x.acerto:4.0f}% | n={x.n:3.0f} | mediana {x.mediana:+6.1f}")

    print(f"\n=== TOP 5 POR ACERTO (com total positivo) ===")
    pos = r[r.total > 0].sort_values('acerto', ascending=False).head(5)
    if len(pos):
        for _, x in pos.iterrows():
            print(f"  stop {x.stop:.2f}x · frac {x.frac:.2f} → acerto {x.acerto:4.0f}% "
                  f"| {x.total:+8.0f} pts | n={x.n:3.0f} | mediana {x.mediana:+6.1f}")
    else:
        print("  nenhuma celula com total positivo")

    print(f"\n=== RELACAO STOP -> ACERTO (melhor fracao por stop) ===")
    print(f"{'stop':>6s} {'alvo':>5s} {'acerto':>7s} {'total':>9s} {'n':>4s} {'mediana':>8s}")
    for s in MULT_STOP:
        sub = r[r.stop == s].sort_values('total', ascending=False)
        if not len(sub):
            continue
        x = sub.iloc[0]
        print(f"{s:6.2f} {x.frac:5.2f} {x.acerto:6.0f}% {x.total:+9.0f} {x.n:4.0f} {x.mediana:+8.1f}")

    melhor = r.sort_values('total', ascending=False).iloc[0]
    df = simula(snaps, ev, atr, perfis, melhor.stop, melhor.frac, contra)
    if len(df):
        p = df.pnl.values
        print(f"\n--- detalhe da melhor: stop {melhor.stop:.2f}x / frac {melhor.frac:.2f} ---")
        print(f"trades {len(df)} | total {p.sum():+.0f} | mediana {np.median(p):+.1f} "
              f"| acerto {(p>0).sum()}/{len(p)} ({(p>0).mean()*100:.0f}%)")
        print(f"saidas: {df.saida.value_counts().to_dict()}")
        print(f"alvo mediano {df.alvo.median():.0f} pts | stop mediano {df.stop.median():.0f} pts "
              f"| R:R mediano {df.rr.median():.2f}")
        print(f"\nATENCAO: {len(r)} celulas testadas em 1 sessao — o maximo e overfit.")


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    main(dia, contra='--contra' in sys.argv)
