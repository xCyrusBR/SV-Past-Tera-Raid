# Plano de implementação do simulador

## Base reutilizável

O checkout irmão `../pokeldn-research` já implementa uma sessão Scarlet/Violet real para Link Trade:

- LDN e associação do console;
- Pia v11, criptografia e sessão;
- protocolos Net, RTT, Session e streams confiáveis;
- anúncio, entrada, confirmação e conclusão de uma interação de jogo.

Ele será tratado como dependência somente de leitura enquanto possuir alterações locais não relacionadas.

## Já implementado aqui

- extração preservada do pacote do evento e do save;
- leitura estruturada do pacote Poké Portal;
- seleção verificável do Mewtwo 7 estrelas;
- manifesto SHA-256 dos cinco arquivos binários do evento;
- máquina de estados do ciclo mínimo do anfitrião;
- simulação offline e testes automatizados.

## Lacuna real

Os pacotes específicos de Tera Raid ainda não estão descritos no código disponível. Não é correto reaproveitar mensagens de Link Trade ou inventar um payload a partir dos JSONs: os arquivos do evento descrevem o conteúdo da raid, enquanto o protocolo de sala define como Scarlet/Violet anuncia o cristal, os participantes e o início.

## Referência real validada

Dois clientes Scarlet 4.0.0 independentes no Eden 0.2.1 entraram na mesma sala LDN, exibiram o segundo jogador no lobby do Mewtwo e carregaram a batalha em ambas as janelas. Isso valida o ambiente de referência necessário para capturar as mensagens ausentes.

Parâmetros reproduzidos:

- servidor Eden dedicado local em UDP `24872`;
- dois nomes de sala distintos no cliente: `Host` e `RaidGuest`;
- segundo cliente com NAND, update e save fisicamente independentes;
- entrada do participante pelo código de quatro dígitos gerado pelo jogo;
- 19 GB de pagefile no host Windows de 16 GB de RAM;
- ordem de boot: participante primeiro, anfitrião depois.

Os ACKs, a atribuição de slot `type 9` e a entrada na sala Eden continuam sendo marcos de transporte; somente o jogador visível no lobby e a batalha carregada contam como sucesso de gameplay.

## Próxima implementação

1. Capturar a sessão de dois clientes validada e identificar o formato da propaganda/sala de Tera Raid, com foco na transição posterior ao `type 9`.
2. Criar um adaptador `RaidWireAdapter` sobre a base LDN/Pia v11 de `pokeldn-research`.
3. Mapear as mensagens observadas para os estados `ADVERTISING`, `PARTICIPANT_JOINED`, `PARTICIPANT_READY` e `BATTLE_STARTED`.
4. Encerrar a rede imediatamente após a confirmação de `BATTLE_STARTED`.
5. Testar primeiro no transporte LAN/emulador já suportado por `sv_host.py`; somente depois ligar ao rádio/ESP32-S3.

Os itens 1 a 3 foram validados em 26/09/2026. Um Host Eden real aceitou o participante sintético `RaidProbe`, exibiu seu nome e Pokémon, recebeu o Ready e mostrou ambos na cena da raid do Mewtwo. O probe foi encerrado nessa fase; o host ficou com o tempo congelado e sem a interface de golpes, logo `BATTLE_STARTED` ainda não foi validado.

O próximo teste deve manter o probe conectado depois da cena da raid e reproduzir/confirmar as mensagens seguintes até a interface de golpes aparecer e o cronômetro correr. Somente depois disso será correto marcar `BATTLE_STARTED`. Em seguida, os payloads de replay que ainda contêm dados do convidado capturado devem ser gerados a partir de uma identidade própria e empacotados como `RaidWireAdapter`. A validação com Switch físico continua sendo uma fase separada.
