begin;
create extension if not exists pgtap with schema extensions;
set local search_path = public, extensions;
select plan(15);

insert into auth.users(id, email) values
  ('10000000-0000-4000-8000-000000000001', 'equipe@example.test'),
  ('10000000-0000-4000-8000-000000000002', 'cliente-a@example.test'),
  ('10000000-0000-4000-8000-000000000003', 'cliente-b@example.test'),
  ('10000000-0000-4000-8000-000000000004', 'pendente@example.test');
insert into public.clientes(id, nome_fantasia, cnpj, contato_principal) values
  ('20000000-0000-4000-8000-000000000001', 'Empresa A', '00000000000101', 'Contato A'),
  ('20000000-0000-4000-8000-000000000002', 'Empresa B', '00000000000202', 'Contato B');
insert into public.perfis(id, nome, papel, cliente_id) values
  ('10000000-0000-4000-8000-000000000001', 'Equipe', 'operador', null),
  ('10000000-0000-4000-8000-000000000002', 'Cliente A', 'cliente', '20000000-0000-4000-8000-000000000001'),
  ('10000000-0000-4000-8000-000000000003', 'Cliente B', 'cliente', '20000000-0000-4000-8000-000000000002');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"10000000-0000-4000-8000-000000000002","role":"authenticated"}', true);
select is((select count(*)::int from public.clientes), 1, 'cliente A vê apenas uma empresa');
select is((select nome_fantasia from public.clientes), 'Empresa A', 'cliente A vê sua própria empresa');
select is((select count(*)::int from public.perfis), 1, 'cliente não consulta outros perfis');
with changed as (update public.clientes set nome_fantasia = 'Invasão' returning id)
select is((select count(*)::int from changed), 0, 'cliente não altera nem o próprio cadastro');
select throws_ok($$insert into public.clientes(nome_fantasia,cnpj,contato_principal) values ('Invasão','00000000000303','X')$$, '42501', null, 'cliente não cria empresas');
select throws_ok($$update public.perfis set papel = 'admin', cliente_id = null$$, '42501', null, 'cliente não se promove a administrador');
select throws_ok($$delete from public.clientes$$, '42501', null, 'exclusão de clientes não está disponível');

select set_config('request.jwt.claims', '{"sub":"10000000-0000-4000-8000-000000000003","role":"authenticated"}', true);
select is((select nome_fantasia from public.clientes), 'Empresa B', 'cliente B tem domínio de leitura independente');

select set_config('request.jwt.claims', '{"sub":"10000000-0000-4000-8000-000000000004","role":"authenticated"}', true);
select is((select count(*)::int from public.clientes), 0, 'conta sem perfil não vê clientes');
select throws_ok($$insert into public.perfis(id,nome,papel) values ('10000000-0000-4000-8000-000000000004','Intruso','admin')$$, '42501', null, 'conta sem perfil não cria permissão');

select set_config('request.jwt.claims', '{"sub":"10000000-0000-4000-8000-000000000001","role":"authenticated"}', true);
select is((select count(*)::int from public.clientes), 2, 'equipe consulta a carteira');
select lives_ok($$insert into public.clientes(nome_fantasia,cnpj,contato_principal) values ('Empresa C','00000000000303','C')$$, 'equipe cria cadastro');
select lives_ok($$update public.clientes set ativo = false where cnpj = '00000000000303'$$, 'equipe desativa cadastro');
select throws_ok($$delete from public.clientes$$, '42501', null, 'equipe também preserva cadastros contra exclusão');

set local role anon;
select throws_ok($$select * from public.clientes$$, '42501', null, 'anônimo não acessa cadastros');
reset role;
select * from finish();
rollback;
