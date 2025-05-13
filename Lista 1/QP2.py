import os
os.system("cls")

idade=int(input("Digite a idade do atleta: "))
if idade<=9 or idade>=19:
    print("Catégoria não registrada.")
elif idade>=10 and idade<=11:
    print("Categoria pré-mirim.")
elif idade>11 and idade<=13:
    print("Categoria mirim.")
elif idade>13 and idade<=15:
    print("Categoria infantil.")
elif idade>15 and idade<=18:
    print("Categoria juvenil.")
