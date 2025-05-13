import os
os.system("cls")

def contador(frases):
    for frase in frases:
        # Divide a frase em palavras
        palavras = frase.split()
        # Gera uma lista com os tamanhos de cada palavra
        tamanhos = [str(len(palavra)) for palavra in palavras]
        # Exibe os tamanhos com '-' como separador
        print('-'.join(tamanhos))

# Lista para armazenar as frases e variável para a maior palavra
lista = []
maior_palavra = ""

while True: 
    palavra = input()
    # Condição de parada
    if palavra == "0":
        break

    # Adiciona à lista e verifica a maior palavra
    lista.append(palavra)
    palavras_da_frase = palavra.split()
    for p in palavras_da_frase:
        if len(p) >= len(maior_palavra):
            maior_palavra = p

# Processa e imprime os tamanhos das palavras de cada frase
contador(lista)
print(f"The biggest word: {maior_palavra}")
