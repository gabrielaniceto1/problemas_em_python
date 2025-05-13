t=int(input())
fib=[]
vetor=[0,1]
for j in range(2,61):
    vetor.append(vetor[j-1] + vetor[j-2])
for i in range(t):
    nmr=int(input())
    fib.append(nmr)
for i in range(t):
    valor=fib[i]
    print(f"Fib ({valor}) = {vetor[valor]}")