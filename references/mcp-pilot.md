# MCP pilot locale

Questa prima integrazione aggiunge un solo flusso end-to-end con tre tool coordinati:
`quote_card_builder_open_editor` apre l'interfaccia una volta, `preview_quote_card` ne aggiorna
i dati senza rimontarla e `produce_quote_card` genera l'SVG canonico dopo il clic
esplicito dell'utente su **Genera**; l'interfaccia lo converte in PNG e preferisce **Download PNG**
oppure **Send PNG to chat**, in base alle capacità dichiarate dall'host.
Il server MCP gira via stdio nel pacchetto locale e via Streamable HTTP nel servizio remoto; usa
il renderer Python esistente come unica fonte di verità.
Il server non rasterizza direttamente PNG, non salva sessioni, non pubblica contenuti e non
modifica l'installazione personale.

## Input

L'input è un oggetto con schema esplicito:

| Campo | Tipo | Default | Note |
| --- | --- | --- | --- |
| `text` | stringa | obbligatorio | da 1 a 600 caratteri |
| `attribution` | stringa | obbligatorio in apertura | etichetta visibile; stringa vuota solo dopo la scelta esplicita “nessuna”, massimo 160 caratteri |
| `profile_mode` | enum | obbligatorio in apertura | `neutral` o `custom`, scelto esplicitamente dall'utente; usato da `quote_card_builder_open_editor` |
| `transformation` | enum | `VERBATIM` | `VERBATIM`, `EDITED`, `PARAPHRASE`, `AI_GENERATED` |
| `evidence_status` | enum | `USER_SUPPLIED` | stato della prova editoriale dichiarato dal chiamante |
| `direction` | enum | obbligatorio in apertura | `editorial`, `statement`, `contextual`; il tool dati mantiene `editorial` come fallback tecnico |
| `palette` | oggetto o nullo | nullo | scelta esplicita `{name, colors}`; `colors` contiene `primary`, `accent`, `background`, `text` in formato `#RRGGBB` |
| `lines` | lista di stringhe | una riga | almeno una riga; devono ricostruire `text`; nessun limite fisso oltre ai 600 caratteri di `text` |
| `styles` | lista | assente | intervalli `{start,end,type}` con offset Unicode |
| `alt_text` | stringa | automatico | sostituzione facoltativa, massimo 400 caratteri |

Il profilo neutro canonico (`#072743`, `#E3F4FF`, `#FEFDFB`, `#323232`, Arial) viene usato
dal tool di apertura solo con `profile_mode: neutral`; il tool dati conserva la palette omessa
come fallback tecnico interno alla UI. In alternativa
il chiamante può trasferire una palette esplicita con nome e quattro colori. Il server non
inferisce, salva o recupera automaticamente un'identità di brand.

## Domande preliminari

La skill/plugin deve raccogliere prima della chiamata iniziale, con queste etichette esatte:
1. frase; 2. attribuzione visibile oppure “nessuna”; 3. palette, scegliendo fra profilo neutro
e personalizzata; 4. direzione Editoriale, Manifesto o Campo. Il terzo dato non è tono o mood
e il quarto non è uno stile generico. Quando le quattro risposte sono presenti il chiamante deve
usare `quote_card_builder_open_editor`, senza sostituire l'app con generazione immagini, SVG, PNG, HTML o altro file creato
direttamente nella chat. Se il runtime locale espone
profili salvati, la skill li elenca e attende una scelta esplicita; non trasferisce font o logo
nel pilot remoto. Il server pubblica la stessa sequenza nelle `instructions` di inizializzazione
e rende obbligatori nello schema di apertura attribuzione, modalità profilo e direzione, così il
connettore remoto non deve inventare valori predefiniti. La MCP App ripropone gli stessi campi
per consentire una correzione senza aprire una seconda anteprima.

### Regressione di routing v1.22

La UI v1.22 rende esplicito anche il contratto di selezione del tool. Il solo tool pubblico
si chiama `quote_card_builder_open_editor`, segue la forma dominio + azione e accetta un input
ridotto a frase, attribuzione, modalità palette, direzione, formato iniziale ed eventuali colori
personalizzati. I quattro campi obbligatori hanno titoli numerati identici al questionario.
Le istruzioni vietano espressamente di sostituire il flusso con generazione immagini, file
autonomi o la ricerca di un editor locale.

