# Árvore de utilidade — passo 5 do ATAM

Sistema analisado: o dashboard **Meu time no Brasileirão / Remo** em produção no Railway.

## Escopo e premissas

O pedido original previa um site estático que lê o Postgres do Supabase pela API REST (PostgREST). Ele mandava ler `app.js`, `supabase/schema.sql`, `scripts/sync_supabase.py`, `.daia/model/scenarios/` e `.daia/evidence/atam-sp3.md` (risco R4). Nenhum desses artefatos existe neste repositório, nem nos branches ou no histórico do git. Por decisão do responsável, a árvore descreve **o sistema que de fato está em produção**:

- **Serviço único no Railway**: Streamlit (`app.py`, `src/dashboard.py`) e agendador (`scripts/scheduler.py`) rodam no mesmo contêiner, iniciados por `scripts/start.sh`.
- **Armazenamento**: JSON em volume montado em `/app/data`, sem MongoDB (`MONGO_URL` vazio). A gravação é atômica (`src/store.py:45`).
- **Dados de entrada**: API do Cartola, ge e ESPN, consultadas só pelo atualizador. O caminho de leitura do visitante não chama APIs externas.
- **Ociosidade**: o serviço dorme quando não há acesso. Ao acordar, o agendador atualiza se o snapshot tiver mais de `STALE_HOURS=20` h.
- **Administração**: a página `/admin` tem login por `ADMIN_USER` e `ADMIN_PASSWORD` e dispara a atualização completa.

Consequências para a análise:

- O risco **R4** do ATAM anterior não pôde ser consultado, então nenhum achado deste documento se refere a ele.
- Os cenários de interface já existentes (legibilidade, uso no celular, facilidade de uso) ficam fora desta árvore.
- As medidas são **metas** propostas para o sistema. Ainda não foram medidas.

Prioridade: par (importância para o negócio, dificuldade arquitetural), cada um em H, M ou L.

## Árvore de utilidade

- **Utilidade**
  - **Desempenho**
    - Latência sob pico de acesso
      - **D1** (H,H) — 200 torcedores abrem o site no minuto seguinte a um gol do Remo. Primeiro conteúdo com p95 ≤ 3 s e falhas < 1%.
      - **D2** (H,M) — Um torcedor troca o time em destaque. A página re-renderiza com p95 ≤ 1 s.
    - Uso de recursos durante a atualização
      - **D3** (H,M) — O serviço acorda num pico e dispara a atualização de 20.000 simulações. O p95 dos visitantes piora no máximo 50% e a atualização termina em ≤ 10 min.
    - Partida a frio
      - **D4** (M,M) — Primeiro acesso depois de o serviço dormir. Página útil em ≤ 20 s.
  - **Disponibilidade**
    - Falha de fontes externas
      - **A1** (H,L) — A API do Cartola responde 5xx ou 403 na atualização. O site segue no ar com o último snapshot: 0 min de indisponibilidade.
    - Falha do atualizador
      - **A2** (H,M) — O processo do agendador morre com o site no ar. A defasagem dos dados é detectada em ≤ 1 h e os dados nunca passam de 26 h.
    - Escritas concorrentes
      - **A3** (H,M) — A atualização manual coincide com a programada. Nenhum JSON publicado fica corrompido e há 0 erros de leitura no site.
    - Implantação
      - **A4** (H,M) — Push na `main` durante um jogo do Remo. Site fora do ar por ≤ 60 s e sessões reconectadas sem ação do usuário.
  - **Segurança (lado do servidor)**
    - Autenticação do admin
      - **S1** (H,M) — Ataque automatizado de força bruta no `/admin`. Bloqueio após 5 falhas por ≥ 15 min e 100% das tentativas registradas.
    - Abuso de operação privilegiada
      - **S2** (M,M) — Uma sessão de admin dispara a atualização em sequência. No máximo 1 atualização em curso e ≤ 1 manual a cada 10 min.
    - Exposição de informação
      - **S3** (M,L) — Um erro não tratado durante a visita. 0 tracebacks ou caminhos internos exibidos a visitantes anônimos.
    - Dados externos não confiáveis
      - **S4** (H,L) — O ge devolve um nome de time com HTML ou script. 0 trechos executados no navegador e 100% dos campos externos escapados.

