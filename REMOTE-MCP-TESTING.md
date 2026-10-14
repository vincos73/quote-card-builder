# Prova web MCP Nastri — 1.8.11 / UI v1.58

14 ottobre 2026. Il servizio web è aggiornato e il plugin personale **Quote Card Builder TEST MCP** contiene la skill web. Endpoint invariato: `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`, autenticazione None. Non installare il pacchetto stdio locale per questa prova.

Aprire [la scheda del plugin](https://chatgpt.com/plugins/plugin_asdk_app_6acdf4f176e081918544ae00a8326edd), aggiornare la connessione MCP e avviare una nuova chat. È la [procedura di refresh indicata da OpenAI](https://developers.openai.com/plugins/build/app-quickstart#next-steps). Verificare il badge **v1.58**.

Prompt di prova: «Usa Quote Card Builder TEST MCP. Crea tre composizioni Nastri diverse per “Le idee migliori diventano utili quando le condividiamo”. Senza autore. Palette acid/pop: primary #3524FF, accent #FF47CA, background #DAFF00, text #072743. Apri l’editor per sceglierne una». La frase è sintetica e la palette sperimentale, non un’attribuzione o identità ufficiale.

Scegliere una scena, modificare grassetto/highlight/dimensione di una selezione e dimensioni di citazione/autore; scegliere un formato e scaricare PNG. Un contrasto insufficiente o una dimensione eccessiva deve produrre solo avvisi descrittivi senza bloccare il download. Salvare una base, riusarla con una frase nuova e senza ereditare autore/selezioni vecchie; provare export/import JSON. Per una nuova proposta creativa dalla chat richiamare il plugin e chiedere tre nuove composizioni dalla bozza corrente: il modello deve usare l’update revisionato e conservare la palette. Le varianti dall’editor sono invece demo dichiarate.

475 test senza skip, smoke SDK canary/produzione e download PNG nei tre formati passano. Il 14 ottobre l’utente ha confermato «ok funziona» nel test ChatGPT; questa attestazione manuale non sostituisce una prova automatizzata di tutte le funzioni del client. Palette e geometria riusabili, senza sincronizzazione cloud o upload di font/logo; un formato per ogni download. Evidenze in RELEASE-STATUS.md.

## Storico 1.8.10 e precedenti

# Quote Card Builder — test MCP remoto

## Storico — Servizio 1.8.10 / UI v1.57

La revisione `quote-card-builder-mcp-00122-yoc` riceveva il 100% del traffico prima della 1.8.11. L’endpoint non cambia: `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`, autenticazione None.

La composizione iniziale privilegia 6–9 righe brevi per frasi medio-lunghe, enfasi selettiva e testo fonte intatto. La firma è più discreta: 46,8 px sulla canvas da 1440 px. La didascalia UI usa `.qcb-preview-caption`, così il suo font da 9 px non si applica più alla firma nell’SVG.

Sono passati due test mirati e i controlli di versione, risorsa UI e singolo rendering su canary e produzione: `work/remote-mcp/canary-smoke-1.8.10.json`, `work/remote-mcp/production-smoke-1.8.10.json`. Nell’esempio su sette righe il font remoto è 106,4 px (27,7 px alla larghezza di 375 px). Non è stata ripetuta la suite completa; nessuna nuova chat nativa o prova visiva di download è attestata. Il confronto browser locale non è stato eseguito perché l’apertura del file di prova è stata respinta dalla policy browser.

Per il test dell’utente: aggiorna gli strumenti di **Quote Card Builder TEST MCP** e apri una nuova chat per ottenere la risorsa v1.57; gli editor già aperti possono mantenere la vecchia UI. Prova la frase del link, confronta anteprima e PNG della stessa card con firma.

## Storico — 1.8.9 / UI v1.56

La versione precedente del servizio era 1.8.9/UI v1.56 del Quote Card Builder. La revisione `quote-card-builder-mcp-00120-gur` riceve il 100% del traffico. Canary, smoke di produzione e apertura nativa iniziale sono PASS; la suite 1.8.9 ha superato 357 test senza skip. Le prove browser automatizzate già documentate sotto appartengono alla versione 1.8.8; non è stato eseguito un nuovo harness browser completo per la 1.8.9. Evidenze e limiti sono registrati in `RELEASE-STATUS.md`.

### Verifiche storiche 1.8.9/UI v1.56

La revisione `quote-card-builder-mcp-00120-gur` era live al 100% sull'endpoint di produzione. Canary e smoke di produzione PASS sono registrati in `work/remote-mcp/canary-smoke-1.8.9.json` e `work/remote-mcp/production-smoke-1.8.9.json`. Il codice UI non è cambiato: la risorsa resta `ui://quote-card-builder/workspace/v1.56.html`, hash `4ffb429c88ab62653f1eeaed48a44a508afc686871f140c7c23f31c00418b732`.

La nuova composizione iniziale usa una guida semantica flessibile: in genere 4–7 righe per frasi di circa 20–40 parole, con unità visive spesso nell'ordine di 18–32 caratteri; una citazione breve può stare su 2–3 righe. Le parole, la punteggiatura, le negazioni e le cautele restano invariate. Si possono applicare da 1 a 3 brevi enfasi senza obbligare all'uso di tutte le modalità. Per una richiesta chiara da URL, il modello legge la fonte tramite l'host e apre in una sola chiamata l'editor popolato con `lines` e `styles`; una modifica di sola impaginazione conserva `VERBATIM` e lo stato della prova.

La suite completa ha superato **357 test senza skip** (`work/remote-mcp/tests-full-1.8.9.log`); i cinque test di composizione iniziale passano (`tests/test_mcp_initial_composition.py`). La prova comparativa locale indica 28,4 px su una riga contro 104,6 px su cinque, con formulazione preservata (`work/remote-mcp/composition-font-comparison-1.8.9.json`). Non attribuire questi valori alla prova nativa. **Non è stato eseguito un nuovo harness browser completo per 1.8.9**.

La prova nativa è PASS nella [nuova chat di verifica](https://chatgpt.com/c/6ace34af-4f78-83ed-b5ab-50f8c69a923b), con prompt generico: «Crea una quote card da https://vincos.it/augmented-marketing-suite/ e procedi.» Il modello non ha ricevuto suggerimenti su a capo o stile: ha aperto una sola volta l'editor, senza domande e senza passare dal workspace vuoto. La citazione originale è rimasta esatta ed è stata impaginata così:

```text
L’IA aiuta a chiarire i problemi
e a valutare le opzioni;
il giudizio e la responsabilità
restano alle persone.
```

Nel DOM la terza riga era in grassetto e la quarta evidenziata; attribuzione “Vincenzo Cosenza”, palette neutra e formato 4:5. Il font effettivo nell'SVG era 72,2 px. Evidenza DOM e screenshot: `work/remote-mcp/browser-1.8.9/chatgpt-native-results.json` e `work/remote-mcp/browser-1.8.9/chatgpt-initial-composition.png`. Aggiornare gli strumenti del plugin esistente non ha richiesto cambiare identità, autenticazione o permessi.

## Storico — Servizio live 1.8.8/UI v1.56

Usa l'endpoint di produzione:

`https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`

Seleziona autenticazione **None**. Lo smoke di produzione ha verificato server 1.8.8, risorsa UI `ui://quote-card-builder/workspace/v1.56.html`, protocolli MCP, tool discovery ed export PNG. Registri: `work/remote-mcp/production-service-1.8.8.json` e `work/remote-mcp/production-smoke-1.8.8.json`.

In una nuova chat, fornisci un URL pubblico leggibile e chiedi in modo esplicito di procedere, per esempio: «Usa Quote Card Builder su questo link e procedi con una card». Verifica che il modello legga la fonte tramite la navigazione dell'host e apra direttamente un solo editor con una citazione esatta; non deve aprire prima il workspace vuoto né chiedere conferma di frase, attribuzione o palette. Una citazione controllata parola per parola sulla fonte può essere marcata `VERIFIED`; un nome compare nell'attribuzione solo se fornito dall'utente o verificato nella fonte. In assenza di nome, l'attribuzione resta vuota e la palette neutra è iniziale. Il server live non scarica o legge URL autonomamente.

Con l'editor aperto, richiama il plugin nella chat (per esempio `@Quote Card Builder TEST MCP`) e chiedi una modifica specifica al testo o all'attribuzione. Il client può non rendere disponibile il tool se il follow-up non richiama il plugin. Verifica che l'aggiornamento usi la revisione e la bozza corrente, che il rendering mostri il testo aggiornato e che palette, formato, motivo, posizione e altre scelte non coinvolte restino uguali. Se il testo cambia, la trasformazione predefinita deve essere `EDITED` e la prova `UNVERIFIED`, salvo nuova verifica esplicita. La risposta del server è una proposta renderizzata; considera l'aggiornamento accettato solo quando la UI conferma la nuova revisione e lo stato corrente.

Per completare la prova, usa **Download PNG** e verifica che il file scaricato corrisponda all'anteprima. La suite completa ha superato 352 test senza skip. Chrome con host MCP Apps simulato e backend live ha superato 33 controlli (`work/remote-mcp/browser-1.8.8/remote-browser-results.json`); questi controlli automatizzati non sostituiscono le verifiche interattive nel client ChatGPT reale.

## Collegare il server a ChatGPT

La configurazione segue la procedura ufficiale [Connect and test your plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt):

1. Apri **Plugins** in ChatGPT. Se l'account richiede developer mode per aggiungere MCP personalizzati, abilitalo nelle impostazioni disponibili per il tuo piano/workspace.
2. Premi **+ → Add custom MCP server** e inserisci un nome riconoscibile, per esempio `Quote Card Builder test`.
3. Come URL del server usa esattamente:

   `https://quote-card-builder-mcp-960066178304.europe-west8.run.app/mcp`

4. Imposta l’autenticazione su **None**, conferma l’avviso mostrato da ChatGPT e seleziona **Create as plugin**. Non servono credenziali o un login aggiuntivo al server.
5. Installa/abilita il plugin appena creato. Avvia una **nuova chat** e richiamalo con `@Quote Card Builder test` (o il nome scelto).

La disponibilità delle impostazioni e dei plugin dipende dai permessi dell’account e del workspace e dall’interfaccia ChatGPT disponibile. Questa guida non presume che la configurazione sia presente su ogni piano o client.

## Prova minima

Nella nuova chat, richiama il plugin e apri un workspace nuovo. Il server riceve `{}` e restituisce uno stato vuoto; dopo l'apertura, la UI mostra il demo modificabile con la frase su quattro righe “Le idee migliori / meritano / di essere / condivise.”, senza autore, con la prima riga in grassetto, “meritano” e “di essere” in corsivo e “condivise” evidenziato. La palette neutra è selezionata quando manca una scelta esplicita. Il testo è soltanto un esempio UI, non proviene dall'utente o dal server. La scelta iniziale di attribuzione è “nessuna” e la palette neutra è selezionata. Modifica la frase per la prova; verifica che il default di nessuna attribuzione resti selezionato e che un nome già scelto venga mantenuto. Se viene selezionata intenzionalmente un’attribuzione nominativa ma il testo resta vuoto, la scelta deve apparire incompleta. Se arriva un testo esplicito mentre il demo non è stato toccato, verifica che lo sostituisca e che le scelte dimostrative tornino da confermare.

Usa **Download PNG** per completare la prova: questa singola azione genera e salva il PNG.

Controlla che:

- il demo contenga la frase indicata, senza un nome di autore inventato, e sia chiaramente indicato;
- la frase sia modificabile e resti marcata come demo; formattazione e spaziatura non devono cancellare le scelte demo;
- dopo il rendering, l’interfaccia mantenga visibile lo stato delle scelte ancora mancanti per una card reale;
- **Download PNG** produca e scarichi l’immagine con un unico clic, senza un precedente passaggio **Genera**;
- l'interfaccia non presenti **Send PNG to chat**;
- il file scaricato corrisponda all'anteprima e sia effettivamente disponibile al tester.

Se una voce o un pulsante non compare, annota il client usato, il passaggio, il messaggio mostrato e, se possibile, il testo restituito dal plugin. Non considerare il solo collegamento del server una verifica dell’intero flusso.

## Dati e limiti del test remoto

Gli export remoti passano da un bucket privato e vengono resi disponibili tramite URL temporanei, validi per 24 ore. Chiunque abbia un URL può accedere al relativo file finché l’URL è valido: non condividere il link fuori dal test. Non usare contenuti riservati o dati personali. Il test non salva gli export nell’archivio personale. La cancellazione fisica dallo storage avviene in modo asincrono.

Il plugin installato localmente, versione 1.8.3, resta indipendente da questo test remoto.

## Stato storico — 1.8.8/UI v1.56

Il servizio live descritto in questa guida è **1.8.8/UI v1.56**. Nella chat nativa di prova, due aggiornamenti consecutivi sono riusciti nell'editor aperto già esistente quando il plugin è stato richiamato in ciascun follow-up. L'apertura iniziale singola da URL era stata verificata in precedenza su v1.55; non è attestata una nuova apertura iniziale v1.56.

**Servizio live 1.8.8/UI v1.56: promozione al 100%, smoke di produzione, 352 test senza skip e 33 controlli browser superati; due follow-up nativi consecutivi verificati.** Le prove browser automatiche usano un host simulato. Per ogni follow-up nativo occorre richiamare il plugin. Dettagli e prove in `RELEASE-STATUS.md`.
