# Release 1.3.0-dev.1

Versão exclusiva para desenvolvimento e homologação do novo IPAM. A produção deve continuar
na versão estável `1.2.0` até a conclusão dos testes no homelab.

## Entregue

- painel IPAM próprio e responsivo;
- hierarquia por cliente, seção, VRF e sub-rede;
- suporte seguro a IPv4 e IPv6;
- busca e filtros operacionais;
- subdivisão com próximo prefixo livre;
- endereços, mapa visual e histórico;
- portal do cliente somente leitura;
- migration incremental que preserva os registros existentes;
- porta de desenvolvimento padrão ajustada para `8021`.

## Ainda não incluído

- descoberta automática de hosts;
- sincronização com roteadores;
- API pública;
- importação/exportação em massa;
- alertas de capacidade.

Esses recursos serão construídos em incrementos separados para manter a homologação rastreável.
