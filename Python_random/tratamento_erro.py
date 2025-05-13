while True:

    try:
        nmr=int(input("Digite um numero para tirar a raiza quadrada"))
        x = nmr**1/2
        print(x)
        break
    except:ValueError
    print("Digite um numero valido")