## Cenários em seis partes

| ID | Fonte | Estímulo | Artefato | Ambiente | Resposta | Medida | Prior. |
|----|-------|----------|----------|----------|----------|--------|--------|
| D1 | 200 torcedores | Abrem o site ao mesmo tempo, no minuto seguinte a um gol. Cada abertura cria uma sessão Streamlit (websocket) e executa `app.py` | Processo Streamlit (`app.py`, `src/dashboard.py`), `data/projection.json` no volume | Pico de acesso, contêiner único, serviço já acordado | Todas as sessões recebem cabeçalho, tabela e probabilidades | p95 até o primeiro conteúdo ≤ 3 s; falhas de conexão ou 5xx < 1%; RAM < 80% do limite do contêiner | (H,H) |
| D2 | Torcedor com o site aberto | Troca o "Time em destaque", o que re-executa o script inteiro | `app.py`, caches `st.cache_resource` e `st.cache_data` | Operação normal, 50 sessões ativas | A página re-renderiza para o novo time | p95 da re-renderização ≤ 1 s | (H,M) |
| D3 | Agendador (`scheduler.py`) | Acorda num pico com snapshot de mais de 20 h e roda a atualização completa: download, treino e 20.000 simulações | Contêiner compartilhado (CPU e RAM) entre o Streamlit e o agendador | Pico de acesso logo após o serviço sair da ociosidade | Visitantes seguem atendidos com o snapshot anterior até a troca atômica | p95 dos visitantes piora ≤ 50% durante a atualização; atualização concluída em ≤ 10 min | (H,M) |
| D4 | Primeiro torcedor do dia | Acessa o site com o serviço dormindo | Railway, `start.sh`, boot do Streamlit, imports (pandas, XGBoost) | Serviço ocioso | O contêiner sobe e serve o último snapshot | Página útil em ≤ 20 s | (M,M) |
| A1 | API do Cartola, ge ou ESPN | Responde 5xx, 403 ou estoura o *timeout* (20 a 40 s) durante a atualização | `store.refresh()`, `scheduler.run_update()` | Atualização programada | Mantém o último snapshot válido, registra o erro e tenta de novo no próximo horário | 0 min de indisponibilidade; idade dos dados visível no cabeçalho | (H,L) |
| A2 | Processo do agendador | Termina (exceção fora do `try`, OOM kill) com o Streamlit ainda no ar | `start.sh` (agendador em segundo plano com `&`), `scheduler.py` | Operação normal, serviço acordado por tráfego contínuo | A falha é detectada e o agendador é reiniciado | Alerta em ≤ 1 h; dados nunca com mais de 26 h | (H,M) |
| A3 | Admin e agendador | Atualização manual no `/admin` ao mesmo tempo que a programada | `store._write_json`, `data/*.json` | Operação normal | Uma das atualizações espera ou é recusada, e o arquivo publicado está sempre íntegro | 0 JSON truncados ou misturados; 0 erros de leitura no site | (H,M) |
| A4 | Mantenedor | Push na `main` dispara novo deploy | Railway (1 réplica), volume `/app/data` | Jogo do Remo em andamento | O novo contêiner assume e as sessões reconectam | Indisponibilidade ≤ 60 s; nenhuma perda de dados no volume | (H,M) |
| S1 | Atacante na internet | Script tenta 10.000 combinações de usuário e senha no formulário do `/admin` | `pages/admin.py` | Operação normal, página pública | Bloqueia a origem após falhas sucessivas e registra as tentativas | Bloqueio após 5 falhas por ≥ 15 min; 100% das tentativas em log; 0 acessos indevidos | (H,M) |
| S2 | Sessão de admin (legítima ou sequestrada) | Clica em "Atualizar sistema agora" várias vezes seguidas | `pages/admin.py`, `store.refresh()`, APIs externas | Operação normal | Aceita uma atualização por vez, com intervalo mínimo | ≤ 1 atualização em curso; ≤ 1 manual a cada 10 min; ≤ 60 req/min ao Cartola | (M,M) |
| S3 | Visitante anônimo | Provoca um erro não tratado (por exemplo, um snapshot com campo ausente) | Streamlit (`client.showErrorDetails`), `src/dashboard.py` | Operação normal | Mostra mensagem genérica em português | 0 tracebacks, caminhos ou variáveis de ambiente exibidos | (M,L) |
| S4 | API do ge ou ESPN | Devolve nome de time ou sede com `<script>` ou HTML | `src/dashboard.py` (blocos com `unsafe_allow_html=True`) | Atualização programada seguida de visita | O texto é exibido literalmente | 0 scripts executados; 100% dos campos externos passam por `html.escape` | (H,L) |

