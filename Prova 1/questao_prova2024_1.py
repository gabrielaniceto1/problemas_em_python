import os
os.system("cls")
vetor_nome=[]
vetor_idade=[]
maior_idade=[]
soma=0
quantidade_funcionarios=int(input("Digite a quantidade de funcionários aptos a se aposentar: "))
for i in range(quantidade_funcionarios):
    nome=input("Digite o nome do funcionário: ")
    idade=int(input("Digite a idade (em anos) do funcionário: "))
    if idade>=60:
        vetor_nome.append(nome)
        vetor_idade.append(idade)
    if idade>soma:
        soma=idade
        x=vetor_nome[i]
    #pendente
    else:
        print("Funcionario com idade abaixo do minimo. Insira outro nome e idade.")
        ##
for i in range(quantidade_funcionarios):
    print(f"Nome: {vetor_nome[i]} - idade: {vetor_idade[i]}")

media=sum(vetor_idade)/len(vetor_idade)

print(f"A media das idades é de: {media} anos e o funcionario mais idoso é: {x}")