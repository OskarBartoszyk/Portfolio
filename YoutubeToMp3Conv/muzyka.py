import os
import re
from pydub import AudioSegment
from yt_dlp import YoutubeDL

def sanitize_filename(s: str) -> str:
    """
    Zamienia wszystkie znaki poza literami, cyframi, kropką, myślnikiem i podkreśleniem
    na podkreślenie, aby uzyskać bezpieczną nazwę pliku.
    """
    return re.sub(r'[^0-9A-Za-z\.\-_]', '_', s)

def download_and_convert_to_mp3(url: str, output_name: str):
    print(f"Pobieranie: {url}")
    
   
    temp_path = "temp_audio"
    
    # Konfiguracja yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_path,
        'quiet': False,
        'no_warnings': False,
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Konwersja do MP3
        audio = AudioSegment.from_file(temp_path)
        audio.export(output_name, format="mp3")
        
        # Usunięcie pliku tymczasowego
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        print(f"Zapisano jako: {output_name}\n")
    except Exception as e:
        print(f"✖ Błąd przy przetwarzaniu {url}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise

def main():

    lista_path = "DoPobrania.txt"
    if not os.path.exists(lista_path):
        print(f"Brak pliku {lista_path}")
        return
    
    with open(lista_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    
    for url in urls:
        try:
            # Pobierz tytuł filmu jako podstawę nazwy pliku
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', url)
            
            # Utwórz bezpieczną nazwę pliku z tytułu
            base_name = sanitize_filename(title)
            output_file = f"{base_name}.mp3"
            
            download_and_convert_to_mp3(url, output_file)
        except Exception as e:
            print(f"ERROR! - Błąd przy przetwarzaniu {url}: {e}\n")

if __name__ == "__main__":
    main()