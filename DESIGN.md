---
name: "Quote Card Builder — Plotter Bench C2"
description: "Un banco di composizione calibrato per dichiarare, verificare visivamente e approvare quote card."
colors:
  aubergine-chrome: "#2b1830"
  aubergine-deep: "#1b121f"
  aubergine-raised: "#35203b"
  concrete-bed: "#cdd5cf"
  concrete-light: "#e7e9e5"
  chartreuse-signal: "#b9d936"
  chartreuse-dark: "#6f8217"
  lavender-guide: "#8c77a1"
  lavender-light: "#d8cedb"
  instrument-ink: "#171619"
  paper-ink: "#252328"
  danger-coral: "#ff8b77"
  seam-dark: "rgba(216, 206, 219, .24)"
  seam-strong: "rgba(216, 206, 219, .48)"
  seam-light: "rgba(23, 22, 25, .22)"
typography:
  display:
    fontFamily: "QCB Orbitron, QCB Barlow, Arial Narrow, sans-serif"
    fontSize: "21px"
    fontWeight: 750
    lineHeight: 1
    letterSpacing: ".045em"
  body:
    fontFamily: "QCB Barlow, Helvetica Neue, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "IBM Plex Mono, SFMono-Regular, Cascadia Mono, Roboto Mono, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: ".03em"
  metadata:
    fontFamily: "IBM Plex Mono, SFMono-Regular, Cascadia Mono, Roboto Mono, Consolas, monospace"
    fontSize: "10px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: ".025em"
rounded:
  square: "0"
spacing:
  micro: "6px"
  compact: "10px"
  control: "13px"
  rail: "16px"
  chrome: "18px"
  identity: "28px"
components:
  format-tab:
    backgroundColor: "transparent"
    textColor: "{colors.lavender-light}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "0 8px"
    height: "38px"
  format-tab-selected:
    backgroundColor: "rgba(185, 217, 54, .035)"
    textColor: "{colors.chartreuse-signal}"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "0 8px"
    height: "38px"
  field:
    backgroundColor: "{colors.aubergine-chrome}"
    textColor: "#f5f0f6"
    typography: "{typography.label}"
    rounded: "{rounded.square}"
    padding: "9px 10px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.lavender-light}"
    typography: "{typography.metadata}"
    rounded: "{rounded.square}"
    padding: "0 11px"
    height: "34px"
  button-generate:
    backgroundColor: "{colors.chartreuse-signal}"
    textColor: "{colors.instrument-ink}"
    typography: "{typography.display}"
    rounded: "{rounded.square}"
    padding: "0 11px"
    height: "34px"
---

# Design System: Quote Card Builder — Plotter Bench C2

## Overview

**Creative North Star: "Il banco plotter editoriale"**

Quote Card Builder mette la prova renderizzata su uno strumento di misura, non dentro un mini-Canva e non dentro una dashboard a schede. Il mondo è tech-industriale e deliberatamente piatto: chrome melanzana quasi nero, letto di cemento freddo, linework da officina, guide lavanda e chartreuse usato come segnale raro. La topologia rende leggibile il lavoro in un colpo d’occhio: testata quieta, grande piano calibrato con prova dominante, rail strumenti compatto e ledger di audit persistente.

L’interfaccia serve un flusso preciso: osservare lo SVG prodotto dal renderer, modificare contenuto e dichiarazioni editoriali, regolare la composizione, verificare il quality gate tecnico, quindi generare. La C2 implementata nei riferimenti desktop e mobile espone una sola CTA produttiva e ha concluso la verifica funzionale desktop/mobile con disposizione **ship**.

**Key Characteristics:**

- plotter bench piatto, ortogonale e misurabile, costruito con HTML, CSS, SVG inline e geometria;
- card server-side al centro, sempre distinta dalla strumentazione che la circonda;
- chartreuse riservato a selezione, stato valido e approvazione;
- Orbitron per il nome del prodotto, Onest per la firma `by`, Barlow per UI e azioni, mono tecnico per controlli, misure e audit;
- dichiarazioni dell’utente e QA persistenti nel ledger inferiore;
- composizione desktop-first che diventa un banco verticale completo su mobile.

## Colors

La palette contrappone chrome melanzana e superfici di cemento, con lavanda per orientamento e chartreuse per le sole decisioni positive.

### Primary

- **Melanzana chrome:** superficie della testata, del rail, dell’actionbar e dei campi; la variante profonda è la camera strutturale, quella rialzata è una variazione tonale locale, non una card fluttuante.
- **Chartreuse di calibrazione:** selezione attiva, check valido, valore dello slider, stato verificato e approvazione. Il tono scuro mantiene lo stesso significato sulle superfici chiare del letto.

### Secondary

- **Lavanda guida:** misure secondarie, metadati, icone, cuciture e area sicura; la variante chiara sostiene testo e linework sul chrome.
- **Corallo di errore:** unico segnale per warning, stato bloccante e messaggi non validi.

### Neutral

