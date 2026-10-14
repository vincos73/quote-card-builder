# MCP — contratto attuale e storico del pilot locale

## Web MCP attuale — 1.8.11 / UI v1.58

Il server web e l’editor MCP attuali aggiungono Nastri ai quattro stili precedenti. Il modello progetta tre scene numeriche diverse; il client può anche offrire prove deterministiche etichettate demo. Citazione e autore hanno dimensioni indipendenti, mentre le parole selezionate possono usare styles di tipo size con scale 0.5–2.5. I formati sono 4:5, 1:1 e 9:16, uno per Download PNG. Il contratto completo di scene, formattazioni e riuso è in [ribbons-web-mcp.md](ribbons-web-mcp.md).

Gli avvisi visuali degli editor locale e MCP sono descrittivi e non bloccano preview o export; gli errori tecnici che impediscono il rendering restano bloccanti. Il Visual Review Studio locale esporta con quality_policy advisory. Il renderer CLI standalone mantiene invece strict come default: questa policy distinta non rende obbligatorie le correzioni negli editor.

Le basi web sul dispositivo conservano la card completa, contenuto e formattazioni inclusi; il progetto JSON la trasferisce esplicitamente. La base di stile locale esclude invece citazione e selezioni. Il web non sincronizza account/dispositivi e non permette upload di font o logo. Con una nuova frase, il riuso resetta intervalli e provenienza; l’autore è quello del campo facoltativo del dialogo, eventualmente precompilato e svuotabile. Un follow-up solo testuale conserva i campi non richiesti.

Le sezioni Storico riportano versioni e risultati precedenti: i loro riferimenti a risorse UI, traffico e controlli non descrivono lo stato corrente. Lo stato di distribuzione e le prove della 1.8.11 sono in RELEASE-STATUS.md.

Questa integrazione coordina l'ingresso globale nel workspace e quello guidato dalla conversazione,
con tool UI interni per preview e produzione e un fallback esplicito:
`quote_card_builder_open_editor` apre l'interfaccia una volta, `preview_quote_card` ne aggiorna
i dati senza rimontarla e `produce_quote_card` genera l'SVG canonico dopo il clic
esplicito dell’utente su **Download PNG** nell’editor MCP v1.58; l’interfaccia lo converte in PNG. Il precedente flusso locale stdio 1.8.3 aveva due azioni separate, Genera e Download PNG.
`quote_card_builder_headless` è visibile al modello soltanto come percorso di recupero: richiede
`ui_unavailable: true`, restituisce la preview come risorsa SVG esplicita e richiede approvazione
del chiamante più l'hash della preview corrente per la produzione.
Il server MCP gira via stdio nel pacchetto locale e via Streamable HTTP nel servizio remoto; usa
il renderer Python esistente come unica fonte di verità.
Il server non rasterizza direttamente PNG e non archivia sessioni o basi della card; non modifica l’installazione personale. Il tool di export HTTP può pubblicare temporaneamente il PNG rasterizzato dal client e restituire il suo link di download. Solo il launcher stdio locale abilita `--local-file-delivery`: il tool privato `quote_card_builder_save_png`, richiamato da Download PNG, salva il PNG esatto in `~/Downloads/Quote Card Builder`. Il servizio HTTP rifiuta questa opzione e il suo salvataggio locale resta disabilitato.

## Storico — MCP remoto 1.8.8 / UI v1.56

Il servizio live apre un solo editor popolato per richieste chiare di procedere da un link: il modello usa la navigazione dell'host per leggere la fonte, sceglie una citazione esatta e chiama `quote_card_builder_open_editor`. Il server MCP non acquisisce URL. Attribuzione assente significa nessuna attribuzione, salvo nome fornito dall'utente o verificato nella fonte; la palette neutra è il default. La risorsa UI corrente è `ui://quote-card-builder/workspace/v1.56.html`.

