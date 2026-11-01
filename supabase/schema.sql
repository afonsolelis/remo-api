-- Tabelas lidas pelo site (GitHub Pages) e escritas pelo GitHub Actions.
-- Idempotente: o script de sincronização roda este arquivo a cada execução.

create table if not exists remo_clubes (
  id          integer primary key,
  nome        text not null,
  abreviacao  text,
  escudo      text
);

create table if not exists remo_partidas (
  partida_id  bigint primary key,
  rodada      integer not null,
  data        timestamptz,
  casa_id     integer not null references remo_clubes(id),
  fora_id     integer not null references remo_clubes(id),
  gols_casa   integer,
  gols_fora   integer,
  encerrada   boolean not null default false
);

create table if not exists remo_atualizacao (
  id            integer primary key default 1 check (id = 1),
  executado_em  timestamptz not null,
  rodada_atual  integer
);

-- Leitura pública (chave publishable), escrita só pela conexão do Actions.
alter table remo_clubes      enable row level security;
alter table remo_partidas    enable row level security;
alter table remo_atualizacao enable row level security;

drop policy if exists leitura_publica on remo_clubes;
drop policy if exists leitura_publica on remo_partidas;
drop policy if exists leitura_publica on remo_atualizacao;
create policy leitura_publica on remo_clubes      for select to anon, authenticated using (true);
create policy leitura_publica on remo_partidas    for select to anon, authenticated using (true);
create policy leitura_publica on remo_atualizacao for select to anon, authenticated using (true);

grant select on remo_clubes, remo_partidas, remo_atualizacao to anon, authenticated;
