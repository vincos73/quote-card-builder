# Plugin personale 1.10.1 / UI v1.60 — compatibilità di installazione

15 ottobre 2026. **La piattaforma ha accettato e salvato l’aggiornamento del plugin privato esistente. L’installazione nei client ChatGPT/Codex dell’utente resta da verificare.**

- Il pacchetto locale ora include `plugin.json` e `mcp.json` Agent Plugins 1.0, oltre agli overlay legacy sincronizzati. Identità e presentazione sono conservate; i prompt iniziali passano da quattro a tre eliminando soltanto quello generico duplicato. Il launcher moderno usa percorsi `${PLUGIN_ROOT}`.
- Lo ZIP 1.10.0 rifiutato dall’utente conteneva solo il formato legacy e pesava circa 5.71 MiB. Non è stata identificata una causa univoca del messaggio generico dei client: anche il precedente 1.9.0 installato conteneva solo il formato legacy. La 1.10.1 corregge il formato e riduce il riferimento illustrativo a 432×540; il raster artistico usato nelle card resta identico. Il nuovo archivio pesa **4,144,344 byte**, SHA-256 `d27e03c55071244cf73ff6af90679ba42aa26a5c32880c2ac3557a565263b277`.
- **17 test mirati superati** per pacchetti, launcher e coerenza delle versioni. Avvio MCP stdio reale dal nuovo ZIP estratto: 9 tool disponibili, rendering Urban riuscito e byte dell’immagine originale preservati nella risposta di circa 8.8 MB. Per il test è stata copiata in modo isolato la venv già installata: il download di dipendenze in una venv vuota è stato bloccato dalla risoluzione DNS di `files.pythonhosted.org` in questo ambiente. Registro e report in `work/installation-fix/`.
- Aggiornato [Quote Card Builder](https://chatgpt.com/plugins/Plugin_a89e7ff110fc8191862bd712eeaaf65c), stesso ID `Plugin_a89e7ff110fc8191862bd712eeaaf65c`, scope USER e visibilità PRIVATE. Release restituita e riletta: `pluginrel_6ad07b33077081918fa9ef024d1b26af`. Tutti gli 82 percorsi del pacchetto sono presenti; manifest moderni e sorgenti selezionati corrispondono ai byte caricati. La piattaforma ha normalizzato gli overlay legacy con un launcher equivalente.
- Archivi 1.10.1 locale, web e server in `dist/`, con `SHA256SUMS-1.10.1.txt`. La UI resta v1.60. Il servizio Cloud Run non è stato distribuito e resta all’ultimo stato confermato 1.8.11/UI v1.58; il plugin web di test è distinto dal plugin privato appena aggiornato. Nessun tag o rilascio pubblico.

# Storico candidato 1.10.0 / UI v1.60 — Urban · Xerox

15 ottobre 2026. **Prima integrazione della prova Xerox/lime scelta dall’utente; pacchetti di prova locali, nessun deploy remoto.**

- Urban · Xerox usa lo stesso collage ImageGen della prova approvata, incorporato nello SVG insieme al font Barlow Condensed Black. Citazione e autore restano testo nativo; dimensioni manuali, formattazione, font e logo personali restano modificabili. Il trattamento iniziale dipinge il testo in maiuscolo senza alterare gli offset del contenuto originale.
- Lo sfondo mantiene i propri colori. I progetti e le basi salvano il riferimento versionato `urban-xerox-lime-v1`; il file è incluso nel runtime locale/server. Non duplicano il raster nel localStorage e non richiedono ImageGen per ogni nuova frase. I JSON con font/logo caricati continuano a trasferire quegli asset. Nastri e le tre composizioni Urban geometriche restano disponibili.
- Il riferimento visivo è ora incluso nelle skill locale e web. È la prova creata in questa chat, non uno degli esempi originali non disponibili. Il formato 4:5 conserva l’impostazione scelta; quadrato e storia adattano il testo e ritagliano lo stesso sfondo. Citazioni molto più lunghe richiedono una valutazione della composizione.
- Suite completa: **519 test superati senza skip**, `uv run --frozen --with cairosvg python -m unittest discover -s tests -q`; registro `work/tests-xerox-final.log`. I test coprono anche registrazione dell’asset, testo e intervalli Unicode, dimensioni manuali, font, import/export e approvazione locale del font.
- Chromium reale, host MCP simulato e tool reali: **8 verifiche superate**, `work/xerox-browser-verification/report.json`, con PNG effettivi 1440×1800, 1440×1440 e 1440×2560, riapertura progetto/base/bozza e viewport 375px. Non equivale a una verifica nativa nell’app installata dall’utente.
- Pacchetti candidati: `dist/quote-card-builder-plugin-1.10.0.zip`, `dist/quote-card-builder-web-1.10.0.zip`, `dist/quote-card-builder-web-server-1.10.0.zip`. Runtime e UI concordano su 1.10.0/v1.60. Endpoint, autenticazione e identità del plugin sono invariati.

Il servizio live rimane all’ultimo stato confermato 1.8.11/UI v1.58; questa sessione non dispone di un’identità Cloud Run configurata. Non sono stati creati tag o release pubbliche. L’utente può installare il pacchetto locale per provare l’integrazione.

# Storico candidato 1.9.0 / UI v1.59 — Urban e riuso portabile

14 ottobre 2026. **Sorgenti e pacchetti preparati e verificati; nuovo servizio non distribuito in questa sessione.** Ultimo stato live confermato: web 1.8.11/UI v1.58 e installazione standalone personale 1.8.3.

- Nastri e Urban condividono scene native, editor tipografico e formati 4:5/1:1/9:16. Urban usa pannelli, fasce e segni di stampa parametrici; i percorsi Nastri precedenti sono preservati.
- Le basi personali escludono il contenuto editoriale; i progetti conservano la card completa. Web e locale condividono i JSON trasferibili, inclusi font/logo. La migrazione delle vecchie basi web conserva le card originali come progetti recuperabili e non cancella l’archivio se la scrittura fallisce.
- Upload e validazione di font/logo nel web; trasferimento degli asset nei JSON e mantenimento delle varianti logo locali. Il contesto del modello riceve una descrizione compatta. Gli aggiornamenti con asset privati sono applicati e renderizzati dalla bozza completa dell’editor, senza font sostitutivi. La richiesta di nuove composizioni del modello è separata dalle varianti demo.
- Suite completa: **510 test superati senza skip**, `uv run --with cairosvg python -m unittest discover -s tests -q`; registro `work/tests-1.9.0.log`. CairoSVG è un backend opzionale usato per la prova del renderer legacy in questo ambiente, non una dipendenza aggiunta al servizio web. Controllo finale di schema/compatibilità e pacchetti: **17 test superati**, inclusa accessibilità del tool di validazione dall’app.
- Browser Chromium reale con host MCP simulato e tool server reali: **9 verifiche superate**, `work/grammars-verification/report.json`. Coperti upload di font e SVG, revisione dalla chat con asset preservati, base priva di contenuto, progetto completo, riuso con frase nuova/autore vuoto, richiesta al modello, import e PNG reale 1440×1800. Screenshot desktop/mobile e PNG in quella directory. La prova non equivale a un test nativo ChatGPT/Codex.
- UI v1.59 autosufficiente: **242214 byte**, entro 256 KiB. I font `*-ui.woff2` sono sottoinsiemi del chrome, separati dai font completi incorporati nelle card. Le risorse v1.58 restano disponibili come alias di compatibilità.
- Pacchetti allineati in `dist/`: `quote-card-builder-plugin-1.9.0.zip`, `quote-card-builder-web-1.9.0.zip`, `quote-card-builder-web-server-1.9.0.zip`, con `SHA256SUMS-1.9.0.txt`. Builder e runtime usano la medesima versione; il server contiene 35 file canonici più BUILD-INFO, senza sessioni o dati utente.

Il deployment Cloud Run e l’aggiornamento del plugin personale/standalone restano da eseguire nel loro ambiente: questa sessione non dispone di un’identità Cloud Run configurata. Endpoint, autenticazione, audience e ID del plugin esistente sono preservati. Non sono stati creati tag o release pubbliche. La sincronizzazione account è una successiva evoluzione di prodotto; il trasferimento corrente è esplicito tramite JSON.

# Storico — web MCP 1.8.11 / UI v1.58

14 ottobre 2026. **Servizio remoto aggiornato al 100% e plugin personale di test aggiornato**. Installazione locale Codex ancora 1.8.3, verificata in lettura e non modificata. Nessuna release GitHub, submission pubblica o installazione stdio eseguita.

- Servizio e autenticazione preservati: `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`, None. Revisione live `quote-card-builder-mcp-00124-dij`, tag `remote1811`, traffico 100%. La precedente `quote-card-builder-mcp-00122-yoc` resta disponibile per rollback.
- Nastri nel vero editor MCP: scene numeriche libere, tre proposte del modello o demo esplicitamente dichiarate, dimensioni separate per citazione/autore, size multiplier sulle selezioni, 4:5/1:1/9:16, basi sul dispositivo e JSON trasferibile. Avvisi visuali descrittivi senza pulsanti o call to action; non bloccano preview o export. Barlow incorporato per la grammatica Nastri, tipografia precedente invariata negli altri stili. Il web conserva palette e geometria; non aggiunge upload di font/logo o sincronizzazione cloud. Esporta un formato alla volta; Tutti/ZIP resta nel locale.
- Pacchetti web: `dist/quote-card-builder-web-1.8.11.zip` e `dist/quote-card-builder-web-server-1.8.11.zip`, con checksum `.sha256`. Il primo contiene la connessione streamable HTTP, skill e reference; il secondo è il sorgente container congelato. Nessun executor locale o dato della bozza utente. Ricostruzione dal checkout con `python3 scripts/build_web_server_package.py --output dist/quote-card-builder-web-server-1.8.11.zip` e, facoltativamente, `--directory dist/web-mcp-source-1.8.11` per un nuovo contesto Docker/deploy isolato; nessuna dipendenza da `work/` o snapshot precedenti. Il pacchetto riproduce i 30 file del sorgente live, digest `30171f04f64e9441cda5b65fb6d90fc2fa4bc36068ddcafa0958135ea7a1ed04`.
- Risorsa UI `ui://quote-card-builder/workspace/v1.58.html`; SHA256 canary/produzione identico `6fb5f478cdd2d51736ac81fa7841840e4a20af6945672583a8e73048d2313a2d`. Risorsa 255409 byte, entro il limite di 256 KiB. Gli SVG dei Nastri, con font e galleria, passano nei metadati UI; il contesto del modello conserva scene native senza duplicare i font.
- Suite completa: **475 test superati senza skip**, `work/remote-mcp/tests-full-1.8.11.log`. Prove comprendono protocollo stdio reale, scena/range/palette conservati, riuso, Unicode, JSON, avvisi non bloccanti, shape dei tool e import del container. Validatore della skill web superato con PyYAML in ambiente uv separato.
- Smoke SDK canary e produzione **PASS**: `canary-smoke-1.8.11.json`, `production-smoke-1.8.11.json` in `work/remote-mcp/`. Verificati tre scene progettate dal modello, tre formati, firme/hash, update revisionato, Barlow e contrasto/overflow non bloccanti; l’hash di approvazione errato resta respinto. Le scene QA sono sintetiche, non card dell’utente.
- PNG reali rasterizzati offline da SVG MCP e pubblicati dal canary: `work/remote-mcp/png-verification-1.8.11-canary/report.json`. Verificata anche la funzione canvas esatta estratta dall’editor v1.58, senza montare l’app: PNG validi in tutti i formati e download di produzione HTTP200 con byte identici (`production-canvas-png-1.8.11.json`). Rispetto al rendering SVG inline, 0/1/7 pixel RGB differenti sui tre formati, su circa 2–3.7 milioni di pixel ciascuno; non dichiarare parità assoluta nei casi con 1/7 pixel. `pixel-comparison.json` e `canvas-export-report.json` conservano i risultati.
- Plugin personale [Quote Card Builder TEST MCP](https://chatgpt.com/plugins/plugin_asdk_app_6acdf4f176e081918544ae00a8326edd), scope USER e audience PRIVATE preservati. Aggiornata la release da 1.0.0 a 1.0.1, ID `pluginrel_6acf08649b0881919f8d3bee6d8dc9a8`. App binding, nome, presentazione e prompt preservati; aggiunti skill web e reference. Read-back al momento dell’aggiornamento corrispondeva ai file caricati; evidenza `work/remote-mcp/account-readback-1.0.1.json`. Questo aggiornamento non crea un nuovo collegamento MCP né cambia l’autenticazione.

**Verifica per GitHub:** dopo l’aggiunta del builder server riproducibile, la suite completa ha superato **481 test senza skip** (`work/remote-mcp/tests-github-1.8.11-verified.log`); la ricostruzione del server mantiene il digest del sorgente live.

**Pubblicazione dei sorgenti:** codice Nastri locale/web, template e builder dei due pacchetti web, test e documentazione sono inclusi nell’aggiornamento GitHub. Il workflow delle future release costruisce anche i pacchetti web; questo aggiornamento dei sorgenti non crea un nuovo tag o una release pubblica. Le basi web conservano il contenuto della card sul dispositivo, come ora chiarito nelle istruzioni del pacchetto. La skill del plugin personale 1.0.1 resta quella caricata durante il deploy; nessun nuovo aggiornamento del plugin è stato eseguito per la sola pubblicazione GitHub.

**Prova dell’utente, 14 ottobre 2026:** l’utente ha confermato «ok funziona» dopo l’aggiornamento per ChatGPT. È una conferma del funzionamento osservato dal tester, non un test automatizzato del client nativo né una verifica separata di ogni funzione. Le prove JS restano basate su trasporto/funzioni simulate e l’export offline usa SVG sintetici, senza host UI o accesso all’editor localhost63657 precedentemente negato. La documentazione nel repository chiarisce anche che una base web conserva il contenuto della card sul dispositivo; il dialogo di riuso mostra il campo autore facoltativo e consente di cambiarlo o svuotarlo.

# Storico — MCP live 1.8.10, UI v1.57; installazione locale 1.8.3

## MCP remoto live 1.8.10 / UI v1.57

La revisione `quote-card-builder-mcp-00122-yoc` riceveva il 100% del traffico prima della 1.8.11. Endpoint, identità del plugin e autenticazione restano quelli esistenti.

- Istruzioni e skill ora privilegiano 6–9 righe brevi per citazioni medio-lunghe, enfasi selettiva e leggibilità su smartphone, preservando parole, punteggiatura, negazioni e cautele.
- Corretto il conflitto CSS: `.meta` dell’interfaccia imponeva 9 px all’attribuzione nell’SVG inline. La didascalia UI usa ora `.qcb-preview-caption`; la firma della card mantiene le sue proprietà nel renderer. Rapporto della firma ridotto da 0,0625 a 0,0325: 46,8 px su canvas1440, circa12,2 px a375. Nessuna sostituzione della famiglia font.
- Risorsa corrente `ui://quote-card-builder/workspace/v1.57.html`, SHA256 `98d2cf5ba58bacee2dc3990021dbbf873ceac6bb720f1b3318195fb3ed30bf43`. Sorgente congelata: `work/remote-mcp/container-source-1.8.10`, digest `61d7531d6d8bd00a538167ae2fccf45ec1a499e3d20662c263fc2df6cba6e629`.
- Due test mirati PASS (isolamento CSS della didascalia, rapporto firma), compilazione Python e controllo diff. Suite completa non ripetuta su richiesta dell’utente. I 357 test della 1.8.9 restano prove storiche.
- Canary e produzione: soli controlli di versione, risorsa UI e un rendering della frase d’esempio, PASS. Font remoto106,4 px su sette righe, firma46,8 px, parole preservate. Registri `work/remote-mcp/canary-smoke-1.8.10.json`, `work/remote-mcp/production-smoke-1.8.10.json` e `work/remote-mcp/production-service-1.8.10.json`.
- Nessuna nuova chat ChatGPT nativa o prova visiva del PNG eseguita. Il confronto browser locale non ha prodotto evidenze: l’apertura del file di prova è stata respinta dalla policy browser. La correzione del CSS è verificata nel codice e dalle prove mirate; la verifica visiva finale resta all’utente.
- Implementazione delegata a due agenti GPT-6 Luna; integrazione e pubblicazione svolte dall’agente principale. Pacchetto1.8.10 ricostruito dalle sorgenti canoniche; installazione locale1.8.3 non aggiornata.

## Storico — MCP remoto 1.8.9 / UI v1.56

La revisione `quote-card-builder-mcp-00120-gur` è stata promossa al 100% del traffico di produzione. La UI resta v1.56; il cambiamento 1.8.9 riguarda la composizione iniziale trasmessa dal modello, non un aggiornamento dell'interfaccia.

- Sorgente container congelato in `work/remote-mcp/container-source-1.8.9`; digest contenuto `348cfb0392ae423a042f45607fe906b4609d6dae7ec9de25fef15f3506e74ef8`. Risorsa `ui://quote-card-builder/workspace/v1.56.html`; hash UI `4ffb429c88ab62653f1eeaed48a44a508afc686871f140c7c23f31c00418b732`.
- Canary e smoke di produzione **PASS**: `work/remote-mcp/canary-smoke-1.8.9.json` e `work/remote-mcp/production-smoke-1.8.9.json`.
- Suite completa: **357 test superati, senza skip**, `work/remote-mcp/tests-full-1.8.9.log`. I cinque test mirati di composizione iniziale passano in `tests/test_mcp_initial_composition.py`; verificano righe, stili, fedeltà di parole e punteggiatura, newline e offset Unicode.
- L'apertura MCP di una citazione già scelta passa le righe e gli stili esplicitamente e conserva testo `VERBATIM` e stato della prova se cambia soltanto il layout. La comparazione eseguita misura 28,4 px per il testo su una riga contro 104,6 px su cinque righe, con formulazione preservata: `work/remote-mcp/composition-font-comparison-1.8.9.json`.
- **Non è stato eseguito un nuovo harness browser completo per 1.8.9**; i 33 controlli browser riportati per 1.8.8 appartengono alla release precedente.
- Prova nativa di apertura iniziale **PASS** in una [nuova chat ChatGPT](https://chatgpt.com/c/6ace34af-4f78-83ed-b5ab-50f8c69a923b), con il prompt generico «Crea una quote card da https://vincos.it/augmented-marketing-suite/ e procedi.» senza suggerimenti su righe o stili. Il modello ha aperto una volta sola l'editor popolato, senza domande e senza workspace vuoto. La citazione esatta è stata resa su quattro righe: “L’IA aiuta a chiarire i problemi” / “e a valutare le opzioni;” / “il giudizio e la responsabilità” / “restano alle persone.” La terza riga era in grassetto, la quarta evidenziata; attribuzione “Vincenzo Cosenza”, palette neutra e formato 4:5. Il font misurato nell'SVG era 72,2 px. Evidenze: `work/remote-mcp/browser-1.8.9/chatgpt-native-results.json` e `work/remote-mcp/browser-1.8.9/chatgpt-initial-composition.png`.
- L'aggiornamento degli strumenti nel plugin ChatGPT esistente è riuscito senza cambiare identità, autenticazione o permessi. L'installazione locale resta 1.8.3; la prova di promozione non attesta un nuovo pacchetto di distribuzione.
- Il pacchetto di distribuzione della skill/plugin non fa parte di questa prova di promozione.

## Storico — MCP remoto live 1.8.8 — UI v1.56

**Promossa al 100% del traffico di produzione** sull'endpoint `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`, senza autenticazione aggiuntiva. L'installazione locale resta 1.8.3.

- Revisione live: `quote-card-builder-mcp-00118-ruq`, 100% del traffico; tag `remote188`. Stato servizio e traffico: `work/remote-mcp/production-service-1.8.8.json` (**PASS**).
- Sorgente container congelato in `work/remote-mcp/container-source-1.8.8-r6`, 26 file; digest contenuto `32193cdfa113e7f6aa19d7837f8c787638aeffb091529d01810ff9d43c88e36a`. UI: `ui://quote-card-builder/workspace/v1.56.html`; hash `4ffb429c88ab62653f1eeaed48a44a508afc686871f140c7c23f31c00418b732`.
- Smoke di produzione **PASS** in `work/remote-mcp/production-smoke-1.8.8.json`: endpoint live, tool discovery e protocolli verificati; PNG di 11.373 byte, GET/HEAD/attachment HTTP 200, accesso anonimo al bucket HTTP 403 e byte esatti.
- Suite completa: **352 test superati, senza skip**, `work/remote-mcp/tests-full-1.8.8-final.log`. Il browser Chrome con host MCP Apps simulato e backend del tag R6 poi promosso ha superato **33 controlli**, `work/remote-mcp/browser-1.8.8/remote-browser-results.json`; il PNG scaricato corrisponde al pubblicato, SHA-256 `86de082897e578b7625b74ef68f40b18d8363018496a43711a70674be286c7f2`.
- Il browser con host simulato ha verificato idratazione iniziale con quote precompilata, aggiornamenti espliciti con snapshot/revisione, sincronizzazione dei ritorni a capo nel draft, conservazione della provenienza e delle scelte di stile. L'host simulato non sostituisce il client ChatGPT nativo.
- Prova nativa finale v1.56: nella stessa chat, dopo aver aggiornato gli strumenti del plugin esistente senza cambiare identità o autenticazione, due follow-up consecutivi richiamando `@Quote Card Builder TEST MCP` sono passati (revisioni 5 e 6). Il primo ha applicato quattro righe esatte con bold su “L’IA” e highlight su “giudizio e la responsabilità”; autore, formato 1:1, palette (`#072743`, `#E3F4FF`, `#FEFDFB`, `#323232`) e seed 1 sono rimasti invariati. Il secondo ha spostato il testo in alto mantenendo righe, stili, autore, palette e seed. Il DOM conferma l'output visibile; la provenienza EDITED/UNVERIFIED è stata verificata separatamente nel harness, perché non è esposta nel DOM. Ogni follow-up deve richiamare il plugin: senza la menzione il client ha segnalato “tool non disponibile”. Evidenza DOM: `work/remote-mcp/browser-1.8.8/chatgpt-native-results.json`; screenshot: `work/remote-mcp/browser-1.8.8/chatgpt-followup.png`. [Chat di prova](https://chatgpt.com/c/6ace16be-6d8c-83eb-8ffd-b161935d39e9).
- L'apertura iniziale singola da URL era stata verificata su R3/UI v1.55. La prova R6/UI v1.56 ha verificato i due aggiornamenti consecutivi nell'editor esistente; non è stata ripetuta l'apertura iniziale v1.56 in una nuova chat.

La revisione 1.8.8/UI v1.55 è stata sostituita dalla UI v1.56 ed è mantenuta come storico. La revisione precedente 1.8.7 resta descritta più sotto.

## Storico — MCP remoto live 1.8.8 — UI v1.55

La revisione `quote-card-builder-mcp-00114-vam` ricevette il 100% del traffico prima della promozione R6. I test R3 registrarono 349 test senza skip e 32 controlli browser; la verifica nativa iniziale e due follow-up riuscirono dopo il richiamo esplicito del plugin. La UI v1.56 è ora live.

## Storico — MCP remoto live 1.8.7 — UI v1.54

**Live e verificato** sull'endpoint `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`, senza OAuth. La revisione `quote-card-builder-mcp-00110-xel` riceve il 100% del traffico con tag `remote187`. L'installazione personale locale resta 1.8.3; gli URL PNG sono temporanei e scadono entro 24 ore.

Il server continua ad aprire `{}` e a restituire uno stato vuoto. Se non c'è una bozza recuperata, la UI conserva il demo su quattro righe e la palette neutra di v1.53; ora sceglie **nessuna attribuzione** quando manca un'attribuzione, senza richiedere una domanda all'utente. Mantiene attribuzioni nominative esplicite; una scelta intenzionale “con autore” senza testo resta incompleta e visibile. Modificare il demo conserva “nessuna attribuzione” e digitare avvia l'anteprima. **Download PNG** resta un'unica azione; **Send PNG to chat** e **Generate PNG** non sono presenti.

- Revisione: `quote-card-builder-mcp-00110-xel`, traffico 100%; tag `remote187`; build `1aa443c8-b6f4-4546-9c73-a6db153d5418`.
- Immagine: `sha256:ba04cf0bc99770420ed2cab9e8f1bcf10a9ba63df9612b772f6877b7d1f8b879`.
- Sorgente congelato in `work/remote-mcp/container-source-1.8.7`, 26 file; digest aggregato `168019eacd5173a1c623a3da8797193314fbc89e0bf04016fcd96a635e57d7b4`; hash UI v1.54 `aa6334d6e5cf9a658aedcacf92ba9f7ba695438e7ac7abd26a87d17a16deeab0`.
- Smoke SDK canary e smoke SDK di produzione superati: `work/remote-mcp/canary-smoke-1.8.7.json` e `work/remote-mcp/production-smoke-1.8.7.json`. HTML UI identico in entrambi, nessuna credenziale, PNG esatto, GET/HEAD/attachment HTTP 200 e bucket anonimo HTTP 403.
- Suite completa: **346 test senza skip**, `work/remote-mcp/tests-full-1.8.7-final.log`; focus: 33 test, browser locale: 18 verifiche, browser remoto: 26 controlli superati.
- Browser remoto: Chrome reale con host MCP Apps simulato e backend remoto live, `work/remote-mcp/browser-1.8.7/remote-browser-results.json`. Verificati default nessuna attribuzione/palette neutra nei nuovi workspace, New Card, input senza attribuzione e draft legacy vuoti; attribuzioni nominative e scelta nominativa vuota intenzionale; anteprima automatica, editing, retry/cache, restore, responsive, focus e download. Il PNG scaricato (168446 byte) ha hash `6dce3bb9e7754e1c41eb594b3a7c60d78e6892dd1e52b6c5a87a23555fc05a19`, identico ai byte pubblicati e recuperati via HTTPS. L'host simulato non ha inviato messaggi chat.
- Limite client ChatGPT: una nuova chat mostra il badge UI v1.54; questa sessione non ha completato un test manuale dei pulsanti nel client reale. La chat precedente può continuare a mostrare v1.52 in cache. La prova browser usa un host simulato. Nessuna submission/pubblicazione nella directory è attestata.

## Storico — MCP remoto live 1.8.6/UI v1.53

**Live e verificato** sull'endpoint `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`, senza OAuth. La revisione `quote-card-builder-mcp-00108-woz` ricevette il 100% del traffico con tag `remote186`; il traffico corrente è ora sulla revisione 1.8.7. Il plugin installato localmente resta 1.8.3. Gli URL PNG sono temporanei e scadono entro 24 ore.

Il server continua ad aprire `{}` e a restituire uno stato vuoto. Se non c'è una bozza recuperata, la UI mostra il demo modificabile “Le idee migliori / meritano / di essere / condivise.”: grassetto sulla prima riga, corsivo su “meritano” e “di essere”, highlight su “condivise”. Le modifiche di formattazione e spaziatura conservano le scelte demo; la palette neutra è il valore iniziale quando manca una scelta esplicita. Le scelte mancanti restano visibili dopo il rendering. **Download PNG** genera e salva con un solo clic; **Send PNG to chat** e l'azione **Generate PNG** non sono presenti.

- Revisione: `quote-card-builder-mcp-00108-woz`, traffico 100%; tag `remote186`; build `b2e438ab-4273-41eb-9135-c9fb3ad659ef`.
- Immagine: `sha256:a753807ef242ae995db81907897a2e983557bbfc5a0aec658e916d652f4241e6`.
- Sorgente congelato in `work/remote-mcp/container-source-1.8.6`, 26 file; digest aggregato `a52f82e73ed3081acbbdc78b72374cb584db4d440ecf6468c276ce9760d53f28`.
- Smoke SDK canary e smoke di produzione superati: `work/remote-mcp/canary-smoke-1.8.6.json` e `work/remote-mcp/production-smoke-1.8.6.json`. Verificati versione/UI, protocolli moderno e legacy, assenza di credenziali, byte PNG esatti, GET/HEAD con attachment HTTP 200 e bucket anonimo HTTP 403.
- Suite completa: **345 test senza skip**, `work/remote-mcp/tests-full-1.8.6.log`; suite mirata di 33 test superata (con sovrapposizione alla suite completa) e 16 verifiche browser locali superate.
- Browser remoto: Chrome reale con host MCP Apps simulato e backend remoto live; **23 controlli superati**. Il demo e gli stili, persistenza di scelte/focus, stato delle scelte mancanti, retry/cache, restore, responsive e download PNG sono verificati in `work/remote-mcp/browser-1.8.6/remote-browser-results.json`. PNG scaricato di 168516 byte; SHA-256 `6f7ce8337b441d79f86e4b49b84a32c0e124da260b704895a2f3dc4dbe8f012c`, identico al risultato di pubblicazione e ai byte HTTP. Nessun messaggio chat è stato inviato dall'host simulato.
- Limite client reale: la chat Chrome aperta mostra ancora la UI v1.52 in cache, anche dopo reload. Lo stato osservato non verifica la UI v1.53 né il comportamento interattivo dei suoi pulsanti; occorre una nuova chat e una nuova chiamata al tool. Questo limite del client resta separato dalla promozione e dalle verifiche del servizio remoto. La submission/pubblicazione nella directory non è attestata.

## Storico — MCP remoto live 1.8.5/UI v1.52

**La revisione 1.8.5 fu promossa al 100% del traffico** sull'endpoint `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`, senza OAuth; il traffico corrente è stato poi trasferito alla revisione 1.8.6. La revisione `quote-card-builder-mcp-00106-hip` ebbe il tag `remote185`. Il plugin installato localmente resta 1.8.3; non è stato aggiornato. Gli URL PNG sono temporanei e scadono entro 24 ore.

Il server apre uno stato vuoto; se non viene ripristinata una bozza, la UI mostra un demo modificabile
e chiaramente marcato, senza autore inventato. **Download PNG** genera e salva con un solo clic;
**Send PNG to chat** non è presente nella UI. Le prove automatizzate e browser sotto attestano la
versione live e i comportamenti verificati.

- Revisione: `quote-card-builder-mcp-00106-hip`, traffico 100%; build `89ec4802-e3e1-4b0c-9cc5-9582d30f43d7`.
- Immagine: `sha256:347d84ab95995fc05c620c6905755084fba8324ca8c9ec11ec7a12486d4e8a74`.
- Sorgente congelato in `work/remote-mcp/container-source-1.8.5-r2`, 26 file; digest aggregato `5b04ae5c5329fc349eac8294e29fd67acc7d9307d48ca11ce855e9e18c5294b0`.
- Smoke SDK canary e smoke di produzione superati: `work/remote-mcp/canary-smoke-1.8.5-r2.json` e `work/remote-mcp/production-smoke-1.8.5.json`. Verificati 1.8.5/UI v1.52, protocolli MCP moderno e legacy, assenza di credenziali, byte PNG esatti, GET/HEAD con attachment HTTP 200 e bucket anonimo HTTP 403.
- Suite completa: 343 test senza skip; regressione UI: 18 test; suite focalizzata: 77 test. Log R2: `work/remote-mcp/tests-full-1.8.5-r2.log` e `work/remote-mcp/tests-ui-regression-1.8.5-r2.log`.
- Browser: 16 verifiche locali e 19 remote superate. Chrome reale, host MCP Apps simulato e backend remoto reale hanno verificato flusso vuoto, demo, fallimento/riprova/cache, modifica, byte esportati, ripristino, mobile e focus: `work/remote-mcp/browser-1.8.5/remote-browser-results.json`.
- La chiamata nativa al plugin Quote Card Builder TEST MCP ha aperto il workspace senza errore, ma non verifica i pulsanti interattivi in una chat ChatGPT reale. La prova manuale dei pulsanti nel client ChatGPT reale resta da effettuare; la submission/pubblicazione nella directory non è attestata.

## Storico — MCP remoto 1.8.4 e installazione locale 1.8.3

## MCP remoto senza login aggiuntivo (13 ottobre 2026)

**La 1.8.4 è pubblicata su Cloud Run**, con UI v1.51, senza OAuth o altre credenziali per il caller MCP. Endpoint per i tester: `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`. Il plugin locale 1.8.3 resta installato e non è stato modificato; l'utente ne ha confermato il funzionamento.

- Revisione: `quote-card-builder-mcp-00103-mac`, traffico 100%; build `6530485e-d41e-445a-849b-80e2f0b3df9c`.
- Immagine: `europe-west8-docker.pkg.dev/quote-card-builder-mcp/cloud-run-source-deploy/quote-card-builder-mcp@sha256:fbce3bf7bfab436704ccdb45a9b78d72619eaa45238265bc050ce98b2593f2b5`.
- Sorgente del container selezionato e congelato in `work/remote-mcp/container-source`; manifest di 26 file, SHA-256 contenuto `88aea685224720d846b05c6de6bea827008b28e1c9388bc7ac348fc5abcc6635`. Il repository principale contiene modifiche non committate: questo digest documenta il contesto effettivamente costruito, non un commit Git del progetto.
- HTTP stateless e JSON, protocollo 2026-07-28 verificato; negoziazione legacy 2025-11-25 verificata. Ingressi global/thread e UI self-contained conservati.
- PNG esatto del browser salvato soltanto su Download/Invia, mediante `quote_card_builder_publish_png`, in bucket privato `quote-card-builder-exports-960066178304`. URL casuali di 192 bit, scadenza massima di 24 ore controllata dal server, nessun archivio personale. Lifecycle di cancellazione asincrono; accesso pubblico diretto al bucket impedito e verificato con HTTP 403.
- Download usa `ui/download-file` dove disponibile, poi `ui/open-link`; fallback con link HTTPS visibile quando il client non può aprirlo. Chat invia un messaggio con immagine Markdown e link riferiti agli stessi byte. Il tool locale di salvataggio resta disabilitato nel servizio HTTP.
- Limiti: PNG 8 MiB, HTTP 12 MiB, caricamenti 60/ora per processo con burst 5 e concorrenza 2; Cloud Run massimo 2 istanze. Il 429 precedente era associato dai log a mancanza di istanze disponibili. Gli smoke finali restituiscono HTTP 200.

### Prove della 1.8.4

- **346 test Python superati, senza skip**, con dipendenze MCP/Extensions/GCS complete: `work/remote-mcp/tests-full-1.8.4.log`.
- Smoke della candidata a traffico zero e dell'URL principale senza cookie/token: versione, discovery, strumenti, apertura vuota, UI, preview/produzione, PNG GET/HEAD/attachment e hash identico: `canary-smoke.json`, `production-smoke.json`.
- Browser Chrome reale con host MCP Apps simulato e iframe che vieta i download: preview ed export reali dal backend remoto, download HTTP attraverso `ui/open-link`, confronto degli hash e una sola pubblicazione riutilizzata da Download/Invia/secondo Download. Prove in `work/remote-mcp/browser/`; PNG finale di 93352 byte, SHA-256 `f9240bbe39c93059d9b075d828cefa75859511f679f638391b336894ec041545`.
- La consegna del messaggio è stata controllata nell'host simulato; **non è ancora una prova in una nuova chat ChatGPT di un tester**. Una chiamata di apertura editor dal plugin remoto collegato ha risposto senza errore, ma non attesta il flusso dei due pulsanti nel client finale.
- `git diff --check` superato. I modelli delegati sono **GPT 5.6 Sol** per server/storage e **GPT 6 Luna** per UI, guide e proxy.

### Pilot Sites preservato

Il Site `appgprj_6abf45cabe3c81918ed306c7f567cd9e` è stato aggiornato alla versione5, mantenendo accesso `custom` solo proprietario e lo stesso plugin `plugin_asdk_app_sites_6a6a4d45dfb48191b73b4bcd47e8a8a7`. Commit sorgente `f07a51fe8e11bbf30fbe59f705c622088ae270a1`; deployment `appgdep_6acdf1cab7908191bc8c22638b154923`, `succeeded`, `has_mcp:true`.

Il proxy passa le richieste stateless e il body MCP senza bootstrap di sessioni, conserva il protocollo e l'alias `/api/mcp`, e continua a filtrare cookie, credenziali e identità del Site. Sei test del Worker superati. La lettura diretta esterna del Site resta limitata dal blocco Cloudflare/Browser osservato. La chiamata nativa finale dal collegamento del pilot restituisce `McpServerError: MCP server/discover was rejected by chatgpt.site`: il deployment riuscito non prova quindi il funzionamento di quel collegamento gestito. Questo limite non è stato aggirato né risolto cambiando l'accesso del Site. Il percorso pubblico Cloud Run è quello verificato per la prima versione senza login aggiuntivo.

Il pilot Sites richiede ancora l'autenticazione della piattaforma: **ai tester della prima versione va passato l'endpoint Cloud Run, con autenticazione None**. Non è stata eseguita una submission o pubblicazione nella directory. I tester devono disporre delle opzioni e dei permessi per collegare MCP personalizzati; il supporto di tutti i piani/client non è attestato.

Guida: `REMOTE-MCP-TESTING.md`. Il piano in `SITES-REMOTE-PLAN.md` distingue questa prima versione dall'eventuale evoluzione con utenti riconosciuti e archivio personale.

## Correzione del terzo test (13 ottobre 2026)

La **1.8.3 è installata e abilitata localmente** come `quote-card-builder@personal`, display name **Quote Card Builder**. Il terzo test ha confermato l’apertura corretta ma ha mostrato che il download Blob dell’iframe non produceva un file per l’utente, mentre `ui/message` con ImageContent consegnava l’immagine al modello senza un link nella risposta. Il tema introdotto nella 1.8.2 aveva inoltre sostituito la skin originale.

- **Download PNG:** nel plugin stdio locale chiama il nuovo tool privato `quote_card_builder_save_png` e salva il PNG esatto rasterizzato dal browser in `~/Downloads/Quote Card Builder`. Non rigenera la card. Mostra il percorso confermato dal server; se il client dichiara `openai/files`, richiede l’apertura tramite `openai/files/open`.
- **Send PNG to chat:** salva o riutilizza lo stesso file, poi invia un messaggio testuale con il percorso assoluto. Server e skill richiedono una vera immagine Markdown e un link al file nella risposta, evitando la sola frase “mostrata sopra”.
- **Skin:** ripristinati Plotter Bench viola/lime, Barlow incorporato e controlli originali. Il tema host non sostituisce colori/font. Layout fullscreen, safe area e comportamento responsive rimangono disponibili.
- Il salvataggio è consentito soltanto al launcher stdio con `--local-file-delivery`; l’HTTP rifiuta questa opzione. Il tool non accetta un percorso: salva nella cartella fissa, valida dimensioni/encoding/checksum PNG, limita a 8 MiB e usa creazione atomica senza sovrascrivere file diversi. La generazione e le preview rimangono in memoria; il salvataggio avviene su azione esplicita.

## Verifica

- **321 test Python superati, senza skip**, con ambiente completo MCP/Extensions. Log: `work/extensions-verification/python-tests-1.8.3.log`.
- **19 verifiche browser superate**, Chrome e renderer reali con host MCP Apps simulato. L’iframe locale vieta i download: la prova conferma il file salvato, byte identici al PNG del browser, messaggio con percorso esistente, riutilizzo idempotente, richiesta `openai/files/open` e skin invariata dopo il tema host. Prove in `browser-results.json`, `local-delivery-evidence.json`, `workspace-restored-skin.png` dentro `work/extensions-verification/`.
- **Launcher installato verificato via protocollo stdio reale:** versione 1.8.3, risorse UI **v1.50**, entrypoint global/thread, apertura vuota e flag locale attivo. Il PNG del terzo test è stato recuperato senza rigenerazione e salvato dal tool installato in `/Users/vincos/Downloads/Quote Card Builder/quote-card-627fa89c78156555.png`. Hash e prova in `installed-smoke-results-1.8.3.json`.
- La sorgente locale, la skill standalone e i 56 file dichiarati nel pacchetto/cache corrispondono alla build finale. ZIP `dist/quote-card-builder-plugin-1.8.3.zip`, checksum `dist/quote-card-builder-plugin-1.8.3.sha256`, SHA-256 **8e6cead7f5c9524198c0c585580deb44b10bca3923006d5c933afd4e63493312**.
- Backup della 1.8.2: `/Users/vincos/plugins/quote-card-builder.backup-20261013-pre-1.8.3` e `/Users/vincos/.codex/skills/quote-card-builder.backup-20261013-pre-1.8.3`.

## Limite della prova nel client

È stato aperto il workspace nella chat corrente e ispezionato tramite il browser MCP Apps di Codex: mostra ancora **v1.49**, perché il processo MCP di questa chat precede l’aggiornamento. Non è una prova della 1.8.3 e non è stato modificato quel processo o la sua cache per simulare una ricarica. **Il ciclo Download/Send nella UI v1.50 di Codex resta da verificare in una chat nuova**. Controllare il badge v1.50 prima del test; se resta v1.49, ricaricare il client. Non dichiarare il successo completo in Codex sulla sola base della suite o dell’host simulato. Nessun deploy remoto o pubblicazione eseguiti.

## Storico — candidata Extension 1.8.2

Aggiornato il 13 ottobre 2026 dopo il secondo test nel client Codex.

La **1.8.2 è installata e abilitata localmente** come `quote-card-builder@personal`. Il secondo test della 1.8.1 aveva chiamato `quote_card_builder_open_editor` con la risorsa preview v1.48 marcata `inline`; non aveva esercitato l'ingresso globale della Extension. Inoltre il PNG era presente come blocco immagine nell'evento MCP, ma la risposta finale aveva mostrato solo il nome del file. Il PNG effettivo del test è stato recuperato in `work/extensions-verification/test-2-quote-card-4431bb01.png`.

La 1.8.2 corregge il percorso di apertura: `quote_card_builder_open_workspace` è richiamabile dal modello quando si seleziona il plugin senza frase, oltre ad avere ingressi `global` e `thread`; apre con `{}` senza generare una card. `quote_card_builder_open_editor` resta disponibile per frasi già scelte e richiede ora una scheda contenuto `fullscreen`. Entrambe le risorse sono v1.49. La skill evita le tre domande preliminari in chat quando si apre il workspace vuoto.

L'editor espone **Download PNG** come azione primaria anche se l'host non dichiara il download nativo; **Send PNG to chat** resta una seconda azione. Questo evita di trattare l'immagine ricevuta nel contesto del modello come prova che l'utente abbia ricevuto un file. Nel test simulato con Chrome reale, sia il download Blob sia l'invio opzionale del PNG alla chat hanno funzionato. Il client Codex reale non è stato pilotabile da questa task via computer use, quindi **l'apertura nella scheda laterale e il download dentro Codex richiedono ancora una prova manuale**: il test di protocollo e il browser simulato non equivalgono a quella prova.

- Suite Python: **314 test superati**, nessuno saltato (`/private/tmp/qcb-182-tests.log`).
- Test Chrome con host MCP Apps simulato: **14 verifiche superate**, nessun errore JavaScript (`work/extensions-verification/browser-results.json`).
- Dal percorso installato: versione server 1.8.2, ingressi `global` e `thread`, visibilità `app` e `model`, apertura vuota e risorsa guided fullscreen v1.49 verificati (`work/extensions-verification/installed-smoke-results-1.8.2.json`).
- `uv lock --check --offline`, `git diff --check` e parità dei file tra pacchetto, sorgente marketplace, cache Codex e skill standalone superati.
- Pacchetto: `dist/quote-card-builder-plugin-1.8.2.zip`, checksum in `dist/quote-card-builder-plugin-1.8.2.sha256`, SHA-256 `1c5ce7b860b8ab26e44d93e62644721bb0d9edbeb4ff307b23457b9fe9285e74`; i 56 file corrispondono a `BUILD-INFO.json`.
- Rollback: `/Users/vincos/plugins/quote-card-builder.backup-20261013-pre-1.8.2` e `/Users/vincos/.codex/skills/quote-card-builder.backup-20261013-pre-1.8.2`.

## Storico della candidata 1.8.1

Aggiornato il 13 ottobre 2026. **Implementazione, pacchetto e installazione locale Codex verificati; distribuzioni remote non aggiornate.**

## Risultato

Il plugin ora espone un ingresso globale MCP Extensions che accetta `{}` e apre un workspace vuoto o una bozza recuperata sul dispositivo. Il renderer Python rimane quello canonico; il percorso guidato dalla conversazione mantiene il proprio editor inline.

- `quote_card_builder_open_workspace` è riservato all'app, ha l'entrypoint `global` e non chiama il renderer all'apertura.
- Workspace fullscreen e preview inline hanno risorse distinte, entrambe v1.48. Restano disponibili gli alias preview da v1.26 a v1.47.
- Prima della preview servono testo, scelta esplicita dell'attribuzione (nome/fonte oppure nessuna) e palette. Un colore non valido blocca preview e produzione, anche durante una richiesta pendente.
- La bozza del workspace usa persistenza locale versionata; il widget inline conserva il proprio stato separato. “New card” cancella bozza, risultato precedente e contesto del modello. Il recupero non è sincronizzazione cloud o tra dispositivi.
- Tema host, safe area, capacità di visualizzazione e contesto del modello sono gestiti dal bridge. La rimozione di un allegato non lo reintroduce automaticamente.
- Il layout fullscreen contiene l'anteprima; la vista stretta non produce scorrimento orizzontale. Branding Barlow/Orbitron e wordmark sono conservati.

## Disallineamenti corretti nel sorgente

La base locale era HEAD `cb232f0`, branch `codex/mcp-plugin-v1.7.12`, candidata 1.7.16, con 45 voci di lavoro preesistente. Il branch non è stato resettato o sostituito.

L'interrogazione del servizio Cloud Run durante questa attività ha rilevato **server 1.7.21 e preview v1.46**. La relativa base sorgente è stata individuata nel branch `codex/qcb-live-png-download`, commit `23ac5d9a35968aa2f7a06b23dd2c9263f3f43c2d`. Le correzioni sono state riconciliate per file e comportamento, senza incorporare indiscriminatamente un branch divergente:

- palette modificabile, palette iniziale e salvataggio dei colori negli stili;
- profili salvati dai valori correnti della bozza;
- stile Gradient, controlli di contrasto/logo/outline e blocco della produzione quando la verifica non passa;
- editor locale allineato per palette e Gradient;
- consegna PNG, redirect regionali, fallback Blob e consegna alla chat;
- branding della UI remota preservato.

Il primo test nel client della 1.8.0 ha poi rivelato un difetto di consegna: quando Codex dichiarava sia messaggi `resource` sia messaggi `image`, l'app preferiva una risorsa con URI interna `file:///…`. La produzione riusciva, ma l'utente non riceveva un file utilizzabile. La 1.8.1 preferisce il blocco immagine PNG reale quando il download nativo non è disponibile; la risorsa interna rimane soltanto come ultimo fallback. La skill ora vieta anche di dichiarare la consegna in base alla sola URI interna.

La candidata usa **1.8.1** in skill, manifest, server, progetto e lockfile. Le dipendenze dichiarate nel container e nel progetto coincidono: `mcp[cli]==2.1.1` e `openai-mcp-extensions==0.2.0`. CI configurata per Python 3.12, 3.13 e 3.14; la verifica locale è stata eseguita su 3.12.13. Non è una prova di esecuzione della matrice GitHub.

Il builder rifiuta versioni o dipendenze incoerenti e inserisce nel pacchetto un `BUILD-INFO.json` con impronte dei file e del contenuto complessivo. I dossier di submission precedenti restano riconoscibili come storico, senza trasformare vecchie prove in attestazioni della nuova candidata.

## Verifiche concluse

| Verifica | Esito ed evidenza |
| --- | --- |
| Suite Python completa con dipendenze da lockfile | **314 test superati, nessuno saltato**; `work/extensions-verification/tests-1.8.1.log` |
| Proxy Sites | **4 test Node superati**, nessuno saltato |
| Browser Chrome isolato | **13 scenari superati**, nessun errore JavaScript; `work/extensions-verification/browser-results.json` |
| Immagine prodotta | PNG generato dal renderer e scaricato nel browser; `work/extensions-verification/browser-download.png` |
| Controllo visivo | Screenshot desktop e vista 375 px esaminati; `work/extensions-verification/workspace-desktop.png` e `workspace-mobile.png` |
| Lockfile | `uv lock --check --offline` superato con cache temporanea |
| Integrità del pacchetto | Archivio leggibile; **56 file** verificati contro `BUILD-INFO.json` |
| Riproducibilità del pacchetto | Due build consecutive identiche byte per byte |
| Diff | `git diff --check` superato |
| Installazione Codex personale | 1.8.1 installata e abilitata; avvio e discovery dal percorso installato superati; `work/extensions-verification/installed-smoke-results.json` |

Il test browser usa **Chrome reale, client/server MCP reali e renderer reale, con host MCP Apps simulato**. Copre apertura vuota, scelte obbligatorie, preview, download PNG, recupero della bozza, passaggio custom→neutral, colore non valido durante aggiornamento, tema host, layout stretto, cancellazione persistente, cancellazione del contesto, compatibilità inline e il caso Codex senza download nativo che espone insieme `resource` e `image`. In quest'ultimo caso è verificato che il messaggio contenga il PNG e nessuna risorsa `file:///`. Non sostituisce il nuovo test manuale nel client Codex. Procedura ripetibile in `tests/browser/README.md`.

## Artefatto pronto

- Pacchetto: `dist/quote-card-builder-plugin-1.8.1.zip` (527.976 byte).
- Checksum: `dist/quote-card-builder-plugin-1.8.1.sha256`.
- SHA-256 ZIP: `8a8cb104b3af27692745bb8bbc92af05416338ac9c5accc20eb975e36cd07c73`.
- Impronta contenuto: `1084d1088923a4fb4e4637df99b65d82e317868fddd92f714166dba93aca62a5`.
- Verifica dettagliata: `work/extensions-verification/package-results.json`.

`dist/` e `work/` sono ignorati da Git: il pacchetto e le prove sono disponibili su questo computer. Il repository contiene i sorgenti dei test per ripeterli; nessun commit o push è stato effettuato.

## Installazione locale

La 1.8.1 è installata e abilitata come `quote-card-builder@personal`:

- sorgente del marketplace: `/Users/vincos/plugins/quote-card-builder`;
- cache Codex: `/Users/vincos/.codex/plugins/cache/personal/quote-card-builder/1.8.1`;
- rollback del plugin 1.8.0: `/Users/vincos/plugins/quote-card-builder.backup-20261013-pre-1.8.1`;
- skill standalone allineata alla 1.8.1: `/Users/vincos/.codex/skills/quote-card-builder`;
- rollback della skill standalone 1.7.21: `/Users/vincos/.codex/skills/quote-card-builder.backup-20261013-pre-1.8.1`.

Codex ha confermato versione 1.8.1, stato installato e abilitato. Dal percorso installato sono stati verificati l'avvio con il lockfile, i cinque tool, la risorsa fullscreen `ui://quote-card-builder/workspace/v1.48.html`, l'entrypoint globale e l'apertura vuota senza render. Il nuovo URI evita che il client riutilizzi la UI v1.47 in cache.

## Ciò che resta da verificare prima della distribuzione

1. Dopo il ricaricamento del client, verificare manualmente la scoperta e apertura dalla sidebar, il recupero alla riapertura, l'isolamento inline e il contesto del modello nel client reale.
2. Ripetere nel client il caso che aveva fallito sulla 1.8.0: **Genera**, poi **Send PNG to chat**, verificando che la conversazione mostri davvero il PNG. Il comportamento corretto è coperto dal test browser, ma la 1.8.1 non è ancora stata provata manualmente in una nuova chat Codex.
3. Pubblicare il sorgente scelto e il pacchetto con checksum; aggiornare deliberatamente Cloud Run e il pilot Sites alla stessa build, quindi interrogare versione server, URI UI ed entrypoint sul deployment.

Questi passi sono **ancora aperti**. Cloud Run è rimasto 1.7.21/v1.46 nella verifica effettuata; GitHub `main` era `6935680904980e8dc224b0c87c4ab79a4ec2195b` (release 1.5.2). Il pilot Sites esistente non è stato modificato. L'installazione personale locale non va interpretata come pubblicazione o sincronizzazione delle distribuzioni remote.

Non fanno parte di questa candidata archivio cloud, risorse di progetto/menzioni, applicazione automatica delle modifiche suggerite dal modello o parità multiformato con il Visual Review Studio locale.

## Delega e modelli usati

- **GPT-5.6 Sol**, ragionamento high: agente backend/Extensions, dipendenze e riconciliazione del renderer.
- **GPT-5.6 Sol**, ragionamento high: agente UI, persistenza, contesto host e regressioni.
- **GPT-6 Luna**, ragionamento high: agente documentazione, manifest, CI e allineamento dell'editor locale.
- Agente principale: integrazione, revisione incrociata, verifica browser e del pacchetto.

Terra non è stato usato. Il risultato è un MVP installato localmente; resta la prova manuale della nuova superficie globale dopo il ricaricamento del client.
