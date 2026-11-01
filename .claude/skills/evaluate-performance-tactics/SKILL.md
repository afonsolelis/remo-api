---
name: evaluate-performance-tactics
description: Avalie se as decisões que atendem cenários de desempenho controlam a demanda por recursos e gerenciam recursos compartilhados (Bass, Clements & Kazman, cap. 8). Use na SP3 e na reavaliação ATAM da SP4 quando houver cenários com characteristic performance_efficiency.
---

# Avaliar táticas de desempenho

Exponha lacunas e consequências; não escolha a tática no lugar do arquiteto.

## Resultado

Em cada `ArchitectureDecision` avaliada, complete:

- `tactics`: táticas que a decisão realiza, no formato `performance/<tática>`.
- `sensitivity_points` e `tradeoff_points`, com os trade-offs conhecidos abaixo.
- `risks`: lacunas que dependem de uma decisão existente.

Relate ao humano os cenários sem nenhuma decisão e as decisões cuja tática não está explícita.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`.

1. Selecione os `QualityScenario` com `characteristic` `performance_efficiency` (sub_characteristic time behaviour, resource utilization ou capacity) ou `flexibility` com sub_characteristic scalability. Comece pelos de importância H no `utility_tree`. Sem `utility_tree`, avalie todos e aponte a falta de priorização. Sem cenários, a skill não se aplica.
2. Leia as decisões cujo `traces_to` inclui cada cenário. Cenário sem decisão é lacuna para `@arch`; não crie a decisão.
3. Separe o tempo de resposta em processamento e bloqueio, e identifique qual dos dois a decisão afeta.
4. Registre em `tactics` somente táticas que o texto da decisão realiza explicitamente. Se ela cita um padrão (ex.: cache, load balancer), registre a tática que ele realiza apenas quando o texto deixar claro; na dúvida, pergunte a `@arch`.
5. Sem tática de controle de demanda ou de gerência de recurso para o gargalo identificado, registre lacuna.
6. Percorra o design checklist do §8.3 nas sete categorias: alocação de responsabilidades, modelo de coordenação, modelo de dados, mapeamento entre elementos, gerência de recursos, momento de binding e escolha de tecnologia.
7. Na SP4, rode `daia impact <AD-id>` e reavalie apenas os cenários listados.
8. Devolva as lacunas a `@arch` e registre o resultado com `daia verify` na etapa aplicável.

## Catálogo

**Controlar demanda**

| Tática | Pergunta de verificação |
|---|---|
| `manage-sampling-rate` | A frequência de amostragem de fluxos ambientais pode ser reduzida com perda controlada? |
| `limit-event-response` | Eventos acima de uma taxa máxima são limitados? Há política para os excedentes (descartar, registrar, notificar)? |
| `prioritize-events` | Eventos têm prioridade explícita sob escassez? |
| `reduce-overhead` | Intermediários e separações desnecessárias foram removidos, com componentes cooperantes co-localizados? |
| `bound-execution-times` | Algoritmos iterativos têm limite de tempo ou de iterações? |
| `increase-resource-efficiency` | Algoritmos nos caminhos críticos foram revisados? |

**Gerenciar recursos**

| Tática | Pergunta de verificação |
|---|---|
| `increase-resources` | Recurso adicional é a forma mais direta de cumprir a medida? Qual o custo? |
| `introduce-concurrency` | Streams independentes são processados em threads ou processos distintos? |
| `maintain-multiple-copies-computations` | Há réplicas com balanceamento de carga para computação? |
| `maintain-multiple-copies-data` | Há cache ou replicação de dados? Qual a política de consistência? |
| `bound-queue-sizes` | Filas têm tamanho máximo? |
| `schedule-resources` | A política de escalonamento (FIFO, prioridade fixa, RM/DM, EDF, estática) corresponde ao cenário? |

## Trade-offs conhecidos

- Desempenho × modificabilidade: co-location e menos camadas reduzem latência e aumentam acoplamento.
- Desempenho × custo: aumentar recursos é rápido e caro.
- Desempenho × consistência: caches e réplicas exigem política de coerência.

## Não faz

- Não define metas de desempenho; isso é papel do cenário (`specify-quality-scenarios`).
- Não recomenda tática sem cenário que a justifique.
