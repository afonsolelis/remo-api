# Parecer de QA (SP4)

Revisor: `@qa`, redigido com IA em 2026-10-31.

## Parecer: **CONCERNS**

Nenhum problema CRITICAL ou HIGH. Os itens MEDIUM ficam como dívida, se o
mantenedor aceitar.

## Verificação de falso positivo

`TC-avisar-falha` (os dois casos) e os cinco contratos de `calculos.js` estavam
vermelhos na SP3 pelo motivo esperado (código de saída 0 e módulo ausente) e
passaram depois da implementação. Os contratos já verdes continuaram verdes.

## Revisão do diff

- **Segurança:** nenhum segredo novo; a chave publishable continua a mesma; não
  há entrada de usuário nova. As mensagens de falha do sync vão para o log do
  Actions, que é privado ao dono do repositório.
- **Testabilidade:** `calculos.js` não tem DOM nem rede, e o sorteio é injetável.
- **Escopo:** nenhuma funcionalidade fora da especificação. `zonaDaPosicao` ficou
  em `app.js` porque só a tela usa.

## Itens

| Severidade | Item |
|---|---|
| MEDIUM | `usou_reserva` é estado de módulo, limpo no começo do `main`. Funciona, mas é acoplamento implícito entre `uuid_atual` e `main`; foi escolhido para preservar o contrato verde de `TC-virada-temporada`. |
| MEDIUM | `RF-data-atualizacao` não tem teste automatizado. |
| MEDIUM | O desempenho no celular não foi medido (proxy no Node). |
| LOW | `simular` ainda usa `structuredClone` uma vez, fora do laço, para a tabela atual. Custo desprezível. |
