# Nastri — contratto del pacchetto web MCP

Questa guida riguarda il server web 1.8.11 e la risorsa MCP App v1.58. Il Visual Review Studio locale usa un manifest differente: non inviare tutto quel manifest al tool web. Verificare il badge dell'editor e lo stato effettivo del servizio prima di attribuire queste capacità a un client.

## Input e stato della card

I tool ricevono `text`, `attribution` opzionale, `palette` opzionale (`name`, `colors` con primary/accent/background/text esadecimali), `format` 4x5/1x1/9x16 e i campi seguenti allo stesso livello:

- `visual_grammar: "ribbons"`; null lascia gli stili precedenti.
- `composition`: scena nativa scelta; `composition_candidates`: fino a tre scene con ID distinti.
- `proposal_source: "model"` per scene progettate dal modello; "demo" per prove deterministiche.
- `quote_font_size`, `author_font_size`: pixel della canvas da 1440 px, da 8 a 720; null indica Auto. Una dimensione manuale resta invariata anche quando produce un avviso.
- `styles`: intervalli Unicode start/end/type nel testo esatto, newline inclusi. Tipi bold, italic, underline, highlight, accent, outline; size aggiunge `scale`, da 0.5 a 2.5. Usare scale solo per size.
- `lines`: a capo che ricostruiscono esattamente la frase, senza cambiarne le parole. Per Nastri i paragrafi possono essere avvolti nella zona assegnata dal renderer.

Le risposte conservano lo snapshot completo, la revisione e le scene. Non includere SVG grezzi nella scena: la geometria è composta da numeri, il server disegna e valida l'SVG.

## Scena nativa

Ogni scena richiede `version: 1`, `id` ASCII distinto e può avere `name` breve. Sono obbligatori:

- `quote_box`, `author_box`, `logo_box`: oggetti x/y/width/height fra 0 e 1, con dimensioni positive e area dentro la canvas. Riservare author_box anche quando manca l'autore. Il web attuale lascia il logo nascosto; logo_box conserva lo spazio nella grammatica, non promette caricamento di un logo.
- `background_role`, `text_role`, `highlight_role`: ciascuno è primary, accent, background o text. Assegnare i ruoli alla palette scelta senza inventare altri colori.
- `ribbons`: da 1 a 8 oggetti con id, color_role, width_ratio e points. width_ratio è fra 0.015 e 0.3 rispetto alla larghezza. points contiene 1+3n coppie [x,y], da 4 a 37 punti, coordinate fra −0.5 e 1.5. Dopo il punto iniziale ogni terna indica due controlli e un punto finale di una curva cubica.
- `crossings`: fino a 32 oggetti over/under/segment/t. over e under sono ID distinti di nastri presenti; segment è l'indice del segmento cubico del nastro superiore e t è fra 0 e 1. Dichiarare incroci geometrici reali.

Progettare percorsi che convivano con le zone di lettura. Le maschere di protezione del renderer non sostituiscono una buona composizione. Non usare un singolo esempio come template obbligatorio: il modello può variare numero, percorso, spessore, incroci, ritaglio ai bordi e collocazione di testo e autore.

## Tre proposte diverse e riuso

Le tre proposte condividono citazione, palette e grammatica; cambiano almeno struttura spaziale, curva dominante e relazione tra nastri. Si possono esplorare un campo laterale, un intreccio superiore oppure un'apertura centrale, senza imporre questa terna a tutte le frasi. Una citazione lunga richiede più area di testo; una breve può avere una curva più dominante e una gerarchia monumentale. Il renderer misura, avvolge e segnala i limiti senza riscrivere la frase.

Nel web, **Save Nastri base** conserva lo snapshot della card: palette, scena, preferenze grafiche, citazione, attribuzione, formattazioni e alt text. Non promettere che escluda il contenuto. **Reuse this card** mantiene la composizione; con una frase nuova azzera le selezioni precedenti, riparte con dimensione automatica della citazione e stato USER_SUPPLIED e usa l’autore del campo facoltativo nel dialogo di riuso. Questo campo può essere precompilato dall’autore della card aperta e può essere svuotato per eliminare l’attribuzione; non dichiarare che l’autore venga sempre cancellato automaticamente. Con frase invariata conserva gli intervalli manuali. **Create in this style · demo** può proporre variazioni dimostrative dall’editor; il modello può progettare tre scene nuove dalla base e mandarle come composition_candidates/proposal_source model tramite l’update revisionato. `reuse_composition` è un input di supporto alle prove deterministiche: non è una chiamata creativa al modello.

**Export project JSON** conserva la card completa per trasferirla esplicitamente. Il formato web è distinto dalla base di stile del Visual Review Studio locale, che esclude citazione e selezioni; non trattare i due file come intercambiabili.

Nel follow-up copiare `base_snapshot` e `base_revision` dallo stato corrente; mettere solo cambiamenti espliciti in `patch`. Per sostituire la frase, mantenere geometria e palette desiderate ma azzerare i vecchi styles/lines e usare trasformazione EDITED e prova UNVERIFIED salvo nuova verifica. Con frase invariata preservare gli intervalli manuali. Non applicare in silenzio una ricomposizione sopra le correzioni dell'utente.

Le basi restano nel dispositivo/client. L'export JSON permette il trasferimento esplicito, senza dipendenze da percorsi di font locali. Nastri usa Barlow incorporato per misurazione ed esportazione coerenti; gli stili precedenti conservano la loro tipografia. Il web non offre ancora un brand kit completo con upload di font e logo. Palette e geometria sono riusabili; non presentare questa prima prova come archivio cloud di brand.

## Anteprima, avvisi e PNG

La galleria usa gli stessi dati nativi della card selezionata; gli SVG delle anteprime viaggiano nei metadati MCP. Una scena valida può avere avvisi visivi: essi sono solo descrizioni, non bloccano preview o produzione. I controlli tecnici e l'hash della preview corrente continuano a proteggere la corrispondenza fra card scelta e output. Download PNG esporta la card corrente nel formato selezionato, senza passaggi di correzione obbligatori.
