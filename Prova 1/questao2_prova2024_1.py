import os
os.system("cls")

matriz=[[],[],[],[],[]]
menor_tempo1=[]
menor_tempo2=[]
menor_tempo3=[]
menor_tempo=10000
for l in range(5):
    for c in range(3):
        matriz[l].append(float(input(f"Digite o tempo (em segundos) do competidor {l} na etapa {c} \n")))
        if c==0:
            menor_tempo1.append(matriz[l][c])
            if matriz[l][c]<menor_tempo:
                menor_tempoA=l
                competidor1=menor_tempoA
        elif c==1:
            menor_tempo2.append(matriz[l][c])
            if matriz[l][c]<menor_tempo:
                 menor_tempoB=l
                 competidor2=menor_tempoB
        elif c==2:
            menor_tempo3.append(matriz[l][c])
            if matriz[l][c]<menor_tempo:
                 menor_tempoC=l
                 competidor3=menor_tempoC
                
for l in range(5):
    for c in range(3):
        print(f"[{matriz[l][c]}]", end=" ")
    print()

print(f"O menor tempo (em segundos) na primeira etapa foi {min(menor_tempo1)} segundos do competidor {competidor1}")
print(f"O menor tempo (em segundos) na segunda etapa foi {min(menor_tempo2)} segundos do competidor {competidor2}")
print(f"O menor tempo (em segundos) na terceira etapa foi {min(menor_tempo3)} segundos do competidor {competidor3}")