## Achados da análise

A análise cobre as folhas (H,H) e (H,M). As folhas A1 e S4, de prioridade (H,L), aparecem no fim como não riscos para registrar a decisão que as sustenta.

### D1 (H,H) — pico após gol · **Risco**

- **Decisão**: um único processo Streamlit, com estado por sessão em websocket, lendo o snapshot de projeções em JSON.
- **O que se observa**:
  - `app.py:42` chama `store.load_projection()` **sem cache** a cada execução do script. Isso inclui a abertura da sessão e toda interação.
  - O mesmo arquivo é tratado como "grande (megabytes)" em `src/dashboard.py:52` e por isso vai para `st.cache_resource` lá. Mas o cabeçalho, em `app.py`, lê e desserializa o arquivo inteiro de novo, fora do cache.
  - Com 200 aberturas simultâneas, são 200 `json.loads` de vários MB concorrendo pelo GIL num único processo. Cada sessão ainda mantém sua cópia do dicionário até o fim da execução.
  - `register_visit()` (`src/store.py:84`) faz leitura, incremento e gravação em `visits.json` a cada sessão nova, sem trava.
- **Por que é risco**: a latência e a memória crescem linearmente com as aberturas simultâneas, justamente no evento de maior interesse. Não existe réplica para dividir a carga (ver A4).
- **Mitigação sugerida**: usar no `app.py` o mesmo `projecao_publicada()` em cache de processo. Medir o p95 com um teste de carga (por exemplo, Locust com 200 websockets) antes e depois.
- **Medição (04/11/2026, [teste de carga](teste-carga-200.md))**: risco confirmado. Com 200 sessões em rajada, 48,5% falham, o p95 do primeiro conteúdo é de 248 s e o pico de RAM é de 3,6 GB. O cache da projeção triplica a vazão, mas sozinho não basta (38,5% de falhas). A causa dominante é renderizar cada visita num único processo Python.

### D2 (H,M) — troca do time em destaque · **Ponto de sensibilidade**

- **Decisão**: o modelo de execução do Streamlit re-executa o script inteiro a cada interação. Os resultados pesados ficam em cache, com chave em `fetched_at` e num balde de 300 s (`src/dashboard.py:66-80`).
- **O que se observa**: o tempo de re-renderização depende quase só de dois fatores. Um é o tamanho de `projection.json`, lido de novo em `app.py:42`. O outro é acertar a chave de cache.
- **Por que é sensibilidade**: aumentar `SIMULATION_COUNT` ou acrescentar ligas a `projection.json` aumenta diretamente a latência de cada clique. A medida de D2 depende desses dois parâmetros.

### D3 (H,M) — atualização no pico · **Ponto de trade-off**

