# process_view
Etap II – Projekt w Python

PROJEKT SCADA – SYMULACJA INSTALACJI ZBIORNIKÓW
(PyQt5 + pygame + Tkinter + matplotlib)

============================================================
1. OPIS PROJEKTU (SCENARIUSZ)
============================================================

Projekt przedstawia symulację uproszczonej instalacji przemysłowej typu SCADA,
składającej się z czterech zbiorników: T1, T2, T3, T4 połączonych trzema rurami.

Celem aplikacji jest wizualizacja i sterowanie procesem:
- przepływu wody pomiędzy zbiornikami,
- poziomu wody,
- temperatury cieczy,
z zachowaniem realistycznej logiki procesu.

Każda rura posiada:
- jedną pompę,
- dwa zawory (łącznie 6 zaworów w systemie).

============================================================
2. WYKORZYSTANE TECHNOLOGIE
============================================================

Projekt wykorzystuje jednocześnie cztery biblioteki:

1) PyQt5
   - główny interfejs użytkownika,
   - sterowanie zbiornikami, pompami i zaworami,
   - okno alertów.

2) pygame
   - wizualizacja instalacji,
   - rysowanie zbiorników i rur,
   - animacja przepływu wody,
   - wizualizacja zaworów i pomp.

3) Tkinter
   - dodatkowe okno diagnostyczne,
   - logi zdarzeń i alarmów.

4) matplotlib
   - wykresy LIVE:
     - poziom wody (T1–T4),
     - temperatura (T1–T4).

============================================================
3. STRUKTURA PROJEKTU
============================================================

scada_project/
│
├─ main.py                 – punkt startowy aplikacji
├─ README.txt              – dokumentacja projektu
│
├─ model/
│   ├─ entities.py         – klasy: Zbiornik, Rura, Pompa, Zawór
│   └─ simulation.py      – logika symulacji i bilans przepływu
│
├─ ui/
│   ├─ main_window.py      – główne okno PyQt5
│   └─ tank_widget.py     – widget zbiornika (QPainterPath)
│
├─ viz/
│   ├─ pygame_view.py     – wizualizacja i animacje
│   └─ mpl_plots.py       – wykresy matplotlib LIVE
│
└─ log/
    └─ tk_log.py           – okno diagnostyki (Tkinter)


============================================================
4. OPIS INSTALACJI
============================================================

ZBIORNIKI (T1–T4)

Każdy zbiornik posiada:
- poziom wody (0–100%),
- temperaturę aktualną,
- temperaturę zadaną (grzanie stopniowe).

Dostępne operacje:
- Napełnij 3 s – szybkie napełnianie,
- Napełnij 15 s – napełnianie stopniowe,
- Opróżnij 3 s – szybkie opróżnianie,
- Opróżnij 15 s – opróżnianie stopniowe.


------------------------------------------------------------
RURY
------------------------------------------------------------

Połączenia:
- T1 <-> T2
- T2 <-> T3
- T3 <-> T4

Każda rura posiada widoczną animację przepływu, która uwzględnia kierunek.

------------------------------------------------------------
POMPY
------------------------------------------------------------

- jedna pompa na każdą rurę,
- szybkość działania pompy (przepływu) sterowana suwakiem,
- działanie pompy ilustrowane animacją obrotu,
- pompa nie może zostać uruchomiona, jeżeli zawory są zamknięte.

------------------------------------------------------------
ZAWORY
------------------------------------------------------------

- po dwa zawory na każdą rurę,
- sterowanie z GUI (OTWARTY / ZAMKNIĘTY),
- wizualizacja w pygame:
  - otwarty – zielony,
  - zamknięty – czerwony,
- każda zmiana stanu zaworu generuje wpis w logach.

============================================================
5.LOGIKA PRZEPŁYWU
============================================================

Przepływ wody zachodzi tylko wtedy, gdy równocześnie:
1) pompa danej rury jest włączona,
2) oba zawory tej rury są otwarte,
3) zbiornik źródłowy ma poziom > 0%,
4) zbiornik docelowy ma poziom < 100%.

Dodatkowe zasady:
- zbiornik źródłowy traci dokładnie tyle wody,
  ile zbiornik docelowy zyskuje,
- suma wody w układzie jest zachowana,
- poziom wody nie spada poniżej 0%,
- poziom wody nie przekracza 100%,
- przy poziomie 0% animacja przepływu jest wyłączana,
- generowany jest komunikat „wyłącz pompę”.


============================================================
6. ALARMY I LOGI
============================================================

Alarmy generowane są, gdy:
- poziom wody > 80%,
- poziom wody < 5%,
- temperatura > 80°C.

Informacje wyświetlane są w:
- oknie alertów (PyQt5),
- oknie diagnostycznym (Tkinter).

Logowane są również:
- zmiany stanów zaworów,
- włączenie / wyłączenie pomp,
- zmiany prędkości pomp.


============================================================
7. WYKRESY LIVE (MATPLOTLIB)
============================================================

Wyświetlane w czasie rzeczywistym:
- wykres poziomu wody (T1–T4),
- wykres temperatury (T1–T4).

Dane aktualizowane są cyklicznie w trakcie działania symulacji.


============================================================
8. INSTRUKCJA URUCHOMIENIA
============================================================

Kroki uruchomienia:
1) Rozpakuj projekt process_view
2) Otwórz Spyder
3) Ustaw katalog roboczy na folder projektu
4) Otwórz plik main.py
5) Uruchom program (Run lub runfile('main.py'))

Po uruchomieniu otworzą się:
- główne okno PyQt5,
- okno pygame (wizualizacja instalacji),
- okno Tkinter (logi),
- wykresy matplotlib LIVE.
