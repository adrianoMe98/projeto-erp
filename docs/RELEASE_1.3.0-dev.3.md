# Release 1.3.0-dev.3

Revisão de manutenção do ambiente dev. Mantém o IPAM da dev.2 e corrige o processo de
instalação e diagnóstico. Não contém migrations novas nem reinicializa volumes.

- `erpctl doctor development` verifica os caminhos montados e testa a senha via TCP/SELECT 1;
- `erpctl db-password development` faz backup e abre a troca segura de senha PostgreSQL;
- exports de banco, porta e projeto no terminal deixam de interferir nas chamadas do erpctl;
- o entrypoint é instalado fora do bind mount em `/usr/local/bin/erp-entrypoint`;
- o deploy ajusta acesso à raiz do diretório dev e interrompe ao falhar o build ou healthcheck;
- backups novos são privados por padrão;
- a instalação interrompe se falta o arquivo de ambiente e o volume padrão do banco já existe;
- diretórios dos arquivos distribuídos recebem permissão 0755.

A recuperação da instalação existente é descrita em `docs/RECUPERACAO_DEV.md`.
A produção 1.2.0 usa outro pacote e diretório.
