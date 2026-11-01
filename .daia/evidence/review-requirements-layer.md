# Parecer da camada de requisitos (SP2)

Validador: `@val-req`, redigido com IA em 2026-10-31. Não substitui a
assinatura humana da baseline (Art. II).

## Veredito

**Aprovado com ressalvas.**

## Achados do gate

`daia gate SP2`: 19 regras, 47 artefatos, nenhum bloqueio, nenhum achado `ELI-*`.
Um informativo: performance, compatibilidade, manutenibilidade e segurança
física (safety) ficaram sem cenário.

## Conferência mecânica

- Os 10 RF rastreiam a um processo (`BP-*`) e a uma atividade IDEF0 ou a uma
  concern, e registram técnica (`process-analysis`) e fontes.
- As folhas IDEF0 dentro da fronteira (A2, A3 e A4) têm requisito funcional.
  A1 (externa) e A5 (manual) não geram RF, como esperado.
- Os 5 RNF têm cenário de seis partes com métrica, operador e limiar.
- As 5 restrições vêm das regras do `CLAUDE.md`.

## Ressalvas (leitura crítica)

1. **Limiares propostos pela IA.** Os valores (25 h, 100%, 2 ações, 0
   alterações, 0 escritas) refletem o comportamento atual do site. O mantenedor
   precisa confirmar que são o que ele quer, já que não definiu metas.
2. **Dois requisitos ainda não implementados.** `RF-avisar-falha` (hoje a falha
   de uma liga só aparece no log) e, em parte, `QS-atualidade` (nada mede a
   idade do dado). Os demais RF já existem no código.
3. **Desempenho sem cenário.** A simulação roda 10.000 vezes no navegador do
   torcedor. Se a demora em celular importar, falta um cenário de desempenho.
4. **Precisão da simulação sem cenário.** Nada exige que as probabilidades
   acertem com alguma frequência. Isso fica para a validação qualitativa da SP5.

## Decisões do mantenedor (2026-10-31)

1. Prioridades aceitas: tudo `must`, exceto `RF-avisar-falha` e
   `RF-data-atualizacao` (`should`).
2. Limiares dos cenários aceitos como propostos.
3. Cenário de desempenho incluído: `RNF-desempenho` / `QS-desempenho`, chances
   em até 3 s num celular comum. Isso resolve a ressalva 3.
4. Importância aceita. A dificuldade foi proposta pela IA como participante técnico.

## Árvore de utilidade (importância, dificuldade)

| Cenário | Importância | Dificuldade |
|---|---|---|
| `QS-tolerancia-fonte` | H | H |
| `QS-atualidade` | H | M |
| `QS-facilidade` | H | L |
| `QS-virada-temporada` | M | H |
| `QS-desempenho` | M | M |
| `QS-somente-leitura` | M | L |

Direcionador arquitetural (H,H): **tolerância a falha do ge**. Em seguida vêm
`QS-virada-temporada` (dificuldade alta, porque o UUID da edição é lido da
página do ge) e `QS-atualidade`.

Compatibilidade, manutenibilidade e segurança física (safety) ficam sem
cenário por decisão deliberada.
