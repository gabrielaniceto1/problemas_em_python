import os
os.system("cls")

def nmr_palavras(frase):
    frase1 = len(frase.replace(" ",""))
    return frase1

frase=input("Digite uma frase: ")
print(f"A frase tem {nmr_palavras(frase)} letras")
