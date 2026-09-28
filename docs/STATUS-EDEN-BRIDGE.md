# Status da ponte Eden ↔ Switch físico

Atualizado em 28/09/2026. Esta linha fica preservada como pesquisa paralela e não é o caminho recomendado para o próximo marco do host final.

## Objetivo

Usar um Scarlet 4.0.0 real no Eden como host de jogo e transportar sua sessão LDN/Pia pela rede física criada pelo ESP32-S3 para um Violet em Switch 2 intacto.

## Implementação atual

`tools/eden_radio_bridge.py`:

- entra na sala Eden em `127.0.0.1:24872`;
- descobre o `NetworkInfo` do Scarlet host;
- cria uma rede LDN física com identidade e chaves independentes;
- assenta o Switch físico como participante no Eden;
- verifica, traduz e sela novamente pacotes Pia nos dois sentidos;
- traduz IPs, network id e constant id derivados do MAC;
- normaliza o Net `0x11` para o formato aceito no host físico: unicast, sem zlib, flags `0x01` e 114 bytes;
- usa o perfil comprovado do ESP32: `skip_encryption=true` e `accept_decrypted_ccmp=true`;
- inicializa `POKELDN_RADIO=esp32:COM4` antes dos imports LDN;
- usa uma identidade LDN física nova e o marcador canônico `aadb8104` apenas no anúncio;
- evita duplicar a mesma estação quando o Switch repete autenticação.

## Resultados confirmados

### `live16`: associação LDN, sem resposta Pia

- O Switch entrou na rede como `169.254.17.2`, MAC `bc89a64bf277`, nome `Cyrus`.
- A ponte recebeu o `NetworkInfo` sincronizado do Eden e transmitiu repetidamente o Net `0x11`.
- Não houve pacote Pia de volta (`rx_seen=0`).
- O Switch saiu da associação cerca de dez segundos depois.
- Artefatos: `lab/eden-radio-bridge-live16.jsonl` e `lab/eden-radio-bridge-live16-esp32.trace`.

### `live19` a `live21`: anúncio recebido pela UI, sem autenticação LDN

- Foram testados perfil de rádio comprovado, SessionId físico novo, inicialização antecipada do backend e marcador canônico.
- O Violet mostrou “Communicating” brevemente em uma tentativa, mas terminou em `No raid was found`.
- O trace não registrou autenticação nem associação do Switch.
- O anúncio bruto de `live20` foi descriptografado e comparado ao host sintético aceito `8184`. Os campos estruturais coincidiram: protocolo 1, versão 4, AES-CTR, scene 7, app version 21, plataforma 1, canal 6, limite 4, um participante e aplicação de 132 bytes. Permaneceram apenas valores naturalmente variáveis: MAC, IP, SSID, aleatórios, senha derivada do código e o próprio código.
- O controle A/B executado logo depois com `tools/sv_raid_host.py`, código `8184`, entrou no lobby do mesmo Violet. Isso comprova que ESP32, COM4, rádio e jogo estavam funcionais.

## Artefatos principais

- Ponte: `tools/eden_radio_bridge.py`
- Comparador de abertura: `tools/compare_eden_opening.py`
- Capturas da ponte: `lab/eden-radio-bridge-live16.jsonl`, `live19.jsonl`, `live20.jsonl`, `live21.jsonl`
- Traces correspondentes: arquivos `lab/eden-radio-bridge-live*-esp32.trace`
- Relatório Eden↔Eden: `lab/eden-two-client-opening-comparison.json`
- A/B sintético aceito: `lab/sv-raid-ab-8184.jsonl`

## Hipótese e próximo passo

Não repetir buscas mudando campos do anúncio: a equivalência estrutural já foi verificada.

O próximo experimento da ponte deve reaproveitar o processo/radio frontend comprovado de `sv_host.py` e separar o cliente ENet em outro processo:

1. processo A, Python 3.10: entra no Eden e publica `NetworkInfo`/Pia em um socket ou pipe local;
2. processo B, runtime do host sintético comprovado: hospeda o ESP32 e faz a tradução Pia;
3. comparar lifecycle e cadência do frontend B com a captura `8184` antes de envolver o jogo;
4. somente depois repetir Eden↔Switch.

Essa separação elimina a principal diferença restante: a ponte monolítica precisa do runtime Python 3.10 por causa do módulo `enet`, enquanto o host sintético comprovado roda no runtime Python atual.

## Integridade deste checkpoint

- `tools/eden_radio_bridge.py`: `9C3CCF394562EFA2CEEABB3A49A54F2D8C959841957FA11DD184D895582A555F`

