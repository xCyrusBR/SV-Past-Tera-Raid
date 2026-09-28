# Status do host sintético de Tera Raid

Atualizado em 28/09/2026. Esta linha é o caminho recomendado para o objetivo final: hospedar a raid para um Switch intacto sem depender do Eden durante a operação normal.

## Resultado confirmado

- O Violet físico encontra o host local anunciado pelo ESP32-S3 em `COM4`.
- O Switch completa LDN, Net e Session/Pia e entra no lobby sintético.
- No teste A/B mais recente, o código `8184` entrou no lobby imediatamente. A captura registra a resposta Net `0x12` ao `seqid 4` e o Session Join do Switch.
- Em testes anteriores, especialmente `7318`, a cena do Mewtwo carregou, o Mew do host apareceu, o Mewtwo executou uma ação inicial e a barra de HP do Mew apareceu.
- Ainda não houve batalha jogável: o menu de golpes não apareceu e nomes/slots/aliados ficaram incorretos.
- No teste `6418`, o host esperou corretamente o Ready real do Violet (`0x80332d`, sequência 3) antes da transição. O convidado respondeu com as sequências 4–6 idênticas às da captura Eden↔Eden, mas não enviou a sequência 7 depois dos registros 56–61 do host. Visualmente apareceram três Iron Hands, um Dudunsparce e dois participantes invisíveis; não houve barra de HP nem menu. Logo, a correção de timing é válida, mas não resolveu a identidade/lista de jogadores.
- No teste `7354`, o ID de PR foi configurado como `4294423561`, separado da identidade do Pokémon selecionado. O Violet físico mostrou o próprio Iron Hands no slot 1; ao sair, PR apareceu tardiamente no slot 3 com esse Iron Hands. O rádio identificou o treinador físico como Cyrus nessa tentativa. Evan é a identidade do save Scarlet de referência, não o convidado físico nem um segundo participante sintético. Portanto os dados de PR chegam, mas o mapeamento/ordem de slots está errado.
- No teste `2846`, omitimos o anúncio port-2 type 7 e mantivemos type 9; o Violet permaneceu em `Communicating`. O anúncio foi restaurado como padrão. O jogo mostra a mensagem de preenchimento das vagas por NPCs somente depois de Start, mas ainda não sabemos se a escolha/seed desses NPCs vem do host ou é decidida pelo cliente. Não há evidência de que criar jogadores sintéticos extras resolva o problema.
- O teste anterior confirmou que, depois de uma raid realmente iniciada, o participante consegue continuar quando o anfitrião desconecta. Portanto o host final não precisa simular o combate inteiro, apenas levar a sessão até `BATTLE_STARTED` real.
- Auditoria offline posterior: a referência funcional tem exatamente duas estações Session (índices 0/1) e um registro kind-1 de identidade para cada treinador. O registro de início `0x80332f` contém o Pokémon local no offset 21 e o Mewtwo no offset 724; substituir o primeiro pelo Mew de PR faria o Violet entrar com o Pokémon errado. A referência usa o mesmo PK9 selecionado nos dois Edens, portanto não comprova o caso com Pokémon distintos. Detalhes em `docs/ROSTER-AUDIT.md`. Nenhuma alteração de protocolo foi feita com base apenas nessa comparação.
- Novos testes controlados de lobby: `4186` com type-7 slot 0 e `9024` com slot 1 entraram, mas ficaram com nomes/ícones vazios. Após selecionar Iron Hands, o convidado ocupou o primeiro lugar; ao encerrar `9024`, ele passou ao segundo e PR surgiu no terceiro com uma cópia do Iron Hands. O host transmitiu PR/ID e Mew corretamente e recebeu ACK da sequência 47 do conjunto de registros. Logo, apenas mudar o slot não resolveu. O teste de timing `5649` colocou o type-7 antes do type-9 e ficou em `Communicating`; a opção experimental foi removida.
- A comparação offline posterior encontrou um campo de conta de 22 bytes zerado no registro kind-1 do host Eden, enquanto o host sintético inventava uma conta `u-...`. Corrigimos o modo raid para preservar o campo offline da referência, mantendo PR/ID; teste local passou. No reteste físico `6742`, o Violet entrou no lobby e recebeu a atualização tardia da Session, mas nomes/ícones continuaram vazios com o contador avançando. Essa correção isolada não resolveu o roster.
- A comparação seguinte descartou uma suspeita de atraso dos registros iniciais: em ambas as capturas, o host os enviou cerca de 0,05–0,08 s após os dois primeiros registros de jogo do convidado. Testamos uma diferença isolável: gerações da Session `0/0/1` na referência Eden e `1/1/2` no host sintético. No teste físico `2851`, `--session-seq-base 0` entrou no lobby, enviou os 44 registros com ACK até 47 e a segunda atualização em +49,07 s; nomes/ícones continuaram vazios com contador avançando. A opção permanece diagnóstica, não uma correção.
- Após encerrar `2851`, o Violet exibiu o convidado no slot 2 e PR no slot 3, ambos com Mew. A captura prova que o convidado havia anunciado Iron Hands (espécie 992) e o host, Mew (151). Em `9024`, uma seleção adicional de Iron Hands feita após o anúncio do host precedeu a exibição tardia de Iron Hands nos dois slots. A correlação sugere que o último anúncio está sendo aplicado aos dois lugares por falha de associação; não prova que o Pokémon real do convidado virou Mew.
- O A/B `4638` omitiu o ACK de entrada da Session, mas o lobby continuou vazio com contador avançando; o conjunto de 44 registros foi confirmado até a sequência 47. Esse ACK isolado não era a causa.
- Encontramos um defeito concreto no `type 6`: ele já existia, mas vinha comprimido e a rotina antiga tentava trocar os IDs sem descomprimir; assim transmitia os IDs da sessão Eden antiga. Na referência funcional, os dois campos são cópias do **ID do host**, não host+convidado. O diagnóstico `6184` duplicou indevidamente a mensagem e `7023` usou host+convidado; ambos falharam antes do lobby. Corrigimos a mensagem única para escrever o ID atual do host nos dois campos e recomprimir.
- No reteste físico `8167`, PR apareceu no slot 1 e Cyrus no slot 2, com o contador avançando: avanço visual real. Porém os ícones ainda eram iguais e os Pokémon ficaram cruzados. A captura confirma Iron Hands anunciado pelo Violet e Mew anunciado pelo host; ao selecionar Iron Hands novamente, PR passou a mostrá-lo enquanto Cyrus permaneceu com Mew. Não houve Ready nem batalha. O próximo A/B curto, quando o usuário puder, é omitir somente o anúncio `type 7` extra mantendo o `type 6` corrigido; a referência Eden não envia type 7, e o teste antigo sem ele tinha IDs stale.

