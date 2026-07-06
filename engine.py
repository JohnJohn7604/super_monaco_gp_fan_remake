import pygame
import sys
import math
import json
import random
from settings import *
from openal import oalOpen, oalQuit
from track import Track
from car import Car
from utils import carregar_img
from ui import MenuUI
from bot_ai import BotAI

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.mixer.init()
        # O SCALED e o DOUBLEBUF transferem o peso do jogo para a Placa de Vídeo!
        flags = pygame.SCALED | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        # Ignora tudo o que for rato e foca o processador SÓ no teclado!
        pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.KEYUP])
        pygame.display.set_caption("Super Monaco GP - Rio Edition")
        self.clock = pygame.time.Clock()
        self.imagem_cache = {}

        # Interface de Menus e bots
        self.ui = MenuUI(self)
        self.ai = BotAI(self)

        self.fonte_grande = pygame.font.SysFont('Arial', 80, bold=True)
        self.fonte_normal = pygame.font.SysFont('Arial', 30)
        
        self.estado_jogo = "INPUT_NAME"
        self.nome_digitado = ""         # Guarda as letras que o jogador vai digitar
        self.track = None
        self.car = None

        self.ultrapassagens_combo = 0
        self.timer_combo = 0

        self.race_finished = False
        self.final_position = 0
        self.lap_limit = 1 # Definimos aqui o limite de 6 voltas

        # ==========================================
        # CARREGAR BANCO DE DADOS VIA JSON E MESCLAR
        # ==========================================
        try:
            # 1. Carrega os carros
            with open('equipes.json', 'r', encoding='utf-8') as f:
                self.equipes = json.load(f)
                
            # 2. Carrega os pilotos atualizados
            with open('pilotos.json', 'r', encoding='utf-8') as f:
                pilotos_externos = json.load(f)
                
            # 3. Agrupa os pilotos por equipe
            pilotos_por_equipe = {}
            for p in pilotos_externos:
                eq = p["equipe"]
                if eq not in pilotos_por_equipe:
                    pilotos_por_equipe[eq] = []
                pilotos_por_equipe[eq].append(p)
                
            # 4. Substitui os pilotos antigos dentro da self.equipes
            for eq_nome, pilotos_lista in pilotos_por_equipe.items():
                if eq_nome in self.equipes:
                    self.equipes[eq_nome]["pilotos"] = pilotos_lista
                    
        except FileNotFoundError as e:
            print(f"ERRO: Ficheiro JSON não encontrado! Detalhes: {e}")
            if not hasattr(self, 'equipes'):
                self.equipes = {} # Evita que o jogo quebre completamente

        # Variáveis de Carreira
        self.equipe_atual_jogador = "Blanche"
        self.rival_atual = None
        self.vitorias_contra_rival = 0


        # ==========================================
        # ÁUDIO 3D VIA OPENAL (Batida e Motor dos Bots)
        # ==========================================
        self.timer_batida = 0 
        
        try:
            self.som_batida = oalOpen("sounds/batida.wav") 
            
            # Cria uma "Piscina" com 5 canais de som para ouvirmos o pelotão!
            self.canais_motor_bot = []
            for _ in range(5):
                som = oalOpen("sounds/bot_motor.wav")
                som.set_looping(True)
                som.set_gain(0.0) # Nasce mudo
                som.play()        # Fica tocando em silêncio
                self.canais_motor_bot.append(som)
                
        except Exception as e:
            print(f"Aviso OpenAL: Erro ao carregar audios! Detalhes: {e}")
            self.som_batida = None
            self.canais_motor_bot = []

        self.steering_locked = False
        
        # Define o tamanho original do seu PNG
        self.bot_base_w = 140  
        self.bot_base_h = 54  
        tamanho_bot = (self.bot_base_w, self.bot_base_h)
        
        self.bot_anim_timer = 0
        self.bot_frame_idx = 0
        
        # Cria um "Armário" vazio para guardar as imagens de cada equipe na memória
        self.cache_sprites = {}

    def tingir_carroceria(self, superficie, mapa_cor):
        """ Pinta o sprite do bot base (azul) com as cores da equipe do JSON """
        if not superficie or not mapa_cor:
            return superficie
            
        imagem_nova = superficie.copy()
        
        # 1. Definição dos 4 azuis fixos do PNG do Bot (em RGB)
        azul_puro     = (0, 0, 255)       
        azul_escuro   = (0, 0, 148)       
        azul_medio    = (106, 148, 189)   
        azul_claro    = (189, 222, 255)   
        
        # 2. Extração das novas cores do JSON
        nova_pura   = tuple(mapa_cor.get("puro", [0, 0, 255]))
        nova_escura = tuple(mapa_cor.get("escuro", [0, 0, 148]))
        nova_media  = tuple(mapa_cor.get("medio", [106, 148, 189]))
        nova_clara  = tuple(mapa_cor.get("claro", [189, 222, 255]))
        
        conversoes = {
            azul_puro: nova_pura,
            azul_escuro: nova_escura,
            azul_medio: nova_media,
            azul_claro: nova_clara
        }
        
        # Faz a mágica da substituição de pixels
        px_array = pygame.PixelArray(imagem_nova)
        for cor_antiga, cor_nova in conversoes.items():
            cor_antiga_mapeada = imagem_nova.map_rgb(cor_antiga)
            cor_nova_mapeada = imagem_nova.map_rgb(cor_nova)
            px_array.replace(cor_antiga_mapeada, cor_nova_mapeada)
            
        px_array.close()
        return imagem_nova

    # Adicionamos o 'mapa_cor' aqui em cima
    def carregar_sprites_equipe(self, pasta_equipe, mapa_cor=None):
        """Carrega os 18 frames de uma equipe, usando o bot base se não existir a pasta."""
        tamanho_bot = (self.bot_base_w, self.bot_base_h)
        
        def pegar_img(direcao, tipo, frame):
            nome_arquivo = f"{direcao}_{tipo}{frame}.png"
            caminho_equipe = f"images/cars/{pasta_equipe}/{nome_arquivo}"
            caminho_bot = f"images/cars/bot/{nome_arquivo}" # O bot base azul
            
            # 1. Tenta carregar um PNG feito à mão (se você tiver feito um no Photoshop)
            img = carregar_img(caminho_equipe, tamanho_bot)
            
            # 2. Se não tem PNG feito à mão, puxa o Bot Base e PINTA ELE!
            if not img:
                img = carregar_img(caminho_bot, tamanho_bot)
                if img and mapa_cor:
                    # MÁGICA: Pinta o bot base instantaneamente!
                    img = self.tingir_carroceria(img, mapa_cor)
                    
            if not img:
                img = pygame.Surface(tamanho_bot, pygame.SRCALPHA)
            return img

        sprites = {}
        perspectivas = ["rear_reto", "front_reto", "front_esq", "front_dir", "rear_esq", "rear_dir"]
        sufixos = ["1", "1a", "1b"]
        
        for pers in perspectivas:
            partes = pers.split('_') 
            direcao = partes[0]
            tipo = partes[1]
            
            sprites[pers] = []
            for suf in sufixos:
                sprites[pers].append(pegar_img(direcao, tipo, suf))
                
        return sprites
    
    def redimensionar_bot_otimizado(self, img_original, pasta, perspectiva, frame, w, h):
        # A traseira tem uma animação suave (passo 5). O resto é agressivo (passo 15) para poupar RAM!
        passo = 5 if perspectiva == "rear_reto" else 15
        
        # MÁGICA ANTI-LAG: Arredonda a altura pedida para o degrau mais próximo
        h_arredondado = max(10, min(332, round(h / passo) * passo))
        w_arredondado = int(h_arredondado * (img_original.get_width() / img_original.get_height()))
        
        # Evita crash de largura zero
        if w_arredondado <= 0: w_arredondado = 1 
            
        chave = f"{pasta}_{perspectiva}_{frame}_{w_arredondado}x{h_arredondado}"
        
        # Puxa do armário. Se não existir (como as frentes e os lados), cria na hora e guarda!
        if chave not in self.imagem_cache:
            self.imagem_cache[chave] = pygame.transform.scale(img_original, (w_arredondado, h_arredondado))
            
        return self.imagem_cache[chave]
    
    def pre_aquecer_cache(self):
        """ Gera APENAS os tamanhos da TRASEIRA dos carros antes da corrida começar! """
        for pasta in self.cache_sprites.keys():
            
            # FOCAMOS APENAS NA TRASEIRA RETA (Poupa 80% da Memória RAM instantaneamente!)
            perspectiva = "rear_reto"
            for frame in range(3):
                img_original = self.cache_sprites[pasta][perspectiva][frame]
                img_w = img_original.get_width()
                img_h = img_original.get_height()
                
                # Passo 5: Salta de 5 em 5 pixels. 
                # Em vez de gerar 300 imagens por carro, gera apenas umas 60!
                for h in range(10, 334, 5):
                    w = int(h * (img_w / img_h))
                    if w > 0:
                        chave = f"{pasta}_{perspectiva}_{frame}_{w}x{h}"
                        self.imagem_cache[chave] = pygame.transform.scale(img_original, (w, h))
    

    def iniciar_corrida(self, track_name):
        # 1. Escolha da pista
        if track_name == "rio":
            self.track = Track()
            
        # =========================================================
        # APLICA AS ESCOLHAS DOS MENUS NO SEU PILOTO (NOVO)
        # =========================================================
        self.nome_jogador_formatado = getattr(self, 'nome_digitado', "PILOTO")
        
        # 1. Puxa a equipa e o índice de piloto (0 ou 1) que você selecionou no Menu
        nome_equipe = self.lista_equipes_nomes[self.equipe_sel_idx]
        self.equipe_atual_jogador = nome_equipe
        
        # 2. Desmarca qualquer "is_player" antigo para evitar bugs com os bots
        for eq_nome, dados_eq in self.equipes.items():
            for p in dados_eq.get("pilotos", []):
                p["is_player"] = False
                
        # 3. Injeta a sua alma no piloto que você escolheu substituir!
        pilotos_da_equipe = self.equipes[nome_equipe]["pilotos"]
        self.dados_do_meu_piloto = pilotos_da_equipe[self.piloto_sel_idx].copy() # Salva as skills dele para você
        
        pilotos_da_equipe[self.piloto_sel_idx]["nome"] = self.nome_jogador_formatado
        pilotos_da_equipe[self.piloto_sel_idx]["is_player"] = True
        
        # 4. Aplica o limite de voltas escolhido no menu
        self.lap_limit = self.opcoes_voltas[self.volta_sel_idx]

        # Descobre a pasta da equipe do jogador agora que já sabe onde você está
        nome_equipe = self.equipe_atual_jogador
        if nome_equipe in self.equipes:
            pasta_do_jogador = self.equipes[nome_equipe]["pasta"]
        else:
            pasta_do_jogador = "minarae" # Segurança caso a equipe não exista

        # =========================================================
        # CARREGAR PERFORMANCE DA EQUIPE (MODO: CARRO PURO)
        # =========================================================
        status = self.equipes[self.equipe_atual_jogador]
        
        # AGORA IGNORAMOS A SKILL DO BOT! 
        # A velocidade máxima será EXATAMENTE a velocidade base do chassi da equipe.
        velocidade_final_jogador = status["velocidade_base"]

        # Passa a velocidade final turbinada para o carro!
        self.car = Car(
            velocidade_maxima = velocidade_final_jogador,
            nivel_aceleracao  = status.get("aceleracao", 1), # Usa apenas a aceleração do carro
            nivel_freio       = status.get("freio", 3),                            # Freio padrão de fábrica do jogador
            nivel_direcao     = status.get("direcao", 3),                          # Direção padrão de fábrica do jogador
            pasta_equipe      = pasta_do_jogador
        )
        

        # =========================================================
        # INJEÇÃO DAS MARCHAS E ATRIBUTOS DO JSON NO CARRO (NOVO)
        # =========================================================
        # Passamos o 'status' (o dicionário completo da equipe) para o carro 
        # configurar a força das 7 marchas e as velocidades de resposta do volante!
        self.car.ajustar_atributos_equipe(status)
            
        
        
        # 3. Limpa a lista e cria os Adversários (Bots) novos
        self.bots = []
        self.cache_sprites = {} # Limpa as imagens antigas
        
        # =========================================================
        # CONFIGURAÇÃO DO GRID E DO JOGADOR
        # =========================================================
        # Pega a posição exata que você escolheu na tela dos quadradinhos!
        # (Se por algum motivo o jogo pular o menu, ele coloca-o em 32º por segurança)
        posicao_jogador = getattr(self, 'posicao_jogador', 32) 
        espaco_grid = 6     # Distância em metros entre os carros no grid

        # Coloca o JOGADOR na pista
        self.car.position = 100 + ((32 - posicao_jogador) * espaco_grid)
        self.car.player_x = 0.33 if posicao_jogador % 2 == 0 else -0.33
        
        # ==========================================
        # ---> NOVO: TELEMETRIA DO JOGADOR <---
        # ==========================================
        self.car.pos_inicial_grid = posicao_jogador
        self.car.velocidade_maxima_corrida = 0
        
        bots_temporarios = []
        
        for nome_eq, dados in self.equipes.items():
            # ... resto do código continua igual ...
            pasta = dados["pasta"]
            mapa_cor = dados.get("mapa_cor", None) # <--- LÊ AS CORES DESTA EQUIPA NO JSON
            
            # CARREGA OS SPRITES DESTA EQUIPE APENAS UMA VEZ E GUARDA NO ARMÁRIO!
            if pasta not in self.cache_sprites:
                # Passa o mapa de cores para o carregador pintar na hora!
                self.cache_sprites[pasta] = self.carregar_sprites_equipe(pasta, mapa_cor)
                
            for i, piloto in enumerate(dados["pilotos"]):
                
                # Agora o jogo só olha para o carimbo oficial! Se for o jogador, ignora.
                if piloto.get("is_player", False):
                    continue # Pula para o próximo, essa vaga é do jogador humano!
                
                # ----------------------------------------------------
                # MATEMÁTICA DE STATUS (Unindo Piloto + Carro)
                # ----------------------------------------------------
                # O bot pega a base do carro e soma a skill de speed dele!
                vel_maxima_do_carro = dados["velocidade_base"] + piloto.get("speed", 0)
                aceleracao_combinada = dados.get("aceleracao", 0) + piloto.get("aceleracao", 0)
                direcao_equipe = dados.get("direcao", dados.get("freio", 3))
                direcao_combinada = direcao_equipe + piloto["direcao"]
                freio_piloto = piloto.get("freio", 3)

                # ---> O CÉREBRO DA CLASSIFICAÇÃO <---
                # Avalia o quão bom este bot é para saber se ele é Classe S, A, B, etc.
                forca_total = vel_maxima_do_carro + (aceleracao_combinada * 15) + (direcao_combinada * 15)

                bots_temporarios.append({
                    "equipe": nome_eq,
                    "nome": piloto["nome"],
                    "speed": 0,
                    "max_speed": vel_maxima_do_carro, 
                    "aceleracao": aceleracao_combinada,
                    "freio": freio_piloto,             
                    "direcao": direcao_combinada,       
                    "cor_capacete": piloto["cor_capacete"],
                    "pasta": pasta,
                    "frame_idx": 0,
                    "anim_timer": 0,    
                    "defesa_timer": 0,
                    "forca_total": forca_total # Usado para organizar o grid
                })

        # =========================================================
        # 3.2 O NOVO SISTEMA DE QUALIFICAÇÃO DINÂMICA
        # =========================================================
        import random
        
        # 1. Aplica um fator de Sorte/Azar na volta de qualificação de cada bot
        for bot in bots_temporarios:
            # O bot pode ganhar ou perder até 35 "pontos de força" neste dia.
            # (Um carro de Classe B com +8 de sorte ultrapassa um Classe S com -8 de azar!)
            fator_sorte = random.randint(-8, 8)
            bot["forca_qualificacao"] = bot["forca_total"] + fator_sorte

        # 2. Ordena os bots do mais rápido para o mais lento com base na sua volta "sorteada"
        bots_temporarios.sort(key=lambda b: b["forca_qualificacao"], reverse=True)

        # 3. Cria a lista limpa de vagas (1 a 32), ignorando apenas a SUA posição
        posicoes_disponiveis = [p for p in range(1, 33) if p != posicao_jogador]

        # 4. Coloca os bots nas suas vagas finais
        for i, bot in enumerate(bots_temporarios):
            if i >= len(posicoes_disponiveis):
                break
            
            posicao_final = posicoes_disponiveis[i]
            bot["pos"] = 100 + ((32 - posicao_final) * espaco_grid)
            bot["x"] = 0.33 if posicao_final % 2 == 0 else -0.33
            bot["linha_padrao"] = bot["x"]
            
            # ---> ADICIONE ESTAS 3 LINHAS DE GRAVAÇÃO AQUI: <---
            bot["pos_inicial_grid"] = posicao_final
            bot["velocidade_maxima_corrida"] = 0
            bot["fator_sorte_qualificacao"] = bot.get("forca_qualificacao", 0) - bot.get("forca_total", 0)
            
            self.bots.append(bot)

        # Inicia a contagem decrescente
        self.timer_countdown = pygame.time.get_ticks()
        self.estado_jogo = "COUNTDOWN"
        self.race_finished = False

    def gerar_resultados(self):
        # 1. Junta você e todos os bots numa lista só
        corredores = [{
            # Usa exatamente o nome que está no JSON (Ex: PLAYER, VOCÊ, ou Ayrton Senna)
            "nome": getattr(self, "nome_jogador_formatado", "VOCÊ").upper(),
            "equipe": self.equipe_atual_jogador,
            "pos": self.car.position
        }]
        for bot in self.bots:
            corredores.append({
                "nome": bot["nome"],
                "equipe": bot["equipe"],
                "pos": bot["pos"]
            })
        
        # 2. Ordena pela posição (quem andou mais metros fica em primeiro)
        corredores.sort(key=lambda x: x["pos"], reverse=True)
        self.classificacao_final = corredores
        
        # 3. Calcula os pontos das Construtoras
        pontuacao = [10, 6, 4, 3, 2, 1] # Pontos para os 6 primeiros
        self.pontos_construtoras = {nome: 0 for nome in self.equipes.keys()}
        
        for i, piloto in enumerate(corredores):
            if i < len(pontuacao):
                self.pontos_construtoras[piloto["equipe"]] += pontuacao[i]
                
        # 4. Cria uma lista ordenada de construtoras para mostrar no ecrã
        self.classificacao_construtoras = sorted(
            self.pontos_construtoras.items(), 
            key=lambda x: x[1], 
            reverse=True
        )

    def renderizar_corrida(self, tempo_atual, keys):
        # 1. RENDERIZA O CHÃO E GUARDA OS SEGMENTOS
        segmentos = self.track.draw(self.screen, self.car.position, self.car.player_x)
        
        # 2. FILTRA OS BOTS VISÍVEIS
        visiveis = []
        for bot in self.bots:
            dist_view = (bot["pos"] - self.car.position) % self.track.total_track_length
            if 2 < dist_view < self.track.draw_distance:
                visiveis.append((dist_view, bot))
        visiveis.sort(key=lambda x: x[0], reverse=True)
        
        # 3. DESENHA OS BOTS NO HORIZONTE
        for dist, bot in visiveis:
            diferenca_x = bot["x"] - self.car.player_x
            if diferenca_x < -0.35: direcao_bot = "esq"
            elif diferenca_x > 0.35: direcao_bot = "dir"
            else: direcao_bot = "reto"

            chave_pista = f"rear_{direcao_bot}"
            pasta_bot = bot["pasta"]
            if chave_pista not in self.cache_sprites[pasta_bot]: 
                chave_pista = "rear_reto"
                
            img_atual = self.cache_sprites[pasta_bot][chave_pista][bot["frame_idx"]]
            indice = int(dist) - 1
            if 0 <= indice < len(segmentos):
                seg = segmentos[indice]
                img_w, img_h = img_atual.get_width(), img_atual.get_height()
                bot_h = int(seg["largura"] * 0.159)
                bot_w = int(bot_h * (img_w / img_h))
                
                # Trava de Gigantismo
                limite_tela_h = 333 
                if bot_h > limite_tela_h:
                    bot_h = limite_tela_h
                    bot_w = int(bot_h * (img_w / img_h))
                
                if bot_w > 0 and bot_h > 0:
                    img_res = self.redimensionar_bot_otimizado(img_atual, pasta_bot, chave_pista, bot["frame_idx"], bot_w, bot_h)
                    bx = seg["centro"] + (bot["x"] * seg["largura"]) - (bot_w // 2)
                    by = seg["y"] - bot_h
                    self.screen.blit(img_res, (bx, by))

        # 4. CALCULA POSIÇÃO EM TEMPO REAL PARA O HUD
        bots_a_frente = sum(1 for bot in self.bots if bot["pos"] > self.car.position)
        posicao_atual = 1 + bots_a_frente

        # 5. DESENHA O COCKPIT POR CIMA DE TUDO
        self.car.draw_cockpit(self.screen, keys, tempo_atual, self.track, self.bots, self.cache_sprites, posicao_atual)

    def eventos_teclado(self):
        # ==========================================
            # 1. LOOP DE EVENTOS (Teclado para Menus)
            # ==========================================
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.car: self.car.cleanup() 
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                
                    # ------------------------------------------
                    # TELA 1: DIGITAR NOME
                    # ------------------------------------------
                    if self.estado_jogo == "INPUT_NAME":
                        if event.key == pygame.K_RETURN:
                            if self.nome_digitado.strip() == "":
                                self.nome_digitado = "PILOTO"
                                
                            # Prepara a tela seguinte (Seleção de Equipa)
                            self.lista_equipes_nomes = list(self.equipes.keys())
                            self.equipe_sel_idx = 0
                            self.piloto_sel_idx = 0
                            self.estado_jogo = "SELECT_TEAM"  # <--- VAI PARA EQUIPAS
                            
                        elif event.key == pygame.K_BACKSPACE:
                            self.nome_digitado = self.nome_digitado[:-1]
                        else:
                            if len(self.nome_digitado) < 12 and event.unicode.isprintable(): 
                                self.nome_digitado += event.unicode.upper()

                    # ------------------------------------------
                    # TELA 2: SELEÇÃO DE EQUIPA E PILOTO (NOVA)
                    # ------------------------------------------
                    elif self.estado_jogo == "SELECT_TEAM":
                        if event.key == pygame.K_RIGHT:
                            self.equipe_sel_idx = (self.equipe_sel_idx + 1) % len(self.lista_equipes_nomes)
                        elif event.key == pygame.K_LEFT:
                            self.equipe_sel_idx = (self.equipe_sel_idx - 1) % len(self.lista_equipes_nomes)
                        elif event.key == pygame.K_DOWN or event.key == pygame.K_UP:
                            self.piloto_sel_idx = 1 - self.piloto_sel_idx # Alterna entre 0 e 1 (1º e 2º piloto)
                        elif event.key == pygame.K_RETURN:
                            self.estado_jogo = "SELECT_POS" # <--- VAI PARA POSIÇÃO

                    # ------------------------------------------
                    # TELA 3: ESCOLHER POSIÇÃO
                    # ------------------------------------------
                    elif self.estado_jogo == "SELECT_POS":
                        if not hasattr(self, 'posicao_jogador'):
                            self.posicao_jogador = 32
                            
                        if event.key == pygame.K_RIGHT:
                            self.posicao_jogador = 1 if self.posicao_jogador > 31 else self.posicao_jogador + 1
                        elif event.key == pygame.K_LEFT:
                            self.posicao_jogador = 32 if self.posicao_jogador < 2 else self.posicao_jogador - 1
                        elif event.key == pygame.K_DOWN:
                            self.posicao_jogador = self.posicao_jogador - 32 if self.posicao_jogador > 24 else self.posicao_jogador + 8
                        elif event.key == pygame.K_UP:
                            self.posicao_jogador = self.posicao_jogador + 32 if self.posicao_jogador < 9 else self.posicao_jogador - 8
                        elif event.key == pygame.K_RETURN:
                            # Prepara a tela seguinte (Seleção de Voltas)
                            self.opcoes_voltas = [1, 3, 5, 10, 15, 30]
                            self.volta_sel_idx = 1 # O padrão é o índice 1 (que são 3 voltas)
                            self.estado_jogo = "SELECT_LAPS" # <--- VAI PARA VOLTAS

                    # ------------------------------------------
                    # TELA 4: SELEÇÃO DE VOLTAS (NOVA)
                    # ------------------------------------------
                    elif self.estado_jogo == "SELECT_LAPS":
                        if event.key == pygame.K_DOWN:
                            self.volta_sel_idx = (self.volta_sel_idx + 1) % len(self.opcoes_voltas)
                        elif event.key == pygame.K_UP:
                            self.volta_sel_idx = (self.volta_sel_idx - 1) % len(self.opcoes_voltas)
                        elif event.key == pygame.K_RETURN:
                            self.iniciar_corrida("rio")
                            self.estado_jogo = "LOADING" # <--- VAI PARA AS PISTAS

                    elif self.estado_jogo == "DEBUG_REPORT":
                        if event.key == pygame.K_RETURN:
                            # Quando aperta ENTER, sai do Debug e vai para a tela de Resultados normal!
                            self.estado_jogo = "RESULTADOS_CORRIDA"

                    # ------------------------------------------
                    # TELA 5: TELA DE RESULTADOS (FIM DA CORRIDA)
                    # ------------------------------------------
                    elif self.estado_jogo == "RESULTADOS_CORRIDA":
                        if event.key == pygame.K_RETURN:
                            # 1. Limpa a lista de bots e o seu carro para evitar lixo na memória
                            self.bots = []
                            self.car = None
                            
                            # 2. Reseta o nome digitado se quiser que o próximo jogador digite um novo,
                            # ou deixe comentado se quiser que o jogo "lembre" o último nome!
                            self.nome_digitado = "" 
                            
                            # 3. Devolve o jogador para o início do jogo (Digitar Nome)
                            self.estado_jogo = "RESULTADOS_CONSTRUTORES"
                    # ------------------------------------------
                    # TELA 6: TELA DOS CONSTRUTORES (FIM DA CORRIDA)
                    # ------------------------------------------
                    elif self.estado_jogo == "RESULTADOS_CONSTRUTORES":
                        if event.key == pygame.K_RETURN:
                            # 1. Limpa a lista de bots e o seu carro para evitar lixo na memória
                            self.bots = []
                            self.car = None
                            
                            # 2. Reseta o nome digitado se quiser que o próximo jogador digite um novo,
                            # ou deixe comentado se quiser que o jogo "lembre" o último nome!
                            self.nome_digitado = "" 
                            
                            # 3. Devolve o jogador para o início do jogo (Digitar Nome)
                            self.estado_jogo = "INPUT_NAME"

    def telas_menu(self, fonte_menu):
        # ==========================================
            # 2. RENDERIZAÇÃO DOS MENUS (AS TRAVAS ANTI-CRASH)
            # ==========================================
            if self.estado_jogo == "INPUT_NAME":
                self.ui.desenhar_tela_nome()  # <--- Agora puxa do ui.py!
                pygame.display.flip()
                self.clock.tick(FPS)
                return True 

            if self.estado_jogo == "SELECT_POS":
                self.ui.desenhar_tela_posicao() # <--- Agora puxa do ui.py!
                pygame.display.flip()
                self.clock.tick(FPS)
                return True

            # ==========================================
            # GAVETA NOVA: TELA DE LOADING
            # ==========================================
            if self.estado_jogo == "LOADING":
                # 1. Desenha o aviso e FORÇA o Pygame a mostrá-lo na tela
                self.screen.fill((20, 20, 25))
                texto = self.fonte_grande.render("LOADING ENGINE...", True, (255, 200, 0))
                self.screen.blit(texto, (WIDTH // 2 - texto.get_width() // 2, HEIGHT // 2 - 40))
                pygame.display.flip() 
                
                # 2. Roda a função pesada (o jogo vai congelar por ~1 segundo aqui)
                self.pre_aquecer_cache()
                
                # 3. Terminou de carregar? Inicia o relógio do GO! e vai para a pista
                self.timer_countdown = pygame.time.get_ticks()
                self.estado_jogo = "COUNTDOWN"
                return True
                
                # 4. Desenha o cockpit
                #posicao_inicial = 1 + sum(1 for bot in self.bots if bot["pos"] > self.car.position)
                #self.car.draw_cockpit(self.screen, keys, tempo_atual, self.track, self.bots, self.cache_sprites, posicao_inicial)
                

            # ==========================================
            # GAVETA 2: TELA DE RESULTADOS DOS PILOTOS
            # ==========================================
            if self.estado_jogo == "RESULTADOS_CORRIDA":
                self.screen.fill((20, 20, 50))
                titulo = fonte_menu.render("RACE RESULTS", True, (255, 255, 0))
                self.screen.blit(titulo, (WIDTH//2 - titulo.get_width()//2, 30))
                
                fonte_lista = pygame.font.SysFont('Arial', 24, bold=True)
                
                # Divide os 32 carros em 2 colunas
                for i, piloto in enumerate(self.classificacao_final):
                    sigla = piloto["equipe"][:3].upper() # Ex: "Madonna" vira "MAD"
                    texto = f"{i+1}. {piloto['nome']} ({sigla})"
                    
                    cor = (0, 255, 0) if piloto["nome"] == "VOCÊ" else (255, 255, 255)
                    img_txt = fonte_lista.render(texto, True, cor)
                    
                    # Lógica da Esquerda/Direita
                    if i < 16: 
                        x, y = WIDTH // 4 - 100, 100 + (i * 30)
                    else: 
                        x, y = 3 * (WIDTH // 4) - 100, 100 + ((i - 16) * 30)
                        
                    self.screen.blit(img_txt, (x, y))
                    
                aviso = fonte_lista.render("PRESS ENTER TO CONTINUE", True, (255, 0, 0))
                self.screen.blit(aviso, (WIDTH//2 - aviso.get_width()//2, HEIGHT - 50))
                
                pygame.display.flip()
                self.clock.tick(FPS)
                return True

            # ==========================================
            # GAVETA 3: TELA DAS CONSTRUTORAS
            # ==========================================
            if self.estado_jogo == "RESULTADOS_CONSTRUTORES":
                self.screen.fill((20, 20, 50))
                titulo = fonte_menu.render("CONSTRUCTORS CHAMPIONSHIP", True, (255, 255, 0))
                self.screen.blit(titulo, (WIDTH//2 - titulo.get_width()//2, 50))
                
                fonte_lista = pygame.font.SysFont('Arial', 30, bold=True)
                
                for i, (equipe, pts) in enumerate(self.classificacao_construtoras):
                    texto = f"{i+1}. {equipe}: {pts} PTS"
                    cor = (0, 255, 0) if equipe == self.equipe_atual_jogador else (255, 255, 255)
                    img_txt = fonte_lista.render(texto, True, cor)
                    
                    self.screen.blit(img_txt, (WIDTH // 2 - 150, 150 + (i * 35)))
                    
                aviso = fonte_lista.render("PRESS ENTER TO RETURN TO MENU", True, (255, 0, 0))
                self.screen.blit(aviso, (WIDTH//2 - aviso.get_width()//2, HEIGHT - 50))
                
    def fisica_colisao_bots(self, tempo_atual, keys):
            # Envia a lógica pesada para a mente brilhante do BotAI!
            curve_intensity, jogador_no_vacuo, menor_distancia_bot = self.ai.atualizar_bots(tempo_atual)

            # Alimenta a física e IA...
            self.car.update_physics(keys, tempo_atual, curve_intensity, self.steering_locked, no_vacuo=jogador_no_vacuo)
            
            # ---> GRAVA RECORDES DE VELOCIDADE DO PLAYER <---
            if self.car.speed > getattr(self.car, 'velocidade_maxima_corrida', 0):
                self.car.velocidade_maxima_corrida = self.car.speed
                
            # ---> GRAVA RECORDES DE VELOCIDADE DOS BOTS <---
            for bot in self.bots:
                if bot["speed"] > bot.get("velocidade_maxima_corrida", 0):
                    bot["velocidade_maxima_corrida"] = bot["speed"]

            self.track.update_parallax(self.car.speed, curve_intensity, keys)
            self.car.update_timer(self.track.total_track_length, self.lap_limit)

    def audio_dinamico(self, tempo_atual):
        # ==========================================
                # ÁUDIO DINÂMICO MULTI-CARRO (Radar 360º + Rev Engine)
                # ==========================================
                bots_audiveis = []
                raio_audicao = 50 
                
                for bot in self.bots:
                    dist_bruta = (bot["pos"] - self.car.position) % self.track.total_track_length
                    if dist_bruta > self.track.total_track_length / 2:
                        dist_bruta -= self.track.total_track_length
                        
                    dist_abs = abs(dist_bruta) 
                    
                    if dist_abs < raio_audicao:
                        bots_audiveis.append((dist_abs, bot))
                
                bots_audiveis.sort(key=lambda x: x[0])
                
                for i, canal in enumerate(self.canais_motor_bot):
                    if i < len(bots_audiveis):
                        dist, bot_som = bots_audiveis[i]
                        fator = dist / raio_audicao
                        
                        volume_calculado = ((1.0 - fator) ** 2) * 0.4
                        volume_seguro = max(0.0, volume_calculado)
                        
                        # ---> MÁGICA DO REV ENGINE <---
                        if self.estado_jogo == "COUNTDOWN":
                            import math
                            ritmo = 0.005 + ((bot_som["pos"] % 4) * 0.001)
                            fase_desalinhada = bot_som["pos"] * 3.7 
                            onda_rpm = math.sin((tempo_atual * ritmo) + fase_desalinhada) 
                            pitch_alvo = 0.75 + (onda_rpm * 0.15) 
                        else:
                            pitch_alvo = 0.6 + (1.0 - fator) * 0.35
                        
                        canal.set_gain(volume_seguro)
                        canal.set_pitch(max(0.4, pitch_alvo)) 
                        
                        if canal.get_state() != 4114: 
                            canal.play()
                    else:
                        canal.set_gain(0.0)

    def countdown_tela(self,tempo_atual):
        tempo_passado = tempo_atual - self.timer_countdown
        fonte_contagem = pygame.font.SysFont('Arial', 120, bold=True)
        
        if tempo_passado < 1000:
            texto = fonte_contagem.render("3", True, (255, 0, 0))
        elif tempo_passado < 2000:
            texto = fonte_contagem.render("2", True, (255, 128, 0))
        elif tempo_passado < 3000:
            texto = fonte_contagem.render("1", True, (255, 255, 0))
        elif tempo_passado < 4000:
            texto = fonte_contagem.render("GO!", True, (0, 255, 0))
        else:
            # ACABOU O TEMPO: LIGA A FÍSICA DA CORRIDA!
            if self.estado_jogo == "COUNTDOWN": # Garante que o impulso só acontece 1 vez
                self.estado_jogo = "RACING"
                self.car.lap_start_tick = tempo_atual 
                
                # ---> LARGADA REALISTA <---
                # Agora o carro não "teletransporta". 
                # Se o RPM estiver muito alto (acima de 70%), as rodas patinam e você perde tempo!
                rpm_ratio = self.car.rpm_neutro / self.car.max_speed
                
                if rpm_ratio > 0.7:
                    # Rodas patinando (Burnout): Perde tração, ganha menos velocidade
                    self.car.speed = (self.car.max_speed * 0.15) 
                else:
                    # Largada perfeita (Grip): Ganha velocidade controlada
                    self.car.speed = (self.car.rpm_neutro * 0.1) 
                
            texto = None
            
        if texto:
            # Centraliza o número na tela
            self.screen.blit(texto, (WIDTH//2 - texto.get_width()//2, HEIGHT//3))

    def final_corrida(self, tempo_atual):
        # Fundo escurecido
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        texto_finish = self.fonte_grande.render("FINISH!", True, (255, 200, 0))

        pos_texto = f"{self.final_position}º PLACE"
        cor_pos = (0, 255, 0) if self.final_position == 1 else (255, 255, 255)
        texto_rank = self.fonte_grande.render(pos_texto, True, cor_pos)
        
        self.screen.blit(texto_finish, (WIDTH//2 - texto_finish.get_width()//2, HEIGHT//2 - 100))
        self.screen.blit(texto_rank, (WIDTH//2 - texto_rank.get_width()//2, HEIGHT//2))
        
        # ---> O DELAY DE 5 SEGUNDOS <---
        if tempo_atual - self.timer_finish > 5000:
            self.car.parar_audios() 
            if hasattr(self, 'canais_motor_bot'):
                for canal in self.canais_motor_bot: canal.set_gain(0.0)

            # ==========================================
            # NOVO: COMPILAÇÃO DO RELATÓRIO DE TELEMETRIA
            # ==========================================
            self.dados_relatorio_corrida = []
            
            # 1. Guarda temporariamente os dados dos bots e a distância percorrida por eles
            for b in self.bots:
                self.dados_relatorio_corrida.append({
                    "nome": b["nome"], 
                    "is_player": False,
                    "pos_inicial": b["pos_inicial_grid"],
                    "pos_final": 32, # Vai ser calculado e corrigido no passo 2!
                    "vmax": b.get("velocidade_maxima_corrida", 0),
                    "sorte": b.get("fator_sorte_qualificacao", 0),
                    "distancia": b["pos"] # O Segredo: Quem tiver maior distância, ficou à frente!
                })
                
            # 2. Ordena os bots por quem andou mais longe
            self.dados_relatorio_corrida.sort(key=lambda x: x["distancia"], reverse=True)
            
            # 3. Atribui as posições oficiais (de 1º a 32º), mas SALTANDO a sua posição!
            posicao_atual_livre = 1
            for bot_data in self.dados_relatorio_corrida:
                # Se a posição atual for a sua, o bot fica com a posição seguinte
                if posicao_atual_livre == self.final_position:
                    posicao_atual_livre += 1
                    
                bot_data["pos_final"] = posicao_atual_livre
                posicao_atual_livre += 1
                
            # 4. Injeta o JOGADOR com a posição final e oficial dele
            self.dados_relatorio_corrida.append({
                "nome": self.nome_jogador_formatado, 
                "is_player": True,
                "pos_inicial": self.car.pos_inicial_grid,
                "pos_final": self.final_position, # A sua posição intocável!
                "vmax": self.car.velocidade_maxima_corrida,
                "sorte": 0 
            })
            
            # 5. Ordena o relatório final (Player + Bots) pela ordem de chegada para ficar bonito na tabela
            self.dados_relatorio_corrida.sort(key=lambda x: x["pos_final"])

            # Altera o estado do jogo para a tela de Telemetria!
            self.estado_jogo = "DEBUG_REPORT"
            return True
        
    def run(self):
        fonte_menu = pygame.font.SysFont('Arial', 50, bold=True)
        while True:
            tempo_atual = pygame.time.get_ticks()
            keys = pygame.key.get_pressed()

            self.eventos_teclado()

            if self.telas_menu(fonte_menu):
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            # ==========================================
            # FÍSICA, IA E COLISÃO DOS BOTS (UNIFICADA)
            # ==========================================
            # Física continua rodando no FINISH para o carro não congelar!
            if self.estado_jogo in ["RACING", "FINISH"]:
                self.fisica_colisao_bots(tempo_atual, keys)

                # VERIFICAÇÃO DE FIM DE CORRIDA
                if not self.race_finished and self.car.laps_completed >= self.lap_limit:
                    self.race_finished = True
                    self.estado_jogo = "FINISH" 
                    self.timer_finish = tempo_atual
                    self.gerar_resultados()
                    bots_a_frente = sum(1 for bot in self.bots if bot["pos"] > self.car.position)
                    self.final_position = 1 + bots_a_frente
                    self.car.speed *= 0.5

            if self.estado_jogo == "SELECT_TEAM":
                self.ui.desenhar_tela_equipes()
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            if self.estado_jogo == "SELECT_LAPS":
                self.ui.desenhar_tela_voltas()
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            if self.estado_jogo == "DEBUG_REPORT":
                self.ui.desenhar_tela_debug_relatorio()
                pygame.display.flip()
                self.clock.tick(FPS)
                continue


            # ==========================================
            # RENDERIZAÇÃO VISUAL DA PISTA E COCKPIT
            # ==========================================
            if self.estado_jogo in ["COUNTDOWN", "RACING", "FINISH"]:
                
                self.audio_dinamico(tempo_atual)

                if self.estado_jogo == "COUNTDOWN":
                    self.car.acelerar_neutro(keys)
                    
                    # --- MÁGICA: O SOM DO MOTOR DO PLAYER NO NEUTRO ---
                    if hasattr(self.car, 'motor_sound') and self.car.motor_sound:
                        rpm_falso = self.car.rpm_neutro / self.car.max_speed
                        self.car.motor_sound.set_gain(0.3 + (rpm_falso * 0.5))
                        self.car.motor_sound.set_pitch(0.6 + (rpm_falso * 0.8))
                        if self.car.motor_sound.get_state() != 4114:
                            self.car.motor_sound.play()

                # Desenha a pista, bots, horizonte e cockpit (Tudo de uma vez só!)
                self.renderizar_corrida(tempo_atual, keys)

                # --- MÁGICA DO COUNTDOWN NA TELA ---
                if self.estado_jogo == "COUNTDOWN":
                    self.countdown_tela(tempo_atual)

            # RESULTADO FINAL DA CORRIDA
            if self.estado_jogo == "FINISH":
                if self.final_corrida(tempo_atual):
                    continue
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()