# Basi personali e progetti trasferibili

Sorgenti candidati 1.10.0. Web e Visual Review Studio locale condividono due formati JSON distinti.

Una base personale ha `schema: qcb-personal-base`, `schemaVersion: 2`, `name` e `design`. Conserva grammatica, scena selezionata, ruoli della palette, preferenze di formato/dimensione, logo e brand kit. Non contiene citazione, autore, intervalli sulle parole, prove editoriali, fonte o alt text. Galleria e origine delle proposte appartengono alla sessione.

Un progetto ha `schema: qcb-card-project`, `schemaVersion: 1`, `name` e `draft`. Conserva la card completa, compresi citazione, a capo, autore, formattazioni e brand kit. Gli intervalli usano indici Unicode nel testo dell’editor, con newline e righe vuote. Il locale converte gli intervalli verso il proprio testo normalizzato e li riconverte nell’export. L’eventuale `editorial.source` mantiene la fonte locale senza incorporare percorsi degli asset.

Le vecchie basi web vengono lette e migrate nello stesso archivio del dispositivo. La loro card completa viene conservata come progetto recuperabile tramite **Restore saved card**. Il salvataggio di altre basi conserva questi progetti; una scrittura fallita per quota non cancella l’archivio precedente. I progetti web v1 e i manifest locali storici restano importabili.

**Reuse this card / Riusa questa card** applica il design della base selezionata. Se le parole sono invariate, conserva le formattazioni del testo corrente; con una citazione nuova azzera i vecchi intervalli e la dimensione assoluta della citazione. Il campo autore facoltativo determina l’attribuzione e può essere svuotato. La base scelta prevale sulla palette e sulla geometria di una card diversa aperta nell’editor.

**Create in this style** nel web invia una richiesta esplicita alla chat dell’host, quando supportata. Il modello legge lo stato corrente e progetta tre nuove scene, applicandole con `quote_card_builder_update_editor` e revisione corrente. Se l’host non supporta il messaggio, l’interfaccia spiega come richiederle in chat. **Demo variations** resta una funzione deterministica separata. Nel locale le nuove scene del modello possono essere inviate alla sessione; le variazioni del solo editor sono dichiarate demo.

**Download base** esporta il design; **Export project JSON / Scarica progetto JSON** esporta il progetto completo. L’export locale riceve la bozza corrente, compresi gli interventi ancora non generati. L’import della base la aggiunge alla biblioteca; l’import del progetto ripristina una card.

Le basi e le bozze restano nel client/dispositivo. I JSON sono il trasferimento esplicito fra ambienti. Un futuro archivio sincronizzato richiede identità dell’utente, autorizzazioni, gestione dei conflitti e una politica per gli asset; non è attivato da questo aggiornamento.
