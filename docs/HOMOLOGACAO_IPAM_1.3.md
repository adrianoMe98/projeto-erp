# Homologação incremental do IPAM 1.3

Rodada de 30/10/2026, derivada de `development` no commit `f8d5326`.
Branch: `feat/ipam-homologacao-1.3.0`. A versão permanece `1.3.0-dev.3`.
Nenhum deploy, promoção para estável ou alteração na produção foi realizado.

## Referência e escopo

O [phpIPAM](https://github.com/phpipam/phpipam) é referência funcional para a
organização de redes, subdivisão, espaço livre e consulta de endereços. Esta rodada
valida os contratos descritos em `docs/IPAM_1.3_DEV.md`; não declara paridade com o
phpIPAM nem comparação visual com sua demonstração. Importação em massa, descoberta
e permissões granulares ficam para entregas específicas.

## Defeito reproduzido e corrigido

As conversões de inteiros inferiam IPv4 para valores abaixo de `2**32`, mesmo quando
a origem era IPv6. Exemplos reproduzidos antes da correção:

- próximo endereço em `::1/128`: retornava `0.0.0.1`;
- próximo endereço após reservas em `::/126`: retornava `0.0.0.2`;
- primeiro bloco `/16` de `::/0`: retornava `0.0.0.0/16`.

A conversão agora usa a família da rede original. O cálculo permanece por intervalos,
sem enumerar espaços IPv6 grandes. Não há mudanças de modelo nem migrations.

## Evidências locais

Preparação: `sh scripts/codex-setup.sh`, com Python 3.12 e dependências travadas.
Validação: `sh scripts/codex-check.sh`, concluído com sucesso:

- 65 testes Django em SQLite (57 existentes e 8 novos);
- 12 testes de manutenção com Docker simulado;
- lint, formatação, checks Django, ausência de migrations pendentes e sintaxe shell.

| Critério | Cobertura nesta rodada |
| --- | --- |
| IPv4 `/31`, `/32`, hierarquia e sobreposição | Testes de domínio |
| IPv6 `/32` para `/48`, prefixos próximos de `::`, `/127` e `/128` | Testes de alocação, sugestão e exaustão |
| VRFs e isolamento por cliente | Mesmo prefixo em domínios distintos sem consumir espaço de outro domínio |
| Reservas e endereços desativados | Não são sugeridos novamente; mapa mantém seus estados |
| Quantidade superior à capacidade | Rejeição sem novos blocos ou histórico parcial |
| Portal somente leitura | GET e POST nas rotas operacionais retornam 403 para cliente |
| Consulta IPv6 entre clientes | Rede própria acessível; rede alheia retorna 404 e não expõe hostname |
| Migração existente | Teste de preservação dos dados mantido na suíte |

## Pendências de homologação externa

- Executar a pipeline com PostgreSQL 16; SQLite não valida bloqueios concorrentes reais.
- Confirmar a recuperação da autenticação do banco no homelab conforme
  `docs/RECUPERACAO_DEV.md`. Essa pendência continua aberta.
- Confirmar `/health/` no desenvolvimento do homelab, porta 8021, após recuperação.
- Conferir login, portal e Admin nos temas claro/escuro em navegador. Não houve mudança
  de interface nesta rodada nem validação visual automatizada.
- Construção e execução Docker reais, backup e restauração no laboratório continuam
  separados dos testes com Docker simulado.

## Próxima evolução

Depois dessas confirmações, revisar a consistência entre indicadores de ocupação,
reservas e sugestões, e a ordenação numérica de endereços IPv4/IPv6 nas listas.
Entregar cada ajuste com teste de regressão em branch de tarefa e PR para `development`.
Só então ampliar o escopo para importação/exportação e permissões mais granulares.
