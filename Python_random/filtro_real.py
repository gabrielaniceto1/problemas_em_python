def filtrar_tempo(lista):
    return float(lista[2])

def filtrar_distancia(lista):
    return float(lista[3])

def filtragem(modo, reverso):
    with open(r"data\treinos.csv", "r", encoding="utf8") as file:
        linhas = file.read().split("\n")[1:]

        for i in range(len(linhas)):
            linhas[i] = linhas[i].split(",")

        if modo == 1:
            linhas.sort(key=filtrar_tempo, reverse=reverso)
        else:
            linhas.sort(key=filtrar_distancia, reverse=reverso)

        for linha in linhas:
            print(", ".join(linha))

def menu_filtragem():
    import csv
    import os
    while True:
        modo =int(input("Gostaria de filtrar por:\n1 - Tempo\n2 - Quilometragem\n"))

        reverso =int(input(f"""
1 - Crescente
2 - Decrescente
"""))
        
        filtragem(modo, True if reverso == 2 else False)
        
if __name__ == "__main__":
    menu_filtragem()