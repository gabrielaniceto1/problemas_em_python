cont=0
cont_incorreto=0
cont_esq=0
cont_dir=0

while cont<10:
    cont=cont+1
    direcao=input("digite a direção utilizando (E ou Esq ou Esquerda) para esquerda e (D ou Dir ou Direita) para direita: ")
    if direcao=='D' or direcao=='Dir' or direcao=='Direita':
        cont_dir=cont_dir+1
    elif direcao=='E' or direcao=='Esq' or direcao=='Esquerda':
        cont_esq=cont_esq+1
    else:
        cont_incorreto=cont_incorreto+1

print(f"A quantidade de curvas a esquerda foi de {cont_esq}. A quantidade de curvas a direita foi de {cont_dir}. E a quantidade de eincorretas foi de {cont_incorreto}.")