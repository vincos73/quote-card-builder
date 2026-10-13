# Quote Card Builder

Quote Card Builder è una skill per ChatGPT e Claude che trasforma una frase, un testo, un URL, un documento o un’idea in una quote card pronta da condividere.

È disponibile come skill e come plugin per ChatGPT e Codex. Il plugin include l'MCP server locale e l'app interattiva; la skill canonica resta utilizzabile anche senza MCP.

È pensata per creator, marketer e professionisti che vogliono ottenere rapidamente una grafica coerente, senza aprire un editor professionale. Il testo, l’attribuzione e le scelte editoriali restano sempre sotto il controllo dell’utente.

Nella release remota 1.8.8/UI v1.56 erano stati verificati apertura popolata da URL e due aggiornamenti consecutivi nell'editor nativo; la versione corrente è 1.8.10/UI v1.57. Per aprire la card da un link, il modello usa la navigazione dell'host, mentre il server non legge URL. Le modifiche successive dalla chat usano un aggiornamento del draft completo con controllo della revisione; per attivare il tool nel client ChatGPT, richiama il plugin in ogni follow-up. La promozione, gli smoke e le prove sono documentati in `RELEASE-STATUS.md`. L'installazione locale resta 1.8.3.

La versione remota **1.8.10/UI v1.57 è live al 100%**. Le istruzioni preparano righe più corte per dare maggiore impatto alla quote su smartphone, senza riscriverla. La firma è più discreta e il CSS dell’interfaccia non ne altera più la resa nell’anteprima. Sono passati due test mirati e i controlli di versione, risorsa UI e rendering sul servizio remoto; la prova visiva nativa e del download è lasciata all’utente. Evidenze e limiti in `RELEASE-STATUS.md`.

<img width="1956" height="1130" alt="quote-card-builder-screen" src="https://github.com/user-attachments/assets/550fbf0b-21b3-4b01-b8f1-48cbd04574d5" />

## Che cosa fa

La skill accompagna l’utente dall’idea al file finale:

1. legge il materiale disponibile o parte da una frase già scelta;
2. propone fino a tre candidati quando serve trovare la formulazione più efficace;
3. distingue il testo originale da una modifica, una parafrasi o una frase generata;
4. mantiene separati fonte, attribuzione e identità del brand;
5. apre un editor locale per controllare testo, a capo, stile e formato;
6. verifica leggibilità, contrasto, margini e possibili sovrapposizioni;
7. genera un PNG oppure un pacchetto ZIP con più formati.

L’editor del plugin offre quattro stili compositivi:

| Stile | Aspetto | Motivo disponibile |
| --- | --- | --- |
| **Blocks** | campi tipografici editoriali | composizione deterministica variabile |
| **Cutouts** | ritagli geometrici piatti | composizione deterministica variabile |
| **Constellations** | reti di nodi e connessioni | composizione deterministica variabile |
| **Gradient** | campi cromatici sfumati | composizione deterministica variabile |

Lo stile si sceglie nell'editor, insieme alla variante riproducibile del motivo; può anche essere nascosto.

## Che cosa non fa

Quote Card Builder non sostituisce Canva, Figma, Photoshop o un art director. Non permette di spostare liberamente ogni elemento e non inventa font, colori, loghi, autori o fonti.

La skill segnala problemi e incongruenze, ma non certifica la correttezza editoriale di una frase. Prima di premere **Genera**, l’utente può modificare testo e attribuzione e si assume la responsabilità della versione finale.

## Un esempio rapido

In una nuova task di Codex, scrivi:

```text
Usa $quote-card-builder per trasformare questa frase in una quote card:
«La tecnologia migliore è quella che ci aiuta a decidere meglio.»
Attribuzione: Mario Rossi
```

La skill prepara il contenuto e apre il Visual Review Studio nel browser. Nell’editor puoi:

- cambiare testo e attribuzione;
- scegliere Blocks, Cutouts, Constellations o Gradient nell'editor;
- variare in modo riproducibile il motivo oppure nasconderlo;
- modificare gli a capo;
- usare grassetto, corsivo, sottolineato, evidenziato, accento o contorno;
- ridurre la dimensione del testo e scegliere la posizione verticale;
- mostrare o nascondere il logo;
- salvare il brand corrente come profilo riutilizzabile;
- esportare in `4:5`, `1:1`, `9:16` oppure in tutti i formati.

