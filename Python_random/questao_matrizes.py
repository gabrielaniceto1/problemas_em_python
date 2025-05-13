import os
os.system("cls")
impar=[]
matriz=[[],[],[]]
soma=0
minimo=[]
for l in range(3):
    for c in range(3):
        matriz[l].append(int(input(f"Insira os valores da matriz na posição : linha {l} coluna {c} \n")))
        if matriz[l][c]%2!=0:
            impar.append(matriz[l][c])
        if c==0:
            soma+=matriz[l][0]
        if l==2:
            minimo.append(matriz[2][c])
for l in range(3):
    for c in range(3):
        print(f"[{matriz[l][c]}]", end=" ")
    print()

while True:
    acao=input("Digite A para: soma de todos os valores impares \nDigite B para: soma dos valores da primeira coluna \nDigite C para: menor valor da terceira linha \nDigite Z para: parar\n").upper()

    if acao=='A':
        print(f"O valor da soma dos numeros impares é de {sum(impar)}")
    elif acao=='B':
        print(f"O valor da soma da primeira coluna é {soma}")
    elif acao=='C':
        print(f"O menor valor da terceira linha é {min(minimo)}")
    elif acao=='Z':
        break