Il set minimo di prova in Developer mode comprende:

- prompt diretto: selezionare Quote Card Builder e scrivere `test` deve produrre le quattro
  domande con **Palette** come terza voce;
- prompt completo: dopo le quattro risposte deve essere chiamato una volta
  `quote_card_builder_open_editor` e deve aprirsi una sola iframe;
- regressione osservata: frase `noli me tangere lauria uber alles`, attribuzione `vincos`,
  profilo `neutral`, direzione `editorial` deve arrivare all'editor senza blocchi immagine
  autonomi;
- prompt negativo: una richiesta esplicita di generare una fotografia non deve attivare Quote
  Card Builder.

I test automatici verificano metadati, schema e round-trip del caso osservato. La scelta del
tool da parte del modello resta una prova host-level da ripetere in una chat nuova dopo
l'aggiornamento del plugin.

### Sincronizzazione palette v1.23

La palette personalizzata è un unico stato condiviso dalle tre direzioni. Editoriale,
Manifesto e Campo ricevono gli stessi quattro colori dal renderer canonico. Nell'iframe,
il cambio di direzione, motivo, formato, posizione o colore rigenera ora automaticamente
la preview; le risposte superate vengono ignorate per evitare che una richiesta precedente
ripristini una palette o una direzione non più selezionata.

### Cornice Campo alternativa v1.24

La variante `route_map` di Campo usa un solo angolo vettoriale come sorgente geometrica.
L'angolo inferiore sinistro riutilizza esattamente lo stesso SVG con una rotazione di 180°:
linee, curva e nodi restano quindi speculari nei formati 4:5 e 1:1. La cornice continua a
essere generata inline dal renderer canonico, adattando dimensioni e colori alla card senza
caricare asset esterni.

### Candidata production v1.29

La risorsa corrente nel sorgente è `ui://quote-card-builder/preview/v1.29.html` e mostra l'etichetta pulita
`v1.29`. Le sole alias di compatibilità mantenute sono v1.26, v1.27 e v1.28: limitano la superficie
esposta allo scanner senza interrompere le due iterazioni beta più recenti. L'editor cresce con il
contenuto e non possiede una propria area `overflow:auto`, evitando uno scroll annidato nell'iframe.
Il container copia soltanto server MCP, adattatore, dipendenze dirette del renderer canonico e il
lockup Vincos incorporato nell'header della UI.

Il server espone inoltre `/.well-known/openai-apps-challenge`. La route restituisce `404` finché
`OPENAI_APPS_CHALLENGE_TOKEN` non è configurata; quando il portale fornisce il token, ne restituisce
il valore esatto senza newline o contenuto aggiuntivo.

## Output

Il risultato strutturato contiene `valid`, `rendered`, `format` (`4x5` o `1x1`), dimensioni
del rapporto selezionato, `profile`, `svg`, `svg_data_uri`, `svg_sha256`, `alt_text`, `warnings`,
`errors`, la dichiarazione `editorial_responsibility: caller` e `editor_state`, lo snapshot
esplicito di frase, attribuzione, profilo, palette e controlli che ripopola il form anche
quando il bridge dell'host consegna soltanto il risultato. `produce_quote_card` aggiunge
`produced`, `filename` e `mime_type`; l'SVG non viene conservato sul server.

Gli errori di input e di contratto sono restituiti come oggetti `{path, code, message}`;
se la validazione fallisce, `svg` è `null` e il renderer non viene chiamato. La validità
è tecnica: `VERIFIED` o altre etichette editoriali restano dichiarazioni del chiamante,
non certificazioni del server.

## Prova locale

Dalla radice del repository:

```bash
python3 -m venv /private/tmp/quote-card-builder-mcp-venv
/private/tmp/quote-card-builder-mcp-venv/bin/python -m pip install -r requirements-mcp.txt
/private/tmp/quote-card-builder-mcp-venv/bin/python -m unittest discover -s tests -v
```

Per verificare soltanto il protocollo, il test `McpProtocolTests` avvia il server reale,
esegue `initialize`, `tools/list` e `tools/call` via stdio. L'avvio manuale resta un
processo MCP senza output umano:

