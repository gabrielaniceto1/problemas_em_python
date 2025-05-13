import os
os.system("cls")

def converter(a):
    numeros_romanos = [(900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    b=""

    for (valor,simbolo) in numeros_romanos:
        while a>=valor:
            b+=simbolo
            a=a-valor
    return b

numero=int(input())

print(converter(numero))