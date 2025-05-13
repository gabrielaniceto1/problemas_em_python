file= open("arquivo2.txt", "r")

for i in file:
    lista=i.split()
    if len(lista)>6:
        print(lista)
file.close()