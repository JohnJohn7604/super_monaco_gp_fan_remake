import pygame
from settings import *

class MenuUI:
    def __init__(self, game):
        # Guarda a referência do main.py para aceder ao ecrã e às variáveis!
        self.game = game 
        
        # Fontes do Menu
        self.fonte_titulo = pygame.font.SysFont('Arial', 50, bold=True)
        self.fonte_pequena = pygame.font.SysFont('Arial', 17, bold=True)
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

    def desenhar_tela_pistas(self):
        self.game.screen.fill((15, 20, 35))
        
        fonte_titulo = pygame.font.SysFont('Arial', 45, bold=True)
        fonte_opcao = pygame.font.SysFont('Arial', 34, bold=True)
        fonte_info = pygame.font.SysFont('Arial', 20)

        # Cabeçalho
        titulo = fonte_titulo.render("SELECT CIRCUIT", True, (255, 215, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 70))

        sub = fonte_info.render(f"DRIVER: {self.game.nome_digitado}", True, (150, 180, 220))
        self.game.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 130))

        # Lista de circuitos
        y_inicial = 230
        for i, pista in enumerate(self.game.lista_pistas):
            selecionado = (i == self.game.pista_sel_idx)
            cor_texto = (0, 255, 100) if selecionado else (200, 200, 200)
            prefixo = "> " if selecionado else "  "

            # Caixa de destaque na opção selecionada
            if selecionado:
                rect_bg = pygame.Rect(WIDTH // 2 - 220, y_inicial + (i * 70) - 10, 440, 56)
                pygame.draw.rect(self.game.screen, (30, 45, 75), rect_bg, border_radius=8)
                pygame.draw.rect(self.game.screen, (0, 255, 100), rect_bg, width=2, border_radius=8)

            txt = fonte_opcao.render(f"{prefixo}{pista['nome']}", True, cor_texto)
            self.game.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, y_inicial + (i * 70)))

        # Rodapé
        inst = fonte_info.render("USE ARROWS TO SELECT  |  PRESS ENTER TO CONFIRM", True, (255, 80, 80))
        self.game.screen.blit(inst, (WIDTH // 2 - inst.get_width() // 2, HEIGHT - 60))

    def desenhar_tela_modo(self):
        self.game.screen.fill((15, 18, 28))

        titulo = self.fonte_titulo.render(f"BEM-VINDO, {self.game.nome_digitado}!", True, (255, 215, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 100))

        sub = self.game.fonte_normal.render("ESCOLHA O MODO DE JOGO:", True, (180, 190, 210))
        self.game.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 175))

        opcoes = [
            ("1. CORRIDA RÁPIDA", "Escolha livremente a pista, o grid e o número de voltas."),
            ("2. TEMPORADA OFICIAL", "Dispute todas as etapas do campeonato em sequência!")
        ]

        for idx, (nome_op, desc) in enumerate(opcoes):
            selecionado = (idx == self.game.modo_jogo_sel_idx)
            cor_caixa = (45, 75, 130) if selecionado else (28, 34, 48)
            cor_borda = (255, 215, 0) if selecionado else (70, 80, 100)
            cor_texto = (255, 255, 255) if selecionado else (160, 170, 185)

            caixa = pygame.Rect(WIDTH // 2 - 280, 245 + idx * 120, 560, 95)
            pygame.draw.rect(self.game.screen, cor_caixa, caixa, border_radius=8)
            pygame.draw.rect(self.game.screen, cor_borda, caixa, width=2, border_radius=8)

            txt_op = self.game.fonte_normal.render(nome_op, True, cor_texto)
            txt_desc = self.game.fonte_pequena.render(desc, True, (200, 210, 225) if selecionado else (120, 130, 145))

            self.game.screen.blit(txt_op, (caixa.x + 25, caixa.y + 18))
            self.game.screen.blit(txt_desc, (caixa.x + 25, caixa.y + 56))

        rodape = self.game.fonte_pequena.render("Use CIMA / BAIXO para selecionar e ENTER para confirmar", True, (140, 150, 165))
        self.game.screen.blit(rodape, (WIDTH // 2 - rodape.get_width() // 2, HEIGHT - 60))

    def desenhar_hud_preliminary(self, melhor_volta, pos_grid, tempo_target_p1, progresso_saida):
        # Barra superior translúcida
        painel = pygame.Surface((WIDTH, 68), pygame.SRCALPHA)
        painel.fill((10, 15, 30, 200))
        self.game.screen.blit(painel, (0, 0))
        pygame.draw.line(self.game.screen, (255, 215, 0), (0, 68), (WIDTH, 68), 2)

        etapa_num = self.game.etapa_atual_idx + 1
        total_etapas = len(self.game.etapas_temporada)
        txt_modo = self.fonte_pequena.render(
            f"PRELIMINARY RACE - STAGE {etapa_num}/{total_etapas} (INFINITE LAPS)",
            True, (255, 215, 0)
        )
        self.game.screen.blit(txt_modo, (20, 10))

        str_melhor = f"{melhor_volta:.2f}s" if melhor_volta is not None else "--.--s"
        str_p1 = f"{tempo_target_p1:.2f}s" if tempo_target_p1 is not None else "--.--s"
        txt_tempos = self.fonte_inst.render(
            f"BEST LAP: {str_melhor}   |   POLE TARGET: {str_p1}   |   GRID POS: {pos_grid}º",
            True, (0, 255, 130)
        )
        self.game.screen.blit(txt_tempos, (20, 34))

        # Instrução de saída no canto direito
        txt_sair = self.fonte_pequena.render("HOLD [A + S + D] FOR 2s TO RACE", True, (255, 120, 120))
        self.game.screen.blit(txt_sair, (WIDTH - txt_sair.get_width() - 20, 12))

        # Barra de progresso ao segurar A + S + D
        if progresso_saida > 0:
            bar_w = 240
            bar_h = 16
            bx = WIDTH - bar_w - 20
            by = 38
            pygame.draw.rect(self.game.screen, (40, 40, 55), (bx, by, bar_w, bar_h), border_radius=4)
            fill_w = int(bar_w * min(1.0, progresso_saida))
            pygame.draw.rect(self.game.screen, (255, 200, 0), (bx, by, fill_w, bar_h), border_radius=4)
            pygame.draw.rect(self.game.screen, (255, 255, 255), (bx, by, bar_w, bar_h), 1, border_radius=4)

    def desenhar_tela_resultados_pilotos(self):
        self.game.screen.fill((20, 20, 50))
        titulo = self.fonte_titulo.render("DRIVERS CHAMPIONSHIP", True, (255, 255, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 30))

        fonte_lista = pygame.font.SysFont('Arial', 24, bold=True)
        meu_nome = getattr(self.game, "nome_jogador_formatado", "PILOTO").upper()

        for i, item in enumerate(self.game.classificacao_pilotos):
            sigla = item["equipe"][:3].upper()
            texto = f"{i+1:2d}. {item['nome']} ({sigla}) - {item['pontos']} PTS"
            cor = (0, 255, 0) if item["nome"].upper() == meu_nome else (255, 255, 255)
            img_txt = fonte_lista.render(texto, True, cor)

            if i < 8:
                x, y = WIDTH // 4 - 140, 120 + (i * 45)
            else:
                x, y = 3 * (WIDTH // 4) - 140, 120 + ((i - 8) * 45)

            self.game.screen.blit(img_txt, (x, y))

        aviso = fonte_lista.render("PRESS ENTER TO CONTINUE", True, (255, 0, 0))
        self.game.screen.blit(aviso, (WIDTH // 2 - aviso.get_width() // 2, HEIGHT - 50))

    def desenhar_tela_resultados_construtores(self):
        self.game.screen.fill((20, 20, 50))
        titulo = self.fonte_titulo.render("CONSTRUCTORS CHAMPIONSHIP", True, (255, 255, 0))
        self.game.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 30))

        fonte_lista = pygame.font.SysFont('Arial', 26, bold=True)
        total_eq = len(self.game.classificacao_construtoras)

        for i, (equipe, pts) in enumerate(self.game.classificacao_construtoras):
            texto = f"{i+1:2d}. {equipe}: {pts} PTS"
            cor = (0, 255, 0) if equipe == self.game.equipe_atual_jogador else (255, 255, 255)
            img_txt = fonte_lista.render(texto, True, cor)

            if total_eq <= 8:
                x = WIDTH // 2 - 160
                y = 130 + (i * 45)
            else:
                if i < 8:
                    x, y = WIDTH // 4 - 130, 130 + (i * 45)
                else:
                    x, y = 3 * (WIDTH // 4) - 130, 130 + ((i - 8) * 45)

            self.game.screen.blit(img_txt, (x, y))

        aviso = fonte_lista.render("PRESS ENTER TO CONTINUE", True, (255, 0, 0))
        self.game.screen.blit(aviso, (WIDTH // 2 - aviso.get_width() // 2, HEIGHT - 50))
