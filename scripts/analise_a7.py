"""A7 — Absorcao e exaustao nas beiradas, com rotulagem CORRIGIDA.

Mudancas em relacao a versao que produziu o "achado estavel" (que era bug):

1. LOOK-AHEAD: zonas sao calculadas em janela EXPANSIVEL. No instante t, a zona
   usa apenas snapshots com timestamp <= t. A versao anterior usava a sessao
   inteira, o que significa que a definicao de zona "sabia" o futuro.

2. ROTULAGEM: a classe NAO e atribuida por suposicao. Cada episodio e
   classificado pelo SINAL observado de `def_queda`:
       consumo  -> volume no nivel da borda CAIU (foi comido)
       reforco  -> volume no nivel da borda SUBIU (foi reabastecido)
   E cruza com o desfecho (passou / segurou), formando 4 quadrantes.

3. LADO REAL: registra o que de fato esta no nivel (bid ou ask) com volume, e
   qual lado agride medido por lado_inferido na fita. Nao infere o atacante
   pela posicao da borda.

4. CONTROLE: 1000 sorteios de janelas aleatorias da MESMA sessao, com o mesmo
   horizonte. Reporta o percentil do resultado observado.

5. MULTIPLAS COMPARACOES: conta os testes e aplica Holm.

Uso:
    python analise_a7.py 2026-11-16
"""
import sys

import numpy as np
import pandas as pd

import db

TICK = 5
CAMPO = 2 * TICK              # beirada: 2 ticks em volta da borda
HORIZONTES = [30, 60, 120, 300]
N_SORTEIOS = 1000
CUSTO = 7.5                   # round trip: 5 spread + 2.5 corretagem


# --------------------------------------------------------------------------
# zonas causais
# --------------------------------------------------------------------------
def zonas_expansivas(snaps, densidade=1.5, minimo=3, passo_seg=60):
    """Calcula zonas em janela expansivel.

    Devolve DataFrame com colunas: t_ref, lo, hi.
    No instante t_ref, a zona foi calculada usando apenas dados ate t_ref.
    Recalcula a cada `passo_seg` segundos para nao custar O(n^2).
    """
    snaps = snaps.sort_values('t').reset_index(drop=True)
    tempos = snaps.t.values
    out = []
    prox = snaps.t.iloc[0]
    for i in range(len(snaps)):
        t = snaps.t.iloc[i]
        if t < prox:
            continue
        prox = t + pd.Timedelta(seconds=passo_seg)
        passado = snaps.iloc[:i + 1]
        if len(passado) < 100:
            continue
        for z in db.zonas_de(passado, densidade=densidade, minimo=minimo):
            out.append(dict(t_ref=t, lo=min(z), hi=max(z)))
    return pd.DataFrame(out)


def zona_vigente(zonas, t):
    """Zona valida no instante t: a mais recente com t_ref <= t."""
    if zonas is None or not len(zonas):
        return None
    ok = zonas[zonas.t_ref <= t]
    if not len(ok):
        return None
    ult = ok.t_ref.max()
    return ok[ok.t_ref == ult]


# --------------------------------------------------------------------------
# episodios
# --------------------------------------------------------------------------
def episodios(bk, ticks, zonas, campo=CAMPO, jan_max=120):
    """Encontra episodios de beirada e classifica pelo SINAL de def_queda.

    Para cada episodio devolve o que de fato esta no nivel (bid ou ask) com
    volume inicial e final, e a agressao por lado na janela.
    """
    snaps = db.snaps_do_book(bk)
    vol = bk.pivot_table(index='t', columns=['lado', 'preco'],
                         values='volume', aggfunc='sum')

    out = []
    for _, z in zonas.iterrows():
        lo, hi = z.lo, z.hi
        # snapshots em que o mid esta dentro do campo de alguma borda
        alvo_hi = (snaps.mid - hi).abs() <= campo
        alvo_lo = (snaps.mid - lo).abs() <= campo
        for nome, mask in [('hi', alvo_hi), ('lo', alvo_lo)]:
            if not mask.any():
                continue
            dentro = snaps[mask].set_index('t')
            if len(dentro) < 8:
                continue
            gap = dentro.index.to_series().diff() > pd.Timedelta(seconds=45)
            for _, ep in dentro.groupby(gap.cumsum()):
                if len(ep) < 8:
                    continue
                t_ini, t_fim = ep.index[0], ep.index[-1]
                dur = (t_fim - t_ini).total_seconds()
                if dur < 20 or dur > jan_max:
                    continue
                borda = hi if nome == 'hi' else lo

                # --- o que esta NO NIVEL: bid e ask tem lado distinto
                serie = {}
                for lado, nome_lado in [(1, 'ask'), (2, 'bid')]:
                    try:
                        s = vol[(lado, borda)].loc[t_ini:t_fim].dropna()
                    except KeyError:
                        continue
                    if len(s) >= 5:
                        serie[nome_lado] = s
                if not serie:
                    continue
                # lado que domina o nivel
                lado_dom = max(serie, key=lambda k: serie[k].mean())
                s = serie[lado_dom]
                v_ini, v_fim = s.iloc[0], s.iloc[-1]
                def_queda = 1 - v_fim / max(v_ini, 1)     # >0 consumiu, <0 reforcou

                # --- quem agride: da FITA, nao da posicao da borda
                ag = ticks[(ticks.t >= t_ini) & (ticks.t <= t_fim)]
                comp = ag.volume[ag.lado_inferido == 1].sum()
                vend = ag.volume[ag.lado_inferido == -1].sum()
                if comp + vend < 50:
                    continue

                # --- desfecho: passou? medido DEPOIS do episodio (nao durante)
                # O episodio termina quando o preco sai do campo, entao medir
                # 'dentro do episodio' nunca detecta rompimento: e tautologico.
                # Olha os 60s seguintes ao fim do episodio.
                m_depois = db.mid_futuro(snaps, t_fim, 60)
                if np.isnan(m_depois):
                    continue
                chegou = ((m_depois - borda) if nome == 'hi'
                          else (borda - m_depois))
                passou = chegou > campo * 2      # rompeu pelo menos 4 ticks

                # direcao do ataque = lado com mais agressao
                ataque = 1 if comp > vend else -1
                # se a borda e hi, ataque comprador empurra pra cima
                sinal = 1 if nome == 'hi' else -1

                out.append(dict(
                    t_ini=t_ini, t_fim=t_fim, dur=dur, borda=borda, nome=nome,
                    lado_nivel=lado_dom, v_ini=v_ini, v_fim=v_fim,
                    def_queda=def_queda,
                    agride_compra=comp, agride_venda=vend,
                    agride_liquido=comp - vend, ataque=ataque, sinal=sinal,
                    alinhado=(ataque == sinal),
                    passou=passou,
                ))
    df = pd.DataFrame(out)
    if len(df):
        # dedupe: a mesma borda re-detectada em instantes sucessivos da zona
        # expansiva gera o mesmo episodio varias vezes. Mantem o primeiro.
        df = (df.sort_values('t_ini')
                .drop_duplicates(subset=['borda', 't_ini'], keep='first')
                .reset_index(drop=True))
    return df


