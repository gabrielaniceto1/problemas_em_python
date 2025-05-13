import os
os.system("cls")

num=int(input("Digite um numero: "))
soma=0
for i in range(1,num):
    if num%i==0:
        soma=soma+i
if num==soma:
    print("O numero é perfeito")
else:
    print("O numero não é perfeito")