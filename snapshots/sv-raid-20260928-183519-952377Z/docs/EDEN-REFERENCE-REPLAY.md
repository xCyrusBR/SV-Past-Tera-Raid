# Replay da sessão Eden↔Eden

Atualizado em 28/09/2026. Este documento registra como a sessão funcional de dois Edens foi
transformada em uma referência executável para o host sintético.

## Referência observada

- Captura: `lab/eden-two-client-raid-20260926.jsonl`
- Decodificação: `lab/eden-two-client-raid-decoded.jsonl`
- Resultado visual: host e `RaidGuest` no lobby, ambos Ready e cena da raid carregada.
- Abertura LDN: um participante no anúncio; depois da entrada, dois nós e dois jogadores.
- Port 2 real: o guest envia type 3 e o host responde type 9. Não existe type 7 nessa abertura.

## Diferenças encontradas no host sintético anterior

1. O replay terminava no registro host `0x80:0` sequência 70; a sessão real continua até 219.
2. Os registros 52/53 e 69/70 são fragmentos. O replay antigo convertia cada fragmento em uma
   mensagem completa, removendo os bits Start/Middle/End observados.
3. A sessão real deixa lacunas deliberadas na janela reliable após registros grandes. O replay
   agora consome essas sequências sem inventar payloads.
4. O A/B 6149 removeu o type 7 porque ele não aparece isoladamente na raid Eden real. O Violet
   completou Pia e type 9, mas permaneceu em `Communicating`. Isso demonstra que o game-host real
   fornece estado equivalente por outra via; o host standalone ainda precisa de `--announce`.
5. Um primeiro A/B tentou devolver ao Violet seus broadcasts `0x80:0`/`0x81:1`, mas a captura
   provou que o Eden entrega os registros do guest somente ao host, não ao próprio guest. Esse
   loopback deixou o Violet preso em `Communicating` e foi removido.

## Implementação

- `tools/sv_raid_host.py` agora deriva da captura todos os registros host 44–219.
- São 92 transmissões reais e 84 avanços de sequência, mantendo a temporização relativa.
- `pokeldn/sv/streams.py` ganhou o marcador `:middle`, para continuações sem Start nem End.
- O A/B 3861 provou que o primeiro PK9 de `0x80332f` é o Pokémon local do destinatário: ao
  colocar Mew ali, o Violet físico entrou na cena como Mew. Agora PR/Mew fica no anúncio de
  lobby `0x80332e`, enquanto o `0x80332f` recebe dinamicamente o PK9 selecionado pelo Violet.
- O Mewtwo da referência permanece intacto.
- Os testes 4682 e 6149 confirmaram LDN, Pia, type 3 e type 9, mas isolaram duas regressões:
  loopback do guest e remoção do type 7. O próximo A/B preserva o caminho de admissão conhecido
  (`announce`) e somente muda o replay posterior. Deve confirmar, nesta ordem: nome PR/Mew,
  treinador físico/Pokémon escolhido,
  cronômetro correndo, cena carregada e menu de golpes.

## Validação local

- `python -m py_compile` passou nos arquivos alterados.
- `python -m unittest discover -s tests -q`: 14 testes, todos passaram.
- ROM e update 4.0.0 não foram necessários nesta etapa: a captura funcional fornece evidência
  mais direta do wire protocol. Eles ficam reservados para identificar campos que ainda permaneçam
  opacos depois do próximo teste A/B.

## Integridade

- `tools/sv_raid_host.py`: `D073248D9156D32A71E41D3DB642430D69CD4C009E7E01A6007BD83EFE926CEB`
- `tests/test_sv_raid_host.py`: `3C9AC002D4F83F8883315EF97D6E56729139B2AC0D839E4A0978D955E8BA0BC4`
- `../pokeldn-research/pokeldn/sv/streams.py`: `E23DA324B8C836FABA2ACC6EEF50D737B88A4F2CF1B6368A7145918992651410`
