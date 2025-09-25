tokenChave = {
    "quilombolas": "indigenas",
    "QUILOMBOLAS": "INDIGENAS",
    "Quilombola": "Indigena",
    "quilombola": "indigena",
    "QUILOMBOLA": "INDIGENA",
}
tokenOrdenado = sorted(tokenChave.keys(), key=len, reverse=True)

with open("script_alterar_txt/documentoOriginal.txt", "r", encoding="utf-8") as fileO:
    with open("script_alterar_txt/documentoNovo.txt", "a", encoding="utf-8") as fileF:
        linhas = fileO.readlines()
        for i in linhas:
            novaLinha = i
            for key in tokenChave:
                novaLinha = novaLinha.replace(key, tokenChave[key])
            fileF.write(novaLinha)