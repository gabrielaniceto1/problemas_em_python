import os
os.system("cls")

cont1=0
cont2=0
cont3=0
cont4=0
print("Digite o codigo do serviço usando: ")
for i in range(1,6,1):
    servico=int(input('\n1-banho \n2-tosa \n3-banhgo e tosa \n4-outro \n'))
    if servico==1:
            cont1+=1
    elif servico==2:
          cont2+=1
    elif servico==3:
          cont3+=1
    elif servico==4:
          cont4+=1
print(f"A quantidade de: \nBanhos: {cont1} \nTosa: {cont2} \nBanho e Tosa: {cont3} \nOutro: {cont4}")