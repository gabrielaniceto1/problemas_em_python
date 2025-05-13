import os
os.system("cls")

def eu(limI,limS,lista):
    lista2=[]
    for i in lista:
        if i>=limitem and i<=limiteM:
            lista2.append(i)
    return lista2
            
lista=[]
for i in range(10):
    lista.append(int(input("Digite uma valor: ")))
limitem=int(input("Digite o valor do limite menor: "))
limiteM=int(input("Digite o valor do limite maior: "))

print(eu(limitem,limiteM,lista))