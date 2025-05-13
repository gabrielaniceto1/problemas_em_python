"""
 1. Importar os treinos
 2. Transformar tempo e quilometragem para float e int
 3. Criar a função para filtragem de menor e maior tempo
 4. Criar a função para a filtragem de menor e maior quilometragem
 5. Exibir para o usuario
"""

def filtragem_menor_tempo():
    import csv
    import os
    #1. Importar os treinos
    with open(r"data\treinos.csv", "r", encoding="utf8") as file:
        lista=[]
        for i in file:
            i=i.split(",")
            #2. Transformar tempo para float
            i=float(i[3])
            lista.append(i)
        lista=lista.sort()
        #3. Criar filtragem de menor tempo
        for j in file:
            for j in file:
                x=j.strip()
                x=j.split(",")
                if x[3]== lista[j]:
                    print(j)
                    #5. Exibir para o usuario

def filtrar_tempo(lista):
    return float(lista[2])

def filtragem_maior_tempo(reverso):
    import csv
    import os
    #1. Importar os treinos
    with open(r"data\treinos.csv", "r", encoding="utf8") as file:
        linhas = file.read().split("\n")[1:]

        for i in range(len(linhas)):
            linhas[i] = linhas[i].split(",")

        linhas.sort(key=lambda linha:float(linha[2]), reverse=reverso)

        texto = ""

        for linha in linhas:
            texto += ", ".join(linha) + "\n"

        print(texto)
        # for i in linhas:
        #     i=i.split(",")
        #     y=float(i[2])
        #     #2. Transformar tempo para float
        #     lista.append(y)
        #     #3. Criar filtragem de maior tempo
        # lista=lista.sort(reverse=True)
        # for j in file:
        #     for j in file:
        #         x=j.strip()
        #         x=j.split(",")
        #         if x[3]== lista[j]:
        #             print(j)
        #             #5. Exibir para o usuario

def filtragem_menor_quilometragem():
    import csv
    import os
    #1. Importar os treinos
    with open("data\treinos.csv", "r", encoding="utf8") as file:
        lista=[]
        for i in file:
            i=i.split(",")
            i=float(i[4])
            #2. Transformar quilometragem para float
            lista.append(i)
        lista=lista.sort()
        #4. Criar filtragem de menor quilometragem
        for j in file:
            for j in file:
                x=j.strip()
                x=j.split(",")
                if x[4]== lista[j]:
                    print(j)
                    #5. Exibir para o usuario

def filtragem_maior_quilometragem():
    import csv
    import os
    #1. Importar os treinos
    with open("data\treinos.csv", "r", encoding="utf8") as file:
        lista=[]
        for i in file:
            i=i.split(",")
            i=float(i[4])
            #2. Transformar quilometragem para float
            lista.append(i)
        lista=lista.sort(reverse=True)
        #4. Criar filtragem de maior quilometragem
        for j in file:
            for j in file:
                x=j.strip()
                x=j.split(",")
                if x[4]== lista[j]:
                    print(j)
                    #5. Exibir para o usuario

"""
1. função para chamar os filtros
2. iniciando loop
3. opção de tempo ou distância
4. opção para ser crescente ou decrescente
5. chamar a função 
6. correção de erros
7. encerrar o loop
"""
#1. função para chamar os filtros
def menu_filtragem():
    import csv
    import os
    #2. iniciando loop
    while True:
        #3. opção de tempo ou distância
        opcao=int(input("Gostaria de filtrar por:\n1 - Tempo\n2 - Quilometragem\n"))
        try:
            if opcao==1:
                #4. opção para ser crescente ou decrescente
                opcao2=int(input("Você gostaria da filtragem ser:\n1 - Decrescente\n2 - Crescente\n"))
                if opcao2==1:
                    #5. chamar a função
                    filtragem_maior_tempo(True)
                    #7. encerrar o loop
                    saida=input("Pressione Enter para sair: ")
                    break
                    os.system("cls")
                elif opcao2==2:
                    #5. chamar a função
                    filtragem_menor_tempo(False)
                    #7. encerrar o loop
                    saida=input("Pressione Enter para sair: ")
                    break
                    os.system("cls")
                else:
                    #6. correção de erros
                    print("Digite um numero válido.")
            
            elif opcao==2:
                #4. opção para ser crescente ou decrescente
                opcao2=int(input("Você gostaria da filtragem ser:\n1 - Decrescente\n2 - Crescente\n"))
                if opcao2==1:
                    #5. chamar a função
                    filtragem_maior_quilometragem()
                    #7. encerrar o loop
                    saida=input("Pressione Enter para sair: ")
                    break
                    os.system("cls")
                elif opcao2==2:
                    #5. chamar a função
                    filtragem_menor_quilometragem()
                    #7. encerrar o loop
                    saida=input("Pressione Enter para sair: ")
                    break
                    os.system("cls")
                else:
                    #6. correção de erros
                    print("Digite um numero válido.")

        except ValueError:
            #6. correção de erros
            print("Tente utilzar os numeros citados:")

if __name__ == "__main__":
    menu_filtragem()