## Artefatos principais

- Implementação: `tools/sv_raid_host.py`
- Base LDN/Pia: `../pokeldn-research/bin/sv_host.py`
- Captura A/B aceita: `lab/sv-raid-ab-8184.jsonl`
- Trace de rádio correspondente: `lab/sv-raid-ab-8184-esp32.trace`
- Log legível: `lab/sv-raid-ab-8184.stdout.log`
- Melhor avanço visual anterior: `lab/sv-raid-host-pr-mew-7318.jsonl`
- Teste com Ready sincronizado: `lab/sv-raid-ready-gated-6418.jsonl`
- Teste de identidade separada: `lab/sv-raid-pr-identity-7354.jsonl`
- Teste sem type 7: `lab/sv-raid-no-type7-2846.jsonl`
- Captura de referência Eden↔Eden: `lab/eden-two-client-raid-20260926.jsonl`
- Decodificação da referência: `lab/eden-two-client-raid-decoded.jsonl`
- Registros reais do host: `lab/mewtwo-host-records/`
- Registros reais do convidado: `lab/mewtwo-guest-records/`
- Mew do host: `C:/Users/allan/Downloads/0151 - Mew - F94FA89CCE3D.pk9`

## Reprodução

Feche qualquer programa que esteja usando `COM4`. A partir da raiz `past-raids-project`:

```powershell
python .\tools\sv_raid_host.py `
  --code 8184 `
  --lobby-only `
  --seconds 180 `
  --capture .\lab\sv-raid-ab-retest.jsonl
```

Sem `--lobby-only`, o script agenda os registros de Ready, início e estado de batalha extraídos da sessão Eden↔Eden.

## Próximo passo exato

Continuar nesta linha, usando a captura Eden↔Eden como oráculo, sem adicionar jogadores sintéticos extras:

1. identificar por que os registros PR/Mew recebidos não são associados ao host no lobby; mudar apenas o byte de slot do type-7 não resolveu, e PR ainda surge tardiamente no slot 3;
2. deixar os dois lugares restantes para os NPCs da batalha e determinar se o host transmite sua escolha/seed ou se o cliente os seleciona;
3. gerar dinamicamente os registros de identidade, seleção do Pokémon e Ready, em vez de repetir identidades capturadas;
4. reproduzir a transição host `0x80:0` imediatamente anterior ao carregamento e conservar ACKs/seqids por porta;
5. considerar sucesso somente quando aparecer o menu de golpes e o cronômetro da batalha correr;
6. depois disso, testar a desconexão do host e a substituição por NPC.

## Checkpoint Eden-reference de 28/09/2026

Foi concluída uma comparação nova com a sessão funcional de dois Edens. O replay anterior
achatava mensagens fragmentadas e terminava na sequência 70. A implementação agora preserva a sequência real completa
44–219, incluindo 92 registros, 84 lacunas reliable e os limites Start/Middle/End. Consulte
[`EDEN-REFERENCE-REPLAY.md`](EDEN-REFERENCE-REPLAY.md) antes do próximo teste físico.

## Integridade deste checkpoint

- `tools/sv_raid_host.py`: `D073248D9156D32A71E41D3DB642430D69CD4C009E7E01A6007BD83EFE926CEB`
- `tools/sv_raid_host.py` atual: `37EEBA61AC8EADA78209271F9FCB4ECC30BBF68941F83E0DC35A1960510D4606`
- `lab/sv-raid-ready-gated-6418.jsonl`: `9549E2DE98B36337E7FD2BCFF08B02BA3044CA4FAF97EE31CB094AB808D26064`
- `lab/sv-raid-pr-identity-7354.jsonl`: `041B590A3653B9E8DEB460FDAD48CF169AAD6FC0DE98C17DFD25289E48E579AA`
- `lab/sv-raid-no-type7-2846.jsonl`: `7FC200FAE7F739051FB0642A64B9F74FEB9B7FCB075005FDE2AEDFA53A34CE92`
- `lab/sv-raid-ab-8184.jsonl`: `ACCE380C55C7A5C6974CDFB61EDFC57818C9D807C25F8CF7E3D14679F92DC342`

