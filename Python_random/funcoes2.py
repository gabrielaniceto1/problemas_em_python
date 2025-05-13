import os
os.system("cls")

def soma(a,b):
    soma=a+b
    return soma

def subtracao(a,b):
    subtracao=a-b
    return subtracao

def multiplicacao(a,b):
    multiplicacao=a*b
    return multiplicacao

def divisao(a,b):
    if a<b:
        print("operação impossivel, insira um divisor correspondente (que seja divisivel) ao numerador")
    elif a>b:
        divisao=a/b
        return divisao

while True:
    acao=int(input("Digite o numero correspondente a acao: \n1 - Soma \n2 - Subtração \n3 - Multiplicação \n4 - Divisão \n0 - SAIR \n"))

    if acao==0:
        break

    elif acao==1:
        valor1=float(input("Digite o valor 1: "))
        valor2=float(input("Digite o valor 2: "))
        print(f"O valor da soma é de {soma(valor1,valor2)}")

    elif acao==2:
        valor1=float(input("Digite o valor 1: "))
        valor2=float(input("Digite o valor 2: "))
        print(f"O valor da subtração é de {subtracao(valor1,valor2)}")

    elif acao==3:
        valor1=float(input("Digite o valor 1: "))
        valor2=float(input("Digite o valor 2: "))
        print(f"O valor da multiplicação é {multiplicacao(valor1,valor2)}")

    elif acao==4:
        valor1=float(input("Digite o valor 1: "))
        valor2=float(input("Digite o valor 2: "))
        print(f"O valor da divisão é {divisao(valor1,valor2)}")