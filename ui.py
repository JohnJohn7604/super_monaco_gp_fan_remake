import pygame
from settings import *

class MenuUI:
    def __init__(self, game):
        # Guarda a referência do main.py para aceder ao ecrã e às variáveis!
        self.game = game 
        
        # Como boa prática, carregamos as fontes aqui UMA VEZ
        self.fonte_titulo = pygame.font.SysFont('Arial', 50, bold=True)
        self.fonte_subtitulo = pygame.font.SysFont('Arial', 40, bold=True)
        self.fonte_input = pygame.font.SysFont('Arial', 40, bold=True)
        self.fonte_inst = pygame.font.SysFont('Arial', 25)
        self.fonte_pos = pygame.font.SysFont('Arial', 25, bold=True)

    def desenhar_tela_nome(self):
        self.game.screen.fill((30, 30, 30))
        
        texto = self.fonte_titulo.render("DIGITE O SEU NOME", True, (255, 255, 255))
        self.game.screen.blit(texto, (WIDTH // 2 - texto.get_width() // 2, 120))
        
        largura_caixa = 400
        x_caixa = WIDTH // 2 - largura_caixa // 2
        y_caixa = 250
        
        pygame.draw.rect(self.game.screen, (50, 50, 50), (x_caixa, y_caixa, largura_caixa, 60), border_radius=10)
        pygame.draw.rect(self.game.screen, (255, 200, 0), (x_caixa, y_caixa, largura_caixa, 60), 3, border_radius=10)
        
        texto_input = self.fonte_input.render(self.game.nome_digitado, True, (255, 255, 255))
        self.game.screen.blit(texto_input, (WIDTH // 2 - texto_input.get_width() // 2, y_caixa + 5))
        
        inst = self.fonte_inst.render("Pressione ENTER para continuar", True, (200, 200, 0))
        self.game.screen.blit(inst, (WIDTH // 2 - inst.get_width() // 2, 400))

    def desenhar_tela_posicao(self):
        self.game.screen.fill((30, 30, 30))
        
        texto = self.fonte_subtitulo.render("ESCOLHA A SUA POSIÇÃO DE LARGADA", True, (255, 255, 255))
        self.game.screen.blit(texto, (WIDTH // 2 - texto.get_width() // 2, 50))
        
        if not hasattr(self.game, 'posicao_jogador'):
            self.game.posicao_jogador = 32

        tamanho_quadrado = 60
        espaco = 10
        largura_total_grelha = 8 * tamanho_quadrado + 7 * espaco
        start_x = WIDTH // 2 - largura_total_grelha // 2
        start_y = 150
        
        for i in range(32):
            pos_num = i + 1
            linha = i // 8
            coluna = i % 8
            
            x = start_x + coluna * (tamanho_quadrado + espaco)
            y = start_y + linha * (tamanho_quadrado + espaco)
            
            rect = pygame.Rect(x, y, tamanho_quadrado, tamanho_quadrado)
            
            if pos_num == self.game.posicao_jogador:
                pygame.draw.rect(self.game.screen, (255, 50, 50), rect, border_radius=8)
                pygame.draw.rect(self.game.screen, (255, 255, 255), rect, 3, border_radius=8)
            else:
                pygame.draw.rect(self.game.screen, (80, 80, 80), rect, border_radius=8)
                
            texto_num = self.fonte_pos.render(str(pos_num), True, (255, 255, 255))
            self.game.screen.blit(texto_num, (x + tamanho_quadrado//2 - texto_num.get_width()//2, 
                                              y + tamanho_quadrado//2 - texto_num.get_height()//2))

        inst = self.fonte_inst.render("Use as SETAS para mover | ENTER para Iniciar Corrida", True, (200, 200, 0))
        self.game.screen.blit(inst, (WIDTH // 2 - inst.get_width() // 2, 480))