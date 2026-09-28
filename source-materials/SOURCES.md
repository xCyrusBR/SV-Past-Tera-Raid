# Materiais da conversa "Projeto de Raids Passadas"

Conversa de origem: https://chatgpt.com/g/g-p-6ab6694e5c6c81919d3deac8e1501b7e-pldn/c/6ab66edf-9cec-83e9-80cb-c83e5f6113dc

## Anexos

### 029 Mighty Mewtwo Showdown - Mewtwo the Unrivaled.zip

- Tamanho: 26.710 bytes
- SHA-256: `FF1980C2E96A421BE50CA14B8E2B0DC56D635B2B237F1D7C8625A2A92BAC9C53`
- Conteúdo verificado:
  - `Encounters.txt`
  - `Identifier.txt`
  - `Files/event_raid_identifier_1_3_0`
  - `Files/fixed_reward_item_array_1_3_0`
  - `Files/lottery_reward_item_array_1_3_0`
  - `Files/raid_enemy_array_1_3_0`
  - `Files/raid_priority_array_1_3_0`
  - equivalentes legíveis em `Json/`

### pkmnscarlet_100.7z

- Tamanho: 4.436.970 bytes
- SHA-256: `145BE0C7D924ED2A8779AB23A7B5AE8429B6ED4E5B49F5FA336D904C1BDE37B0`
- Conteúdo verificado: um arquivo `main`.
- A conversa registra o `main` com 4.436.579 bytes e estrutura geral compatível com save de Scarlet/Violet.
- O save foi preservado sem alterações.

## Links fornecidos pelo usuário

- Greninja, encontro: https://projectpokemon.org/home/files/file/4913-tera-raids-unrivaled-greninja/
- Greninja, pacote Poké Portal Event #08: https://projectpokemon.org/home/files/file/4914-pok%C3%A9-portal-event-08-greninja-the-unrivaled/
- Mewtwo, pacote Poké Portal Event #29: https://projectpokemon.org/home/files/file/5202-pok%C3%A9-portal-event-29-mighty-mewtwo-showdown-mewtwo-the-unrivaled/

## Referências citadas nas respostas

- Nintendo, multiplayer local/online de Scarlet/Violet: https://en-americas-support.nintendo.com/app/answers/detail/a_id/60279/p/988
- Nintendo, instruções relacionadas: https://en-americas-support.nintendo.com/app/answers/detail/a_id/60279/p/989/c/871
- Event Raid Injector: https://github.com/Insektaure/Event-Raid-Injector
- Discussão sobre comportamento de Tera Raids e desconexão: https://www.reddit.com/r/PokemonScarletViolet/comments/13jhx38

## Leitura técnica consolidada

- O pacote do Mewtwo contém dados do evento (chefes, recompensas, prioridade e identificador), não apenas um Pokémon capturado.
- O pacote Poké Portal do Greninja é o paralelo útil ao ZIP do Mewtwo; a página de encontro isolado tem finalidade diferente.
- As fontes descrevem importação dos dados de evento no save. Não demonstram distribuição desses arquivos pelo LDN.
- O save e o pacote de evento fornecem referência para reconhecer campos em capturas LDN, mas não executam nem hospedam a raid sozinhos.
- Ainda é necessário capturar uma sessão LDN real desde o anúncio da sala até o início (e, idealmente, conclusão) da batalha.
