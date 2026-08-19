# Quote Card Builder

Quote Card Builder è una skill per Codex che trasforma una frase, un testo, un URL, un documento o un’idea in una quote card pronta da condividere.

È pensata per creator, marketer e professionisti che vogliono ottenere rapidamente una grafica coerente, senza aprire un editor professionale. Il testo, l’attribuzione e le scelte editoriali restano sempre sotto il controllo dell’utente.

Versione corrente: **1.5.0**

## Che cosa fa

La skill accompagna l’utente dall’idea al file finale:

1. legge il materiale disponibile o parte da una frase già scelta;
2. propone fino a tre candidati quando serve trovare la formulazione più efficace;
3. distingue il testo originale da una modifica, una parafrasi o una frase generata;
4. mantiene separati fonte, attribuzione e identità del brand;
5. apre un editor locale per controllare testo, a capo, stile e formato;
6. verifica leggibilità, contrasto, margini e possibili sovrapposizioni;
7. genera un PNG oppure un pacchetto ZIP con più formati.

L’editor offre tre stili compositivi:

| Stile | Aspetto | Motivi disponibili |
| --- | --- | --- |
| **Editorial** | pagina aperta e tipografia editoriale | Contours, Rhythm Lines |
| **Poster** | testo dominante e impatto da manifesto | Echo Rings, Modules |
| **Frame** | contenuto inserito in un campo cromatico | Dot Grid, Route Map |

Ogni stile può essere usato anche senza motivo.

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
- scegliere Editorial, Poster o Frame;
- applicare uno dei motivi disponibili oppure nasconderlo;
- modificare gli a capo;
- usare grassetto, corsivo, sottolineato, evidenziato, accento o contorno;
- ridurre la dimensione del testo e scegliere la posizione verticale;
- mostrare o nascondere il logo;
- salvare il brand corrente come profilo riutilizzabile;
- esportare in `4:5`, `1:1`, `9:16` oppure in tutti i formati.

L’alt text viene creato automaticamente. Se serve correggerlo, il campo facoltativo si trova nel pannello **Accessibilità**.

Quando premi **Genera**, l’interfaccia mostra il nome del file, una cartella abbreviata, il comando per copiare il percorso completo e l’azione per tornare alla task Codex.

## Profili riutilizzabili

Apri **Palette della card** e scegli **Salva profilo** per conservare il brand corrente. Il profilo include soltanto:

- nome del brand;
- quattro colori della card;
- famiglia e file del font;
- file del logo.

Citazioni, fonti, attribuzioni e alt text non vengono salvati nel profilo. Nei lavori successivi la skill elenca i profili locali disponibili e ne usa uno solo dopo la tua scelta esplicita.

I profili restano sul computer in:

```text
~/.quote-card-builder/profiles.json
```

Questa cartella è separata dall’installazione della skill: aggiornare Quote Card Builder non elimina i profili. Se sposti o cancelli font e loghi collegati, la skill segnala gli asset mancanti prima di usarli.

## Installazione semplice

### Prima installazione su macOS

1. Apri la pagina delle [release](https://github.com/vincos73/quote-card-builder/releases/latest).
2. Scarica il file `quote-card-builder.zip` dalla sezione **Assets**.
3. Fai doppio clic sullo ZIP per estrarlo.
4. Nel Finder scegli **Vai > Vai alla cartella…**.
5. Incolla `~/.codex/skills` e premi Invio.
6. Sposta nella cartella `skills` la cartella estratta e chiamala `quote-card-builder`.
7. Chiudi e riapri Codex, oppure avvia una nuova task.

L’installazione è corretta se questo file esiste:

```text
~/.codex/skills/quote-card-builder/SKILL.md
```

Attenzione a non creare un livello in più, per esempio `quote-card-builder/quote-card-builder/SKILL.md`: in quel caso Codex potrebbe non trovare la skill.

### Aggiornamento di una versione esistente

1. Chiudi le task che stanno usando Quote Card Builder.
2. Rinomina la cartella attuale `quote-card-builder` in `quote-card-builder.backup`.
3. Installa la nuova cartella seguendo i passaggi precedenti.
4. Avvia una nuova task e controlla la versione in `SKILL.md`.
5. Quando la nuova versione funziona, puoi conservare o eliminare il backup.

Questo metodo evita di lasciare file appartenenti a versioni precedenti dentro la nuova installazione.

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

- Codex con supporto alle skill locali;
- Python 3;
- un browser locale per il Visual Review Studio.

La generazione PNG usa Node.js e `sharp` quando sono già disponibili nella sessione. La skill non installa dipendenze automaticamente. Se non trova un convertitore PNG compatibile, conserva l’SVG e dichiara il fallback invece di simulare una consegna riuscita.

Il server dell’editor ascolta soltanto su `127.0.0.1` e usa un token di sessione. Fonte, brand e dimensioni sono campi protetti nell’interfaccia.

## Dove vengono salvati i file

Il percorso dipende dalla task e dalla cartella di lavoro. Dopo la generazione, l’editor mostra:

- lo stato della produzione;
- il nome dell’artefatto;
- il percorso locale assoluto;
- un collegamento per aprire o scaricare il file.

Un singolo formato produce normalmente un PNG. L’opzione **Tutti** produce un solo ZIP con i tre rapporti, le miniature e una scheda di contatto.

## Problemi comuni

### Codex non trova `$quote-card-builder`

Controlla che il percorso termini esattamente con `quote-card-builder/SKILL.md`. Poi riavvia Codex o apri una nuova task.

### L’editor non si apre

Verifica che Python 3 sia disponibile e che il browser possa aprire indirizzi locali su `127.0.0.1`. La skill deve mostrare un errore reale prima di usare un percorso alternativo.

### Vedo un SVG invece di un PNG

Il convertitore PNG non era disponibile. Installa o rendi disponibili Node.js e `sharp` nell’ambiente usato da Codex, quindi ripeti la generazione.

### Non trovo il file generato

Leggi la voce **Salvato in** mostrata al termine della generazione. Contiene il percorso completo, non soltanto il nome del file.

### Un motivo invade il testo

Riduci la scala del testo o prova un’altra posizione. Preview, controllo qualità ed export usano lo stesso calcolo; se una sovrapposizione reale resta nella card, la generazione deve essere bloccata.

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

La pipeline GitHub esegue la suite su Python 3.10, 3.11, 3.12 e 3.13. Il workflow di release controlla che il tag coincida con la versione dichiarata in `SKILL.md`, crea `quote-card-builder.zip` e pubblica il checksum SHA-256.

## Licenze dei font

I font incorporati nell’interfaccia sono accompagnati dalle rispettive licenze OFL nella cartella `assets/card-editor/fonts/`.
