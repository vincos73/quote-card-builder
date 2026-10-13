# Quote Card Builder su ChatGPT Sites: pilot del 2–3 ottobre 2026

## Esito

**Il Site privato dichiara ora un server MCP e Sites ha creato il plugin associato.** È pubblicato su
https://quote-card-builder-mcp-pilot-20261002.vincos.chatgpt.site. Il deployment v3, dopo
l'aggiunta di `"capabilities": ["mcp"]` in `.openai/hosting.json` e di `POST /mcp`, è
`succeeded` con `has_mcp: true`. Il deployment v4 mantiene lo stesso plugin e rende il Worker
stateless rispetto al client: per ogni richiesta successiva all'inizializzazione apre e chiude
una sessione indipendente verso Cloud Run. `get_site(include_mcp_connection: true)` restituisce l'endpoint,
la risorsa OAuth e un `plugin_id`; la scheda di installazione del plugin è stata proposta nell'app.
La pagina del plugin in ChatGPT mostra ancora il pulsante «Installa plugin»; non risulta installato
nell'account aperto in Chrome.

Il Worker continua a inoltrare le richieste MCP al servizio Quote Card Builder su Cloud Run. La
verifica autenticata del percorso applicativo `/api/mcp` ha completato `initialize`, `tools/list`,
`resources/read` e una chiamata read-only a `quote_card_builder_open_editor` con testo sintetico,
senza inviare `Mcp-Session-Id`. L'endpoint gestito `/mcp` ha restituito HTTP 401 al token
temporaneo di accesso al Site: richiede la connessione OAuth del plugin. **Installazione,
connessione, tool call tramite il plugin e rendering dell'editor nel client restano da verificare.**
Il backend Cloud Run resta sessionale e necessario al rendering: l'hosting autonomo del renderer
Python su Sites non è stato provato.

Il precedente deployment v2 era `succeeded` ma `has_mcp: false` perché il manifest non dichiarava
la capability. Il token temporaneo del proprietario è stato passato alle prove via stdin, senza
salvarlo nei file.

## Oggetti e prove

| Oggetto | Identificativo o risultato |
| --- | --- |
| Site | `appgprj_6abf45cabe3c81918ed306c7f567cd9e` |
| Accesso | Solo proprietario: policy `custom`, un utente autorizzato, nessun gruppo |
| Sorgente Sites | `https://git.chatgpt-team.site/dadce729-360d-4034-a033-9bb1b2f0b021/appgprj_6abf45cabe3c81918ed306c7f567cd9e.git`, branch `main` |
| Commit pubblicato | `ae58aa203eaf57ca0f3c939401d9112d8de40f10` |
| Versione Sites | `appgprj_6abf45cabe3c81918ed306c7f567cd9e~appgver_cdb3f3789e148191ad28a9605c81978e` |
| Deployment | `appgdep_6ac0a25878748191a9a023ee4c3b0543`, `succeeded`, `has_mcp: true` |
| Plugin Sites | `plugin_asdk_app_sites_6a6a4d45dfb48191b73b4bcd47e8a8a7` (pagina visibile, pulsante «Installa plugin», connessione non verificata) |
| `/health` | HTTP 200 dal proxy |
| `/mcp` | Endpoint dichiarato da Sites; HTTP 401 usando il solo token temporaneo Site, in attesa del login OAuth del plugin |
| `/api/mcp` | Percorso di prova autenticato con token proprietario; accetta `POST` |
| MCP via `/api/mcp` senza session ID | `initialize`, `tools/list`, `resources/read`, `tools/call`: HTTP 200; quattro tool, UI HTML e apertura editor di test |
| Backend Cloud Run diretto senza session ID | `initialize`: HTTP 200; `tools/list`: HTTP 400. L'adattatore Sites risolve questa dipendenza per il client. |

Lo smoke ha elencato `quote_card_builder_open_editor`, `preview_quote_card`,
`produce_quote_card`, `quote_card_builder_headless` e letto
`ui://quote-card-builder/preview/v1.45.html`. Nel checkout locale la risorsa corrente è
`v1.40.html`: il pilot usa dunque lo stato live di Cloud Run e non dimostra la parità con il
checkout in lavorazione. La chiamata di prova ha usato solo la frase sintetica “Pilot tecnico
Sites MCP.” e non ha salvato né pubblicato dati editoriali.

## Architettura provata

```text
Site privato (Worker) ── /mcp, /api/mcp ──► Cloud Run MCP ──► renderer canonico
                        /health ──────────► Cloud Run
```

Il Worker costruisce solo gli header MCP necessari. Cookie, token di accesso al Site e header di
identità non sono inoltrati a Cloud Run. Per ogni richiesta MCP successiva a `initialize`, apre
una sessione Cloud Run temporanea, usa il suo ID solo verso il backend e prova a chiuderla dopo
la risposta. Il token temporaneo di prova è passato al processo tramite
stdin e non è incluso nei file. L'istanza dipende ancora dal servizio Cloud Run: non è una
migrazione del renderer Python su Sites.

Per riprodurre le verifiche locali:

```sh
npm test
npm run build
```

`scripts/probe_site.py` e `scripts/smoke_mcp.py` accettano su stdin una riga JSON con `url` e
`token` restituiti al proprietario dal controllo Sites. Lo smoke accetta anche `mcp_path` e
`omit_session` per diagnosticare separatamente l'endpoint gestito e il backend. Non inserire il
token nel repository o nella shell history.

