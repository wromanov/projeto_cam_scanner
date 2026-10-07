# CAM SCANNER — continuidade do projeto

Use esta página para retomar o trabalho sem depender do histórico do chat.

## Estado e plano

- [`PROJECT_STATE.md`](PROJECT_STATE.md): estado factual, gates, autorização e ponto seguro de retomada.
- [`ACTIVE_AUTHORITY_MAP.md`](ACTIVE_AUTHORITY_MAP.md): authorities ativas e localizadores.
- [`CONTINUITY_RECORD.md`](CONTINUITY_RECORD.md): decisões, achados e pendências.
- [`PROJECT_GOVERNANCE_BINDING.json`](PROJECT_GOVERNANCE_BINDING.json): baseline adotado e pins por identidade, versão e SHA-256.
- [`planning/ROADMAP.md`](planning/ROADMAP.md): roadmap aprovado.
- [`planning/EXECUTION_PLAN.md`](planning/EXECUTION_PLAN.md): sequência de atividades e critérios de saída.
- [`../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md`](../contracts/P1_SINGLE_MINIMUM_VERTICAL_SLICE.md): contrato P1 aprovado; implementação P1-A01 autorizada com tipagem dos 14 campos fechada.
- [`handoff/LAST_HANDOFF.md`](handoff/LAST_HANDOFF.md): handoff deste checkpoint.
- [`NEW_AGENT_BOOTSTRAP.md`](NEW_AGENT_BOOTSTRAP.md): instruções para novo agente.

## Regras de retomada

Leia `AGENTS.md`, este pacote e resolva os pins do binding por identidade e hash. O root de governança global está fora deste projeto e deve ser redescoberto por seus arquivos canônicos; neste ambiente ele fica em `../governanca_de_projetos/`. O primeiro checkpoint governado foi publicado em `origin/master`; confirme branch, HEAD, upstream e estado de trabalho em runtime. A documentação usa `CURRENT_GOVERNED_CHECKPOINT = CURRENT_REPOSITORY_HEAD` para evitar o ciclo de inserir o próprio hash no commit.

P0-A02 executou Foundation Review com resultado `CHANGES_REQUIRED`; decisões F-01…F-08 e remediação estão registradas em `PROJECT_STATE.md` e `CONTINUITY_RECORD.md`. `PROJECT_OPENING_GATE` e `AGENT_HANDOFF_GATE` refletem somente evidências registradas no pacote. Nenhum gate concede autorização de implementação ou publicação Git. O usuário autorizou P1-A01; nenhuma escrita Git está autorizada.

## Estado histórico após P1-C01-R2 (supersedido por P1-A01)

P0-A04 permanece como revisão concluída com `PASS_WITH_ACCEPTED_FINDINGS`; evidência em [`../audit/FOUNDATION_REVIEW_P0_A04.md`](../audit/FOUNDATION_REVIEW_P0_A04.md). P0-A05-R1 reconciliou a aprovação já concedida: Project Opening Gate `PASS` e P0 `CLOSED`. P1-C01-R1 reconciliou os 14 campos de `CameraResult`; P1-C01-R2 fechou as tipagens. PROJECT_STATE é a fonte do estado corrente; P0-A02 permanece histórico. Os pins foram resolvidos nos ZIPs exatos indicados em ACTIVE_AUTHORITY_MAP.

## Estado atual após P1-A02

P1-A01 implementou e integrou o fluxo SINGLE, validado com ONVIF falso em Python 3.14.0. P1-A02 executou o fluxo autorizado contra `10.143.36.33`, mas três tentativas retornaram `AUTH_ERROR`; nenhum dado de dispositivo foi obtido. P1 continua `NOT_READY`. Consulte `PROJECT_STATE.md` para o próximo passo. Credenciais devem ser informadas localmente pelo prompt `getpass()`.
