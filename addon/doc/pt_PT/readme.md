# NVDA Network Status

O NVDA Network Status informa sobre o estado da rede e da ligação à Internet, bem como a intensidade do sinal Wi-Fi.

* Versão: 1.0
* Manutenção: Michael Bledig
* Repositório: https://github.com/mg-bledig/nvdaNetworkStatus

## Compatibilidade

Requer o NVDA 2026.1 ou posterior.
Testado com o NVDA 2026.2.

## Comportamento atual

* Anuncia automaticamente "Network disconnected" quando se perde a ligação de rede.
* Anuncia "No Internet access" quando a rede local permanece ligada, mas se perde o acesso à Internet.
* Anuncia "Internet access restored" quando a ligação à Internet regressa.
* NVDA+Control+Shift+N informa manualmente sobre o estado atual da ligação à Internet.
* NVDA+Control+N informa sobre a intensidade do sinal da ligação Wi-Fi ativa.

A intensidade do sinal Wi-Fi é obtida através da API WLAN nativa do Windows, em vez de analisar a saída do netsh.

## Atribuição / História

Rui Fontes criou o extra original "networkStrenght" em 2020, lançado pela primeira vez em 18 de março de 2020. O projeto original informava sobre a intensidade do sinal da rede sem fios.

O NVDA Network Status é uma continuação/obra derivada mantida por Michael Bledig, baseada em parte no trabalho original de Rui, com monitorização da ligação à Internet. Rui mantém o crédito e os direitos de autor sobre o seu trabalho original.

* Copyright original 2020 Rui Fontes.
* Modificações/continuação: copyright 2026 Michael Bledig.

## Alterações

### Versão 1.0

Lançamento inicial do NVDA Network Status, baseado no extra original networkStrenght de Rui Fontes. Adiciona anúncios automáticos de alterações na ligação à Internet, um comando manual para consultar o estado da Internet e informações sobre a intensidade do sinal da ligação Wi-Fi ativa através da API WLAN nativa do Windows.

## Licença

Os termos da licença permanecem inalterados. Consulte o ficheiro [COPYING.txt](https://github.com/mg-bledig/nvdaNetworkStatus/blob/HEAD/COPYING.txt).