## Plugin Extensions e futura submission

La documentazione ufficiale consente di dichiarare una voce globale della sidebar aggiungendo
all'`_meta` di un tool con UI `"openai/ui": {"entrypoints": [{"type": "global"}]}`. Per Quote Card
Builder è il primo punto di integrazione sensato: l'editor avrebbe una sede permanente. **La
specifica richiede però che il tool di ingresso globale accetti `{}`.** Il tool attuale
`quote_card_builder_open_editor` richiede frase, attribuzione e palette, quindi non può ricevere
semplicemente questi metadati. Occorre un tool di apertura distinto, senza argomenti obbligatori,
che mostri l'editor inizialmente vuoto; il tool attuale conserva il flusso guidato da chat. Il
pannello di conversazione (`type: "thread"`) ha lo stesso requisito di `{}` ed è una seconda
possibilità da valutare con una prova visiva.
File viewer e composer mentions non hanno ancora un caso d'uso necessario per questo pilot. Il tool
live restituisce `_meta.ui.resourceUri`, ma non è stata osservata una dichiarazione `openai/ui`.

La submission nella directory è un percorso distinto: il portale richiede un pacchetto ZIP con il
server MCP incluso nella prima versione, identità editore verificata, endpoint raggiungibile e
scansione degli strumenti. Il server da sottoporre a review deve essere accessibile pubblicamente,
e il portale richiede la verifica del dominio e casi di prova positivi e negativi. Dopo
l'approvazione si sceglie quando pubblicare. L'origine del server
MCP non può cambiare nelle versioni dello stesso plugin: passare da Cloud Run a un hostname Sites
dopo la submission richiederebbe un nuovo plugin. Non è stata effettuata alcuna submission.

**Decisione del pilot:** il prerequisito Sites è superato (`has_mcp: true`, `mcp_connection`,
`plugin_id`). Il trasporto stateless del Worker è stato provato sul percorso applicativo;
restano installazione, OAuth, tool call e apertura dell'editor attraverso il plugin nel client.
Mantenere Cloud Run come candidato per una submission pubblica finché queste prove non riescono e
finché la dipendenza del renderer dal servizio esistente non è valutata. Il plugin Sites resta
privato.

Fonti ufficiali consultate:

- https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites
- https://learn.chatgpt.com/docs/sites
- https://developers.openai.com/plugins/build/extensions
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/build/chatgpt-ui
- https://developers.openai.com/plugins/build/auth
- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://developers.openai.com/plugins/concepts/ui-guidelines
- https://developers.openai.com/plugins/deploy/submission
- https://developers.openai.com/plugins/deploy/app-review
- https://github.com/openai/mcp-extensions
- https://github.com/openai/mcp-extensions/blob/main/docs/spec.md
- https://github.com/openai/mcp-extensions/blob/main/python/README.md

## Verifica del repository MCP Extensions (2 ottobre 2026)

La ricognizione del repository ufficiale `openai/mcp-extensions` è riferita al commit
`900032d8bd7c1566202d0cb1666986584f932043`. Il progetto comprende specifica, SDK TypeScript,
SDK Python (`openai-mcp-extensions`) e il plugin dimostrativo Bits & Bolts. L'SDK Python mostra
come registrare l'entrypoint con `OpenAIUiToolMetadata` e `OpenAIGlobalEntrypoint` sul tool MCP App;
mostra anche `OpenAIUiResourceMetadata` per indicare i display mode disponibili.

Per un primo incremento a Quote Card Builder:

1. Registrare un tool d'ingresso dedicato che accetti `{}` e restituisca lo stato iniziale vuoto
   senza creare una quote card o scegliere contenuti al posto dell'utente.
2. Associare a quel tool la risorsa `ui://...` dell'editor e l'entrypoint `global`; fornire titolo e
   icona secondo la specifica. Verificare la resa fullscreen dell'interfaccia.
3. Lasciare `quote_card_builder_open_editor` come tool guidato dal modello per i tre dati editoriali
   già raccolti. Collaudare separatamente l'apertura da sidebar e da conversazione.

Il repository delle Extensions **non documenta l'attivazione del server MCP su ChatGPT Sites**:
risolve il contratto delle superfici ChatGPT dopo la connessione. La capability Sites `mcp` è stata
ricavata dalla skill Sites MCP del runtime e verificata con il deployment v3. Nessun pacchetto SDK
è stato aggiunto al progetto e nessuna Extension è stata annunciata come funzionante nel client.

## Applicazione futura a Mission

La pagina Extensions e la specifica `openai/mcp-extensions` separano il server MCP dalla superficie
che lo apre in ChatGPT. Per Mission, la prima prova sensata è una voce `global` nella sidebar che
apra la sua interfaccia senza argomenti obbligatori; un ingresso `thread` avrebbe senso se la
stessa vista debba restare accanto alla conversazione. I deep link potrebbero aprire una missione
specifica, mentre Model-App Context servirebbe solo se chat e vista devono scambiarsi stato.
Onboarding e settings sono opzioni successive, da giustificare con un flusso reale. Prima va
verificato il contratto dei tool, la risorsa UI e la connessione nel client: il solo deployment
MCP su Sites non abilita automaticamente queste Extensions.
