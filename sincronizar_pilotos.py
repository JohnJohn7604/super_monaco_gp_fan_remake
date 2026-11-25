import json


def sincronizar_pilotos_para_equipes(
    caminho_pilotos="pilotos.json",
    caminho_equipes="equipes.json",
):
    with open(caminho_pilotos, "r", encoding="utf-8") as f:
        pilotos_externos = json.load(f)

    with open(caminho_equipes, "r", encoding="utf-8") as f:
        equipes = json.load(f)

    # Agrupa os pilotos por equipe removendo a chave redundante "equipe"
    pilotos_por_equipe = {}
    for p in pilotos_externos:
        eq = p.get("equipe")
        if not eq:
            continue
        dados_limpos = {k: v for k, v in p.items() if k != "equipe"}
        pilotos_por_equipe.setdefault(eq, []).append(dados_limpos)

    alterado = False
    for eq_nome, novos_pilotos in pilotos_por_equipe.items():
        if eq_nome not in equipes:
            print(f"Aviso: Equipe '{eq_nome}' não encontrada em {caminho_equipes}.")
            continue

        pilotos_atuais = equipes[eq_nome].get("pilotos", [])
        mapa_atuais = {
            p.get("nome", "").strip().lower(): p for p in pilotos_atuais
        }

        lista_atualizada = []
        for novo_p in novos_pilotos:
            chave_nome = novo_p.get("nome", "").strip().lower()
            if chave_nome in mapa_atuais:
                # Atualiza os atributos do mesmo piloto preservando a estrutura
                piloto_mesclado = mapa_atuais[chave_nome].copy()
                piloto_mesclado.update(novo_p)
                lista_atualizada.append(piloto_mesclado)
            else:
                lista_atualizada.append(novo_p)

        if equipes[eq_nome].get("pilotos") != lista_atualizada:
            equipes[eq_nome]["pilotos"] = lista_atualizada
            alterado = True

    if alterado:
        with open(caminho_equipes, "w", encoding="utf-8") as f:
            json.dump(equipes, f, indent=4, ensure_ascii=False)
        print("Sincronização concluída: equipes.json foi atualizado!")
    else:
        print("Tudo já estava sincronizado. Nenhuma alteração necessária.")

    return equipes


if __name__ == "__main__":
    sincronizar_pilotos_para_equipes()