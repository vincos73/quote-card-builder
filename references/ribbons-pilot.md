# Nastri: prima grammatica editabile, prototipo locale

Questo percorso riguarda il Visual Review Studio locale di questo checkout, non installato nella skill standalone attiva. La grammatica Nastri è disponibile anche nel web MCP 1.8.11/UI v1.58 attraverso un contratto distinto: vedere [ribbons-web-mcp.md](ribbons-web-mcp.md). Formati locali disponibili: 4:5, 1:1 e 9:16, singolarmente oppure insieme, con citazione e autore opzionale, kit esplicitamente scelto e geometrie SVG native. ImageGen può servire per esplorare la direzione, ma l'anteprima editabile deriva dai dati del renderer.

## Il modello progetta; il renderer misura

Il modello conserva le parole approvate, individua eventuali enfasi sensate e prepara **tre composizioni numeriche realmente differenti**. Cambiare colore o spostare lo stesso disegno di pochi pixel non basta: variare posizione del gruppo grafico, spazio occupato dal testo, percorso dei nastri e relazione fra gli incroci. Esempi: anse laterali con testo asimmetrico; intreccio in alto con testo in basso; percorsi che avvolgono un'apertura centrale. Sono esempi, non tre template obbligatori.

Il modello sceglie numero di nastri, curvature, spessori, ordine degli incroci e colori per ruolo fra quelli del kit. Non inventa colori né altera il logo. Mantiene una zona per l'autore anche quando assente. I percorsi devono aggirare citazione, autore e logo: le protezioni del renderer sono una salvaguardia, non un modo per costruire il disegno tagliando i nastri.

Il renderer valida i dati, misura il font, avvolge il testo, posiziona le enfasi e segnala overflow, collisioni o contrasto insufficiente. Le tre anteprime e la card selezionata usano gli stessi dati. Una dimensione scelta manualmente non viene rimpicciolita silenziosamente per superare il controllo.

Il controllo distingue cause geometriche e cromatiche. Tutti gli avvisi di qualità dell'editor locale sono indicazioni facoltative, senza pulsanti o inviti ad agire: contrasto, overflow e sovrapposizioni non bloccano Genera. Il report conserva gli avvisi e le scelte manuali. L'esportazione dell'editor usa `quality_policy: advisory`; i controlli tecnici sui dati, sui file e sulla possibilità effettiva di creare il PNG restano necessari. Si verificano soltanto i formati scelti in Output finale; le altre anteprime rimangono consultabili. Il rapporto diverso adatta aree normalizzate e fitting del testo, senza ritagliare il PNG originale.

Il PNG Nastri usa Chromium tramite Node/Playwright già disponibili e attende il caricamento dei font incorporati, così conserva la resa del browser. Se questa capacità manca, la conversione segnala l'errore e conserva l'SVG; non passa silenziosamente a un convertitore che sostituisce font o spazi. Gli stili precedenti mantengono il loro percorso di esportazione.

## Dati di una composizione

`presentation.visual_grammar` vale `ribbons`. `presentation.composition` conserva la scena scelta; `composition_candidates` e `proposal_source: model` appartengono alla sessione, non alla base salvata.

Ogni composizione contiene:

- `version: 1`, `id` distinto e `name` breve.
- `quote_box`, `author_box`, `logo_box`: x, y, width, height normalizzati 0–1, con aree positive dentro la card.
- `background_role`, `text_role`, `highlight_role`: primary, accent, background o text.
- `ribbons`: 1–8 oggetti con id, color_role, width_ratio (0.015–0.3 rispetto alla larghezza) e points. Ogni percorso cubico contiene 1+3n coppie x,y, da 4 a 37 punti, coordinate fra −0.5 e 1.5. Dopo il punto iniziale, ogni terna contiene due controlli e un punto finale.
- `crossings`: over, under, segment e t. over/under sono nastri esistenti distinti; segment e t (0–1) individuano la porzione superiore. Annotare incroci reali, non punti lontani dall'altro nastro.

Le dimensioni assolute opzionali `presentation.quote_font_size` e `author_font_size` sono in pixel della canvas, 8–720. Una formattazione locale `content.styles` di tipo size conserva start/end Unicode e scale 0.5–2.5; bold, italic e highlight possono sovrapporsi alla selezione. Invio conserva gli a capo manuali fra paragrafi; ciascun paragrafo viene avvolto automaticamente nello spazio disponibile. I nuovi formati condividono la larghezza della canvas iniziale, preservando il significato delle dimensioni manuali in pixel.

## Preparazione e revisione

1. Preparare il manifest locale 0.4 con fonte, dichiarazioni editoriali, testo e brand disponibili. Generare tre scene con un breve motivo per ciascuna.
2. Salvare le scene in un JSON con `composition_candidates`. Eseguire `python3 scripts/prepare_ribbon_review.py <base.json> <proposals.json> --output <review.json>`: convalida struttura e asset, preserva le parole e prepara il progetto in revisione.
3. Avviare `scripts/card_review_server.py <review.json> --session-dir <session-dir>` con il runtime PNG già disponibile, aprire l'URL locale restituito e verificare le tre card visibili. L'utente sceglie e interviene nella stessa superficie editabile.
4. Consentire grassetto, corsivo, highlight, dimensione della frase, dimensione della selezione, autore indipendente e undo/redo. La scelta visiva non produce ancora la card finale; `Genera` conserva il flusso locale esistente.

L'editor, da solo, non contiene una chiamata a un modello. Se mancano dati progettati dal modello, `/api/compositions` offre tre **proposte di prova** deterministiche etichettate. Non presentarle come ragionamento creativo del modello.

## Base personale e nuova card

**Salva base** conserva kit, grammatica, percorsi, incroci, spessori, aree e preferenze di dimensione. Non conserva la frase o le selezioni tipografiche nella base. **Scarica progetto JSON** conserva invece la card completa, testo e selezioni inclusi. Il formato portabile 1.9.0 incorpora font e logo nel brand kit e può essere importato nell’editor web. I vecchi manifest locali con percorsi restano importabili; vedere [brand kit](brand-kits.md).

**Riusa questa card** applica esattamente la composizione della base. Il testo attuale, se invariato, conserva le formattazioni. Con testo nuovo si cancellano gli intervalli della vecchia frase, la sua attribuzione se non fornita di nuovo e le prove editoriali non applicabili; la frase parte con fitting automatico.

**Crea nello stesso stile** conserva ruoli cromatici, repertorio e spessori, e prepara tre nuove disposizioni. Nel prototipo l'editor offre variazioni dimostrative. Per una vera rielaborazione, il modello legge la base, scrive tre scene nuove e le fornisce come `composition_candidates` a `/api/styles/apply` con `reuse_mode: style`, id della base, draft, testo e attribuzione disponibili. Queste proposte sono dichiarate model. L'utente sceglie di nuovo; il modello non deve sovrascrivere correzioni manuali senza richiesta.

Nuove famiglie potranno dichiarare altre geometrie e regole di riuso. Il formato Nastri e i suoi test non garantiscono già quella compatibilità.
