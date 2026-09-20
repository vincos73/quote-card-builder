# MCP pilot locale

Questa integrazione aggiunge un flusso end-to-end con tre tool dell'editor e un fallback esplicito:
`quote_card_builder_open_editor` apre l'interfaccia una volta, `preview_quote_card` ne aggiorna
i dati senza rimontarla e `produce_quote_card` genera l'SVG canonico dopo il clic
esplicito dell'utente su **Genera**; l'interfaccia lo converte in PNG e preferisce **Download PNG**
oppure **Send PNG to chat**, in base alle capacità dichiarate dall'host.
`quote_card_builder_headless` è visibile al modello soltanto come percorso di recupero: richiede
`ui_unavailable: true`, restituisce la preview come risorsa SVG esplicita e richiede approvazione
del chiamante più l'hash della preview corrente per la produzione.
Il server MCP gira via stdio nel pacchetto locale e via Streamable HTTP nel servizio remoto; usa
il renderer Python esistente come unica fonte di verità.
Il server non rasterizza direttamente PNG, non salva sessioni, non pubblica contenuti e non
modifica l'installazione personale.

## Ordine di routing e dipendenze

Il server MCP è una capacità opzionale della skill condivisa. La configurazione locale in `.mcp.json`
fornisce il server quando il plugin viene eseguito in un ambiente che lo supporta; la skill non
richiede un endpoint remoto e resta utilizzabile come skill standalone.

Applicare questo ordine: le istruzioni esplicite dell'utente prevalgono sulle indicazioni della
skill, salvo i limiti effettivi imposti da tool disponibili, sicurezza e consenso. Se l'utente
chiede esplicitamente di saltare o non aprire l'editor, non aprirlo né sostituire quella scelta
con il percorso headless; se il percorso richiesto non è supportato, dichiarare il limite. Se l'utente
chiede esplicitamente il percorso locale, usare l'editor locale quando Python, browser e ricezione
degli eventi sono disponibili e non chiamare MCP. Altrimenti, se `quote_card_builder_open_editor` è
disponibile, usarlo una sola volta; se il percorso locale è stato richiesto ma non è disponibile,
dichiarare il limite senza passare a MCP; se il tool MCP non è disponibile ma Python, browser locale e
ricezione degli eventi sono disponibili, usare l'editor locale vincolato. Usare
`quote_card_builder_headless` solo dopo aver osservato e dichiarato che l'interfaccia non può essere
montata o che un editor necessario non è disponibile, quando il tool headless è disponibile e il
chiamante può rispettarne il consenso. La sola assenza del server MCP non è una ragione per
scegliere il percorso headless quando l'editor locale è operativo.

Una futura variante esclusivamente MCP potrà dichiarare `dependencies.tools` in `agents/openai.yaml`
soltanto insieme a un endpoint approvato e mantenuto. La skill condivisa non dichiara oggi quella
dipendenza perché il formato la tratta come requisito, mentre questo pilot supporta anche il
runtime locale senza MCP.

## Input

L'input è un oggetto con schema esplicito:

| Campo | Tipo | Default | Note |
| --- | --- | --- | --- |
| `text` | stringa | obbligatorio | da 1 a 600 caratteri |
| `attribution` | stringa | obbligatorio in apertura | etichetta visibile; stringa vuota solo dopo la scelta esplicita “nessuna”, massimo 160 caratteri |
| `profile_mode` | enum | obbligatorio in apertura | `neutral` o `custom`, scelto esplicitamente dall'utente; usato da `quote_card_builder_open_editor` |
| `transformation` | enum | `VERBATIM` | `VERBATIM`, `EDITED`, `PARAPHRASE`, `AI_GENERATED` |
| `evidence_status` | enum | `USER_SUPPLIED` | stato della prova editoriale dichiarato dal chiamante |
| `style` | enum | `blocks` | preselezione facoltativa: `blocks`, `cutouts`, `constellations`, `gradient`; la scelta resta nell'editor |
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
e personalizzata. La palette non è tono o mood. Lo stile non è una domanda preliminare: l'utente
lo sceglie nell'editor fra Blocks, Cutouts, Constellations e Gradient. Quando le tre risposte sono
presenti e il tool MCP è disponibile, il chiamante deve usare una sola volta
`quote_card_builder_open_editor`, senza sostituire l'app con generazione immagini, SVG, PNG, HTML o
altro file creato direttamente nella chat. Se il tool MCP non è disponibile ma il runtime locale è
operativo, usare l'editor locale vincolato. Se nessun editor può essere montato, dopo averlo
osservato e dichiarato, e il tool headless è disponibile con consenso verificabile, usare il percorso headless previsto sotto. Se l'utente ha
già indicato uno dei quattro stili, il chiamante può trasferirlo soltanto come preselezione. Se il
runtime locale espone profili salvati, la skill li elenca e attende una scelta esplicita; non
trasferisce font o logo nel pilot remoto. Il server pubblica la stessa sequenza nelle `instructions`
di inizializzazione, così il connettore remoto non deve inventare valori predefiniti.

