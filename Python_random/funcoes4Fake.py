lista=[]
for i in range(10):
    lista.append(int(input("Digite uma valor: ")))
limitem=int(input("Digite o valor do limite menor: "))
limiteM=int(input("Digite o valor do limite maior: "))
for i in lista:
    if lista[i]>=limitem and lista[i]<=limiteM:
        print(lista[i])