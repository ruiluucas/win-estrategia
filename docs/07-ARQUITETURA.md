# 07 — Arquitetura

Três repositórios, papéis separados. Misturar os três foi uma fonte de erro.

```
~/Projetos/win-book-lab       coleta + app de visualização
~/Projetos/mt5-bridge         ponte RPyC para o MetaTrader 5
~/Projetos/win-estrategia     ESTE repo: método, análise, evidência
```

## Fronteiras

### win-book-lab — captura e visualização

**Responsabilidade:** falar com o MT5, gravar book e tick no banco, renderizar
Bookmap e candles. **Não decide nada sobre estratégia.**

Não deve conter lógica de sinal. Se aparecer um `if` que decida comprar ou
vender, ele está no repositório errado.

### mt5-bridge — transporte

**Responsabilidade:** expor `MetaTrader5` via RPyC a partir de um processo rodando
dentro do prefixo Wine. Substituível: qualquer coisa que entregue book e tick
serve.

### win-estrategia — este repositório

**Responsabilidade:** definições de hipótese, código de análise, evidência
resumida. **Não contém dados e não coleta.**

O `scripts/` daqui abre conexão somente-leitura no banco. Nenhum script deste
repositório deve escrever no banco de dados.

## Regra de dependência

```
win-estrategia  →  lê banco   (nunca escreve, nunca coleta)
win-book-lab    →  escreve banco
mt5-bridge      →  entrega dados ao win-book-lab
```

Este repositório pode ser lido e executado sem o `win-book-lab` estar rodando,
desde que o banco tenha dados.

## O que um revisor precisa para reproduzir

1. Banco TimescaleDB com as tabelas de `02-DADOS.md` e pelo menos uma sessão.
2. Python 3.12 com `psycopg2`, `pandas`, `numpy`, `scipy`, `arch`.
3. Rodar `scripts/<analise>.py` — cada um imprime o resultado e o comando usado.

`[DESCONHECIDO]` Não há dataset congelado versionado. Isso significa que a
reprodução exata de um número antigo depende de o banco local ainda ter aquela
sessão. É uma limitação conhecida e não resolvida — a alternativa seria versionar
dados, o que foi descartado por tamanho (~800 MB/sessão).

## Convenção de nomes de script

| prefixo | papel |
|---|---|
| `analise_` | um teste de hipótese completo |
| `diag_` | diagnóstico exploratório, não é teste |
| `perfil_` | descritor de contexto (zonas, tempo, volume) |

Cada script imprime, no final, um bloco `=== RESUMO ===` com os números que vão
para `05-RESULTADOS.md`.
