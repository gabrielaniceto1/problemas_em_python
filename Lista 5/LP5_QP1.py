import os
os.system("cls")



def classificar_triangulo(a):

    a.sort(reverse=True)
    
    if a[0]>=a[1]+a[2]:
         print("NAO FORMA TRIANGULO")
    else:         
        if a[0]**2== a[1]**2+a[2]**2:
         print("TRIANGULO RETANGULO")
        elif a[0]**2> a[1]**2+a[2]**2:
         print("TRIANGULO OBTUSANGULO")
        elif a[0]**2< a[1]**2+a[2]**2:
         print("TRIANGULO ACUTANGULO")
        if a[0]==a[1]==a[2]:
         print("TRIANGULO EQUILATERO")
        elif a[0]==a[1] or a[0]==a[2] or a[1]==a[2]:
         print("TRIANGULO ISOSCELES")

lados=[]
lista=input().split()

for i in lista:
    i=float(i)
    lados.append(i)

classificar_triangulo(lados)