- **Cemento freddo:** piano di misura, righelli e sfondo della preview; la variante chiara distingue la barra strumenti senza simulare elevazione.
- **Inchiostro strumentale:** griglia, tacche, misure e testo sulle superfici chiare.
- **Inchiostro carta:** valore di zoom e microtesto ad alto contrasto sul banco.
- **Cuciture:** tre intensità semitrasparenti separano chrome e cemento con linee da un pixel.

**The Signal-Rarity Rule.** Il chartreuse non è una decorazione né un colore di riempimento generico: deve sempre significare selezione, validità o approvazione.

**The Two-Materials Rule.** Le grandi superfici appartengono al chrome o al cemento; non introdurre un terzo materiale cromatico per creare gerarchie artificiali.

## Typography

**Product Font:** QCB Orbitron variabile, usato soltanto per `Quote Card Builder`, con Barlow e Arial Narrow come fallback.

**Byline Font:** QCB Onest Medium per `by`, affiancato al lockup Vincos bianco.

**Body Font:** QCB Barlow, incorporato, con Helvetica Neue e system UI come fallback.

**Label/Mono Font:** IBM Plex Mono con fallback SFMono-Regular, Cascadia Mono, Roboto Mono, Consolas e monospace.

**Character:** Orbitron coordina il nome del prodotto con gli altri builder Vincos; Onest accompagna la firma senza competere; Barlow mantiene una voce industriale nelle informazioni leggibili e nell’azione primaria. Il mono trasforma controlli, valori, dimensioni, rapporti, revisioni e stati in dati di uno strumento calibrato.

### Hierarchy

- **Identità prodotto** (Orbitron 750, 21px desktop / 12px mobile, maiuscolo): firma la testata senza diventare un hero; `Quote Card` usa lavanda chiaro e `Builder` lavanda medio.
- **Azione di generazione** (800, 15px): unica CTA con enfasi Barlow piena e non tutta maiuscola.
- **Body UI** (400, 14px, 1.4): testo leggibile, candidato selezionato e contenuto editoriale modificabile.
- **Label strumento** (500, 11px, tracking .03em, maiuscolo): nomi dei controlli e intestazioni del rail.
- **Metadato** (400–500, 9–10px, maiuscolo quando è uno stato): misure, aiuti, formati, valori, revisione e ledger; valori numerici con cifre tabulari.

**The Instrument-Language Rule.** Usa il mono quando il testo si comporta come misura, comando o stato; usa Barlow per lettura e decisione; limita Orbitron e Onest alla firma di prodotto.

**The No-Hero Rule.** La gerarchia non usa titoli oversize: l’artefatto renderizzato, non il chrome, è il contenuto più importante della schermata.

## Layout

Il desktop è un banco a due regioni: una preview fluida con larghezza minima di 620px e un rail strumenti da 310px. La topbar misura 68px; il ledger/actionbar sticky occupa almeno 82px. Il piano contiene una barra strumenti da 48px, righello orizzontale da 38px, righello verticale da 46px, griglia maggiore da 80px e minore da 16px. La shell 4:5 usa fino al 45% del piano e 520px, resta centrata rispetto al letto utile e conserva il proprio rapporto; 1:1 e 9:16 cambiano dimensione in modo compositivo, non per crop.

Il linework è topologico: righelli e tacche definiscono il letto; quote 1080×1350 e crocini di registro definiscono la prova; la safe area è un overlay tratteggiato al 7%, attivabile senza alterare lo SVG. La actionbar divide tre responsabilità: esito QA a sinistra, ledger di dichiarazione/sessione al centro, azioni a destra.

A 1120px il rail si compatta a 290px e la quota verticale scompare. A 820px il banco diventa verticale: preview sopra, strumenti sotto, form a due colonne e ledger ridotto. A 560px il form torna a una colonna, i righelli scendono a 32×34px, la griglia maggiore a 64px e le quote scompaiono; il ledger centrale viene rimosso dalla actionbar, che mostra soltanto stato, output disponibili e `Genera`. La larghezza minima supportata è 320px.

**The Proof-Dominance Rule.** La card deve restare il maggior oggetto continuo del primo viewport; rail e ledger sono strumenti periferici, non pannelli concorrenti.

**The Independent-Formats Rule.** 4:5, 1:1 e 9:16 mantengono preview e impostazioni proprie; non simulare un formato con il ritaglio di un altro.

## Elevation & Depth

Il sistema non usa ombre per costruire gerarchia. Profondità e separazione derivano da materiali tonali, bordi da 1px, griglia, righelli, registration marks e sovrapposizione esplicita della safe area. Anche la prova resta otticamente appoggiata sul banco: il contorno sottile la delimita senza farla fluttuare.

**The Flat-Instrument Rule.** Non aggiungere box shadow, glow, gradienti, vetro o blur a chrome, campi, controlli e card; la precisione del linework sostituisce l’elevazione.

## Shapes

La forma dominante è il rettangolo ortogonale con raggio zero. Tab, campi, gruppi segmentati, CTA, status box e pannelli si congiungono tramite cuciture dritte; le icone SVG usano stroke sottile, cap quadrato e join miter. Le rare geometrie circolari appartengono a funzioni strumentali specifiche, come la manopola del range o il simbolo mobile di ripristino, e non diventano un linguaggio a pillola.

