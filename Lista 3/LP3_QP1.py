import os
os.system("cls")
vetor_par=[]
vetor_impar=[]
vetor_positivo=[]
vetor_negativo=[]
for i in range (1,6):
    nmr=int(input())
    if nmr%2==0:
        vetor_par.append(nmr)
    else:
        vetor_impar.append(nmr)
    if nmr>0:
        vetor_positivo.append(nmr)
    else:
        vetor_negativo.append(nmr)


print(f"{len(vetor_par)} valor(es) par(es) \n{len(vetor_impar)} valor(res) impar(res) \n{len(vetor_positivo)} valor(es) positivo(s) \n{len(vetor_negativo)} valor(es) negativo(s)") 