Le modifiche successive esplicite dalla chat usano `quote_card_builder_update_editor` sulla stessa risorsa UI. L'input include `base_revision`, lo snapshot completo `base_snapshot` restituito nel contesto modello e una patch sparsa. Il server fonde la patch, invalida a capo e intervalli manuali se cambia il testo, renderizza la bozza completa e restituisce lo stato aggiornato. Il widget applica l'input solo quando revisione e snapshot corrispondono alla bozza corrente; una nuova istanza può inizializzarsi dal rendering restituito. Non viene introdotta una sessione server o un endpoint di mutazione.

La revisione live `quote-card-builder-mcp-00118-ruq` riceve il 100% del traffico. La UI v1.56 è verificata da smoke di produzione, browser e due aggiornamenti consecutivi nella chat ChatGPT nativa. Per ogni follow-up occorre richiamare il plugin per rendere disponibile `quote_card_builder_update_editor`.

## Storico — MCP remoto 1.8.8/UI v1.55

La revisione precedente `quote-card-builder-mcp-00114-vam` è stata sostituita. Le prove native su quella UI hanno verificato apertura singola da URL e due aggiornamenti successivi dopo il richiamo del plugin.

## Storico — MCP remoto live 1.8.7 — workspace UI v1.54

La versione è live. Imposta “nessuna attribuzione” per impostazione predefinita in un
nuovo workspace, New Card, input senza attribuzione e draft legacy vuoti. Mantiene attribuzioni
nominative esplicite; la scelta nominativa esplicita senza testo resta incompleta e visibile. La
modifica del demo conserva “nessuna attribuzione” e la digitazione avvia l'anteprima. La palette
neutra resta il valore iniziale come in UI v1.53.

## Storico — MCP remoto live 1.8.6/UI v1.53

Il servizio live è 1.8.6/UI v1.53. Mostra un demo
editabile su quattro righe (“Le idee migliori / meritano / di essere / condivise.”), con prima riga in grassetto, “meritano” e “di essere” in corsivo e ultima parola evidenziata. Formattazione e spaziatura non
resettano le scelte demo; le scelte mancanti restano indicate dopo il rendering. La palette neutra è
preselezionata nei nuovi workspace, in New Card, negli input senza palette e nei draft ripristinati
con scelta ancora pendente. L'editing del testo conserva la selezione neutra o personalizzata esplicita. La chat ChatGPT già aperta può mostrare UI v1.52 in cache; per verificare i controlli v1.53 serve una nuova chat e una nuova chiamata al tool.

## Storico — MCP remoto live 1.8.5/UI v1.52

Il servizio remoto live conserva l'endpoint `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`, senza OAuth; gli export PNG sono temporanei e gli URL scadono entro 24 ore. Il tool di apertura con `{}` restituisce uno stato vuoto e non crea testo o attribuzioni. Se non viene recuperata una bozza, la UI presenta la frase demo “Le idee migliori meritano di essere condivise.”, senza autore, con le scelte nessuna attribuzione e palette neutra marcate come demo-only. Se il modello fornisce una frase mentre il demo è ancora intatto, questa lo sostituisce. Per produrre una card reale, frase, scelta dell'attribuzione e palette devono essere confermate nell'editor.

Nel workspace remoto, un solo clic su **Download PNG** produce e salva il PNG. Non c'è un passaggio separato **Genera** e non c'è l'azione **Send PNG to chat**. Questo flusso UI v1.52 è distinto dall'installazione locale 1.8.3, che mantiene il proprio percorso **Genera** seguito da **Download PNG** e salva in `~/Downloads/Quote Card Builder`.

## Storico — Workspace Extension locale 1.8.3

Il sorgente candidato aggiunge il tool globale e di thread `quote_card_builder_open_workspace`, con input
vuoto `{}` e risorsa UI `ui://quote-card-builder/workspace/v1.50.html`. Apre l'editor inattivo:
prima di preview o generazione, l'utente sceglie frase, attribuzione (o “nessuna”) e palette.
`quote_card_builder_open_editor` resta l'apertura guidata da conversazione per dati già scelti,
ora con modalità fullscreen nel client desktop.
La bozza si recupera localmente nel workspace. Non c'è sincronizzazione fra dispositivi o
conversazioni, associazione a file o menzioni, né applicazione automatica di modifiche del modello.
La risorsa workspace 1.50 è un riferimento della candidata locale e non prova che il server remoto
o un plugin installato la servano.

