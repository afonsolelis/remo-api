# Parecer da camada de negócio (SP1)

Validador: `@val-neg`, redigido com IA em 2026-10-31. Não substitui a
assinatura humana da baseline (Art. II).

## Veredito

**Aprovado com ressalvas.**

## Achados do gate

`daia gate SP1`: 11 regras, 22 artefatos, nenhum bloqueio, nenhum alerta.
Nenhum achado `BIZ-*`.

## Conferência mecânica

- As personas `PER-torcedor` e `PER-mantenedor` derivam de `STK-torcedor` e `STK-mantenedor` e citam evidência.
- Os três processos (`BP-acompanhar-time`, `BP-avaliar-chances`, `BP-atualizar-dados`) têm BPMN com início, atividades, fluxo, fim e raia com o nome exato da persona.
- O IDEF0 tem raiz A0 e 5 filhos (A1 a A5), dentro da faixa de 3 a 6, com ICOM completo.
- Cada direcionador é sustentado por um processo, e cada concern é tratada pela `VW-enterprise`.

## Ressalvas (leitura crítica)

1. **Evidência fina.** As personas e os direcionadores do torcedor vêm de uma única fonte: as respostas do mantenedor. Nenhum torcedor foi ouvido. Isso é aceitável num projeto pessoal, mas a hipótese da SP5 deve ser confrontada com torcedores.
2. **Hipóteses sem medida.** Por decisão do mantenedor, não há metas numéricas. Na SP5, a validação será qualitativa (demonstração com torcedores), não por métrica.
3. **Processos as-is a partir do código.** `BP-atualizar-dados` descreve o que o sync faz hoje. No passo "Avaliar a falha da atualização", o mantenedor só fica sabendo da falha de uma liga se abrir o log, porque o script termina com sucesso (ver `recovery.md`).
4. **`BD-manutencao-baixa`** vem das regras do `CLAUDE.md` e do histórico do git, não das respostas do onboarding. Confirme se é um direcionador do projeto.

## Perguntas para decisão humana

1. A fronteira está certa: ge externo (A1), coleta, apresentação e simulação no sistema (A2 a A4), interpretação manual pelo torcedor (A5)?
2. A lista de "fora do escopo" na `VW-enterprise.md` (ao vivo, notícias, escalações, contas, notificações, chances em mata-mata) está correta?
3. `BD-manutencao-baixa` entra como direcionador?
4. Quem assina a baseline SP1, e com que justificativa?
