# Dokumentacja techniczna zamka

## Zamek wydziałowy ("back-end")
- działa z kartami `RFID 125kHz`
- manualne otwieranie (tj. przycisk wewnątrz sali):
  - wyzwalane stanem niskim na kablu sygnałowym (zwarciem z masą)
  - napięcie sterowania: `12V`, natężenie niewielkie (poniżej `1A`)
## Połączenie zamek wydziałowy - zamek KSI
- wykorzystuje mechanizm manualnego otwierania zamka wydziałowego (dzieli przewód sygnałowy z przyciskiem)
- jednocześnie nie wpływa na zachowanie wyżej wymienionego - przycisk działa bez zmian
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
- częstotliwość `13.56 MHz` (daleko poza zakresem pracy zamka wydziałowego
