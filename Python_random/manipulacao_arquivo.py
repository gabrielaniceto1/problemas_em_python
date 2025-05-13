cont=0
lista=[]
file=open("arquivo1.txt", "r")

for i in file:
    i=float(i)
    lista.append(float(i))
file.close()

for i in range(len(lista)):
    if lista[i]>lista[i-1]:
        cont+=1
        
print(f"A quantidade de numeros maiores que o anterior foi de {cont}")