### Regressione di routing v1.22

La candidata v1.7.19 rende esplicito anche il contratto di selezione del tool. Il tool pubblico
principale si chiama `quote_card_builder_open_editor`, segue la forma dominio + azione e accetta un input
ridotto a frase, attribuzione, modalità palette, formato iniziale ed eventuali colori
personalizzati. I tre campi obbligatori hanno titoli numerati identici al questionario; lo stile
è una preselezione facoltativa dell'editor.
Le istruzioni vietano espressamente di sostituire il percorso editoriale MCP già scelto con
generazione immagini, file autonomi o un editor locale; il fallback headless si attiva solo dopo
un'indisponibilità UI osservata.

Il set minimo di prova in Developer mode comprende:

- prompt diretto: selezionare Quote Card Builder e scrivere `test` deve produrre le tre
  domande con **Palette** come terza voce, senza chiedere lo stile;
- prompt completo: dopo le tre risposte deve essere chiamato una volta
  `quote_card_builder_open_editor` e deve aprirsi una sola iframe;
- regressione osservata: frase `noli me tangere lauria uber alles`, attribuzione `vincos`,
  profilo `neutral` deve arrivare all'editor senza blocchi immagine
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
del rapporto selezionato, `profile`, `svg_sha256`, `alt_text`, `warnings`, `errors`, la
dichiarazione `editorial_responsibility: caller` e `editor_state`, lo snapshot esplicito di
frase, attribuzione, profilo, palette e controlli che ripopola il form anche quando il bridge
dell'host consegna soltanto il risultato. Le chiamate della nuova UI con `compact_output: true`
omettono SVG e data URI dal JSON e leggono `_meta.quoteCard.svg`. Per compatibilità, l'apertura
iniziale e le chiamate senza questa opzione conservano `svg` e `svg_data_uri` nel risultato
strutturato. `produce_quote_card` aggiunge
`produced`, `filename` e `mime_type`. Il fallback headless aggiunge `action`, `ui_unavailable`,
`approval_required`, `approval_received` e `resource_uri`; il blocco `resource` in `content`
contiene l'SVG quando la preview è valida o la produzione è stata approvata. Un tentativo di
produzione senza approvazione non restituisce alcuna risorsa di produzione.

Gli errori di input e di contratto sono restituiti come oggetti `{path, code, message}`;
se la validazione fallisce, `svg` è `null` e il renderer non viene chiamato. La validità
è tecnica: `VERIFIED` o altre etichette editoriali restano dichiarazioni del chiamante,
non certificazioni del server.

## Prova locale

Dalla radice del repository:

```bash
uv run --frozen python -m unittest discover -s tests -v
```

Per verificare soltanto il protocollo, il test `McpProtocolTests` avvia il server reale,
esegue `initialize`, `tools/list` e `tools/call` via stdio. L'avvio manuale resta un
processo MCP senza output umano:

```bash
uv run --frozen python scripts/mcp_server.py
```

Per provare il trasporto che userà il futuro servizio remoto, senza alcun deploy:

