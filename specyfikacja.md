# Dokumentacja techniczna zamka

## Zamek wydziałowy ("back-end")
- działa z kartami `RFID 125kHz`
- manualne otwieranie (tj. przycisk wewnątrz sali):
  - wyzwalane stanem niskim na kablu sygnałowym (zwarciem z masą)
  - napięcie sterowania: `12V`, natężenie niewielkie (poniżej `1A`)
## Połączenie zamek wydziałowy - zamek KSI
- wykorzystuje mechanizm manualnego otwierania zamka wydziałowego (dzieli przewód sygnałowy z przyciskiem)
- jednocześnie nie wpływa na zachowanie wyżej wymienionego - przycisk działa bez zmian
- w przypadku wystąpienia sytuacji awaryjnej (np. awaria zasilania, pożar itp.) układ nie wpływa na zachowanie zamka wydziałowego oraz systemów pożarowych
- konstrukcja układu pozwala mu jedynie na otwieranie drzwi za pomocą przycisku
  - nie może on w żaden sposób "zamknąć" drzwi czy w inny sposób je zablokować
  - nie może wpłynąć na działanie elektroniki zamka wydziałowego, w szczególności na jego zdolność do otwierania drzwi po przyłożeniu karty czy też zdalnego otwarcia drzwi (jeśli możliwe)
  - może jedynie w sytuacji krytycznego błędu kontrolera powodującego zablokowanie układu w pozycji "otwórz drzwi" (co jest praktycznie niemożliwe, jednakże projektując układ i przeprowadzając testy sprawdziliśmy i tą możliwość) chwilowo uniemożliwić otwarcie drzwi za pomocą przycisku - w tej sytuacji wystarczy odłączyć układ od zasilania (wtyczka zasilająca jest bezpośrednio pod przyciskiem otwierania drzwi), powoduje to natychmiastowe przywrócenie normalnej funkcjonalności zamka wydziałowego.
- pełna izolacja prądowa pomiędzy układami - na styku wykorzystano optoizolator `ILD213T` (para dioda LED - fototranzystor)
certyfikowany do napięcia `4000V` (ponad 300-krotnie przewyższającego napięcie układu)
- z uwagi na powyższe brak możliwości przenoszenia się zakłóceń lub skoków napięć pomiędzy układami
## Kontroler zamka
- komputer `Raspberry Pi Zero W`
- oprogramowanie bazuje na sprawdzonej bibliotece do obsługi komunikacji NFC (`libnfc`)
- połączenie z systemem uwierzytelnienia koła (`ERC`) przez sieć koła
## Czytnik NFC
- moduł oparty o standardowy kontroler `PN532`
- komunikacja z komputerem przez `UART/Serial`
- współpracuje z kartami w standardzie `MiFare` (w tym Elektroniczną Legitymacją Studencką)
- częstotliwość `13.56 MHz` (daleko poza zakresem pracy zamka wydziałowego)
