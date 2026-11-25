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

    def _desenhar_moldura_xadrez(self, rect, cor_miolo=(56, 58, 62), borda_xadrez=14):
        """Desenha uma moldura metálica chanfrada com borda interna quadriculada estilo 16-bits."""
        # Sombra projetada
        sombra_rect = rect.move(6, 6)
        pygame.draw.rect(self.game.screen, (25, 26, 30), sombra_rect)

        # Base metálica externa
        pygame.draw.rect(self.game.screen, (122, 125, 132), rect)

        # Chanfro iluminado (topo/esquerda) e escuro (base/direita)
        pygame.draw.line(self.game.screen, (185, 188, 195), rect.topleft, rect.topright, 3)
        pygame.draw.line(self.game.screen, (185, 188, 195), rect.topleft, rect.bottomleft, 3)
        pygame.draw.line(self.game.screen, (45, 47, 52), rect.bottomleft, rect.bottomright, 3)
        pygame.draw.line(self.game.screen, (45, 47, 52), rect.topright, rect.bottomright, 3)

        # Área quadriculada interna
        quad_rect = rect.inflate(-14, -14)
        tam_tile = 10
        cor_q1 = (66, 68, 73)
        cor_q2 = (88, 90, 96)

        clip_antigo = self.game.screen.get_clip()
        self.game.screen.set_clip(quad_rect)
        for y in range(quad_rect.top, quad_rect.bottom, tam_tile):
            linha = (y - quad_rect.top) // tam_tile
            for x in range(quad_rect.left, quad_rect.right, tam_tile):
                coluna = (x - quad_rect.left) // tam_tile
                cor_tile = cor_q1 if (linha + coluna) % 2 == 0 else cor_q2
                pygame.draw.rect(self.game.screen, cor_tile, (x, y, tam_tile, tam_tile))
        self.game.screen.set_clip(clip_antigo)

        # Miolo central
        miolo_rect = quad_rect.inflate(-(borda_xadrez * 2), -(borda_xadrez * 2))
        pygame.draw.rect(self.game.screen, cor_miolo, miolo_rect)
        pygame.draw.rect(self.game.screen, (42, 44, 48), miolo_rect, 2)
        return miolo_rect

    def _desenhar_tecla(self, rect, rotulo, cor_fundo, cor_borda, cor_texto=(255, 255, 255), destaque=False):
        """Desenha uma tecla 3D estilizada."""
        sombra = rect.move(3, 4)
        pygame.draw.rect(self.game.screen, (25, 28, 34), sombra, border_radius=6)
        pygame.draw.rect(self.game.screen, cor_fundo, rect, border_radius=6)
        pygame.draw.rect(self.game.screen, cor_borda, rect, 2 if destaque else 1, border_radius=6)

        # Brilho superior da tecla
        pygame.draw.line(
            self.game.screen,
            (255, 255, 255) if destaque else (175, 180, 190),
            (rect.left + 5, rect.top + 3),
            (rect.right - 5, rect.top + 3),
            2
        )

        fonte_k = pygame.font.SysFont('Arial', 18 if len(rotulo) <= 2 else 13, bold=True)
        txt = fonte_k.render(rotulo, True, cor_texto)
        self.game.screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2 - 1))

    def _desenhar_diagrama_teclado(self, miolo_rect):
        """Desenha a ilustração do teclado e as legendas de direção, pedal e câmbio."""
        fonte_legenda = pygame.font.SysFont('Arial', 19, bold=True)
        fonte_sub = pygame.font.SysFont('Arial', 14, bold=True)

        # Carcaça estilizada do teclado à esquerda
        kb_rect = pygame.Rect(miolo_rect.left + 26, miolo_rect.top + 48, 430, 155)
        pygame.draw.rect(self.game.screen, (185, 190, 200), kb_rect.move(4, 5), border_radius=10)
        pygame.draw.rect(self.game.screen, (42, 46, 56), kb_rect, border_radius=10)
        pygame.draw.rect(self.game.screen, (95, 102, 118), kb_rect, 2, border_radius=10)

        # Fileira superior decorativa (ESC, F1..F8)
        for i in range(9):
            rx = kb_rect.left + 14 + i * 31
            self._desenhar_tecla(pygame.Rect(rx, kb_rect.top + 12, 25, 18), "", (70, 75, 88), (105, 112, 128))

        # Fileira QWERTY decorativa
        for i in range(8):
            rx = kb_rect.left + 24 + i * 33
            self._desenhar_tecla(pygame.Rect(rx, kb_rect.top + 38, 28, 26), "", (75, 80, 94), (110, 118, 134))

        # Teclas principais A (FREIA) e S (ACELERA) em destaque
        rect_a = pygame.Rect(kb_rect.left + 32, kb_rect.top + 72, 34, 32)
        rect_s = pygame.Rect(kb_rect.left + 72, kb_rect.top + 72, 34, 32)
        self._desenhar_tecla(rect_a, "A", (215, 45, 45), (255, 190, 190), destaque=True)
        self._desenhar_tecla(rect_s, "S", (35, 175, 85), (190, 255, 210), destaque=True)

        # Demais teclas decorativas da fileira ASDF + Barra de Espaço
        for i in range(5):
            rx = kb_rect.left + 112 + i * 33
            self._desenhar_tecla(pygame.Rect(rx, kb_rect.top + 72, 28, 30), "", (75, 80, 94), (110, 118, 134))
        self._desenhar_tecla(pygame.Rect(kb_rect.left + 68, kb_rect.top + 112, 175, 26), "", (75, 80, 94), (110, 118, 134))

        # Cluster das Setas Direcionais no canto direito do teclado
        base_setas_x = kb_rect.right - 122
        base_setas_y = kb_rect.top + 72
        rect_up    = pygame.Rect(base_setas_x + 38, base_setas_y, 34, 32)
        rect_left  = pygame.Rect(base_setas_x,      base_setas_y + 38, 34, 32)
        rect_down  = pygame.Rect(base_setas_x + 38, base_setas_y + 38, 34, 32)
        rect_right = pygame.Rect(base_setas_x + 76, base_setas_y + 38, 34, 32)

        self._desenhar_tecla(rect_up, "↑", (235, 175, 20), (255, 245, 170), (20, 20, 20), destaque=True)
        self._desenhar_tecla(rect_down, "↓", (35, 145, 225), (185, 235, 255), (255, 255, 255), destaque=True)
        self._desenhar_tecla(rect_left, "←", (95, 102, 118), (150, 158, 175))
        self._desenhar_tecla(rect_right, "→", (95, 102, 118), (150, 158, 175))

        # --- CALLOUTS / LINHAS INDICADORAS ---
        # S -> ACELERA (acima do teclado)
        p_s1 = (rect_s.centerx, kb_rect.top - 4)
        p_s2 = (rect_s.centerx, miolo_rect.top + 18)
        pygame.draw.line(self.game.screen, (25, 145, 65), (rect_s.centerx, rect_s.top), p_s2, 3)
        pygame.draw.circle(self.game.screen, (25, 145, 65), p_s2, 4)
        txt_s = fonte_legenda.render("[ S ]  ACELERA", True, (20, 130, 55))
        self.game.screen.blit(txt_s, (p_s2[0] + 10, p_s2[1] - 10))

        # A -> FREIA (abaixo do teclado)
        p_a2 = (rect_a.centerx, kb_rect.bottom + 18)
        pygame.draw.line(self.game.screen, (200, 35, 35), (rect_a.centerx, rect_a.bottom), p_a2, 3)
        pygame.draw.circle(self.game.screen, (200, 35, 35), p_a2, 4)
        txt_a = fonte_legenda.render("[ A ]  FREIA", True, (190, 25, 25))
        self.game.screen.blit(txt_a, (p_a2[0] + 10, p_a2[1] - 10))

        # Painel de Legenda das Marchas à direita do teclado
        leg_x = kb_rect.right + 28
        leg_y = miolo_rect.top + 32

        titulo_ctrl = fonte_sub.render("CONTROLE DE MARCHAS (MANUAL):", True, (65, 72, 85))
        self.game.screen.blit(titulo_ctrl, (leg_x, leg_y))

        # Linha CIMA -> BAIXA MARCHA
        y_cima = leg_y + 36
        pygame.draw.line(self.game.screen, (210, 145, 10), (rect_up.right, rect_up.centery), (leg_x - 8, y_cima + 12), 3)
        pygame.draw.rect(self.game.screen, (235, 175, 20), (leg_x, y_cima, 30, 26), border_radius=5)
        txt_ico_up = fonte_legenda.render("↑", True, (20, 20, 20))
        self.game.screen.blit(txt_ico_up, (leg_x + 9, y_cima + 1))
        txt_cima = fonte_legenda.render("CIMA: BAIXA MARCHA", True, (165, 110, 0))
        self.game.screen.blit(txt_cima, (leg_x + 40, y_cima + 2))

        # Linha BAIXO -> SOBE MARCHA
        y_baixo = leg_y + 82
        pygame.draw.line(self.game.screen, (25, 130, 205), (rect_down.right, rect_down.centery), (leg_x - 8, y_baixo + 12), 3)
        pygame.draw.rect(self.game.screen, (35, 145, 225), (leg_x, y_baixo, 30, 26), border_radius=5)
        txt_ico_dn = fonte_legenda.render("↓", True, (255, 255, 255))
        self.game.screen.blit(txt_ico_dn, (leg_x + 9, y_baixo + 1))
        txt_baixo = fonte_legenda.render("BAIXO: SOBE MARCHA", True, (20, 110, 180))
        self.game.screen.blit(txt_baixo, (leg_x + 40, y_baixo + 2))

        # Nota sobre direção nas setas laterais
        y_dir = leg_y + 132
        txt_dir = fonte_sub.render("[ ← / → ]  ESTERÇAR VOLANTE", True, (85, 92, 105))
        self.game.screen.blit(txt_dir, (leg_x, y_dir))

    def desenhar_tela_transmissao(self):
        """Tela clássica TRANSMISSION SELECT antes de iniciar qualquer corrida."""
        self.game.screen.fill((56, 58, 62))

        # 1. Banner Superior: TRANSMISSION SELECT
        banner_rect = pygame.Rect(WIDTH // 2 - 430, 32, 860, 84)
        miolo_banner = self._desenhar_moldura_xadrez(banner_rect, cor_miolo=(56, 58, 62), borda_xadrez=10)

        fonte_banner = pygame.font.SysFont('Arial', 44, bold=True)
        txt_sombra = fonte_banner.render("TRANSMISSION SELECT", True, (15, 15, 18))
        txt_titulo = fonte_banner.render("TRANSMISSION SELECT", True, (245, 205, 20))
        tx = miolo_banner.centerx - txt_titulo.get_width() // 2
        ty = miolo_banner.centery - txt_titulo.get_height() // 2
        self.game.screen.blit(txt_sombra, (tx + 3, ty + 3))
        self.game.screen.blit(txt_titulo, (tx, ty))

        # 2. Opções de Câmbio (AUTOMATIC e 7 SPEED MANUAL)
        fonte_op = pygame.font.SysFont('Arial', 38, bold=True)
        box_w, box_h = 740, 56
        start_y = 152
        gap_y = 74

        for idx, opcao in enumerate(self.game.opcoes_transmissao):
            selecionado = (idx == self.game.transmissao_sel_idx)
            box_rect = pygame.Rect(WIDTH // 2 - box_w // 2, start_y + idx * gap_y, box_w, box_h)

            # Sombra deslocada
            pygame.draw.rect(self.game.screen, (25, 26, 30), box_rect.move(6, 6), 3)

            if selecionado:
                cor_borda = (232, 148, 148)
                cor_texto = (238, 154, 154)
            else:
                cor_borda = (125, 150, 185)
                cor_texto = (132, 158, 192)

            pygame.draw.rect(self.game.screen, cor_borda, box_rect, 3)

            label = opcao["label"]
            img_sombra = fonte_op.render(label, True, (15, 15, 18))
            img_label = fonte_op.render(label, True, cor_texto)
            lx = box_rect.centerx - img_label.get_width() // 2
            ly = box_rect.centery - img_label.get_height() // 2
            self.game.screen.blit(img_sombra, (lx + 3, ly + 3))
            self.game.screen.blit(img_label, (lx, ly))

        # 3. Moldura Inferior com o Desenho do Teclado
        painel_kb_rect = pygame.Rect(WIDTH // 2 - 430, 325, 860, 320)
        miolo_kb = self._desenhar_moldura_xadrez(painel_kb_rect, cor_miolo=(242, 244, 248), borda_xadrez=12)
        self._desenhar_diagrama_teclado(miolo_kb)

        # 4. Rodapé de instrução
        rodape = self.fonte_inst.render("SETAS CIMA / BAIXO: Escolher Câmbio   |   ENTER: Iniciar Corrida", True, (245, 215, 65))
        self.game.screen.blit(rodape, (WIDTH // 2 - rodape.get_width() // 2, HEIGHT - 42))
