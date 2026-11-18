# CLAUDE.md — contexto do projeto

Este arquivo é lido automaticamente por agentes que usam Claude Code. Se você é
uma IA revisando este repositório, comece por `AI-REVIEW.md`.

## O que é

Pesquisa de microestrutura no mini-índice B3 (WIN). Objetivo: encontrar gatilhos
de absorção e exaustão operáveis em 30 s – 5 min, líquidos de custo.

## As três coisas que você precisa saber antes de opinar

1. **São 2 sessões, não 20.** Nada aqui é conclusivo. O protocolo exige 20.
2. **Toda afirmação tem marcador de evidência** (`docs/00-LEIA-PRIMEIRO.md`).
   Sem marcador = erro de documentação, sinalize.
3. **9 de 10 erros do projeto foram de definição, não de aritmética.** A métrica
   media algo correlato mas diferente do fenômeno. Antes de aceitar uma definição
   nova, pergunte: "se este número estiver alto, o que aconteceu no mercado?"

## Comandos

```bash
# ambiente
source ~/Projetos/quant-lab/.venv/bin/activate

# rodar um teste
cd ~/Projetos/win-estrategia/scripts
python analise_a5b.py 2026-11-16 2026-11-17

# checar se o banco responde
python -c "import db; print(len(db.carrega_tick('2026-11-17')))"
```

## Convenções de código

- Conexão via `scripts/db.py` — **somente leitura**. Script que escreve no banco
  é bug, não feature.
- `ts` volta do SQL como **texto em horário local**. Não reconverta no pandas:
  aplica o deslocamento duas vezes (ver `docs/06-BECOS-SEM-SAIDA.md` §8).
- `lado_inferido`: **+1 compra, −1 venda**. Não é 1/2.
- Sempre mediana, nunca só média.
- Sempre controle da mesma sessão e horário.

## Estrutura

```
docs/      método, hipóteses, resultados, becos sem saída
scripts/   análise (read-only no banco)
```

Dados brutos ficam no banco TimescaleDB local, **nunca** no repositório.
