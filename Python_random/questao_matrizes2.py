import os
os.system("cls")

matriz=[[],[],[]]
diagonal=[]
multiplicacao=1
cont=0
soma=0
c2=[]
vetor=[]
for l in range(3):
    for c in range(3):
        matriz[l].append(int(input(f"Insira os valores da matriz na posição : linha {l} coluna {c} \n")))
        cont+=1
        soma+=matriz[l][c]
    
        if l==c:
            multiplicacao=multiplicacao*matriz[l][c]
            
        if c==1:
            c2.append(matriz[l][c])

media=soma/cont   

for l in range(3):
    for c in range(3):
        print(f"[{matriz[l][c]}]", end=" ")
        if matriz[l][c]<=media:
            vetor.append(matriz[l][c])
    print()
    
while True:
    acao=int(input("Digite: \n1 - produto dos elementos da diagonal principal \n2 - media de todos os elementos da matriz \n3 - maior valor da segunda coluna \n4 - exibir os valores menores ou iguais a media \n0 - parar\n"))
    if acao==1:
        print(f"O produto dos elementos da diagonal principal é {multiplicacao}")
    elif acao==2:
        print(f"A media de todos os elementos é {media}")
    elif acao==3:
        print(f"O maior valor da segunda coluna é {max(c2)}")
    elif acao==4:
        print(f"os valores menores ou iguais a media são {vetor}")
    elif acao==0:
        break