Il workspace della precedente installazione locale 1.8.3 manteneva 4:5 e 1:1. Il web 1.8.11 aggiunge 9:16 e basi sul dispositivo; i profili completi con font/logo e l’export Tutti/ZIP restano funzioni del Visual Review Studio locale. I riferimenti alle risorse v1.40
più avanti descrivono la versione documentata in quello storico tecnico e non sono aggiornati per
rappresentare una risorsa remota corrente.

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

Il pacchetto web in `web-plugin/` è la variante esclusivamente MCP e collega l’endpoint mantenuto tramite `mcp.json`. La skill condivisa resta utilizzabile anche con runtime locale senza MCP; non confondere il suo adattatore opzionale con i requisiti del pacchetto web.

## Input

### Storico — MCP remoto 1.8.10 / UI v1.57, composizione mobile iniziale

La revisione `quote-card-builder-mcp-00122-yoc` riceveva il 100% del traffico della 1.8.10. Risorsa di quella versione: `ui://quote-card-builder/workspace/v1.57.html`. La firma usa il rapporto 0,0325 della larghezza della card; il CSS della didascalia dell’interfaccia è separato dall’SVG per conservare la tipografia nell’anteprima e nel PNG. Controlli mirati PASS; prova visiva ChatGPT e download a cura dell’utente.

Le stesse regole editoriali valgono per l'editor MCP e per il Visual Review Studio locale. Con una citazione già scelta e una richiesta chiara di procedere, prepara un'apertura già impaginata in una sola chiamata `quote_card_builder_open_editor`; non chiedere prima conferma degli a capo o dei trattamenti. L'impaginazione non autorizza riscritture: mantieni parole, punteggiatura, negazioni e cautele della citazione. Mantieni `VERBATIM` e lo stato di prova già stabilito quando cambi soltanto righe o stili. Per i follow-up che chiedono soltanto una nuova disposizione, rispetta le righe già composte finché l'utente non chiede di cambiarle.

Per una citazione iniziale medio-lunga di circa 20–40 parole, usa in genere 6–9 righe brevi e semanticamente bilanciate, adattando il conteggio al testo. Punta a 12–20 caratteri per riga; considera 22 un limite morbido. Evita articoli, congiunzioni, preposizioni o verbi isolati a fine riga. Il testo dovrebbe occupare circa il 45–60% dell'altezza della card senza un vuoto centrale e restare circa 30–40px a 375px di larghezza (equivalenti a 115–155px sulla canvas 1440). Spezza semanticamente le righe troppo lunghe anziché ridurre l'intero testo. Non forzare una citazione breve in molte righe né accorciare automaticamente una citazione verificata. Per l'enfasi, applica 1–3 brevi intervalli scegliendo di norma non più di due tipi tra bold, italic e highlight; metti in rilievo la tesi centrale, non ogni parola o un'intera riga lunga. Rispetta sempre una richiesta esplicita di layout, stile o testo semplice.

Esempio di testo esatto su sette righe:

```text
L’IA aiuta
a chiarire i problemi
e a valutare
le opzioni;
il giudizio
e la responsabilità
restano alle persone.
```

Per questa proposta, applica il grassetto soltanto a “L’IA” e l'evidenziazione soltanto a “giudizio”. Passa le righe in `lines` e imposta `text` alla loro unione con newline (`\n`), senza aggiungere marcatori Markdown. Gli intervalli in `styles` restano metadati separati: gli offset contano i caratteri Unicode e i newline, non le unità UTF-16 di JavaScript. Una modifica di layout soltanto non cambia testo né classificazioni editoriali.

### Input attuale 1.8.11

