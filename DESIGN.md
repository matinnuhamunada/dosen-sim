# DESIGN.md: slide decks for dosen-sim

Direction for talks about this project. Derived from the author's own lecture template (a
16:9 Arial deck in navy and yellow). Sizes are for a 1920 × 1080 canvas; the template was built
at 960 × 540 pt, so its point sizes are doubled here.

The template's institutional elements are used with the author's approval: the university logo
(top right of content slides, top left of the cover), the pencil sketch of the main building on
the cover, the campus photograph on section dividers, and the footer line (`ugm.ac.id`, the
university motto). Simulator screenshots and figures carry the content. Image files come from the
author's template and stay out of the repository (`data/` is git-ignored).

## Colour

| Token | Hex | Use |
| --- | --- | --- |
| navy | `#01416B` | titles, headings, table headers, the lower right-edge bar, footer rule, info-callout bar, divider band |
| yellow | `#FDD402` | title underline, the upper right-edge bar, note-callout bar, divider block |
| gold | `#B08900` | eyebrow labels above titles |
| ink | `#1B2A38` | body text |
| muted | `#5B6B7A` | captions, sources, footnotes |
| paper | `#FFFFFF` | slide background |
| info-bg | `#EDF2F6` | info callout background |
| note-bg | `#FFF8DD` | note callout background |
| note-ink | `#8A6D00` | note callout heading |
| row-alt | `#F2F6F9` | alternate table rows |
| rule | `#D5DBE1` | table and image borders |

Two accents only (navy and yellow). Yellow never carries text on white; text on yellow is navy.
Colour never carries meaning alone: a highlighted row or a callout also says why in words.

## Type

Arial throughout (regular and bold; bold italic only in the divider band).

| Role | Size | Weight | Colour |
| --- | --- | --- | --- |
| Divider / cover title | 64 px | bold | navy |
| Slide title | 48 px | bold | navy |
| Lead statement, subheading | 32 px | bold | navy |
| Body, lists | 28 px | regular | ink |
| Table text | 26 px | regular | ink (header bold white on navy) |
| Eyebrow | 24 px | bold, uppercase | gold |
| Caption, source, footer | 24 px | regular | muted (footer: navy) |

Sentence case for titles. One idea per title, stated as the finding where there is one.

## Layout (1920 × 1080)

- **Margins:** content from x 96 to x 1840; the right-edge bar occupies x 1886 to 1920.
- **Header block** (every content slide): eyebrow at top 72; title at top 104; yellow underline
  152 × 8 px at x 96, top 190. Content starts at top 250.
- **Right-edge bar:** yellow from y 0 to 610, navy from 610 to 1080, 34 px wide, pinned at x 1886.
- **Footer:** navy rule (2 px) from x 56 to 1860 at top 1004; below it at top 1018: `ugm.ac.id`
  letter-spaced left (x 96), the motto centred in bold italic navy, page number right (ends at
  x 1810). 24 px.
- **Logo:** 260 × 74 px, top right (x 1580, top 48) on content and divider slides.
- **Content area:** x 96 to 1840, y 250 to 980. Two-column slides split 55 / 45 with a 64 px gap.

## Components

- **Eyebrow:** a short uppercase label naming the block and topic, for example
  `B.2 · DATA SOURCES`. It adds information the title does not repeat.
- **Info callout:** info-bg, 8 px navy left bar, 32 px padding; optional bold navy heading, then
  body. Used for definitions and asides.
- **Note callout:** note-bg, 8 px yellow left bar; heading in note-ink. Used for the one caveat or
  takeaway that must not be missed. At most one callout of each kind per slide.
- **Tables:** header row navy with bold white text; body rows alternate paper and row-alt; 1 px
  rule borders; numbers right-aligned; a source line under the table.
- **Figures and screenshots:** `object-fit: contain` on white with a 1 px rule border; the title
  states what the figure shows; a source or seed line under it.
- **Section divider:** left panel 632 × 792 with the campus photograph (cover crop); below it a
  yellow block (0 to 632, y 792 to 1080) with `ugm.ac.id` in navy; a navy band (632 to 1920) with
  the motto in bold italic white. Title (64 px bold navy, `Block A` on its own line) at x 742, top 260;
  a 28 px navy lead below.
- **Cover:** the pencil sketch full-bleed (it fades to white on the right), the logo top left, the
  right-edge bar, title block at x 990: title 52 px bold navy, yellow underline, then course-style details (venue or
  status, date, author, contact) in 28 px navy.

## Writing rules (from anti-slop, applied while writing)

- No em dashes; use a colon, comma or full stop.
- No buzzwords, no hype, no signposting ("let's dive in"), no "not X but Y" drama.
- No emoji and no decorative icons. Real screenshots and figures only.
- Every number has a source on the slide (data, payslip, user estimate, or model run with seeds);
  placeholders are labelled as placeholders. No invented figures or quotes.
- Chart and table titles say what they show.
- Speaker notes carry the spoken explanation; slides carry the claim and the evidence.
- The template's small uppercase eyebrow labels are kept on purpose (author's template), against
  anti-slop's general advice on tracked uppercase labels.
