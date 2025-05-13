cont=0
contM=0
contF=0
somaM=0
somaF=0
quant_est=int(input("Digite a quantidade de estudantes: "))
while cont<quant_est:
    cont+=1
    genero=input("Digite o genero (utilize 'F' para frminino e 'M' para masculino): ")
    altura=float(input("Digite a altura do estudante em metros: "))
    if genero=='F':
        somaF=somaF+altura
        contF+=1
    if genero=='M':
        somaM=somaM+altura
        contM+=1
    
print(f"A media das alturas femininas é de {somaF/contF:.2} e a media do masculino é de {somaM/contM:.2}")