# Quote Card Builder

Skill per Codex che trasforma frasi, testi, URL, documenti e idee in quote card verificabili e coerenti con un brand approvato.

## Caratteristiche

- provenienza, trasformazione e stato della prova mantenuti separati;
- tre direzioni visuali autonome: editoriale, manifesto e scheda fonte;
- editor locale con a capo manuali, righe vuote, grassetto, corsivo, sottolineato ed evidenziato;
- composizioni indipendenti `4:5`, `1:1` e `9:16`;
- consegna di tutti i rapporti oppure di un singolo formato scelto dall’utente;
- PNG come output predefinito, con SVG conservato soltanto come fallback tecnico;
- quality gate e finalizzazione con hash degli artefatti.

## Installazione

Scaricare `quote-card-builder.zip` dalla release più recente ed estrarlo nella cartella delle skill di Codex con nome `quote-card-builder`. Il file `SKILL.md` deve trovarsi direttamente nella radice della cartella installata.

## Uso

Invocare la skill con:

```text
$quote-card-builder
```

La conversione PNG usa Node.js e `sharp` quando sono già disponibili nella sessione. La skill non installa dipendenze automaticamente.

## Verifica

```bash
python3 -m unittest discover -s tests -v
```

L’editor locale si avvia soltanto su `127.0.0.1` con token di sessione e mantiene fonte, brand e dimensioni come campi protetti.

## Licenze dei font

I font incorporati nell’interfaccia sono accompagnati dai rispettivi file OFL nella cartella `assets/card-editor/fonts/`.
