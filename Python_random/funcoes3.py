def perda_de_peso(a,b):
    c=a-b
    percentual=((c/a)*100)
    return percentual
peso_inicial=float(input("Digite  peso inicial: "))
peso_atual=float(input("Digite o peso atual: "))

print(f"O percentual de perda de peso foi de {perda_de_peso(peso_inicial,peso_atual):.1f}%")