```bash
/private/tmp/quote-card-builder-mcp-venv/bin/python scripts/mcp_server.py
```

Per provare il trasporto che userà il futuro servizio remoto, senza alcun deploy:

```bash
/private/tmp/quote-card-builder-mcp-venv/bin/python scripts/mcp_server.py \
  --transport streamable-http --host 127.0.0.1 --port 8000
```

L'endpoint MCP locale sarà `http://127.0.0.1:8000/mcp`. Il test automatico usa una porta
effimera e chiude il processo al termine del round-trip.

## Container Cloud Run e prova locale

`Dockerfile` costruisce un solo servizio Python non-root: installa esclusivamente
`requirements-mcp.txt`, copia gli script canonici e avvia Streamable HTTP su `0.0.0.0`.
Legge la porta dalla variabile `PORT`, quindi è compatibile con la porta fornita da Cloud Run.
`.dockerignore` esclude esplicitamente `work/`, test, repository Git e altri artefatti locali.

Su una macchina con Docker disponibile, la prova resta interamente locale:

```bash
docker build -t quote-card-builder-mcp:local .
docker run --rm -p 9090:8080 -e PORT=8080 quote-card-builder-mcp:local
curl http://127.0.0.1:9090/health
```

La risposta attesa è `{"status":"ok","service":"quote-card-builder","mcp_path":"/mcp"}`;
il client MCP si collega a `http://127.0.0.1:9090/mcp`. Questi comandi non richiedono
credenziali Google e non creano un servizio Cloud Run.
La CI costruisce inoltre l'immagine senza autenticarsi a un registry, eseguire push o deploy.

## Stato del servizio remoto

Il servizio personale usa l'endpoint
`https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`. Revisione, digest,
risorsa effettivamente servita e smoke test sono evidenze di release soggette a cambiamento e
vengono registrate nel dossier `submission/evidence.md`, non congelate in questo documento di
architettura. Il deploy verificato della candidata v1.29 resta registrato nel dossier insieme a
revisione, digest, traffico e smoke test.

Il pacchetto espanso contiene `.mcp.json` con il wrapper `mcpServers` richiesto dal
validator locale e punta a
`skills/quote-card-builder/scripts/mcp_server.py`; il builder copia automaticamente
anche `mcp_quote_card.py`, `mcp_app.py` e `requirements-mcp.txt` nella skill inclusa.

## MCP App: preview visuale opzionale

Il vertical slice ora include una MCP App portabile per host compatibili con MCP Apps.
La risorsa UI ha URI stabile versionato
`ui://quote-card-builder/preview/v1.38.html`, MIME type
`text/html;profile=mcp-app` e viene collegata al tool tramite
`_meta.ui.resourceUri`; include anche l'alias ChatGPT
`_meta["openai/outputTemplate"]` per compatibilità con host legacy. Solo
`quote_card_builder_open_editor` possiede questi metadati e va chiamato una volta. La componente
è un iframe HTML autonomo, senza dipendenze frontend aggiuntive: incorpora versioni WOFF2
latine ridotte di Barlow e il WOFF2 variable di Orbitron usato dal wordmark dell'editor locale,
e riusa i token Plotter Bench del Visual Review Studio locale, mantenendo
separate la palette dell'interfaccia e quella della card. Riceve il risultato
iniziale, mostra lo `svg` prodotto dal renderer canonico e richiama `preview_quote_card`
dal pulsante **Update preview** con `output_image: false`. Il pulsante **Generate PNG** chiama
`produce_quote_card`, riesegue la stessa validazione e converte l'SVG canonico in PNG nel browser.
La UI negozia il protocollo MCP Apps `2026-01-26` e legge le capacità restituite da
`ui/initialize`. Quando l'host dichiara `downloadFile`, invia il PNG come risorsa binaria incorporata
tramite `ui/download-file`: è il percorso principale perché il salvataggio è mediato dal client e
non dipende da link o popup nell'iframe sandboxato. Se è disponibile soltanto la modalità immagine
di `ui/message`, l'azione diventa **Send PNG to chat** e trasferisce lo stesso PNG alla conversazione.
Le estensioni ChatGPT `uploadFile`, `getFileDownloadUrl`, `openExternal`, `sendFollowUpMessage` e
`setWidgetState.imageIds` restano fallback di compatibilità. La UI segnala inoltre l'altezza
dinamica sia tramite MCP Apps sia tramite `window.openai.notifyIntrinsicHeight`, e rende visibile
immediatamente lo stato della richiesta di apertura con un timeout esplicito. Sugli host che
non espongono queste API mantiene un Blob URL locale come fallback. Se la rasterizzazione fallisce, segnala
esplicitamente che il PNG non è disponibile senza offrire un SVG come falsa consegna finale. I due
tool dati non possiedono template UI, quindi gli aggiornamenti non possono
aprire altre iframe.

