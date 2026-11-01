---
name: evaluate-availability-tactics
description: Avalie se as decisões que atendem cenários de confiabilidade aplicam táticas de detecção, recuperação e prevenção de defeitos (Bass, Clements & Kazman, cap. 5). Use na SP3 e na reavaliação ATAM da SP4 quando houver cenários com characteristic reliability.
---

# Avaliar táticas de disponibilidade

Exponha lacunas e consequências; não escolha a tática no lugar do arquiteto.

## Resultado

Em cada `ArchitectureDecision` avaliada, complete:

- `tactics`: táticas que a decisão realiza, no formato `availability/<tática>`.
- `sensitivity_points` e `tradeoff_points`, com os trade-offs conhecidos abaixo.
- `risks`: lacunas que dependem de uma decisão existente.

Relate ao humano os cenários sem nenhuma decisão e as decisões cuja tática não está explícita.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`.

1. Selecione os `QualityScenario` com `characteristic` `reliability` (sub_characteristic faultlessness, availability, fault tolerance ou recoverability). Comece pelos de importância H no `utility_tree`. Sem `utility_tree`, avalie todos e aponte a falta de priorização. Sem cenários, a skill não se aplica.
2. Leia as decisões cujo `traces_to` inclui cada cenário. Cenário sem decisão é lacuna para `@arch`; não crie a decisão.
3. Registre em `tactics` somente táticas que o texto da decisão realiza explicitamente. Se ela cita um padrão, registre a tática que ele realiza apenas quando o texto deixar claro; na dúvida, pergunte a `@arch`.
4. Responda às perguntas de verificação das famílias pertinentes ao estímulo do cenário. O catálogo não é checklist: uma tática ausente só é lacuna quando o cenário a exige.
5. Percorra o design checklist do §5.3 nas sete categorias: alocação de responsabilidades, modelo de coordenação, modelo de dados, mapeamento entre elementos, gerência de recursos, momento de binding e escolha de tecnologia.
6. Na SP4, rode `daia impact <AD-id>` e reavalie apenas os cenários listados.
7. Devolva as lacunas a `@arch` e registre o resultado com `daia verify` na etapa aplicável.

## Catálogo

**Detectar defeitos**

| Tática | Pergunta de verificação |
|---|---|
| `ping-echo` | Há verificação de alcançabilidade entre nós com timeout definido? |
| `monitor` | Existe componente que observa a saúde de processos, recursos e rede? |
| `heartbeat` | O monitorado envia sinal periódico, ou um watchdog é reiniciado? |
| `time-stamp` | Sequência incorreta de eventos em mensagens é detectada? |
| `sanity-checking` | Saídas de operações são validadas contra o conhecimento de design? |
| `condition-monitoring` | Invariantes do processo (ex.: checksums) são verificados? |
| `voting` | Para falhas críticas, há redundância com voter? Qual tipo (replicação, funcional, analítica)? |
| `exception-detection` | Exceções de sistema, de parâmetro e de timeout são detectadas? |
| `self-test` | Componentes críticos têm autoteste iniciado por si ou pelo monitor? |

**Recuperar de defeitos**

| Tática | Pergunta de verificação |
|---|---|
| `active-redundancy` | O tempo de failover exigido admite standby quente? |
| `passive-redundancy` | Basta standby com checkpoint periódico? |
| `spare` | O cenário tolera recuperação por reinício (cold spare)? |
| `exception-handling` | Exceções são tratadas, não apenas propagadas até a falha? |
| `rollback` | Há checkpoints para voltar a um estado bom? |
| `software-upgrade` | Atualização sem interromper o serviço está prevista (ISSU)? |
| `retry` | Falhas transitórias são retentadas com limite? |
| `ignore-faulty-behavior` | Mensagens de fontes espúrias são ignoradas (ex.: ACL contra DoS)? |
| `degradation` | Funções críticas sobrevivem à perda das demais? |
| `reconfiguration` | Responsabilidades são reatribuídas aos recursos restantes? |
| `shadow` | Componente reparado passa por período sombra antes de voltar a ser ativo? |
| `state-resynchronization` | Após reparo, o estado é resincronizado? |
| `escalating-restart` | A granularidade do reinício é escalonada conforme a gravidade? |
| `non-stop-forwarding` | Em plano de controle com reinício, o plano de dados continua operando? |

**Prevenir defeitos**

| Tática | Pergunta de verificação |
|---|---|
| `removal-from-service` | Há rejuvenescimento periódico para limpar defeitos latentes? |
| `transactions` | Atualizações concorrentes têm semântica ACID (ex.: two-phase commit)? |
| `predictive-model` | Parâmetros operacionais preveem falhas antes de ocorrerem? |
| `exception-prevention` | Há proteções contra exceções previsíveis (limites, ponteiros inteligentes)? |
| `increase-competence-set` | Casos que hoje geram exceção podem ser tratados como parte da operação normal? |

## Trade-offs conhecidos

- Disponibilidade × custo: redundância ativa é cara; cold spare é barato e lento.
- Disponibilidade × evolução: parameter typing rígido dificulta mudanças de formato.

## Não faz

- Não cria cenário de confiabilidade que não esteja nos requisitos (Art. IV).
- Não recomenda tática sem cenário que a justifique.
