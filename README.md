```
Instrukcja obsługi aplikacji "Pobieranie postów z Telegrama"

Aplikacja służy do pobierania postów z kanałów Telegrama i zapisywania ich do plików tekstowych.

**1. Przygotowanie listy kanałów:**

*   **Rekomendacja:** Utwórz *dwie* oddzielne listy kanałów w plikach `.txt`.  Możesz je podzielić tematycznie (np. "wiadomości", "sport", "technologie") lub według *political bias* (np. "prorosyjskie", "proukraińskie", "neutralne").  Taki podział ułatwi późniejszą analizę.  Każdy kanał powinien być w osobnej linii, w formacie pełnego adresu URL (np. `https://t.me/nazwa_kanalu`) lub samej nazwy (np. `nazwa_kanalu`). *Nie* dodawaj znaku '/' na końcu nazwy kanału
*   Jeśli masz kanały w formacie pełnego URL, program automatycznie usunie wszystko przed ostatnim '/' i pobierze samą nazwę kanału.

**2. Uruchomienie aplikacji:**

*   Po uruchomieniu aplikacji zobaczysz główne okno programu.

**3. Konfiguracja:**

*   **Wybór pliku z kanałami:**
    *   Kliknij przycisk "Przeglądaj...".
    *   W oknie dialogowym wybierz plik `.txt` zawierający listę kanałów.
    *   Ścieżka do wybranego pliku pojawi się w polu tekstowym.

*   **Wybór daty:**
    *   Wybierz, czy chcesz pobrać posty z "Dzisiaj" (domyślnie) czy z "Wczoraj", zaznaczając odpowiedni przycisk radiowy.

**4. Pobieranie postów:**

*   Kliknij przycisk "Rozpocznij pobieranie".
*   Aplikacja rozpocznie pobieranie postów z kanałów znajdujących się w wybranym pliku.
*   **Logi (co się dzieje):** W dolnej części okna, w polu "Logi", będą wyświetlane komunikaty informujące o postępach:
    *   Nazwa aktualnie pobieranego kanału.
    *   Liczba pobranych postów z danego kanału.
    *   Treść pobranych postów (wraz z linkiem).
    *   Ewentualne komunikaty o błędach.
*   Proces pobierania może chwilę potrwać, w zależności od liczby kanałów i postów.  Nie zamykaj okna programu, dopóki proces się nie zakończy.

**5. Zapis wyników:**

*   Po zakończeniu pobierania, aplikacja automatycznie zapisze posty do pliku `.txt`.
*   Nazwa pliku wyjściowego będzie miała format: `output_NAZWA-PLIKU-Z-KANALAMI_RRRR-MM-DD.txt`, gdzie:
    *   `NAZWA-PLIKU-Z-KANALAMI` to nazwa pliku, który wybrałeś z listą kanałów (bez rozszerzenia `.txt`).
    *   `RRRR-MM-DD` to data, z której pobrano posty (rok-miesiąc-dzień).
*   Plik wyjściowy zostanie utworzony w tym samym katalogu, w którym znajduje się plik wykonywalny aplikacji (.exe) lub skrypt Pythona.
*   Komunikat o sukcesie lub błędzie pojawi się w okienku.

**6. Analiza danych z NotebookLM:**

*   **Kluczowy Krok:** Po pobraniu danych (plików `output_*.txt`), możesz skorzystać z *NotebookLM* od Google, aby efektywnie analizować zgromadzone informacje. NotebookLM działa jak RAG (Retrieval-Augmented Generation), co oznacza, że możesz "rozmawiać" ze swoimi danymi.
*   **Jak używać NotebookLM:**
    1.  Prześlij pobrane pliki `.txt` do NotebookLM jako źródła.
    2.  NotebookLM przetworzy te pliki i pozwoli Ci zadawać pytania w języku naturalnym dotyczące ich treści.
    3.  Możesz poprosić o streszczenia, analizę sentymentu, wyszukiwanie konkretnych informacji, porównywanie treści z różnych kanałów, identyfikację trendów, a nawet generowanie nowych tekstów na podstawie pobranych danych.
    4. Używaj notatnika do zadawania pytań do przesłanych plików.

*   **Zalety analizy w NotebookLM (RAG):**
    *   **Kontekst:** NotebookLM analizuje Twoje pytania w *kontekście* przesłanych danych. Odpowiedzi są oparte *bezpośrednio* na informacjach z plików, co minimalizuje ryzyko halucynacji (wymyślania informacji przez model językowy).
    *   **Precyzja:** Możesz odwoływać się do konkretnych fragmentów tekstu, co ułatwia weryfikację informacji i śledzenie źródeł.  NotebookLM potrafi wskazać, skąd pochodzi dana odpowiedź.
    *   **Wydajność:** Nie musisz ręcznie przeszukiwać setek postów. NotebookLM robi to za Ciebie, oszczędzając Twój czas i wysiłek.
    *   **Głębsza analiza:** Dzięki możliwości zadawania pytań i generowania podsumowań, możesz uzyskać znacznie głębszy wgląd w dane niż przy tradycyjnej analizie. Możesz odkrywać ukryte wzorce, powiązania i trendy, które inaczej mogłyby Ci umknąć.
    *   **Interaktywność:** NotebookLM pozwala na dynamiczną interakcję z danymi.  Możesz na bieżąco modyfikować swoje zapytania i uzyskiwać natychmiastowe odpowiedzi.
    * **Bezpieczeństwo:** NotebookLM, używając jako źródła informacji przesłanych plików, nie czerpie informacji z niepewnych źródeł.

**Dodatkowe uwagi:**

*   Upewnij się, że masz stabilne połączenie z Internetem podczas pobierania postów.
*   W przypadku bardzo dużej liczby kanałów lub postów, pobieranie może zająć więcej czasu.
*   Jeśli wystąpi błąd, sprawdź treść komunikatu w polu "Logi" i upewnij się, że podana nazwa kanału jest poprawna.
* Program korzysta z biblioteki `accless-tg-scraper` która działa bez używania oficjalnego API Telegrama.

Dzięki tej instrukcji i wykorzystaniu NotebookLM, proces zbierania i analizy danych z Telegrama stanie się znacznie prostszy i bardziej efektywny.
