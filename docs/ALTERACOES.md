# Resumo das alterações

## Desenvolvimento 1.3.0-dev.3

- diagnóstico de permissões e autenticação real do banco com `erpctl doctor`;
- troca interativa da senha PostgreSQL no dev com backup prévio;
- configuração do ambiente protegida contra exports conflitantes do terminal;
- raiz do diretório dev acessível ao usuário do container, sem abrir o `.env.dev`;
- entrypoint da imagem fora do bind mount de desenvolvimento;
- interrupção imediata quando build, inicialização ou healthcheck falham;
- bloqueio da criação de credenciais novas quando falta o .env e o volume do banco já existe;
- pacote com diretórios em 0755 e doze regressões do instalador testadas com Docker simulado.

## Desenvolvimento 1.3.0-dev.2

- alocação transacional com bloqueio do bloco pai;
- subdivisão ignora faixas que já possuam IPs documentados no pai;
- bloqueio de redimensionamentos que invalidem filhos ou endereços existentes;
- endereços desativados não são sugeridos para cadastro duplicado;
- mapa visual diferencia espaço livre de faixas ocupadas por sub-redes filhas;
- sete novos testes de regressão para integridade do IPAM.

## Desenvolvimento 1.3.0-dev.1

- painel IPAM inspirado no fluxo operacional do phpIPAM;
- seções IPAM e VRFs por cliente;
- subdivisão IPv4/IPv6 com cálculo de próximo bloco livre;
- busca, mapa visual, ocupação, histórico e endereços enriquecidos;
- portal IPAM somente leitura e isolado por cliente;
- porta padrão do desenvolvimento alterada para `8021`.

## Versão estável 1.2.0

- tema claro/escuro no login, portal e Admin, salvo no navegador;
- identificação visual de desenvolvimento e versão em execução;
- ambientes Compose independentes para produção e desenvolvimento;
- Pix simulado desabilitado por padrão na produção;
- utilitário `erpctl` para instalação, atualização, backup, status, logs e rollback;
- verificação de pacote e SHA-256 antes da atualização;
- backup automático do banco e do código antes de cada atualização;
- restauração do código anterior quando o healthcheck falha.
- promoção da candidata `1.2.0-rc.1` sem mudanças funcionais adicionais.
- healthcheck interno compatível com redirecionamento HTTPS obrigatório.

## Homologação v1.1

- corrigida a abertura do painel `/admin/` com `DJANGO_DEBUG=0`;
- mantidos os nomes versionados e a compressão dos arquivos estáticos em produção;
- adicionado teste de regressão que renderiza o índice administrativo após `collectstatic`.

## Funcionalidades

- autenticação unificada por usuário/e-mail com redirecionamento por perfil;
- recuperação de senha e tratamento de conta ainda não vinculada;
- CGNAT determinístico para RouterOS 6/7, `iptables` e `nftables`;
- snapshot do mapa, SHA-256 da configuração e relatório PDF para o cliente;
- Pix simulado com QR Code, webhook autenticado, idempotência e baixa financeira;
- formulário seguro de abertura de chamados no portal.

## Confiabilidade e segurança

- variáveis de ambiente e falha explícita quando segredos obrigatórios faltam;
- PostgreSQL em container com healthchecks e volumes nomeados;
- Gunicorn, WhiteNoise e execução do container como usuário sem privilégios;
- validações de VLAN, IP, hierarquia de sub-redes e isolamento entre clientes;
- proteção de downloads e de telas administrativas customizadas;
- sanitização de minuta de contrato e validação de uploads PDF;
- proteção contra exclusões em cascata de dados empresariais;
- limite de operações que poderiam expandir redes ou mapas em excesso.

## Qualidade

- migrações versionadas para todos os novos modelos e restrições;
- comando `auditar_dados` para preparar bases existentes;
- 39 testes automatizados cobrindo domínio, permissões, login, temas, Admin, CGNAT e Pix;
- Ruff para lint/formatação e workflow de integração contínua;
- documentação de instalação, upgrade e roteiro de aceite.