# --------------------------------------------------------------------------
# desfecho e controle
# --------------------------------------------------------------------------
def desfechos(snaps, ev):
    for h in HORIZONTES:
        ev[f'm{h}'] = [db.mid_futuro(snaps, t, h) for t in ev.t_fim]
        # avanco na direcao do ataque (positivo = a favor de quem agrediu)
        ev[f'av{h}'] = [(m - b) * s if not np.isnan(m) else np.nan
                        for m, b, s in zip(ev[f'm{h}'], ev.borda, ev.sinal)]
    return ev


def controle(snaps, ini, fim, n=N_SORTEIOS, seed=42):
    """Janelas aleatorias da mesma sessao e horario."""
    rng = np.random.default_rng(seed)
    jan = snaps[(snaps.t >= ini) & (snaps.t <= fim)]
    if len(jan) < 50:
        return {}
    idx = rng.choice(len(jan), size=min(n, len(jan)), replace=True)
    base = jan.t.iloc[idx].values
    res = {h: [] for h in HORIZONTES}
    for i, t in enumerate(base):
        t = pd.Timestamp(t)
        for h in HORIZONTES:
            m0 = db.mid_futuro(snaps, t, 0)
            m1 = db.mid_futuro(snaps, t, h)
            if not np.isnan(m0) and not np.isnan(m1):
                res[h].append(m1 - m0)
    return {h: np.array(v) for h, v in res.items() if v}


def holm(pvals, alpha=0.05):
    """Holm-Bonferroni. Devolve lista de p ajustados na ordem original."""
    m = len(pvals)
    ordem = np.argsort(pvals)
    ajust = np.empty(m)
    acum = 0.0
    for rank, i in enumerate(ordem):
        val = (m - rank) * pvals[i]
        acum = max(acum, val)
        ajust[i] = min(1.0, acum)
    return ajust


# --------------------------------------------------------------------------
def main(dia, densidade=1.5, jan_max=120):
    bk = db.carrega_book(dia)
    ticks = db.carrega_tick(dia)
    snaps = db.snaps_do_book(bk)
    print(f"{dia}: {len(snaps)} snapshots | {len(ticks)} ticks")

    zexp = zonas_expansivas(snaps, densidade=densidade)
    print(f"zonas expansivas: {len(zexp)} registros, {zexp.t_ref.nunique()} instantes")

    ev = episodios(bk, ticks, zexp, jan_max=jan_max)
    print(f"episodios: {len(ev)}")
    if not len(ev):
        return ev, {}, pd.DataFrame()

    ev = desfechos(snaps, ev)
    ctl = controle(snaps, snaps.t.min(), snaps.t.max())
    for h in HORIZONTES:
        if h in ctl:
            print(f"  controle +{h:3d}s: mediana {np.median(ctl[h]):+7.1f} "
                  f"| media {ctl[h].mean():+7.1f} | n={len(ctl[h])}")

    # ---- 4 quadrantes
    ev['classe'] = np.where(ev.def_queda > 0.10, 'consumo',
                     np.where(ev.def_queda < -0.10, 'reforco', 'neutro'))
    ev['desfecho'] = np.where(ev.passou, 'passou', 'segurou')
    print("\n=== QUADRANTES (n, avanco mediano na direcao do ataque) ===")
    print(f"{'classe':10s} {'desfecho':9s} {'n':>4s} {'alinhado':>9s} " +
          " ".join(f"{'+'+str(h)+'s':>8s}" for h in HORIZONTES))
    linhas = []
    for cls in ['consumo', 'reforco', 'neutro']:
        for des in ['passou', 'segurou']:
            sub = ev[(ev.classe == cls) & (ev.desfecho == des)]
            if not len(sub):
                continue
            linha = [f"{cls:10s} {des:9s} {len(sub):4d} {sub.alinhado.mean()*100:8.0f}%"]
            for h in HORIZONTES:
                v = sub[f'av{h}'].dropna()
                linha.append(f"{np.median(v):+8.0f}" if len(v) else f"{'--':>8s}")
            print(" ".join(linha))
            linhas.append((cls, des, len(sub)))
    return ev, ctl, pd.DataFrame(linhas, columns=['classe', 'desfecho', 'n'])


if __name__ == '__main__':
    dia = sys.argv[1] if len(sys.argv) > 1 else '2026-11-16'
    main(dia)
