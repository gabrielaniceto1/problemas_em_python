import os
os.system("cls")

cont=0
ano_final=0
vel_final=0
while True:
    marca=input("Digite a marca do carro (para parar a contagem, digite 'N'):")
    if marca=='N':
        break
    else:
        cont=cont+1
    ano=int(input("Digite o ano do carro: "))
    if ano>ano_final:
        ano_final=ano
    vel=float(input("Digite a velocidade que o carro passou em km por hora: "))
    if vel>vel_final:
        vel_final=vel
print(f"A quantidade de carros foi de {cont}, o carro mais novo foi do ano de {ano_final}, e o carro mais rapido passou a {vel_final} km por hora.")