- **Decisão**: o agendador roda no mesmo contêiner do site (`ENABLE_UPDATER=1`, `scripts/start.sh:11`). O serviço dorme quando ocioso e atualiza ao acordar se o snapshot tiver mais de `STALE_HOURS` h.
- **O que se observa**: o primeiro acesso depois de um período ocioso é, por construção, o gatilho da atualização. Depois de um gol, esse acesso vem junto com o pico. O treino e as 20.000 simulações (`src/projections.py:26`) disputam CPU e RAM com as sessões do D1.
- **O trade-off**: a escolha ganha **custo** (um serviço, sem banco e sem worker dedicado) e perde **desempenho** e **disponibilidade** no momento de maior acesso. A troca atômica do arquivo (`src/store.py:45`) garante que o visitante nunca veja dados pela metade. Ela não evita a lentidão.
- **Alternativas**:
  - Rodar o worker em outro serviço do Railway com o mesmo volume, o que esbarra em A4.
  - Baixar a prioridade do agendador com `nice`.
  - Adiar a atualização ao acordar por alguns minutos.

### A2 (H,M) — morte do agendador · **Risco**

- **Decisão**: o agendador é iniciado em segundo plano por `start.sh` com `&`, sem supervisor e sem verificação de saúde. O Streamlit é o processo principal (`exec`).
- **O que se observa**:
  - As exceções dentro de `run_update` são capturadas (`scripts/scheduler.py:87` e `:96`), o que mantém o laço vivo.
  - Um OOM kill, um erro na leitura de `UPDATE_TIMES` ou um sinal externo, porém, encerram o processo, e nada o reinicia. O Railway só observa o Streamlit, então o contêiner segue "saudável".
  - Enquanto houver tráfego contínuo, o serviço não dorme e o agendador não volta.
- **Por que é risco**: a disponibilidade aparente fica preservada, mas a correção dos dados se degrada em silêncio. O único sinal é a legenda "Dados atualizados há X h" no rodapé do cabeçalho (`app.py`). Não há alerta.
- **Mitigação sugerida**:
  - Um *healthcheck* que falhe quando `fetched_at` passar de 26 h, para o Railway reiniciar o contêiner.
  - Ou um supervisor mínimo no `start.sh`, que reinicie o agendador quando ele sair.

### A3 (H,M) — atualização manual e programada simultâneas · **Risco**

- **Decisão**: gravação atômica por arquivo temporário e `os.replace`, sem exclusão mútua entre escritores (`src/store.py:45-51`). O botão do admin chama `store.refresh()` e `generate_and_save()` na própria thread da sessão (`pages/admin.py:54`).
- **O que se observa**:
  - O nome do temporário é fixo (`season.json.tmp`, `projection.json.tmp`). Se o agendador e a página de admin gravarem o mesmo arquivo ao mesmo tempo, um `write_text` pode truncar o temporário do outro antes do `os.replace`. O resultado é um JSON truncado publicado como atual.
  - Como `app.py:42` faz `json.loads` sem tratamento, um `projection.json` inválido derruba **todas** as páginas.
  - Mesmo sem corrupção, as duas execuções podem publicar `season.json` de uma e `projection.json` de outra. Isso é contido, em parte, pelo uso de `projection["season"]` em `app.py`.
- **Por que é risco**: a atomicidade foi pensada para "um escritor e muitos leitores", mas o sistema tem dois escritores possíveis.
- **Mitigação sugerida**:
  - Um *lock* de arquivo (`fcntl.flock` em `data/.update.lock`) compartilhado por `refresh()` e `generate_and_save()`.
  - Temporários com sufixo único (`tempfile.NamedTemporaryFile` no mesmo diretório).
  - Uma leitura tolerante em `load_projection()`, que volte ao snapshot anterior se o JSON for inválido.

### A4 (H,M) — deploy durante jogo · **Ponto de trade-off**

