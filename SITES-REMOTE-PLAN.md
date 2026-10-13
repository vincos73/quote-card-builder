# Quote Card Builder remoto: piano per accesso con account ChatGPT

Data: 13 ottobre 2026. Il piano originale è riportato sotto; le decisioni di questa sezione lo aggiornano per la prima versione autorizzata.

## Decisione aggiornata: MCP senza login aggiuntivo

L'utente ha chiarito che la prima versione deve funzionare nelle chat dei singoli tester, senza archivio personale. Il riconoscimento degli utenti è una possibile evoluzione. Ha autorizzato l'implementazione della versione MCP senza login aggiuntivo.

- Prima versione: endpoint MCP pubblico Cloud Run, autenticazione `None`, renderer e UI derivati dalla base locale funzionante; il Site e il suo plugin personale restano il pilot esistente.
- Consegna PNG: storage privato condiviso tra istanze, URL casuali con scadenza di 24 ore, creati su Download/Invia; nessun archivio personale. La cancellazione fisica avviene tramite lifecycle asincrono.
- Test prima della submission: ogni tester abilitato aggiunge il server tramite URL `/mcp`, seleziona `None` e installa il plugin di prova. Il test del server non sostituisce la distribuzione pubblica del plugin con le sue skill.
- OAuth Sites per distribuzione pubblica: **non confermato**. La documentazione descrive il percorso personale/workspace; le sonde esterne sono state bloccate da Cloudflare Error1010, e i tentativi browser da `ERR_BLOCKED_BY_CLIENT`. Questi errori non provano incompatibilità OAuth. Il requisito OAuth non è necessario per la prima versione scelta.
- Un'eventuale integrazione autonoma di Sign in with ChatGPT in un plugin esterno richiede accesso al programma limitato descritto da OpenAI; non è un'alternativa da presumere subito disponibile. [Documentazione](https://developers.openai.com/siwc/chatgpt-plugin).
- Diagnosi Cloud Run: i log associano il429 a mancanza di istanze disponibili; il limite del servizio è1. La revisione attuale contiene il sorgente1.7.21/UIv1.46. La candidata remota aggiorna protocollo stateless e consegna file, con capacità limitata e verifiche prima della promozione.

Procedura tester: [REMOTE-MCP-TESTING.md](REMOTE-MCP-TESTING.md). Le fasi di login/isolamento per utente riportate nel piano originale sono rinviate all'evoluzione con archivio personale. Lo stato effettivo del deployment sarà registrato separatamente in `RELEASE-STATUS.md`.

**Esito dell'implementazione:** Cloud Run 1.8.4/UI v1.51 pubblicato e verificato senza credenziali; 346 test Python superati e prova browser con backend remoto e sandbox reale, mediante host simulato. Il Site è aggiornato alla versione 5 e conserva accesso privato/identità precedenti. Il suo collegamento gestito respinge però `server/discover`, quindi non è il percorso da usare per i tester della prima versione. Stato e prove in `RELEASE-STATUS.md`.

## Obiettivo e decisione consigliata

Consentire a persone esterne di usare Quote Card Builder con il proprio account ChatGPT, senza installare un server locale. Il prodotto deve conservare apertura dell'editor, skin, modifica della card, download PNG e invio del risultato in chat.

Conviene riutilizzare il Site esistente come ingresso e il renderer Python su Cloud Run. Portare subito tutto il renderer su Sites aggiungerebbe lavoro e rischi senza risolvere la distribuzione del plugin. L'hosting Sites usa Workers: il backend Python corrente non è già trasferibile al suo ambiente di esecuzione.

Il requisito ha due risultati distinti: un editor sul sito accessibile dopo login ChatGPT e un plugin installabile da account esterni. Il secondo richiede un percorso di pubblicazione dedicato e una verifica iniziale della compatibilità dell'autenticazione. La pubblicazione del sito da sola non completa il requisito del plugin pubblico.

## Lavoro esistente verificato

| Componente | Stato e riuso |
| --- | --- |
| Plugin locale | Versione 1.8.3, UI v1.50; il proprietario ha confermato che apertura, skin e pulsanti funzionano. È la base del nuovo editor remoto. |
| Site | [Quote Card Builder MCP pilot](https://quote-card-builder-mcp-pilot-20261002.vincos.chatgpt.site), progetto `appgprj_6abf45cabe3c81918ed306c7f567cd9e`. |
| Deployment Sites | v4, stato `succeeded`, `has_mcp: true`, pubblicato il 3 ottobre. Commit sorgente indicato dal servizio: `ae58aa203eaf57ca0f3c939401d9112d8de40f10`. |
| Accesso Site | Policy `custom`, solo proprietario; il servizio offre anche la modalità `public`. |
| Plugin del Site | `plugin_asdk_app_sites_6a6a4d45dfb48191b73b4bcd47e8a8a7`, versione 1.0.0, scope USER, visibilità PRIVATE. Contiene manifest e `.app.json`, senza skill. |
| Sorgenti locali del pilot | `experiments/sites-mcp-pilot/`: Worker che inoltra MCP al renderer Cloud Run; la home è una pagina tecnica, senza editor. Non è dimostrata la parità con il repository sorgente del Site. |
| Renderer remoto | Origine già configurata: `https://quote-card-builder-mcp-960066178304.europe-west8.run.app`. L'interrogazione diretta di `/health` è andata in timeout: versione e operatività attuali restano da verificare. |
| Dossier submission | `submission/` contiene checklist e prove precedenti riutilizzabili come traccia. Sono snapshot storici, non attestazioni della candidata corrente. |

## Limite di distribuzione da risolvere per primo

OpenAI documenta che gli account personali/Pro non possono condividere direttamente il proprio plugin Sites con altri utenti; la condivisione nel workspace è un percorso separato. [Hosting dei plugin Sites](https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites).

Il portale pubblico richiede review e approvazione e non accetta attualmente ZIP con riferimenti `apps` / `.app.json`. Il pacchetto del pilot contiene proprio quel riferimento: non è una candidata pubblica caricabile invariata. Serve una configurazione MCP remota e la verifica di dominio/autenticazione. [Submission dei plugin](https://developers.openai.com/plugins/deploy/submission).

**Prima prova da fare:** verificare che l'endpoint MCP gestito dal Site e il suo OAuth possano essere collegati al plugin pubblico nel portale. Controllare registrazione del client, dominio verificabile, scope e identità utente restituita. Il login browser del Site non dimostra automaticamente questa compatibilità.

Se il percorso è supportato, mantenere il medesimo endpoint Sites. Se non lo è, valutare un ingresso MCP su dominio controllato dal publisher, collegato allo stesso renderer, con autenticazione compatibile documentata. Anche in quel caso, ottenere login con il solo account ChatGPT è un requisito da provare prima di costruire un diverso sistema di accesso. Evitare di promettere un plugin pubblico autenticato finché questa prova non passa.

Conservare il plugin Sites come pilot. Riutilizzare l'identità pubblica se il portale consente la conversione; altrimenti creare una sola identità di produzione quando necessario, con nome **Quote Card Builder** e indicazioni chiare che distinguano il pilot.

## Piano di implementazione

### 1. Ricostruire una base pubblicabile e verificare la distribuzione

- Confrontare il sorgente Sites al commit pubblicato con il pilot locale, prima di modificarlo.
- Verificare deployment e versione effettiva di Cloud Run; preparare una build tracciabile derivata dalla 1.8.3, rispettando le modifiche già presenti nel repository.
- Eseguire la prova di autenticazione/pubblicazione descritta sopra. Definire l'origine MCP definitiva prima della submission.
- Verificare editor ed entrypoint sui client ChatGPT destinatari. Le Plugin Extensions hanno una matrice di compatibilità: il funzionamento locale non prova tutti i client. [Specifica MCP Extensions](https://github.com/openai/mcp-extensions/blob/main/docs/spec.md).

Risultato: architettura e percorso di accesso comprovati, senza costruire un nuovo pilot da zero.

### 2. Aggiornare MCP ed editor remoto mantenendo il pilot privato

- Portare sul deployment editor, font, skin e ingressi global/thread della base funzionante.
- Adeguare il Worker al protocollo MCP richiesto da Sites, incluse discovery, strumenti e lettura delle risorse UI.
- Correggere la negoziazione delle capability: il proxy attuale reinizializza le sessioni con `capabilities: {}`, con rischio di perdere il supporto Apps/Extensions.
- Conservare metadati UI, schemi e risposte compatibili; aggiornare domini UI e CSP alla destinazione reale.
- Derivare dalla skill corrente istruzioni adatte al servizio remoto, senza comandi locali o percorsi del Mac del proprietario.

Risultato: stesso editor utilizzabile tramite MCP remoto, con prove di apertura sul client reale.

### 3. Rendere affidabile la consegna dei PNG

Il salvataggio locale in `~/Downloads` non può consegnare un file al computer di un visitatore. Il percorso HTTP disabilita già il flag di consegna locale.

- Conservare la rasterizzazione SVG → PNG corrente e i controlli su dimensioni, integrità e limite del file.
- Salvare il PNG esatto in storage remoto, proponendo R2 per i file e metadati minimi di proprietà/scadenza; D1 solo se necessario.
- Offrire download autenticato e una modalità di allegato supportata dal client. Per il recupero da chat, provare URL temporanei autorizzati se la piattaforma non supporta il trasferimento nativo.
- Verificare che il file scaricato e quello inviato in chat abbiano lo stesso hash del PNG prodotto dall'editor.
- Definire scadenza, pulizia e quote per utente. Proposta iniziale: esportazioni temporanee, senza archivio permanente di tutte le card.

Risultato: download e invio in chat funzionanti nel servizio ospitato; nessun riferimento ai file locali del publisher.

### 4. Consentire accesso esterno con login ChatGPT

- Usare il login nativo Sites per l'editor web; Sites fornisce un identificativo utente stabile all'interno del sito.
- Rendere pubblico l'ingresso dopo aver protetto editor e API: un Site pubblico può ricevere richieste anonime, quindi il server deve controllare l'identità per ogni operazione protetta.
- Separare file, esportazioni e bozze per utente, comprese eventuali bozze conservate nel browser quando si cambia account.
- Proteggere o eliminare `/api/mcp`, oggi un percorso di prova che dipende dal confine del Site privato.
- Impedire che Cloud Run consenta di aggirare i controlli del Site: adottare autenticazione tra servizi supportata e segreti soltanto server-side. Non inoltrare cookie o token personali al renderer.

Risultato: persone esterne accedono con il proprio account e vedono soltanto i propri dati. Il token tecnico del proprietario non sostituisce questa prova.

### 5. Test esterno e pubblicazione del plugin

- Provare con due account distinti e una sessione anonima: login, isolamento, apertura editor, modifica, download e invio in chat.
- Eseguire la suite con dipendenze MCP complete e senza skip pertinenti; aggiungere test mirati di protocollo, autenticazione e storage.
- Verificare i client effettivamente supportati, con prove visive e controlli di accessibilità pertinenti.
- Aggiornare il dossier esistente sulla build congelata, completare informazioni del publisher e materiali richiesti dal portale, quindi eseguire review e pubblicazione.

L'accessibilità universale del plugin resta soggetta a supporto del client, permessi del workspace e disponibilità del prodotto. Non richiedere il developer mode come procedura ordinaria agli utenti finali.

## Criteri di completamento e costi

Il lavoro è completo quando un account esterno può installare/connettere il plugin pubblico, aprire l'editor sul client supportato e ottenere il PNG corretto tramite entrambi i pulsanti, senza dipendere dal computer del proprietario. L'editor web autenticato è un risultato utile della stessa architettura, ma l'installazione pubblica del plugin va verificata separatamente.

Il login identifica l'utente; non trasferisce automaticamente sul suo abbonamento i costi di Cloud Run e storage. Il rendering corrente non richiede chiamate a un modello. Prima dell'apertura ampia, misurare consumo reale e definire limiti di utilizzo.

In questa verifica sono stati letti sorgenti, stato Sites, deployment, metadata e file del plugin e documentazione ufficiale. Non sono stati modificati codice operativo, accessi, plugin o deployment. Non è stata verificata una connessione remota da un secondo account né l'operatività attuale di Cloud Run.
