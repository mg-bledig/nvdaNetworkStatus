# NVDA Network Status

NVDA Network Status informa o estado da rede e da conexão com a Internet, além da intensidade do sinal Wi-Fi.

* Versão: 1.0
* Manutenção: Michael Bledig
* Repositório: https://github.com/mg-bledig/nvdaNetworkStatus

## Compatibilidade

Requer NVDA 2026.1 ou posterior.
Testado com NVDA 2026.2.

## Comportamento atual

* Anuncia automaticamente "Network disconnected" quando a conexão de rede é perdida.
* Anuncia "No Internet access" quando a rede local permanece conectada, mas o acesso à Internet é perdido.
* Anuncia "Internet access restored" quando a conexão com a Internet retorna.
* NVDA+Control+Shift+N informa manualmente o estado atual da conexão com a Internet.
* NVDA+Control+N informa a intensidade do sinal da conexão Wi-Fi ativa.

A intensidade do sinal Wi-Fi é obtida pela API WLAN nativa do Windows, em vez de analisar a saída do netsh.

## Atribuição / Histórico

Rui Fontes criou o complemento original "networkStrenght" em 2020, com o primeiro lançamento em 18 de março de 2020. O projeto original informava a intensidade do sinal da rede sem fio.

NVDA Network Status é uma continuação/obra derivada mantida por Michael Bledig, baseada em parte no trabalho original de Rui, com monitoramento da conexão com a Internet. Rui mantém o crédito e os direitos autorais sobre seu trabalho original.

* Copyright original 2020 Rui Fontes.
* Modificações/continuação: copyright 2026 Michael Bledig.

## Alterações

### Versão 1.0

Lançamento inicial do NVDA Network Status, baseado no complemento original networkStrenght de Rui Fontes. Adiciona anúncios automáticos de alterações na conexão com a Internet, um comando manual para consultar o estado da Internet e informações sobre a intensidade do sinal da conexão Wi-Fi ativa usando a API WLAN nativa do Windows.

## Licença

Os termos da licença permanecem inalterados. Consulte o arquivo [COPYING.txt](https://github.com/mg-bledig/nvdaNetworkStatus/blob/HEAD/COPYING.txt).