**The Square-Control Rule.** Se un nuovo controllo può essere rettangolare, resta rettangolare: non introdurre pillole o arrotondamenti morbidi per renderlo “amichevole”.

## Components

### Testata e tab formato

La testata porta `Quote Card Builder`, seguito dalla firma `by` e dal lockup Vincos bianco, più i tre tab 4:5, 1:1 e 9:16. Il nome usa Orbitron e soltanto i due lavanda della palette: chiaro per `Quote Card`, medio per `Builder`. I tab sono pulsanti nativi con `aria-pressed`; il bordo lavanda diventa chartreuse nello stato attivo, con una velatura quasi impercettibile. Su mobile titolo e firma si dispongono su due righe compatte e restano nel primo viewport.

### Letto plotter e prova SVG

Il letto di cemento combina griglia, righelli, tacche, quote e linee di registro. La preview ricevuta dal server è uno SVG reale, inserito senza reinterpretazione nella shell del formato; il renderer incorpora il font del brand, calcola il massimo tipografico compatibile con guide e aree riservate per la posizione scelta e restituisce un `viewBox` coerente. L’editor può modificare il testo attraverso il contratto revisionato, ridurre la scala dall'80% al 100% di quel massimo, mostrare guide, cambiare zoom e sovrapporre safe area/crocini, ma non deve rasterizzare o ridisegnare lo SVG.

### Rail strumenti

Il rail melanzana è una sequenza di sezioni separate da cuciture da 1px: Provenienza richiudibile, Direzione, Testo e formattazione, Scala dal massimo, Posizione, Logo, Virgolette e Quality gate. Il testo usa un editor visuale con toolbar per grassetto, corsivo, sottolineato ed evidenziato; Invio crea una riga e una riga vuota produce un'interlinea completa. Trattamento e stato della prova non sono controlli: restano informazioni persistenti nel ledger. Campi ed editor hanno fondo aubergine-chrome, raggio zero e bordo tenue; hover rafforza il bordo, focus lo porta al chartreuse. I gruppi segmentati e le direzioni condividono lo stesso stato attivo bordo+testo, senza card interne.

### Ledger di audit e actionbar

Il ledger persiste in basso e tiene visibili conteggio QA, dichiarazioni correnti, stato sessione e revisione. Il check chartreuse indica gate superato; una X corallo e messaggi espliciti indicano errore. `Genera`, unica campitura chartreuse, salva le modifiche correnti, esegue gate e renderer e, a esito positivo, mostra i link compatti ai formati prodotti.

### Stati, feedback e accessibilità

Loading attenua temporaneamente lo SVG e imposta `aria-busy`; il preview message, la lista warning e il messaggio d’azione spiegano l’esito. Le modifiche salvano una bozza locale e aggiornano l’anteprima dopo 360ms. `Genera` si disabilita durante la richiesta; conflitti di revisione, generazione pendente e QA tecnica fallita restano stati testuali e bloccanti, non soli cambi di colore.

Tutti i controlli interattivi usano elementi nativi, label o nomi accessibili. Il focus visibile è un outline chartreuse da 2px con offset 3px; gli stati selezionati aggiornano `aria-pressed`; warning e stato usano regioni live. Con `prefers-reduced-motion: reduce` transizioni e scroll animato vengono disattivati.

**The Renderer-Boundary Rule.** Il chrome misura e controlla; il renderer produce la card. Non replicare la card con HTML/CSS né applicare la palette del banco al contenuto del brand.

**The Text-Plus-State Rule.** Colore, opacità e icone rafforzano uno stato, ma testo, attributo ARIA o disabilitazione devono sempre renderlo comprensibile da soli.

## Do's and Don'ts

### Do:

- **Do** mantenere la prova SVG dominante, centrata sul letto e accompagnata da righelli, quote, griglia e area sicura.
- **Do** conservare chartreuse come segnale raro per selezione, validità e approvazione.
- **Do** usare Orbitron e Onest soltanto nella firma di testata, Barlow per UI leggibile e il mono per controlli, numeri, misure e audit.
- **Do** mantenere l’actionbar/ledger persistente e condensarlo, senza rimuoverne dichiarazione e azione primaria, sui viewport stretti.
- **Do** esporre loading, salvataggio locale, warning, conflitto, disabilitazione e successo con feedback testuale azionabile.
- **Do** preservare focus visibile, `aria-pressed`, `aria-busy`, regioni live e preferenza reduced motion.

### Don't:

- **Don't** trasformare il rail in una collezione di card, aggiungere sidebar annidate o competere con la prova nel primo viewport.
- **Don't** usare gradienti, glassmorphism, glow, box shadow, angoli morbidi, pillole o decorazioni AI generiche.
- **Don't** impiegare chartreuse per grandi superfici o testo ordinario, né corallo per messaggi non bloccanti.
- **Don't** rasterizzare lo SVG, ritagliare un formato per ottenerne un altro o modificare fonte, brand e dimensioni protette.
- **Don't** nascondere dichiarazioni e QA nell’header o in un drawer: appartengono al ledger persistente.
- **Don't** affidare selezione, validità, errore o blocco al solo colore.
