-- Base independente do banco Django. Não importa nem altera dados do legado.
begin;

create type public.papel_erp as enum ('admin', 'operador', 'cliente');

create table public.clientes (
  id uuid primary key default gen_random_uuid(),
  nome_fantasia text not null check (length(btrim(nome_fantasia)) between 1 and 150),
  razao_social text not null default '' check (length(razao_social) <= 150),
  cnpj text not null unique check (cnpj ~ '^[A-Z0-9]{12}[0-9]{2}$'),
  contato_principal text not null check (length(btrim(contato_principal)) between 1 and 100),
  email text not null default '' check (length(email) <= 254),
  telefone text not null default '' check (length(telefone) <= 30),
  ativo boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.perfis (
  id uuid primary key references auth.users(id) on delete cascade,
  nome text not null check (length(btrim(nome)) between 1 and 150),
  papel public.papel_erp not null default 'cliente',
  cliente_id uuid references public.clientes(id) on delete restrict,
  constraint perfil_cliente_coerente check (
    (papel = 'cliente' and cliente_id is not null)
    or (papel in ('admin', 'operador') and cliente_id is null)
  )
);
create index perfis_cliente_id_idx on public.perfis(cliente_id);
create index clientes_nome_idx on public.clientes(nome_fantasia, id);

create schema if not exists private;
revoke all on schema private from public;
grant usage on schema private to authenticated;

-- O perfil é definido por administração confiável, nunca por user_metadata.
-- O definer evita recursão de RLS e só devolve o acesso do usuário autenticado.
create function private.equipe_erp() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.perfis p
    where p.id = (select auth.uid()) and p.papel in ('admin', 'operador')
  );
$$;
create function private.cliente_erp() returns uuid
language sql stable security definer set search_path = '' as $$
  select p.cliente_id from public.perfis p where p.id = (select auth.uid());
$$;
revoke all on function private.equipe_erp() from public, anon;
revoke all on function private.cliente_erp() from public, anon;
grant execute on function private.equipe_erp(), private.cliente_erp() to authenticated;

create function private.atualizar_timestamp() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  new.created_at = old.created_at;
  return new;
end;
$$;
revoke all on function private.atualizar_timestamp() from public;
create trigger clientes_atualizados before update on public.clientes
for each row execute function private.atualizar_timestamp();

alter table public.clientes enable row level security;
alter table public.perfis enable row level security;

-- Limpa os privilégios padrão do Supabase antes dos grants mínimos.
revoke all on public.clientes, public.perfis from anon, authenticated;
grant select, insert, update on public.clientes to authenticated;
grant select on public.perfis to authenticated;

create policy perfis_leitura_propria on public.perfis for select to authenticated
using (id = (select auth.uid()));

create policy clientes_leitura on public.clientes for select to authenticated
using ((select private.equipe_erp()) or id = (select private.cliente_erp()));
create policy clientes_criacao_equipe on public.clientes for insert to authenticated
with check ((select private.equipe_erp()));
create policy clientes_edicao_equipe on public.clientes for update to authenticated
using ((select private.equipe_erp())) with check ((select private.equipe_erp()));

comment on table public.perfis is 'Gerenciado por administração confiável. Sem autoinscrição ou autopromoção de papéis.';
comment on table public.clientes is 'Clientes do ERP reescrito. Clientes consultam apenas o próprio cadastro; equipe opera a carteira.';
commit;
