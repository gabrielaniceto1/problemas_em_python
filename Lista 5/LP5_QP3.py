import os 
os.system("cls")

def contador(a):
    a.split()
    
    for i in range(len(a)-1):
        if i<a:
            print(f"/n{a}-")
        elif i==a:
            print(f"/n{a}")

lista=[]
maior=""

while True: 
    palavra=input()
    lista.append(palavra)

    if len(palavra)>len(maior):
        maior=palavra

    if palavra=="0":
        break

for i in range(len(lista)-1):
    x=lista[i]
    print(f"{contador(x)}")
print(maior)