# PolOCRBench: pary obraz -> tekst

Każda strona to para plików o tym samym identyfikatorze, leżących obok siebie:

- `<id>.png`: obraz strony (skan, render PDF albo zdjęcie),
- `<id>.md`: tekst wzorcowy strony w Markdown (zadanie A: pełna strona w kolejności czytania, nagłówki, listy,
  akapity; tabele jako HTML; wzory jako LaTeX w `$...$`),
- `<id>.html`: tabele strony jako HTML (zadanie B),
- `<id>.json`: pola dokumentu (zadanie C).

Układ katalogu `train/`:

| katalog | zawartość |
|---|---|
| `real/` | prawdziwe dokumenty (pisma urzędów i wnioskodawców, skany urzędowe), obraz czysty |
| `real_handwritten/` | skany archiwalne pisma ręcznego (notatki i zeszyty z matematyki, lata 50. i 60.; Archiwum Akt Nowych) |
| `real_degraded/` | te same prawdziwe strony ze zniszczonym obrazem (prześwietlenie, obrót, perspektywa, światło, rozmycie, szum, JPEG); tekst wzorcowy jak strony bazowej |
| `synthetic/A_markdown/` | strony syntetyczne do zadania A (tekst aktów prawnych złożony w stronę i zniszczony) |
| `synthetic/B_tables/` | syntetyczne tabele do zadania B |
| `synthetic/C_fields/` | syntetyczne faktury, umowy i pisma do zadania C (pola w JSON) |

Każdy katalog ma `metadata.csv` z jednym wierszem na stronę:

| kolumna | znaczenie |
|---|---|
| id | identyfikator pary |
| zadanie | A, B albo C |
| typ_dokumentu | rodzaj pisma / dokumentu |
| okres | epoka druku / pisma |
| zrodlo | adres dokumentu źródłowego (puste dla stron syntetycznych) |
| licencja | licencja tekstu; dla stron syntetycznych też licencja kroju pisma |
| zniszczenia | zniszczenia obrazu (np. przeswietlenie, obrot, rozmycie, jpeg), puste = obraz czysty |
| strona_bazowa | w `real_degraded/`: id strony z `real/`, z której powstała kopia (ten sam tekst wzorcowy) |

W tekstach wzorcowych pisma ręcznego `[?]` oznacza fragment nieczytelny na obrazie; ocena pomija go razem z
odpowiadającym mu fragmentem wyniku modelu. Tekst skreślony przez piszącego nie wchodzi do tekstu wzorcowego.

Ocena: wynik modelu dla strony porównuje się z plikiem tekstu wzorcowego tej samej pary.
Sumy kontrolne wszystkich plików: `SHA256SUMS`.