- **Decisão**: o armazenamento é JSON em volume local do Railway, numa única réplica, no lugar do MongoDB (commits `54aea37` e `ed9519a`). O deploy é automático a cada push na `main`.
- **O que se observa**:
  - O volume fica preso a uma instância, o que impede réplicas paralelas e *rolling deploy* sem janela.
  - Todo push derruba as sessões abertas, e o novo contêiner passa pela partida a frio (D4).
  - Se o snapshot estiver velho, o novo contêiner ainda dispara a atualização do D3.
- **O trade-off**: a decisão ganha **simplicidade e custo** (sem banco gerenciado, com leitura local rápida) e perde **disponibilidade** e **escalabilidade horizontal**. É a mesma decisão que torna o D1 um risco: sem réplicas, o pico cai todo num processo.
- **Mitigação sugerida**: evitar push durante jogos, o que é processo e não arquitetura. A saída estrutural é mover o snapshot publicado para armazenamento compartilhado (objeto estático ou banco), o que permite mais de uma réplica.

### S1 (H,M) — força bruta no admin · **Risco**

- **Decisão**: autenticação própria na página Streamlit, com comparação direta de usuário e senha das variáveis de ambiente (`pages/admin.py:28`) e estado em `st.session_state`.
- **O que se observa**:
  - Não há limite de tentativas, bloqueio, atraso progressivo nem log de falhas.
  - A comparação usa `==`, não `hmac.compare_digest`. O vazamento por tempo é pequeno pelo websocket, mas não é zero.
  - Cada tentativa é uma re-execução barata do script, então um script automatizado testa senhas sem atrito.
  - Uma senha descoberta dá acesso a S2, a operação mais cara do sistema.
- **Por que é risco**: a medida "bloqueio após 5 falhas" não tem nenhum mecanismo que a sustente hoje.
- **Mitigação sugerida**:
  - Contador de falhas com bloqueio por tempo, guardado em processo (`st.cache_resource`) ou em arquivo.
  - `hmac.compare_digest` na comparação e log das tentativas.
  - Ou tirar o admin da rede pública: proteção por proxy ou acesso apenas pelo `railway run scripts/update_data.py`.

### Folhas (H,L) — não riscos registrados

- **A1, falha de API externa · Não risco.** Toda a atualização é envolvida por `try/except` (`scripts/scheduler.py:87`, `:96`; `src/store.py`, `refresh_*`). As gravações são atômicas, e o caminho do visitante só lê o volume, sem chamar APIs. A decisão de **pré-computar e publicar snapshots** isola o site das fontes externas.
- **S4, HTML vindo das APIs · Não risco.** Os blocos com `unsafe_allow_html=True` em `src/dashboard.py` passam os campos externos por `html.escape` (por exemplo, `src/dashboard.py:284-329`). Fica a recomendação de manter isso como regra em revisões, porque um único campo sem escape transforma o achado em risco.

### Resumo

| Folha | Prioridade | Decisão arquitetural | Classificação |
|-------|-----------|----------------------|---------------|
| D1 | (H,H) | Processo Streamlit único lendo o JSON de projeções sem cache no `app.py` | Risco |
| D2 | (H,M) | Re-execução total por interação, com cache por `fetched_at` | Ponto de sensibilidade |
| D3 | (H,M) | Agendador no mesmo contêiner, com atualização ao acordar | Ponto de trade-off |
| A2 | (H,M) | Agendador em segundo plano sem supervisor | Risco |
| A3 | (H,M) | Gravação atômica sem exclusão mútua entre escritores | Risco |
| A4 | (H,M) | JSON em volume local, numa réplica, com deploy a cada push | Ponto de trade-off |
| S1 | (H,M) | Login próprio sem limite de tentativas | Risco |
| A1 | (H,L) | Snapshots pré-computados e isolados das APIs | Não risco |
| S4 | (H,L) | Escape de todos os campos externos | Não risco |

**Tema de risco**: a decisão de concentrar site, agendador e armazenamento num único contêiner com volume local reduz custo, mas une os riscos D1, D3, A2, A3 e A4. Esses riscos se manifestam todos no mesmo momento: o pico de acesso logo depois de um gol.
