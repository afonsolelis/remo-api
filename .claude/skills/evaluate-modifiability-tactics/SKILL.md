---
name: evaluate-modifiability-tactics
description: Avalie se as decisões que atendem cenários de mudança controlam tamanho, coesão, acoplamento e momento do binding (Bass, Clements & Kazman, cap. 7). Use na SP3 e na reavaliação ATAM da SP4 quando houver cenários com characteristic maintainability ou flexibility.
---

# Avaliar táticas de modificabilidade

Exponha lacunas e consequências; não escolha a tática no lugar do arquiteto.

## Resultado

Em cada `ArchitectureDecision` avaliada, complete:

- `tactics`: táticas que a decisão realiza, no formato `modifiability/<tática>`.
- `sensitivity_points` e `tradeoff_points`, com os trade-offs conhecidos abaixo.
- `risks`: lacunas que dependem de uma decisão existente.

Relate ao humano os cenários sem nenhuma decisão e as decisões cuja tática não está explícita.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`.

1. Selecione os `QualityScenario` com `characteristic` `maintainability` (sub_characteristic modularity, reusability, analysability ou modifiability) ou `flexibility` (adaptability ou replaceability). Cenário de `maintainability` sem sub_characteristic entra aqui quando o estímulo é uma mudança; se o estímulo é um teste, use `evaluate-testability-tactics`. Comece pelos de importância H no `utility_tree`. Sem `utility_tree`, avalie todos e aponte a falta de priorização. Sem cenários, a skill não se aplica.
2. Leia as decisões cujo `traces_to` inclui cada cenário. Cenário sem decisão é lacuna para `@arch`; não crie a decisão.
3. Liste as mudanças prováveis que cada cenário descreve. Elas são o critério das perguntas abaixo; não antecipe outras.
4. Registre em `tactics` somente táticas que o texto da decisão realiza explicitamente. Se ela cita um padrão (ex.: camadas, publish-subscribe), registre a tática que ele realiza apenas quando o texto deixar claro; na dúvida, pergunte a `@arch`.
5. Para cada mudança provável, verifique se alguma tática contém sua propagação. Se nenhuma contém, registre lacuna.
6. Percorra o design checklist do §7.3 nas sete categorias: alocação de responsabilidades, modelo de coordenação, modelo de dados, mapeamento entre elementos, gerência de recursos, momento de binding e escolha de tecnologia.
7. Na SP4, rode `daia impact <AD-id>` e reavalie apenas os cenários listados.
8. Devolva as lacunas a `@arch` e registre o resultado com `daia verify` na etapa aplicável.

## Catálogo

**Reduzir tamanho do módulo**

| Tática | Pergunta de verificação |
|---|---|
| `split-module` | Algum módulo acumula responsabilidades que mudam por motivos diferentes? |

**Aumentar coesão**

| Tática | Pergunta de verificação |
|---|---|
| `increase-semantic-coherence` | Responsabilidades não afetadas pelas mudanças prováveis estão no mesmo módulo? |

**Reduzir acoplamento**

| Tática | Pergunta de verificação |
|---|---|
| `encapsulate` | Cada módulo expõe interface explícita e abstrata quanto aos detalhes prováveis de mudança? |
| `use-intermediary` | Dependências diretas entre módulos que mudam juntos foram quebradas por intermediário? |
| `restrict-dependencies` | Há restrição de quem pode depender de quem (camadas, visibilidade)? |
| `refactor` | Duplicação que faz dois módulos sofrerem a mesma mudança foi fatorada? |
| `abstract-common-services` | Serviços quase iguais foram generalizados e parametrizados? |

**Deferir o binding**

| Tática | Pergunta de verificação |
|---|---|
| `defer-binding` | Valores que mudam com frequência são ligados em build, deploy, inicialização ou runtime, conforme o cenário pedir, com mecanismo explícito (arquivo de configuração, plug-in, registro dinâmico)? |

## Trade-offs conhecidos

- Modificabilidade × desempenho: intermediários e separação de responsabilidades custam latência.
- Modificabilidade × custo: binding tardio exige mecanismo que só compensa se a mudança se repetir.

## Não faz

- Não antecipa mudanças que os cenários não descrevem (Art. IV).
- Não recomenda tática sem cenário que a justifique.
