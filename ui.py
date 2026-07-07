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

    def desenhar_tela_equipes(self):
        self.game.screen.fill((15, 15, 30))
        titulo = self.fonte_titulo.render("SELECT TEAM & DRIVER", True, (255, 255, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 50))

        # Puxa os dados da equipa selecionada
        nome_equipe = self.game.lista_equipes_nomes[self.game.equipe_sel_idx]
        dados_equipe = self.game.equipes[nome_equipe]
        pilotos = dados_equipe["pilotos"]

        # 1. Desenha o Nome da Equipa
        txt_eq = self.fonte_subtitulo.render(f"< TEAM: {nome_equipe.upper()} >", True, (0, 255, 255))
        self.game.screen.blit(txt_eq, (WIDTH // 2 - txt_eq.get_width() // 2, 150))

        # 2. Desenha os Pilotos (1º e 2º)
        for i in range(2):
            if i < len(pilotos):
                nome_piloto = pilotos[i]["nome"]
            else:
                nome_piloto = "N/A"

            cor = (0, 255, 0) if i == self.game.piloto_sel_idx else (150, 150, 150)
            prefixo = ">> " if i == self.game.piloto_sel_idx else "   "
            cargo = "1st Driver" if i == 0 else "2nd Driver"

            txt_p = self.fonte_subtitulo.render(f"{prefixo}{cargo}: {nome_piloto}", True, cor)
            self.game.screen.blit(txt_p, (WIDTH // 2 - 200, 250 + i * 50))

        instrucao = self.fonte_inst.render("UP/DOWN: Change Driver | LEFT/RIGHT: Change Team | ENTER: Select", True, (255, 50, 50))
        self.game.screen.blit(instrucao, (WIDTH // 2 - instrucao.get_width() // 2, HEIGHT - 60))

    def desenhar_tela_voltas(self):
        self.game.screen.fill((15, 15, 30))
        titulo = self.fonte_titulo.render("RACE LENGTH", True, (255, 255, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 100))

        for i, num_voltas in enumerate(self.game.opcoes_voltas):
            cor = (0, 255, 0) if i == self.game.volta_sel_idx else (150, 150, 150)
            prefixo = ">> " if i == self.game.volta_sel_idx else "   "
            texto = f"{prefixo}{num_voltas} LAPS"

            txt = self.fonte_subtitulo.render(texto, True, cor)
            self.game.screen.blit(txt, (WIDTH // 2 - 100, 200 + i * 40))

        instrucao = self.fonte_inst.render("UP/DOWN: Change | ENTER: Select", True, (255, 50, 50))
        self.game.screen.blit(instrucao, (WIDTH // 2 - instrucao.get_width() // 2, HEIGHT - 60))

    def desenhar_tela_debug_relatorio(self):
        self.game.screen.fill((20, 20, 40)) 
        
        titulo = self.game.fonte_normal.render("DEBUG TELEMETRY REPORT (ALL GRID)", True, (255, 255, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 20))

        fonte_dados = pygame.font.SysFont('Arial', 18, bold=True)

        # Varre todos os 32 pilotos do relatório compilado
        for i, bot in enumerate(self.game.dados_relatorio_corrida):
            
            # 1. Extraímos os dados com segurança (usando int para evitar erros de decimal)
            grid = bot.get('pos_inicial', 32)
            final = bot.get('pos_final', 32)
            vmax = int(bot.get('vmax', 0))
            sorte = int(bot.get('sorte', 0))
            
            # 2. Calculamos se o piloto subiu ou caiu na corrida
            dif = grid - final
            if dif > 0:
                sinal_dif = f"(+{dif})"  # Ganhou posições
            elif dif < 0:
                sinal_dif = f"({dif})"   # Perdeu posições
            else:
                sinal_dif = "(=)"        # Manteve a posição
            
            # 3. Montamos a linha de telemetria completa e compacta
            # O {:+d} coloca automaticamente o sinal de + ou - no número da sorte!
            texto = f"{final}º {bot['nome'][:11]:<11} | Grid: {grid}º {sinal_dif} | VMAX: {vmax}km/h | Sorte: {sorte:+d}"
            
            # Destaca o jogador em verde, os bots em branco
            cor = (0, 255, 0) if bot.get("is_player", False) else (255, 255, 255)
            img_txt = fonte_dados.render(texto, True, cor)

            # MÁGICA DA SEPARAÇÃO: Se for até 16, vai para a esquerda. Se passar, vai para a direita!
            if i < 16:
                pos_x = 40
                pos_y = 70 + (i * 35)
            else:
                pos_x = WIDTH // 2 + 20
                pos_y = 70 + ((i - 16) * 35)

            self.game.screen.blit(img_txt, (pos_x, pos_y))