```bash
uv run --frozen python scripts/mcp_server.py \
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
validator locale. Avvia `uv run --frozen python scripts/mcp_server.py` con `cwd` impostato a
`skills/quote-card-builder`, quindi usa il `pyproject.toml` e `uv.lock` inclusi. Il builder copia
automaticamente anche `mcp_quote_card.py`, `mcp_app.py`, `requirements-mcp.txt`, il progetto e il
lockfile nella skill inclusa.

## MCP App: preview visuale opzionale

Il vertical slice ora include una MCP App portabile per host compatibili con MCP Apps.
La risorsa UI ha URI stabile versionato
`ui://quote-card-builder/preview/v1.40.html`, MIME type
`text/html;profile=mcp-app` e viene collegata al tool tramite
`_meta.ui.resourceUri`. Usa soltanto il contratto standard gestito dall'estensione MCP Apps e non mantiene un secondo
`_meta["openai/outputTemplate"]`, così ogni URI UI pubblicizzato passa dallo stesso registro. Solo
`quote_card_builder_open_editor` possiede questi metadati e va chiamato una volta. La componente
è un iframe HTML autonomo, senza dipendenze frontend aggiuntive. Usa font di sistema e
colori forniti dall'host, con fallback chiaro/scuro. Il cambio di tema modifica soltanto
l'interfaccia, preservando la palette della card. I sorgenti per tema, stato e lettura dei
risultati sono in `assets/mcp-editor/` e vengono incorporati nella risorsa HTML.
Riceve il risultato
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
`window.openai.toolOutput` e `window.openai.toolResponseMetadata` come compatibilità per il risultato iniziale. Il flusso
resta utile senza UI tramite `quote_card_builder_headless`. Il server non conserva dati
né pubblica contenuti. La bozza viene invece salvata nello stato della singola interfaccia,
quando l'host espone `setWidgetState`, e ripristinata senza essere sovrascritta dal risultato
iniziale. `ui/update-model-context` comunica testo, attribuzione e scelte correnti al modello.
Questo stato non è un archivio durevole fra account, dispositivi o conversazioni. Il flusso è
deliberatamente una singola card inline; un editor multi-card o strumenti separati
di dati e presentazione saranno decisioni successive.

`preview_quote_card` può includere un blocco `image` con MIME type `image/svg+xml` quando
viene chiamato da un client MCP generico. Per compatibilità con UI già aperte, le risposte
di `quote_card_builder_open_editor` e quelle senza opzione compact di preview/production
conservano `structuredContent.svg` e `structuredContent.svg_data_uri`;
la nuova UI passa `compact_output: true` e usa l'SVG soltanto in `_meta.quoteCard.svg`.
Il tool headless lo restituisce come risorsa SVG esplicita, senza duplicarlo nello structured
output. `produce_quote_card` è visibile soltanto alla app e non restituisce un blocco immagine,
così la produzione resta nella singola iframe.
La skill canonica decide quando chiamare `quote_card_builder_open_editor`, raccoglie le domande
preliminari e impedisce che la sola apertura venga trattata come approvazione. La produzione
dell'SVG canonico e la conversione PNG avvengono soltanto con **Genera**; questo flusso
produce una singola card 4:5 o 1:1 e non sostituisce l'export PNG multi-formato del Visual Review
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
- **Autenticazione:** i quattro tool restano `noauth` e senza dati per-utente; preview e produzione
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
- **Packaging/runtime:** `.mcp.json` usa `uv run --frozen` dal `cwd` relativo alla skill inclusa.
  Il runtime è definito da `pyproject.toml` e `uv.lock`, senza affidarsi all'ambiente Python
  personale dell'utente.


### Affidabilità della UI v1.40

Le richieste al bridge scadono e liberano le richieste pendenti. Ogni modifica invalida
la produzione precedente; conversione PNG e preparazione del download controllano che
la revisione sia ancora corrente prima di mostrare la consegna. Le risposte iniziali
o superate non sovrascrivono una bozza modificata. La suite comprende regressioni per
risposte assenti, conversioni e caricamenti ritardati, recupero della bozza e tema host.

Nel fallback senza interfaccia, `input` contiene i parametri del renderer. Dopo
`action: preview`, l'utente può approvare la produzione: la chiamata successiva invia
`action: produce`, `ui_unavailable: true`, `approve_production: true` e
`approved_preview_sha256` uguale allo `svg_sha256` approvato. Un rifiuto o un hash non
corrispondente non restituiscono alcuna risorsa di produzione. L'approvazione resta
una dichiarazione del chiamante, non una certificazione dell'identità dell'utente.