L’alt text viene creato automaticamente. Se serve correggerlo, il campo facoltativo si trova nel pannello **Accessibilità**.

Quando premi **Genera**, l’interfaccia mostra il nome del file, una cartella abbreviata, il comando per copiare il percorso completo e l’azione per tornare alla task Codex.

## Profili riutilizzabili

Apri **Palette della card** e scegli **Salva profilo** per conservare il brand corrente. Dopo il salvataggio, **Esporta JSON** scarica un file `<nome-brand>-quote-card-brand.json`. Il profilo include soltanto:

- nome del brand;
- quattro colori della card;
- famiglia e file del font;
- file del logo.

Citazioni, fonti, attribuzioni e alt text non vengono salvati nel profilo. Nei lavori successivi la skill elenca i profili locali disponibili e ne usa uno solo dopo la tua scelta esplicita. Puoi anche allegare il JSON esportato all'inizio di una nuova conversazione: la skill lo valida, mostra palette, font, logo ed eventuali asset mancanti e attende la tua approvazione prima di applicarlo.

I profili restano sul computer in:

```text
~/.quote-card-builder/profiles.json
```

Questa cartella è separata dall’installazione della skill: aggiornare Quote Card Builder non elimina i profili. Se sposti o cancelli font e loghi collegati, la skill segnala gli asset mancanti prima di usarli.

Il JSON non incorpora i file binari di font e logo: conserva i loro riferimenti. Per controllare manualmente un profilo allegato puoi usare:

```text
python3 scripts/brand_profiles.py validate <profilo.json>
```

## Installazione semplice

### Plugin per ChatGPT e Codex

La release include `quote-card-builder-plugin.zip`, il pacchetto destinato al Plugin Directory. Per lo sviluppo locale viene installato tramite un marketplace personale; la candidatura pubblica resta separata dalla normale installazione della skill.

### Prima installazione su MacOS

