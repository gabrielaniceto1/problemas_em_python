import os 
os.system("cls")

def contador(a):
    for i in range(len(a)):
        vetor=a[i]
        vetor.split()
        for j in range(len(vetor)):
            if j<len(vetor):
                print(f"{len(vetor[j])}-", end="")
            elif j==len(vetor):
                print(f"{len(vetor[j])}")

lista=[]
maior=""

while True: 
    palavra=input()
    lista.append(palavra)

    if len(palavra)>len(maior):
        maior=palavra

    if palavra=="0":
        break

contador(lista)
print(f"The biggest word: {maior}")