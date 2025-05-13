a=[]
b=[]
c=[]

for i in range(10):
    a.append(int(input("Digite um valor inteiro: ")))
    if a[i]%2==0:
        b.append(a[i])
    else:
        c.append(a[i])
print(a, b, c)