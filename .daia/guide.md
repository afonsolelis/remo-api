# Guia DAIA-E

Este guia orienta o assistente de IA e a pessoa que conduz o projeto. O CLI é a
fonte da verdade: comece sempre por `daia next --json`, que calcula a etapa a
partir das baselines e dos gates atuais.

## Onde está cada coisa

| Caminho | Conteúdo |
|---|---|
| `.daia/model/` | os artefatos do projeto, um JSON por artefato, em qualquer subpasta |
| `.daia/schemas/` | os schemas de cada tipo de artefato |
| `.daia/agents/` | os 23 papéis; leia o do papel antes de produzir |
| `.claude/skills/` ou `.agents/skills/` | as skills, conforme o runtime (Claude ou Codex) |
| `.daia/evidence/` | relatórios da SP4 e da SP5 |
| `.daia/baselines/` | baselines assinadas; não edite à mão |
| `.daia/config.json` | configuração e comandos de verificação por contrato |

## Como produzir um artefato

1. Rode `daia next --json` e leia a skill indicada para a etapa.
2. Leia o agente do papel em `.daia/agents/` (ex.: `analyst.md` na SP1).
3. Leia o schema do tipo em `.daia/schemas/`.
4. Grave o JSON em `.daia/model/`. Todo artefato tem `id` estável com o prefixo
   do tipo (`STK-`, `BD-`, `PER-`...), `kind`, `sprint` e `provenance`
   (`{"drafted_by": "ai-assisted"}` quando a IA redigiu). Referências entre
   artefatos usam os IDs.
5. Rode `daia gate SP<n>` e corrija cada bloqueio. A mensagem diz o que falta e
   qual regra exige.
6. Rode `daia verify SP<n>` para registrar a verificação.
7. Apresente o resultado à pessoa. **Só ela aprova a baseline.** Registre a
   assinatura com `@rec` apenas após autorização explícita, com o nome e a
   justificativa que ela informar.

## Percurso

1. **SP1 — negócio** (`@analyst`, `@pm`, `@ux-design-expert`): partes
   interessadas, preocupações, direcionadores com hipótese, personas com
   evidência, processos em BPMN (arquivo `.bpmn` com uma raia com o nome exato
   de cada persona), decomposição IDEF0 a partir de A0, fronteira (`automation`)
   e a view enterprise. Parecer de `@val-neg`.
2. **SP2 — requisitos** (`@po`, `@pm`, `@qaw`): requisitos elicitados dos
   processos e das atividades IDEF0, com `elicitation` (técnica e fontes),
   `priority` decidida pela pessoa e cenários de qualidade de seis partes com
   medida real. Parecer de `@val-req`.
3. **SP3 — arquitetura** (`@arch`, `@data-engineer`, `@atam`, `@spec`, `@test`):
   modelos estático e dinâmico; a view engineering (modelo `deployment`,
   correspondência com a view lógica); a view technology (correspondência com a
   engenharia, escolhas como decisões com alternativa); táticas arquiteturais
   avaliadas pelas skills `evaluate-*-tactics`; especificação e contratos de
   teste em vermelho. Pareceres de `@val-eng` e `@val-tec`. Rode `daia verify SP3`.
4. **SP4 — implementação** (`@dev`, `@qa`, `@audit`, `@devops`): implemente só
   após a aprovação da SP3, execute os testes e escreva
   `.daia/evidence/quality-report.md` com medidas, limiares e limitações, por
   característica de qualidade.
5. **SP5 — demonstração** (`@val`, `@devops`): escreva
   `.daia/evidence/validation.md` com roteiro, hipótese, resultados e limitações.

Em qualquer sprint, `@sm` trata impedimentos e `@daia-master` indica o agente certo.

## Software existente

Antes da SP1, inventarie código, integrações, testes e documentos existentes.
Registre origem e incertezas em `.daia/evidence/recovery.md`. Recupere as views
com `status: recovered` e peça revisão humana antes de definir `confirmed: true`.
Preserve os testes existentes verdes; contratos novos são escritos antes da
implementação da mudança. Use `--mode existing` no onboarding.

## Execução dos testes

Configure comandos sem shell em `.daia/config.json`, por contrato:

```json
{"verification":{"TC-exemplo":{"command":"node","args":["--test","tests/exemplo.test.js"],"inputs":["src/exemplo.js","package.json"]}}}
```

`daia verify SP3` executa esses comandos e grava código de saída, saída e
fingerprints. Declare em `inputs` todos os arquivos locais que influenciam o
resultado; o arquivo de teste e o modelo entram automaticamente. Dependências
externas, serviços e arquivos omitidos não são cobertos pelo fingerprint.
Atualize `phase` somente conforme o resultado observado. Uma falha em vermelho
exige revisão: o código de saída sozinho não distingue comportamento ausente de
erro no teste.

## Mudanças depois da assinatura

Alterar um artefato coberto por baseline assinada faz `daia status` mostrar
"revisão necessária". Desfazer a alteração restaura o estado assinado; mantê-la
exige nova aprovação da pessoa.

## Limites da validação

O gate verifica estrutura, referências tipadas, arquivos, rastreabilidade e
evidências declaradas. Não certifica conformidade integral com a ISO 42010, não
interpreta semanticamente todo diagrama e não prova que uma arquitetura é boa.
Use testes de arquitetura como contratos para restrições executáveis.
Tradeoffs, fronteiras, adequação e resultados exigem revisão humana.
A assinatura local registra uma aprovação declarada; não autentica identidade.