L’input è un oggetto con schema esplicito. La tabella copre i campi comuni; per le scene Nastri e i controlli granulari usare [ribbons-web-mcp.md](ribbons-web-mcp.md):

| Campo | Tipo | Default | Note |
| --- | --- | --- | --- |
| `text` | stringa | obbligatorio | da 1 a 600 caratteri |
| `attribution` | stringa | vuota (`nessuna`) | facoltativa; usa un nome fornito dall'utente o verificato nella fonte, senza chiedere conferma; massimo 160 caratteri |
| `profile_mode` | enum | `neutral` | facoltativo; `custom` soltanto se l'utente fornisce o sceglie esplicitamente una palette; usato da `quote_card_builder_open_editor` |
| `transformation` | enum | `VERBATIM` | `VERBATIM`, `EDITED`, `PARAPHRASE`, `AI_GENERATED` |
| `evidence_status` | enum | `USER_SUPPLIED` | stato della prova editoriale dichiarato dal chiamante |
| `style` | enum | `blocks` | preselezione facoltativa: `blocks`, `cutouts`, `constellations`, `gradient`, `ribbons`; con Nastri passare anche le scene native |
| `format` | enum | `4x5` | `4x5`, `1x1` o `9x16`, uno per output web |
| `palette` | oggetto o nullo | nullo | scelta esplicita `{name, colors}`; `colors` contiene `primary`, `accent`, `background`, `text` in formato `#RRGGBB` |
| `lines` | lista di stringhe | una riga | almeno una riga; devono ricostruire `text`; nessun limite fisso oltre ai 600 caratteri di `text` |
| `styles` | lista | assente | intervalli `{start,end,type}` con offset Unicode; `size` aggiunge `scale` 0.5–2.5 e richiede Nastri |
| `alt_text` | stringa | automatico | sostituzione facoltativa, massimo 400 caratteri |

La palette neutra canonica (`#072743`, `#E3F4FF`, `#FEFDFB`, `#323232`) è il default; gli stili precedenti usano Arial e Nastri usa Barlow incorporato. Il profilo neutro è predefinito
nel tool di apertura (`profile_mode: neutral`); il tool dati conserva la palette omessa
come fallback tecnico interno alla UI. In alternativa
il chiamante può trasferire una palette esplicita con nome e quattro colori. Il server non
inferisce, salva o recupera automaticamente un'identità di brand.

## Routing attuale

Per una richiesta chiara di procedere da un link leggibile, il modello legge la fonte tramite la
navigazione dell'host, seleziona una citazione esatta e chiama una sola volta
`quote_card_builder_open_editor`. Non apre prima il workspace vuoto e non chiede conferma di frase,
attribuzione o palette. Usa l'attribuzione fornita o verificata; se manca, “nessuna”. La palette
neutra è predefinita. Il server non acquisisce URL. Le richieste ambigue o le fonti non leggibili
richiedono soltanto il chiarimento necessario. La palette non è tono o mood; lo stile resta una
scelta nell’editor fra Blocks, Cutouts, Constellations, Gradient e Nastri. Per Nastri il modello prepara tre scene native diverse con la stessa frase e palette, passando visual_grammar ribbons, composition_candidates, composition e proposal_source model; le variazioni deterministiche dell’editor sono demo dichiarate.

Per le successive modifiche esplicite in chat, il modello passa la revisione e lo snapshot completo
della bozza corrente a `quote_card_builder_update_editor`, insieme alla patch dei soli campi richiesti.
Il server fonde e renderizza la bozza risultante. Il widget applica l'aggiornamento solo se revisione
e snapshot corrispondono; altrimenti occorre rileggere il nuovo contesto prima di riprovare. Un host
può rimontare la UI: in quel caso il risultato renderizzato contiene lo stato completo da cui partire.

### Regressione di routing v1.22

La candidata storica v1.7.16 rende esplicito anche il contratto di selezione del tool. Il tool pubblico
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

