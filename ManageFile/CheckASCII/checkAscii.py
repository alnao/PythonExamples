import os

def check_non_ascii(file_path):
   with open(file_path, 'r', encoding='utf-8') as file:
       for line_num, line in enumerate(file, 1):
           non_ascii_chars = []
           for pos, char in enumerate(line):
               if not char.isascii():
                   non_ascii_chars.append((pos, char, ord(char)))
           
           if non_ascii_chars:
               print(f"\nRiga {line_num}:")
               print(f"Testo: {line.strip()}")
               print("Caratteri non ASCII trovati:")
               for pos, char, code in non_ascii_chars:
                   print(f"  Posizione {pos}: '{char}' (Unicode: {code})")


if __name__ == '__main__':
    # Ottiene il percorso della directory dove si trova lo script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'file.txt')

    try:
        check_non_ascii(file_path)
        print("\nScansione completata!")
    except FileNotFoundError:
        print(f"File {file_path} non trovato.")
    except Exception as e:
        print(f"Errore durante la lettura del file: {e}")