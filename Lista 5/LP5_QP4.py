import os
os.system("cls")

vitaminaC={"suco de laranja":120,
           "morango fresco":85,
           "mamao":85,
           "goiaba vermelha":70,
           "manga":56,
           "laranja":50,
           "brocolis":34
}

def contar_vitamina(a):
    separados = a.split(maxsplit=1)
    quantidade = int(separados[0])
    fruta = separados[1]

    if fruta in vitaminaC:
        valor=vitaminaC[fruta]*quantidade

    else:
        valor=0
        
    return valor

def restante_vitamina(b):

    if 110<=b<=130:
        print(f"{b} mg")

    elif b<110:
        resto=110-b
        print(f"mais {resto} mg")

    else:
        resto=b-130
        print(f"menos {resto} mg")


while True:

    total=0
    quantidade_frutas=int(input())

    if quantidade_frutas==0:
        break

    else:
        for i in range(quantidade_frutas):
            frutas=input()
            total += contar_vitamina(frutas)

        restante_vitamina(total)