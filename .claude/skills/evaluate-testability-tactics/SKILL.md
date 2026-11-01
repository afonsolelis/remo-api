---
name: evaluate-testability-tactics
description: Avalie se as decisões que atendem cenários de testabilidade expõem e controlam o estado do sistema e limitam sua complexidade (Bass, Clements & Kazman, cap. 10). Use na SP3 e na reavaliação ATAM da SP4 quando houver cenários com characteristic maintainability e sub_characteristic testability.
---

# Avaliar táticas de testabilidade

Exponha lacunas e consequências; não escolha a tática no lugar do arquiteto.

## Resultado

Em cada `ArchitectureDecision` avaliada, complete:

- `tactics`: táticas que a decisão realiza, no formato `testability/<tática>`.
- `sensitivity_points` e `tradeoff_points`, com os trade-offs conhecidos abaixo.
- `risks`: lacunas que dependem de uma decisão existente.

Relate ao humano os cenários sem nenhuma decisão e as decisões cuja tática não está explícita.

## Fluxo

Antes de produzir artefatos, consulte `daia next --json`, `.daia/guide.md` e os schemas locais em `.daia/schemas/`.

1. Selecione os `QualityScenario` com `characteristic` `maintainability` e sub_characteristic testability. Cenário de `maintainability` sem sub_characteristic entra aqui quando o estímulo é um teste; se o estímulo é uma mudança, use `evaluate-modifiability-tactics`. Comece pelos de importância H no `utility_tree`. Sem `utility_tree`, avalie todos e aponte a falta de priorização. Sem cenários, a skill não se aplica.
2. Leia as decisões cujo `traces_to` inclui cada cenário. Cenário sem decisão é lacuna para `@arch`; não crie a decisão.
3. Para cada componente sob teste, pergunte: consigo levá-lo a um estado arbitrário e observar o resultado?
4. Registre em `tactics` somente táticas que o texto da decisão realiza explicitamente. Se ela cita um mecanismo (ex.: injeção de dependência), registre a tática que ele realiza apenas quando o texto deixar claro; na dúvida, pergunte a `@arch`.
5. Sem tática de controle e observação para o componente, registre lacuna.
6. Percorra o design checklist do §10.3 nas sete categorias: alocação de responsabilidades, modelo de coordenação, modelo de dados, mapeamento entre elementos, gerência de recursos, momento de binding e escolha de tecnologia.
7. Na SP4, rode `daia impact <AD-id>` e reavalie apenas os cenários listados.
8. Devolva as lacunas a `@arch` e registre o resultado com `daia verify` na etapa aplicável.

## Catálogo

**Controlar e observar o estado**

| Tática | Pergunta de verificação |
|---|---|
| `specialized-interfaces` | Há interfaces de teste separadas para leitura, escrita, reset e relatório de estado? |
| `record-playback` | Entradas que cruzam uma interface podem ser gravadas e reproduzidas após falha? |
| `localize-state-storage` | O estado está concentrado em um único lugar, inicializável em qualquer valor? |
| `abstract-data-sources` | Dados vêm de interfaces abstratas, trocáveis por fontes de teste? |
| `sandbox` | Há instância isolada, com virtualização de relógio, rede e recursos? |
| `executable-assertions` | Invariantes e pré/pós-condições críticas são verificados em tempo de execução? |

**Limitar complexidade**

| Tática | Pergunta de verificação |
|---|---|
| `limit-structural-complexity` | Há dependências cíclicas, hierarquias profundas ou dependências externas não isoladas? |
| `limit-nondeterminism` | Paralelismo irrestrito ou outras fontes de não determinismo podem ser eliminadas? Onde não puderem, há record/playback? |

## Trade-offs conhecidos

- Testabilidade × desempenho: interfaces e instrumentação de teste custam ciclos.
- Testabilidade × segurança: interfaces de teste em produção ampliam a superfície de ataque.
- Testabilidade × fidelidade: em sistemas críticos, código de teste em produção difere do código testado.

## Não faz

- Não escreve testes; isso é papel de `write-executable-specification`.
- Não recomenda tática sem cenário que a justifique.
