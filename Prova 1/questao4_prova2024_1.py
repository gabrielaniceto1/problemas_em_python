import os
os.system("cls")

corretas=0
incorretas=0
while True:
    resposta=input("Digite a resposta utilizando: \nC;Correta;Certa - Correta \nI;Incorreta;Errada - Incorreta \nSair - parar o programa\n").lower()
    if resposta=='c' or resposta=='correta' or resposta=='certa':
        corretas+=1
    elif resposta=='i' or resposta=='incorreta' or resposta=='errada':
        incorretas+=1
    else:
        break
print(f"A quantidade de respostas corretas foi de {corretas}")
print(f"A quantidade de respostas erradas foi de {incorretas}")