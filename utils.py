# utils.py
import pygame

def carregar_img(caminho, tamanho):
    """Carrega uma imagem e redimensiona. Se não achar, cria um bloco cinza."""
    try:
        img = pygame.image.load(caminho).convert_alpha()
        return pygame.transform.scale(img, tamanho)
    except Exception as e:
        print(f"AVISO CRÍTICO: Imagem não encontrada -> {e}")
        sup = pygame.Surface(tamanho)
        sup.fill((100, 100, 100)) # Cor de erro (Cinza)
        return sup