import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import asyncio
import threading
import queue
from datetime import date, timedelta
import os

from accless_tg_scraper import TgScraper

# --- Zmiana: przekazujemy obiekt event, który sygnalizuje przerwanie.
async def scrape_channels(channellist_file: str, offset: int, log_callback, stop_event: threading.Event) -> str:
    """
    Asynchroniczna funkcja pobierająca posty z kanałów.
    offset = 0 -> dziś
    offset = 1 -> wczoraj
    
    log_callback: funkcja do przekazywania komunikatów do GUI
    stop_event: event sygnalizujący przerwanie (z wątku GUI).
    """
    # Wylicza wybraną datę (dzisiejsza lub wczorajsza)
    selected_date = date.today() - timedelta(days=offset)
    date_str = selected_date.strftime("%Y-%m-%d")
    
    # Tworzy nazwę pliku wyjściowego: np. output_channellist_2025-03-04.txt
    base_name = os.path.splitext(os.path.basename(channellist_file))[0]
    output_file = f"output_{base_name}_{date_str}.txt"

    # Wczytuje listę kanałów
    try:
        with open(channellist_file, "r", encoding="utf-8") as infile:
            lines = [line.strip() for line in infile if line.strip()]
            channels = []
            for line in lines:
                line = line.rstrip('/')
                channel_name = line.rsplit('/', 1)[-1]
                channels.append(channel_name)
    except FileNotFoundError:
        raise FileNotFoundError("Nie znaleziono pliku z listą kanałów.")

    # Plik wyjściowy do zapisu
    with open(output_file, "w", encoding="utf-8") as outfile:
        # Dodajemy nagłówek
        outfile.write(f"###Wpisy z dnia {date_str}\n\n")

        for channel in channels:
            # --- Sprawdzamy czy nastąpiło żądanie przerwania
            if stop_event.is_set():
                log_callback("[INFO] Przerwano pobieranie postów.")
                break

            # Wysyłamy log do GUI
            log_callback(f"Pobieranie kanału: {channel}")
            outfile.write(f"Kanał: {channel}\n")

            try:
                telegram = TgScraper()
                page = await telegram.get_posts_page(channel)
                posts = page.posts

                # Filtrowanie postów z wybranej daty
                selected_posts = [p for p in posts if p.timestamp.date() == selected_date]

                msg = (
                    f"Pobrano {len(posts)} postów z kanału {channel}, "
                    f"z czego wybranych: {len(selected_posts)}."
                )
                log_callback(msg)
                outfile.write(f"Pobrano postów: {len(selected_posts)}.\n")

                for post in selected_posts:
                    # --- Ewentualnie możemy też w pętli sprawdzać stop_event,
                    #     jeżeli zależy Ci na jeszcze "dokładniejszym" zatrzymaniu.
                    post_info = f"{post.url} : {post.content}"
                    log_callback(post_info)
                    outfile.write(post_info + "\n")

                outfile.write("\n")

            except Exception as e:
                msg = f"Wystąpił błąd podczas pobierania kanału {channel}: {e}"
                log_callback(msg)
                outfile.write(msg + "\n\n")

    return output_file


def run_scraping(channellist_file: str, offset: int, log_callback, stop_event: threading.Event):
    """
    Funkcja wywołująca asynchroniczny scrape_channels w sposób synchroniczny
    (z użyciem asyncio.run). Całość będzie uruchamiana w osobnym wątku, żeby nie blokować GUI.
    """
    try:
        output_file = asyncio.run(scrape_channels(channellist_file, offset, log_callback, stop_event))
        return output_file
    except Exception as e:
        # Błędy do GUI
        log_callback(f"[BŁĄD] {str(e)}")
        raise


class TelegramScraperGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Pobieranie postów z Telegrama")

        # Zmienna na ścieżkę do pliku z listą kanałów
        self.channellist_path = tk.StringVar()

        # 0 - dziś, 1 - wczoraj
        self.date_offset = tk.IntVar(value=0)

        # Kolejka do przekazywania logów z wątku roboczego do GUI
        self.log_queue = queue.Queue()

        # Ustawia, że co 100 ms odczytuje logi z kolejki
        self.master.after(100, self.process_log_queue)

        # --- Zmienna informująca o tym, że chcemy przerwać pobieranie:
        self.stop_event = threading.Event()

        # ===== UI: Wybór pliku =====
        self.file_frame = tk.LabelFrame(master, text="Plik z kanałami")
        self.file_frame.pack(padx=10, pady=10, fill="x")

        self.file_label = tk.Label(self.file_frame, text="Wybierz plik z listą kanałów:")
        self.file_label.pack(anchor="w", padx=5, pady=5)

        self.file_entry = tk.Entry(self.file_frame, textvariable=self.channellist_path, width=50)
        self.file_entry.pack(side="left", padx=5, pady=5)

        self.browse_button = tk.Button(self.file_frame, text="Przeglądaj...", command=self.open_file_dialog)
        self.browse_button.pack(side="left", padx=5, pady=5)

        # ===== UI: Wybór daty (dziś/wczoraj) =====
        self.date_frame = tk.LabelFrame(master, text="Zakres dat")
        self.date_frame.pack(padx=10, pady=10, fill="x")

        self.today_radiobutton = tk.Radiobutton(
            self.date_frame,
            text="Dzisiaj",
            variable=self.date_offset,
            value=0
        )
        self.today_radiobutton.pack(anchor="w", padx=5, pady=2)

        self.yesterday_radiobutton = tk.Radiobutton(
            self.date_frame,
            text="Wczoraj",
            variable=self.date_offset,
            value=1
        )
        self.yesterday_radiobutton.pack(anchor="w", padx=5, pady=2)

        # ===== UI: Przycisk Start =====
        self.start_button = tk.Button(master, text="Rozpocznij pobieranie", command=self.start_scraping)
        self.start_button.pack(padx=10, pady=5)

        # --- UI: Przycisk Przerwij
        self.stop_button = tk.Button(master, text="Przerwij", command=self.stop_scraping)
        self.stop_button.pack(padx=10, pady=5)

        # ===== UI: Pole tekstowe na logi =====
        self.log_frame = tk.LabelFrame(master, text="Logi (co jest pobierane)")
        self.log_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.log_text = ScrolledText(self.log_frame, wrap="word", height=10)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

    def open_file_dialog(self):
        """
        Otwiera okno dialogowe do wyboru pliku z listą kanałów i ustawia ścieżkę w self.channellist_path.
        """
        filename = filedialog.askopenfilename(
            title="Wybierz plik z listą kanałów",
            filetypes=(("Plik tekstowy", "*.txt"), ("Wszystkie pliki", "*.*"))
        )
        if filename:
            self.channellist_path.set(filename)

    def start_scraping(self):
        """
        Metoda wywoływana po naciśnięciu przycisku 'Rozpocznij pobieranie'.
        Uruchamiamy wątek roboczy, by nie blokować GUI.
        """
        channellist_file = self.channellist_path.get().strip()
        if not channellist_file:
            messagebox.showwarning("Brak pliku", "Proszę wybrać plik z listą kanałów.")
            return

        offset = self.date_offset.get()

        # --- Resetujemy event "stop" gdy zaczynamy nowe pobieranie
        self.stop_event.clear()

        # Uruchamia wątek roboczy, w którym wykonamy run_scraping
        thread = threading.Thread(
            target=self.scrape_in_thread,
            args=(channellist_file, offset),
            daemon=True
        )
        thread.start()

    # --- Metoda wywoływana po naciśnięciu "Przerwij"
    def stop_scraping(self):
        """
        Ustawia event, aby przerwać pobieranie.
        """
        self.stop_event.set()

    def scrape_in_thread(self, channellist_file, offset):
        """
        Funkcja uruchamiana w osobnym wątku.
        """
        try:
            output_file = run_scraping(channellist_file, offset, self.log_callback, self.stop_event)
            # Po zakończeniu – w wątku głównym pokaż komunikat, tylko jeśli faktycznie coś pobrano
            if not self.stop_event.is_set():
                self.master.after(
                    0,
                    lambda: messagebox.showinfo("Sukces!", f"Zapisano posty w pliku: {output_file}")
                )
            else:
                self.master.after(
                    0,
                    lambda: messagebox.showinfo("Przerwano", "Pobieranie zostało przerwane.")
                )
        except Exception as e:
            # W razie błędu – w wątku głównym pokaż komunikat
            self.master.after(
                0,
                lambda: messagebox.showerror("Błąd", str(e))
            )

    def log_callback(self, message: str):
        # Wrzuca wiadomości do kolejki logów.
        self.log_queue.put(message)

    def process_log_queue(self):
        """
        Obsługuje nowe logi z kolejki.
        """
        try:
            while True:
                msg = self.log_queue.get_nowait()
                # Wstawia wiadomość do pola tekstowego
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)  # przewijamy na dół
        except queue.Empty:
            pass
        # Wywołanie ponownie za 100ms
        self.master.after(100, self.process_log_queue)


def main():
    root = tk.Tk()
    app = TelegramScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    # Aby uniknąć okna konsoli w Windows, zapisz plik jako .pyw
    # lub uruchamiaj go przez pythonw.exe, np.:
    # pythonw.exe twoj_skrypt.pyw
    main()
