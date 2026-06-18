import pygame
import os # <--- Garanta que o os está importado!

def carregar_img(caminho, tamanho=None):
    # 1. Verifica se o ficheiro sequer existe no computador antes de tentar abrir!
    if not os.path.exists(caminho):
        return None
        
    try:
        # 2. Carrega a imagem e otimiza para a placa de vídeo
        img = pygame.image.load(caminho).convert_alpha()
        
        # 3. Redimensiona se for pedido
        if tamanho:
            img = pygame.transform.scale(img, tamanho)
            
        return img
        
    except pygame.error as e:
        # Se a imagem estiver corrompida, ele simplesmente devolve None sem crashar
        print(f"Erro ao carregar {caminho}: {e}")
        return None