La UI usa il bridge MCP Apps (`ui/initialize`, notifiche di input/output e
`tools/call`) e legge anche gli alias ChatGPT `window.openai.toolInput` e
`window.openai.toolOutput` come fallback compatibile per il risultato iniziale. Il flusso
resta utile anche quando l'host non supporta una UI. Non
salva dati, non pubblica contenuti e non duplica il rendering Python. Il flusso è
deliberatamente una singola card inline; un editor multi-card o strumenti separati
di dati e presentazione saranno decisioni successive.

`preview_quote_card` può includere un blocco `image` con MIME type `image/svg+xml` quando
viene chiamato da un client MCP generico. `quote_card_builder_open_editor` non include quel
blocco, evitando una seconda anteprima accanto alla UI; lo stesso SVG resta disponibile
nello structured output come fallback, senza un secondo renderer. `produce_quote_card`
è visibile soltanto alla app e non restituisce un blocco immagine, così la produzione resta
nella singola iframe.
La skill canonica decide quando chiamare `quote_card_builder_open_editor`, raccoglie le domande
preliminari e impedisce che la sola apertura venga trattata come approvazione. La produzione
dell'SVG canonico e la conversione PNG avvengono soltanto con **Genera**; questo flusso
produce una singola card 4:5 e non sostituisce l'export PNG multi-formato del Visual Review
Studio locale. Collegare direttamente l'endpoint Cloud Run verifica il solo server MCP, non il
comportamento completo del plugin.

## Decisione per il prossimo incremento

La prossima fase resta un **solo servizio Python**: il processo MCP e il renderer canonico
vivono nello stesso container e l'adattatore continua a chiamare `render_quote_card.py`.
Non viene creato un microservizio di rendering né una seconda logica grafica.

- **Trasporto:** il plugin continua a usare stdio. `mcp_server.py --transport streamable-http`
  espone `/mcp` e costituisce il percorso usato anche su Cloud Run. Il test automatico copre
  `initialize`, `tools/list` e `tools/call` su questo percorso HTTP.
- **Cloud Run:** il pilot personale usa un solo container,
  URL HTTPS stabile con suffisso `/mcp`, health check su `/health`, log e metriche. Non servono storage o
  servizi aggiuntivi per la preview attuale.
- **Autenticazione:** i tre tool restano `noauth` e senza dati per-utente; preview e produzione
  SVG non persistono stato sul server. La scelta è ammessa soltanto dopo averla resa coerente con
  privacy policy, log infrastrutturali, limiti di traffico e monitoraggio abusi. Non introdurre una
  chiave API proprietaria. Prima di esporre profili, output salvati o azioni di scrittura, adottare
  OAuth 2.1 secondo MCP con scope per tool e autorizzazione lato server.
- **Storage:** nessun database, bucket o retention nel vertical slice. L'SVG è restituito nella
  risposta e non viene conservato. La scelta storage si riapre solo insieme a profili/output
  persistenti e relative policy di proprietà, quota e cancellazione.
- **MCP App/Apps SDK:** il primo incremento è un editor inline con preview e produzione SVG,
  non una migrazione completa del Visual Review Studio. La componente resta self-contained e usa il bridge standard;
  l'eventuale adozione di `@openai/apps-sdk-ui` si valuterà solo quando servono più
  controlli, stati condivisi o componenti riusabili. Gli aggiornamenti incompatibili
  della UI devono usare un nuovo URI versionato per evitare cache stale nell'host.
- **Packaging/runtime:** `.mcp.json` usa `python3` e un path relativo al plugin espanso;
  prima della distribuzione va definito il bootstrap del runtime Python, senza affidarsi
  all'ambiente personale dell'utente.
