import pygame
from settings import *

class MenuUI:
    def __init__(self, game):
        # Guarda a referência do main.py para aceder ao ecrã e às variáveis!
        self.game = game 
        
        # Fontes do Menu
        self.fonte_titulo = pygame.font.SysFont('Arial', 50, bold=True)
        self.fonte_subtitulo = pygame.font.SysFont('Arial', 36, bold=True)
        self.fonte_input = pygame.font.SysFont('Arial', 40, bold=True)
        self.fonte_inst = pygame.font.SysFont('Arial', 24)
        self.fonte_pos = pygame.font.SysFont('Arial', 24, bold=True)

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

    def desenhar_tela_equipes(self):
        self.game.screen.fill((15, 15, 30))
        titulo = self.fonte_titulo.render("QUEM SEREI EU?", True, (255, 255, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 35))

        sub = self.fonte_inst.render("Escolha o piloto titular que você irá substituir na temporada", True, (200, 200, 220))
        self.game.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 95))

        # Puxa os dados da equipa selecionada
        nome_equipe = self.game.lista_equipes_nomes[self.game.equipe_sel_idx]
        dados_equipe = self.game.equipes[nome_equipe]
        pilotos = dados_equipe.get("pilotos", [])
        piloto_original = pilotos[0] if pilotos else {"nome": "N/A", "speed": 0}

        classe_eq = dados_equipe.get("classe", "C")

        # Painel central da equipe
        card_rect = pygame.Rect(WIDTH // 2 - 290, 140, 580, 360)
        pygame.draw.rect(self.game.screen, (25, 25, 45), card_rect, border_radius=12)
        pygame.draw.rect(self.game.screen, (0, 200, 255), card_rect, width=2, border_radius=12)

        txt_eq = self.fonte_titulo.render(f"<  {nome_equipe.upper()}  >", True, (0, 255, 255))
        self.game.screen.blit(txt_eq, (WIDTH // 2 - txt_eq.get_width() // 2, 160))

        txt_classe = self.fonte_subtitulo.render(f"CATEGORIA: CLASSE {classe_eq}", True, (255, 215, 0))
        self.game.screen.blit(txt_classe, (WIDTH // 2 - txt_classe.get_width() // 2, 225))

        # Piloto Titular a ser substituído
        nome_piloto = piloto_original.get("nome", "N/A")
        txt_substituido = self.fonte_inst.render("Piloto Titular Atual:", True, (160, 160, 180))
        self.game.screen.blit(txt_substituido, (WIDTH // 2 - 240, 280))

        txt_p_orig = self.fonte_subtitulo.render(f"{nome_piloto}", True, (255, 100, 100))
        self.game.screen.blit(txt_p_orig, (WIDTH // 2 - 240, 310))

        # Novo Piloto (Você!)
        txt_novo = self.fonte_inst.render("Será Substituído Por:", True, (160, 160, 180))
        self.game.screen.blit(txt_novo, (WIDTH // 2 + 30, 280))

        meu_nome = getattr(self.game, 'nome_digitado', 'VOCÊ').upper()
        if not meu_nome.strip():
            meu_nome = "VOCÊ"
        txt_meu_nome = self.fonte_subtitulo.render(f">> {meu_nome} <<", True, (0, 255, 0))
        self.game.screen.blit(txt_meu_nome, (WIDTH // 2 + 30, 310))

        # Ficha Técnica / Stats
        vel_base = dados_equipe.get("velocidade_base", 360)
        spd_piloto = piloto_original.get("speed", 0)
        vel_total = vel_base + spd_piloto

        linha_stats = f"Velocidade Máxima: {vel_total} km/h  |  Aceleração: Nível {dados_equipe.get('aceleracao', 1)}"
        txt_stats = self.fonte_inst.render(linha_stats, True, (240, 240, 255))
        self.game.screen.blit(txt_stats, (WIDTH // 2 - txt_stats.get_width() // 2, 385))

        msg_confirm = self.fonte_pos.render(f"Você assumirá o cockpit da {nome_equipe}!", True, (255, 255, 100))
        self.game.screen.blit(msg_confirm, (WIDTH // 2 - msg_confirm.get_width() // 2, 440))

        instrucao = self.fonte_inst.render("SETAS: Mudar Equipe/Piloto | ENTER: Confirmar Escolha", True, (255, 200, 0))
        self.game.screen.blit(instrucao, (WIDTH // 2 - instrucao.get_width() // 2, HEIGHT - 70))

    def desenhar_tela_posicao(self):
        self.game.screen.fill((30, 30, 30))
        
        texto = self.fonte_subtitulo.render("ESCOLHA A SUA POSIÇÃO DE LARGADA (GRID COM 16 CARROS)", True, (255, 255, 255))
        self.game.screen.blit(texto, (WIDTH // 2 - texto.get_width() // 2, 50))
        
        if not hasattr(self.game, 'posicao_jogador'):
            self.game.posicao_jogador = 16

        tamanho_quadrado = 75
        espaco = 15
        largura_total_grelha = 8 * tamanho_quadrado + 7 * espaco
        start_x = WIDTH // 2 - largura_total_grelha // 2
        start_y = 200
        
        for i in range(16):
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
                
            texto_num = self.fonte_subtitulo.render(str(pos_num), True, (255, 255, 255))
            self.game.screen.blit(texto_num, (x + tamanho_quadrado//2 - texto_num.get_width()//2, 
                                              y + tamanho_quadrado//2 - texto_num.get_height()//2))

        inst = self.fonte_inst.render("Use as SETAS para mover | ENTER para Escolher Voltas", True, (200, 200, 0))
        self.game.screen.blit(inst, (WIDTH // 2 - inst.get_width() // 2, 460))

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
        
        titulo = self.game.fonte_normal.render("DEBUG TELEMETRY REPORT (ALL 16 DRIVERS)", True, (255, 255, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 20))

        fonte_dados = pygame.font.SysFont('Arial', 20, bold=True)

        for i, bot in enumerate(self.game.dados_relatorio_corrida):
            grid = bot.get('pos_inicial', 16)
            final = bot.get('pos_final', 16)
            vmax = int(bot.get('vmax', 0))
            sorte = int(bot.get('sorte', 0))
            
            dif = grid - final
            if dif > 0:
                sinal_dif = f"(+{dif})"
            elif dif < 0:
                sinal_dif = f"({dif})"
            else:
                sinal_dif = "(=)"
            
            texto = f"{final:2d}º {bot['nome'][:12]:<12} | Grid: {grid:2d}º {sinal_dif:<5} | VMAX: {vmax}km/h | Sorte: {sorte:+d}"
            
            cor = (0, 255, 0) if bot.get("is_player", False) else (255, 255, 255)
            img_txt = fonte_dados.render(texto, True, cor)

            if i < 8:
                pos_x = 60
                pos_y = 90 + (i * 45)
            else:
                pos_x = WIDTH // 2 + 40
                pos_y = 90 + ((i - 8) * 45)

            self.game.screen.blit(img_txt, (pos_x, pos_y))

        aviso = self.fonte_inst.render("Pressione ENTER para continuar para a Classificação", True, (200, 200, 0))
        self.game.screen.blit(aviso, (WIDTH // 2 - aviso.get_width() // 2, HEIGHT - 50))