1. Apri la pagina delle [release](https://github.com/vincos73/quote-card-builder/releases/latest).
2. Scarica il file `quote-card-builder.zip` dalla sezione **Assets**.
3. Caricalo in ChatGPT o Claude e chiedi di installarlo come skill

### Installazione da Terminale su macOS o Linux

Se preferisci il Terminale e lo ZIP si trova in `Downloads`:

```bash
mkdir -p "$HOME/.codex/skills/quote-card-builder"
unzip "$HOME/Downloads/quote-card-builder.zip" -d "$HOME/.codex/skills/quote-card-builder"
```

Per un aggiornamento è meglio rinominare prima la cartella già installata, come indicato sopra, e poi eseguire questi comandi.

### Windows

Estrai lo ZIP in:

```text
%USERPROFILE%\.codex\skills\quote-card-builder
```

Anche su Windows `SKILL.md` deve trovarsi direttamente nella cartella `quote-card-builder`.

## Requisiti

Per il flusso completo servono:

- ChatGPT o Claude con supporto alle skill locali;
- Python 3;
- un browser locale per il Visual Review Studio.

La generazione PNG usa Node.js e `sharp` quando sono già disponibili nella sessione. La skill non installa dipendenze automaticamente. Se non trova un convertitore PNG compatibile, conserva l’SVG e dichiara il fallback invece di simulare una consegna riuscita.

Il server dell’editor ascolta soltanto su `127.0.0.1` e usa un token di sessione. La fonte, i font, i loghi e le dimensioni restano protetti nell’interfaccia; l’utente può modificare esplicitamente la palette della card con i controlli colore.

## Problemi comuni

### Codex non trova `$quote-card-builder`

Controlla che il percorso termini esattamente con `quote-card-builder/SKILL.md`. Poi riavvia Codex o apri una nuova task.

### L’editor non si apre

Verifica che Python 3 sia disponibile e che il browser possa aprire indirizzi locali su `127.0.0.1`. La skill deve mostrare un errore reale prima di usare un percorso alternativo.

## Verifica del download

Ogni release include `SHA256SUMS.txt`. Su macOS o Linux puoi verificare lo ZIP con:

```bash
shasum -a 256 -c SHA256SUMS.txt
```

Il risultato atteso è:

```text
quote-card-builder.zip: OK
```

## Per sviluppatori

Esegui tutti i test dalla radice del progetto:

```bash
python3 -m unittest discover -s tests -v
```

### Vertical slice MCP locale

Il repository include ora un backend MCP stdio minimo ma reale, documentato in
[references/mcp-pilot.md](references/mcp-pilot.md). Il flusso principale usa tre tool coordinati:
`quote_card_builder_open_editor` apre una sola MCP App, `preview_quote_card` aggiorna i dati
nella stessa interfaccia senza rimontarla e `produce_quote_card` genera l'SVG canonico
solo dopo il clic dell'utente su **Genera**. Se l'host dichiara che la UI non può essere montata,
`quote_card_builder_headless` offre una preview accessibile al modello e una produzione esplicita,
vincolata all'approvazione del chiamante e all'hash della preview corrente. Prima della chiamata la
skill apre l'editor con il testo selezionato e usa attribuzione fornita/verificata oppure nessuna;
la palette neutra è predefinita salvo scelta personalizzata esplicita. Per un link usa la lettura
dell'host, perché il server non acquisisce URL. Le modifiche successive passano dal tool di update
revisionato, che preserva i campi non modificati. Non chiede tono o stile e non usa file locali o generazione immagini. La UI lascia scegliere Blocks, Cutouts, Constellations o
Gradient e consente di variare o nascondere il pattern. Uno stile già dichiarato dall'utente è solo
una preselezione dell'editor. I tool riusano il renderer canonico e il profilo neutro soltanto quando
l'utente lo sceglie. Lo structured output conserva stato e validazione compatti; l'SVG della UI è
nei metadati MCP e quello headless è una risorsa esplicita. Non esegue pubblicazione, storage remoto
o modifiche all'installazione personale.

La MCP App riprende ora i controlli principali del vecchio editor: toolbar per grassetto,
corsivo, sottolineato e riempimenti, riequilibrio degli a capo, quattro stili con seed
riproducibile, scala dal massimo, posizione verticale e palette esplicita. L'iframe incorpora inoltre
Barlow e Orbitron e usa la palette Plotter Bench dell'editor locale; la palette della card resta
quella del profilo neutro o personalizzato scelto dall'utente. Il vertical slice supporta
4:5 e 1:1; il formato 9:16 continua a essere gestito dal Visual Review Studio locale finché
non verrà portato nello stesso contratto MCP.

Il percorso workspace resta un ingresso vuoto per chi apre il plugin senza una citazione. Quando l'utente fornisce un link e chiede di procedere, il modello legge la fonte con la navigazione dell'host, seleziona una citazione esatta e apre un solo editor popolato. Se non fornisce un nome e la fonte non ne verifica uno, l'attribuzione resta vuota; la palette neutra è predefinita. Per modifiche successive in chat, `quote_card_builder_update_editor` riceve la bozza corrente completa, la revisione e i soli campi modificati; il server restituisce una preview aggiornata e la UI respinge aggiornamenti basati su una bozza superata. Il risultato segnala l'accettazione effettiva. La versione 1.8.10/UI v1.57 è live sul servizio remoto; bozze e modifiche non si sincronizzano tra dispositivi o conversazioni.

Per provarlo in un ambiente isolato:

```bash
uv run --frozen python -m unittest discover -s tests -v
```

Il manifest del plugin collega `.mcp.json` al server incluso; il builder mantiene
sincronizzati sorgente della skill e pacchetto plugin. Il server espone inoltre una
MCP App per la preview in una scheda contenuto, descritta nel documento del pilot; Cloud Run,
autenticazione e storage restano decisioni operative separate.

La pipeline GitHub copre Python 3.12, 3.13 e 3.14, in linea con il requisito `>=3.12,<3.15`. Il workflow di release, quando attivato da un tag, verifica la versione della skill, esegue i test di coerenza del pacchetto e prepara gli ZIP e i checksum SHA-256 per la release. Questa descrizione della pipeline non prova che una specifica versione sia stata pubblicata.

## Stili generativi nell’editor locale

Il selettore offre Blocks, Cutouts, Constellations e Gradient, con variazioni riproducibili del motivo. **Save style** e **My styles** salvano e riapplicano identità visiva, famiglia e seed alla citazione corrente. I motivi precedenti restano compatibili. Contratto e archivio locale: [generative-styles.md](references/generative-styles.md).

## Licenze dei font

I font incorporati nell’interfaccia sono accompagnati dalle rispettive licenze OFL nella cartella `assets/card-editor/fonts/`.