Il risultato strutturato contiene `valid`, `rendered`, `format` (`4x5`, `1x1` o `9x16`), dimensioni
del rapporto selezionato, `profile`, `svg_sha256`, `alt_text`, `warnings`, `errors`, la
dichiarazione `editorial_responsibility: caller` e `editor_state`, lo snapshot esplicito di
frase, attribuzione, profilo, palette e controlli che ripopola il form anche quando il bridge
dell'host consegna soltanto il risultato. Le chiamate della nuova UI con `compact_output: true`
omettono SVG e data URI dal JSON e leggono `_meta.quoteCard.svg`; per Nastri la galleria SVG arriva in `_meta.quoteCard.composition_previews`, mentre lo stato conserva geometria, proposte e dimensioni manuali. Per compatibilità, l'apertura
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

## Storico — stato del servizio remoto e pacchetto stdio

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

## Storico — MCP App v1.50 della versione locale 1.8.3

Il vertical slice 1.8.3 includeva la MCP App portabile descritta in questa sezione. Le sue azioni Generate/Download/Send e i due formati sono storici; il web v1.58 usa Download PNG in un solo passaggio e include Nastri e 9:16.
La risorsa UI ha URI stabile versionato
`ui://quote-card-builder/preview/v1.50.html`, MIME type
`text/html;profile=mcp-app` e viene collegata al tool tramite
`_meta.ui.resourceUri`. Usa soltanto il contratto standard gestito dall'estensione MCP Apps e non mantiene un secondo
`_meta["openai/outputTemplate"]`, così ogni URI UI pubblicizzato passa dallo stesso registro.
`quote_card_builder_open_editor` è l'ingresso guidato visibile al modello e usa la risorsa preview;
`quote_card_builder_open_workspace` è visibile all'app e al modello, accetta `{}` e dichiara gli
entrypoint globale e di thread con la risorsa workspace. La componente
è un iframe HTML autonomo, senza dipendenze frontend aggiuntive. Usa Barlow incorporato e la skin originale Plotter Bench viola/lime, indipendente dai colori e dai font comunicati dall’host. Il cambio di tema non sostituisce la skin né la palette della card; le safe area e il layout fullscreen restano gestiti. I sorgenti per tema, stato e lettura dei
risultati sono in `assets/mcp-editor/` e vengono incorporati nella risorsa HTML.
Riceve il risultato
iniziale, mostra lo `svg` prodotto dal renderer canonico e richiama `preview_quote_card`
dal pulsante **Update preview** con `output_image: false`. Il pulsante **Generate PNG** chiama
`produce_quote_card`, riesegue la stessa validazione e converte l'SVG canonico in PNG nel browser.
La UI negozia il protocollo MCP Apps `2026-01-26` e legge le capacità restituite da
`ui/initialize`. Nel plugin locale, prima dei fallback del browser, salva il PNG tramite `quote_card_builder_save_png`, ne mostra il percorso verificato e può aprirlo con `openai/files/open`. Il pulsante chat invia il percorso assoluto tramite `ui/message`; la skill richiede l’immagine Markdown e il link a quel file. Nei client remoti, quando l’host dichiara `downloadFile`, invia il PNG come risorsa binaria incorporata
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

## Storico — decisione per l’incremento del servizio remoto

La prossima fase resta un **solo servizio Python**: il processo MCP e il renderer canonico
vivono nello stesso container e l'adattatore continua a chiamare `render_quote_card.py`.
Non viene creato un microservizio di rendering né una seconda logica grafica.

- **Trasporto:** il plugin continua a usare stdio. `mcp_server.py --transport streamable-http`
  espone `/mcp` e costituisce il percorso usato anche su Cloud Run. Il test automatico copre
  `initialize`, `tools/list` e `tools/call` su questo percorso HTTP.
- **Cloud Run:** il pilot personale usa un solo container,
  URL HTTPS stabile con suffisso `/mcp`, health check su `/health`, log e metriche. Non servono storage o
  servizi aggiuntivi per la preview attuale.
- **Autenticazione:** i cinque tool restano `noauth` e senza stato per-utente sul server; preview e produzione
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


### Storico: affidabilità della UI v1.40

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
