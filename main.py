# main.py
import pygame
import sys
import math
import json
from settings import *
from openal import oalOpen, oalQuit
from track import Track
from car import Car
from utils import carregar_img
from ui import MenuUI


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
        # Inicializa a Interface de Menus e passa o jogo (self) para ela
        self.ui = MenuUI(self)

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
        # ÁUDIO 3D VIA OPENAL (Batida e Motor do Bot)
        # ==========================================
        self.timer_batida = 0 
        
        try:
            self.som_batida = oalOpen("sounds/batida.wav") 
            self.som_bot_motor = oalOpen("sounds/bot_motor.wav")
            
            # --- START DO ZERO ---
            if self.som_bot_motor:
                self.som_bot_motor.set_looping(True)
                self.som_bot_motor.set_gain(0.0) # Nasce mudo
                self.som_bot_motor.play()        # Fica tocando em silêncio no fundo
                
        except Exception as e:
            print(f"Aviso OpenAL: Erro ao carregar audios dos bots! Detalhes: {e}")
            self.som_batida = None
            self.som_bot_motor = None

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
        # LÊ O JSON PARA DESCOBRIR A SUA EQUIPA AUTOMATICAMENTE!
        # =========================================================
        self.nome_jogador_formatado = getattr(self, 'nome_digitado', "PILOTO")
        self.dados_do_meu_piloto = {} # <--- NOVO: Guarda as suas skills!
        
        for nome_eq, dados in self.equipes.items():
            for piloto in dados.get("pilotos", []):
                
                nome_json = str(piloto.get("nome", "")).upper()
                if piloto.get("is_player", False) or nome_json in ["PLAYER", "VOCÊ"]:
                    
                    self.equipe_atual_jogador = nome_eq
                    piloto["nome"] = self.nome_jogador_formatado 
                    piloto["is_player"] = True 
                    
                    self.dados_do_meu_piloto = piloto # <--- SALVA TUDO AQUI!
                    break

        # Descobre a pasta da equipe do jogador agora que já sabe onde você está
        nome_equipe = self.equipe_atual_jogador
        if nome_equipe in self.equipes:
            pasta_do_jogador = self.equipes[nome_equipe]["pasta"]
        else:
            pasta_do_jogador = "minarae" # Segurança caso a equipe não exista

        # 2. Carregar performance da sua equipe
        status = self.equipes[self.equipe_atual_jogador]
        
        # SOMA A VELOCIDADE DO CARRO + A SKILL "SPEED" DO SEU PILOTO
        vel_carro_base = status["velocidade_base"]
        minha_skill_speed = self.dados_do_meu_piloto.get("speed", 0)
        velocidade_final_jogador = vel_carro_base + minha_skill_speed

        # Passa a velocidade final turbinada para o carro!
        self.car = Car(
            velocidade_maxima = velocidade_final_jogador,
            nivel_aceleracao = status.get("aceleracao", 1) + self.dados_do_meu_piloto.get("aceleracao", 0),
            nivel_freio = self.dados_do_meu_piloto.get("freio", 3),
            nivel_direcao = self.dados_do_meu_piloto.get("direcao", 3),
            pasta_equipe = pasta_do_jogador
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

        # 1. Coloca o JOGADOR na pista
        # A posição 1 fica lá na frente (+ metros). A 32 fica atrás (100 metros).
        self.car.position = 100 + ((32 - posicao_jogador) * espaco_grid)
        self.car.player_x = 0.33 if posicao_jogador % 2 == 0 else -0.33
        
        bots_temporarios = []
        
        for nome_eq, dados in self.equipes.items():
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
        # 3.2 EMBARALHAMENTO DO GRID POR CLASSES
        # ==========================================
        # Ordena do bot mais forte para o mais fraco
        bots_temporarios.sort(key=lambda b: b["forca_total"], reverse=True)

        # Cria as zonas ignorando a posição do jogador
        pos_S = [p for p in range(1, 5) if p != posicao_jogador]   # 1º ao 4º
        pos_A = [p for p in range(5, 9) if p != posicao_jogador]   # 5º ao 8º
        pos_B = [p for p in range(9, 17) if p != posicao_jogador]  # 9º ao 16º
        pos_C = [p for p in range(17, 25) if p != posicao_jogador] # 17º ao 24º
        pos_D = [p for p in range(25, 33) if p != posicao_jogador] # 25º ao 32º

        # Embaralha quem fica na frente dentro da mesma classe!
        import random
        random.shuffle(pos_S)
        random.shuffle(pos_A)
        random.shuffle(pos_B)
        random.shuffle(pos_C)
        random.shuffle(pos_D)

        posicoes_disponiveis = pos_S + pos_A + pos_B + pos_C + pos_D

        # Coloca os bots nas suas vagas finais
        for i, bot in enumerate(bots_temporarios):
            # ==========================================
            # TRAVA DE SEGURANÇA ANTI-CRASH
            # ==========================================
            # Se já preenchemos todas as 31 vagas e ainda sobrou bot, 
            # interrompe o loop para não quebrar o jogo!
            if i >= len(posicoes_disponiveis):
                break
            
            posicao_final = posicoes_disponiveis[i]
            
            bot["pos"] = 100 + ((32 - posicao_final) * espaco_grid)
            bot["x"] = 0.33 if posicao_final % 2 == 0 else -0.33
            bot["linha_padrao"] = bot["x"]
            
            self.bots.append(bot)

        # 4. Iniciar contagem decrescente
        self.timer_countdown = pygame.time.get_ticks()
        self.estado_jogo = "COUNTDOWN"
        self.race_finished = False
        self.lap_limit = 3

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

    def run(self):
        fonte_menu = pygame.font.SysFont('Arial', 50, bold=True)
        while True:
            tempo_atual = pygame.time.get_ticks()
            keys = pygame.key.get_pressed()

            # ==========================================
            # 1. LOOP DE EVENTOS (Teclado para Menus)
            # ==========================================
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.car: self.car.cleanup() 
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN:
                
                    # TELA 1: DIGITAR O NOME
                    if self.estado_jogo == "INPUT_NAME":
                        if event.key == pygame.K_RETURN:
                            if self.nome_digitado.strip() == "":
                                self.nome_digitado = "PILOTO"
                            self.estado_jogo = "SELECT_POS" 
                            
                        elif event.key == pygame.K_BACKSPACE:
                            self.nome_digitado = self.nome_digitado[:-1]
                        else:
                            if len(self.nome_digitado) < 12 and event.unicode.isprintable(): 
                                self.nome_digitado += event.unicode.upper()

                    # TELA 2: ESCOLHER POSIÇÃO
                    elif self.estado_jogo == "SELECT_POS":
                        if not hasattr(self, 'posicao_jogador'):
                            self.posicao_jogador = 32
                            
                        # CORREÇÃO: event.key ao invés de event.type
                        if event.key == pygame.K_RIGHT:
                            self.posicao_jogador += 1
                            if self.posicao_jogador > 32: self.posicao_jogador = 1
                            
                        elif event.key == pygame.K_LEFT:
                            self.posicao_jogador -= 1
                            if self.posicao_jogador < 1: self.posicao_jogador = 32
                            
                        elif event.key == pygame.K_DOWN:
                            self.posicao_jogador += 8 
                            if self.posicao_jogador > 32: self.posicao_jogador -= 32
                            
                        elif event.key == pygame.K_UP:
                            self.posicao_jogador -= 8 
                            if self.posicao_jogador < 1: self.posicao_jogador += 32
                        
                        elif event.key == pygame.K_RETURN:
                            self.iniciar_corrida("rio")
                            self.estado_jogo = "LOADING"        

            # ==========================================
            # 2. RENDERIZAÇÃO DOS MENUS (AS TRAVAS ANTI-CRASH)
            # ==========================================
            if self.estado_jogo == "INPUT_NAME":
                self.ui.desenhar_tela_nome()  # <--- Agora puxa do ui.py!
                pygame.display.flip()
                self.clock.tick(FPS)
                continue 

            if self.estado_jogo == "SELECT_POS":
                self.ui.desenhar_tela_posicao() # <--- Agora puxa do ui.py!
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

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
                continue

            if self.estado_jogo == "COUNTDOWN":
                # 1. Desenha a pista E guarda os segmentos para os bots usarem
                segmentos = self.track.draw(self.screen, self.car.position, self.car.player_x)
                
                # 2. DESENHA OS BOTS PARADOS NO GRID DE LARGADA
                visiveis = []
                for bot in self.bots:
                    dist_view = (bot["pos"] - self.car.position) % self.track.total_track_length
                    if 2 < dist_view < self.track.draw_distance:
                        visiveis.append((dist_view, bot))

                visiveis.sort(key=lambda x: x[0], reverse=True)
                
                for dist, bot in visiveis:
                    # Agora ele vai no armário, procura a pasta da equipe deste bot e pega a imagem reta!
                    img_atual = self.cache_sprites[bot["pasta"]]["rear_reto"][0]
                    
                    indice = int(dist) - 1
                    if 0 <= indice < len(segmentos):
                        seg = segmentos[indice]
                        
                        img_w = img_atual.get_width()
                        img_h = img_atual.get_height()
                        
                        bot_h = int(seg["largura"] * 0.188)
                        bot_w = int(bot_h * (img_w / img_h))
                        
                        limite_tela_h = 333 
                        if bot_h > limite_tela_h:
                            bot_h = limite_tela_h
                            bot_w = int(bot_h * (img_w / img_h))
                        
                        if bot_w > 0 and bot_h > 0:
                            # ---> SUBSTITUA APENAS ESTA LINHA <---
                            img_res = self.redimensionar_bot_otimizado(img_atual, bot["pasta"], "rear_reto", 0, bot_w, bot_h)
                            
                            bx = seg["centro"] + (bot["x"] * seg["largura"]) - (bot_w // 2)
                            by = seg["y"] - bot_h
                            self.screen.blit(img_res, (bx, by))

                # 3. Aceleração no neutro
                self.car.acelerar_neutro(keys)
                
                # 4. Desenha o cockpit
                posicao_inicial = 1 + sum(1 for bot in self.bots if bot["pos"] > self.car.position)
                self.car.draw_cockpit(self.screen, keys, tempo_atual, self.track, self.bots, self.cache_sprites, posicao_inicial)
                

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
                continue

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
                
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            # ==========================================
            # FÍSICA, IA E COLISÃO DOS BOTS (UNIFICADA)
            # ==========================================
            # Pega a curva da pista para o jogador
            curve_intensity = self.track.get_curve(self.car.position)
            
            self.steering_locked = False 
            menor_distancia_bot = 9999 
            jogador_no_vacuo = False

            for bot in self.bots:
                
                # ---> A MÁGICA DA LARGADA (MODO SPRINT) <---
                # A IA entra em modo fúria (ignora freio de curva) APENAS nos primeiros 8 segundos!
                sprint_largada = (self.car.laps_completed == 0 and self.car.current_lap_time < 8)

                # ==========================================
                # 1. Distância Circular Perfeita
                # ==========================================
                dist_bruta = bot["pos"] - self.car.position
                dist_relativa = dist_bruta % self.track.total_track_length
                if dist_relativa > self.track.total_track_length / 2:
                    dist_relativa -= self.track.total_track_length

                # ==========================================
                # 1.5. EVENTO ALEATÓRIO: "FALHA MECÂNICA LÁ NA FRENTE"
                # ==========================================
                # O bot só tem problemas se estiver bem à sua frente e fora do seu ecrã (> 200 metros)
                if not bot.get("falha_mecanica", False):
                    if 200 < dist_relativa < (self.track.total_track_length / 2):
                        import random
                        # Sorteia 1 número entre 1 e 1500 por frame. 
                        # Isso garante que a cada corrida, 1 ou 2 carros lá na frente vão engasgar!
                        if random.randint(1, 1500) == 1:
                            bot["falha_mecanica"] = True
                            bot["fim_falha"] = tempo_atual + random.randint(5000, 9000) # O problema dura entre 5 e 9 segundos
                else:
                    # Verifica se o mecânico avisou no rádio que o problema já foi resolvido
                    if tempo_atual > bot.get("fim_falha", 0):
                        bot["falha_mecanica"] = False

                # ==========================================
                # 2. IA de Curvas Corajosas
                # ==========================================
                curva_do_bot = self.track.get_curve(bot["pos"])
                
                if abs(curva_do_bot) > 0.02 and not sprint_largada:
                    intensidade_curva = abs(curva_do_bot) * 5.0  
                    bonus_direcao = bot.get("direcao", 3) * 0.015 
                    
                    multiplicador_curva = 1.0 - intensidade_curva + bonus_direcao
                    
                    target_speed = bot["max_speed"] * multiplicador_curva
                    target_speed = min(bot["max_speed"], target_speed)
                    target_speed = max(150, target_speed) 
                else:
                    target_speed = bot["max_speed"]

                # O PEDAL DE FREIO
                if bot["speed"] > target_speed:
                    forca_freio = 4.0 + (bot.get("freio", 3) * 0.6)
                    bot["speed"] -= forca_freio 

                # ==================================================
                # 3. Aceleração Feroz e Controle de Largada (Launch Control)
                # ==================================================
                forca_motor = 0.25 + (bot["aceleracao"] * 0.1)
                arrancada_grid = (self.car.laps_completed == 0 and self.car.current_lap_time < 8)

                if bot["speed"] < target_speed: 
                    if bot["speed"] < 100: 
                        impulso = 1.5 if arrancada_grid else 0.8
                        bot["speed"] += impulso * forca_motor  
                        
                    elif bot["speed"] < 200: 
                        impulso = 1.8 if arrancada_grid else 0.5
                        bot["speed"] += impulso * forca_motor  
                        
                    elif bot["speed"] < 280: 
                        bot["speed"] += 0.3 * forca_motor  
                        
                    else:
                        taxa_acel = 0.6 * (1 - (bot["speed"] / (target_speed + 1)))
                        bot["speed"] += max(0.2 + (bot["aceleracao"] * 0.15), taxa_acel * forca_motor)
                        
                elif bot["speed"] > target_speed + 15: 
                    bot["speed"] -= 3.5  
                elif bot["speed"] > target_speed: 
                    bot["speed"] -= 0.8 

                # ==========================================
                # 4. O SISTEMA DE 3 LINHAS E TANGÊNCIA (RACING LINE)
                # ==========================================
                # Sorteia a linha de preferência do bot para as retas
                if "linha_reta" not in bot:
                    import random
                    # Atribui uma das 3 pistas rígidas: Linha 1, 2 ou 3.
                    bot["linha_reta"] = random.choice([-0.65, -0.21, 0.0, 0.21, 0.65])
                
                # ---> O CÉREBRO DA CURVA: Lê a pista 30 metros à frente! <---
                curva_futura = self.track.get_curve(bot["pos"] + 30)
                
                if curva_futura > 0.05:
                    # Vem aí uma Curva para a Direita -> Abre na Esquerda (Linha 1)
                    tracado_ideal = -0.65  
                elif curva_futura < -0.05:
                    # Vem aí uma Curva para a Esquerda -> Abre na Direita (Linha 3)
                    tracado_ideal = 0.65   
                else:
                    # É uma Reta -> Volta para a sua linha de corrida favorita
                    tracado_ideal = bot["linha_reta"] 
                
                # Define o destino base do bot
                target_x = tracado_ideal
                bot["pos"] += bot["speed"] * 0.005 

                #SENSOR DE VÁCUO
                if 1 < dist_relativa < 60 and self.car.speed > 100:
                    #SE A DIFERENÇA DA POSIÇAÕ HORIZONTAL ENTRE VOCê E O BOT FOR MENOR QUE 0.5 O VÁCUO É ATIVADO
                    if abs(self.car.player_x - bot["x"]) < 0.5: 
                        jogador_no_vacuo = True

                # ==========================================
                # REGRA DA LARGADA (MANTER AS LINHAS)
                # ==========================================
                # O grid mantém as 3 linhas por exatos 15 segundos após o sinal verde!
                if self.car.laps_completed == 0 and self.car.current_lap_time < 15:
                    # Na primeira volta, não há ataques. O grid organiza-se em 3 filas perfeitas!
                    for outro_bot in self.bots:
                        if bot == outro_bot: continue
                        dist_bruta_bots = outro_bot["pos"] - bot["pos"]
                        dist_entre_bots = dist_bruta_bots % self.track.total_track_length
                        if dist_entre_bots > self.track.total_track_length / 2: dist_entre_bots -= self.track.total_track_length
                        
                        if abs(dist_entre_bots) < 8:
                            distancia_lateral = bot["x"] - outro_bot["x"]
                            if abs(distancia_lateral) < 0.35:
                                target_x = bot["x"] + (0.3 if distancia_lateral > 0 else -0.3)
                else:
                    # ==========================================
                    # DA VOLTA 1 EM DIANTE: TÁTICAS LIBERADAS
                    # ==========================================
                    # 5. Táticas Contra o Jogador (Sistema de 3 Linhas)
                    jogador_na_pista = -1.0 <= self.car.player_x <= 1.0
                    
                    # 1º Passo: O bot faz a leitura de qual "LANE" você está ocupando agora
                    if self.car.player_x < -0.33:
                        linha_jogador = 1 # Você está na Esquerda
                    elif self.car.player_x > 0.33:
                        linha_jogador = 3 # Você está na Direita
                    else:
                        linha_jogador = 2 # Você está no Centro
                    
                    if 0 < dist_relativa < 60:
                        target_x = tracado_ideal
                        
                    elif -150 < dist_relativa < 0 and jogador_na_pista:
                        # RADAR DO RETROVISOR: Percebe você a 150 metros de distância!
                        if abs(dist_relativa) < 150 and bot["speed"] > self.car.speed:
                            
                            # Escolha Definitiva de Linha de Ultrapassagem (Lá de trás)
                            if linha_jogador == 2:
                                if curva_futura > 0.05: target_x = 0.65 
                                elif curva_futura < -0.05: target_x = -0.65 
                                else: target_x = -0.65 if bot["x"] < 0 else 0.65 
                                    
                            elif linha_jogador == 1:
                                target_x = 0.65 if curva_futura > 0.05 else 0.0
                                
                            elif linha_jogador == 3:
                                target_x = -0.65 if curva_futura < -0.05 else 0.0
                            
                            # Acelera apenas se já estiver fora da sua reta de colisão
                            if abs(bot["x"] - self.car.player_x) > 0.35: 
                                bot["speed"] += 0.5 
                                
                            # Golpe de Volante de Emergência (Se chegar a 25m e ainda estiver alinhado)
                            if abs(dist_relativa) < 25 and abs(bot["x"] - self.car.player_x) < 0.4:
                                target_x = 0.85 if bot["x"] >= self.car.player_x else -0.85
                                bot["speed"] = min(bot["speed"], self.car.speed * 0.95)

                    # 6. Radar de Tráfego IA vs IA
                    for outro_bot in self.bots:
                        if bot == outro_bot: continue
                        
                        dist_bruta_bots = outro_bot["pos"] - bot["pos"]
                        dist_entre_bots = dist_bruta_bots % self.track.total_track_length
                        if dist_entre_bots > self.track.total_track_length / 2: dist_entre_bots -= self.track.total_track_length
                        
                        if abs(dist_entre_bots) < 8:
                            distancia_lateral = bot["x"] - outro_bot["x"]
                            if abs(distancia_lateral) < 0.35:
                                target_x = bot["x"] + (0.3 if distancia_lateral > 0 else -0.3)

                        if 0 < dist_entre_bots < 45 and abs(bot["x"] - outro_bot["x"]) < 0.45:
                            target_x = -0.65 if outro_bot["x"] > 0 else 0.65

                    # Ultrapassagem
                    if 0 < dist_entre_bots < 45 and abs(bot["x"] - outro_bot["x"]) < 0.45:
                        target_x = -0.65 if outro_bot["x"] > 0 else 0.65

                # 7. Direção Dinâmica (Física do Volante Real)
                velocidade_volante = 0.025 + (bot["direcao"] * 0.005) 
                
                # ---> CRIAMOS UMA VARIÁVEL REAL PARA O VOLANTE <---
                # Mede a força exata que a IA está a fazer para mudar de faixa
                bot["steer_real"] = target_x - bot["x"]
                
                # Aplica a força real no eixo X do carro
                bot["x"] += bot["steer_real"] * velocidade_volante

                #    ==========================================
                # 8.  COLISÃO ABSOLUTA E HITBOX 3D
                #    ==========================================
                hitbox_x = 0.22 # Aumentamos de 0.15 para 0.22 (Bate roda com roda)
                
                # --- A MÁGICA DA PROFUNDIDADE 3D ---
                if dist_relativa > 0:
                    # ==========================================
                    # HITBOX "Y" DIANTEIRA (O bico do seu carro)
                    # ==========================================
                    # Este 3.5 é o limite! Se quiser que o bico do seu carro 
                    # bata mais cedo de longe, aumente para 4.0 ou 4.5.
                    bateu = (dist_relativa < 2.5) and (abs(self.car.player_x - bot["x"]) < hitbox_x)
                else:
                    # ==========================================
                    # HITBOX "Y" TRASEIRA (O motor do seu carro)
                    # ==========================================
                    # Este 1.5 é o limite! É a distância que a IA tem de chegar 
                    # da sua câmera para bater na sua traseira.
                    bateu = (abs(dist_relativa) < 1.5) and (abs(self.car.player_x - bot["x"]) < hitbox_x)

                dist_abs = abs(dist_relativa)
                if dist_abs < menor_distancia_bot:
                    menor_distancia_bot = dist_abs
                
                if bateu:
                    # Trava do som (para não estourar os alto-falantes a 60fps)
                    if tempo_atual - self.timer_batida > 500: 
                        if hasattr(self, 'som_batida') and self.som_batida: 
                            self.som_batida.play()
                        self.timer_batida = tempo_atual
                        
                    if dist_relativa > 0: 
                        # Rebate o seu carro para trás da zona de colisão
                        self.car.position = bot["pos"] - 3.6 
                        self.car.speed = min(self.car.speed * 0.7, bot["speed"]) 
                        
                        # ==================================================
                        # EMPURRÃO LATERAL (TRANSFERÊNCIA DE MOMENTO)
                        # ==================================================
                        if self.car.player_x < bot["x"]:
                            # Você está na Esquerda do bot -> Empurra ele para a DIREITA
                            bot["x"] += 0.15
                        else:
                            # Você está na Direita do bot -> Empurra ele para a ESQUERDA
                            bot["x"] -= 0.15
                            
                        # Limite para garantir que o empurrão não jogue ele para fora do mapa
                        bot["x"] = max(-0.95, min(0.95, bot["x"]))
                        # ==================================================
                        
                        # Memória de Batidas da IA
                        if tempo_atual - bot.get("tempo_ultima_batida", 0) > 10000:
                            bot["contador_batidas"] = 0
                            
                        bot["contador_batidas"] = bot.get("contador_batidas", 0) + 1
                        bot["tempo_ultima_batida"] = tempo_atual
                        
                        if bot["contador_batidas"] == 1:
                            bot["speed"] *= 0.7  
                        else:
                            bot["speed"] *= 0.9  
                            
                    else: 
                        # --- ELE BATEU NA SUA TRASEIRA ---
                        bot["speed"] *= 0.4  
                        self.car.speed = min(self.car.max_speed, self.car.speed + 8) 
                        self.steering_locked = True

                # 9. Animação
                if tempo_atual - bot["anim_timer"] > 50: 
                    bot["frame_idx"] = (bot["frame_idx"] + 1) % 3
                    bot["anim_timer"] = tempo_atual

                # 10. COMBO DE ULTRAPASSAGEM (Ataque de 3 seguidas)
                if dist_relativa > -5 and dist_relativa < 0 and bot["speed"] < self.car.speed:
                    self.ultrapassagens_combo += 1
                    self.timer_combo = tempo_atual
                
                if tempo_atual - self.timer_combo > 4000:
                    self.ultrapassagens_combo = 0

                if self.ultrapassagens_combo >= 3 and 0 < dist_relativa < 40:
                    # Correção da tremedeira: Agora ele assume a sua linha suavemente, sem somar infinitamente
                    target_x = self.car.player_x
                    bot["defesa_timer"] = tempo_atual + 2000

            # ==========================================
            # ÁUDIO DINÂMICO DOS BOTS (SISTEMA LIMPO)
            # ==========================================
            if hasattr(self, 'som_bot_motor') and self.som_bot_motor:
                
                # Só ouvimos bots que estão a menos de 150 metros
                raio_audicao = 80
                
                if menor_distancia_bot < raio_audicao:
                    # Fator vai de 0.0 (colado em você) até 1.0 (lá nos 150m)
                    fator = menor_distancia_bot / raio_audicao
                    
                    # VOLUME: Máximo de 0.6 (perto) caindo até 0.0 (longe)
                    volume = (1.0 - fator) * 0.6
                    self.som_bot_motor.set_gain(volume)
                    
                    # PITCH (AFINAÇÃO): 1.8 (agudo, perto) caindo até 0.8 (grave, longe)
                    pitch = 1.0 - (fator * 1.0)
                    self.som_bot_motor.set_pitch(max(0.68, min(3.0, pitch)))
                    
                    # Trava de segurança: Se a OpenAL dormir, a gente acorda ela!
                    if self.som_bot_motor.get_state() != 4114: # 4114 = PLAYING
                        self.som_bot_motor.play()
                
                else:
                    # Se não tem ninguém no raio de 150m, muta o som!
                    self.som_bot_motor.set_gain(0.0)

            # ==========================================
            # 2. ATUALIZA A SUA FÍSICA (COM A TRAVA)
            # ==========================================
            self.car.update_physics(keys, tempo_atual, curve_intensity, self.steering_locked, no_vacuo=jogador_no_vacuo)
            self.track.update_parallax(self.car.speed, curve_intensity, keys)
            self.car.update_timer(self.track.total_track_length, self.lap_limit)

            # ==========================================
            # 3. VERIFICAÇÃO DE FIM DE CORRIDA
            # ==========================================
            if not self.race_finished and self.car.laps_completed >= self.lap_limit:
                self.race_finished = True
                self.estado_jogo = "FINISH" 
                self.timer_finish = tempo_atual # <--- NOVO: Ativa o cronômetro de 5 segundos
                # =======================================================
                # CONGELA OS RESULTADOS AGORA! (NÃO ESPERA OS 5 SEGUNDOS)
                # =======================================================
                self.gerar_resultados()
                
                bots_a_frente = sum(1 for bot in self.bots if bot["pos"] > self.car.position)
                self.final_position = 1 + bots_a_frente
                self.car.speed *= 0.5

                

            # ==========================================
            # 4. RENDERIZAÇÃO DOS CARROS E CENÁRIO
            # ==========================================
            segmentos = self.track.draw(self.screen, self.car.position, self.car.player_x)
            
            visiveis = []
            for bot in self.bots:
                dist_view = (bot["pos"] - self.car.position) % self.track.total_track_length
                if 2 < dist_view < self.track.draw_distance:
                    visiveis.append((dist_view, bot))

            visiveis.sort(key=lambda x: x[0], reverse=True)
            
            for dist, bot in visiveis:
                
                # ==========================================
                # LÓGICA DE PERSPECTIVA 3D (VISÃO FRONTAL)
                # ==========================================
                # Subtrai a sua posição da posição dele para saber o ângulo relativo
                diferenca_x = bot["x"] - self.car.player_x
                
                #Margem para mudar o Sprite de perspectiva de visao do oponente
                # Se ele está à sua esquerda (negativo)
                if diferenca_x < -0.35: direcao_bot = "esq"
                # Se ele está à sua direita (positivo)
                elif diferenca_x > 0.35: direcao_bot = "dir"
                # Se ele está na mesma reta
                else: direcao_bot = "reto"

                chave_pista = f"rear_{direcao_bot}"
                pasta_bot = bot["pasta"] # Descobre de qual equipe o bot é
                
                if chave_pista not in self.cache_sprites[pasta_bot]: 
                    chave_pista = "rear_reto"
                    
                # Puxa o frame da animação usando as cores exclusivas dele!
                img_atual = self.cache_sprites[pasta_bot][chave_pista][bot["frame_idx"]]

                indice = int(dist) - 1
                if 0 <= indice < len(segmentos):
                    seg = segmentos[indice]
                    
                    # ==========================================
                    # LARGURA DINÂMICA (Pega o tamanho real de 180, 140 ou 114)
                    # ==========================================
                    img_w = img_atual.get_width()
                    img_h = img_atual.get_height()
                    
                    # 1. Calculamos a ALTURA primeiro! 
                    # FATOR_ESCALA! O 0.188 é a escala matemática exata para a altura base.
                    bot_h = int(seg["largura"] * 0.159)
                    
                    # 2. A largura se adapta automaticamente para manter a proporção do seu PNG!
                    bot_w = int(bot_h * (img_w / img_h))
                    
                    # Anti-Gigantismo (Trava de limite para não cobrir o céu)
                    limite_tela_h = 333 
                    if bot_h > limite_tela_h:
                        bot_h = limite_tela_h
                        bot_w = int(bot_h * (img_w / img_h))
                    
                    if bot_w > 0 and bot_h > 0:
                        img_res = self.redimensionar_bot_otimizado(img_atual, pasta_bot, chave_pista, bot["frame_idx"], bot_w, bot_h)
                        
                        bx = seg["centro"] + (bot["x"] * seg["largura"]) - (bot_w // 2)
                        by = seg["y"] - bot_h
                        self.screen.blit(img_res, (bx, by))

            # --- CÁLCULO DA POSIÇÃO EM TEMPO REAL ---
            bots_a_frente = 0
            for bot in self.bots:
                # Quem tem mais metros percorridos no total está na frente
                if bot["pos"] > self.car.position:
                    bots_a_frente += 1
            posicao_atual = 1 + bots_a_frente

            # Agora, passamos esse valor 'posicao_atual' para dentro do draw_cockpit
            self.car.draw_cockpit(self.screen, keys, tempo_atual, self.track, self.bots, self.cache_sprites, posicao_atual)

            # RESULTADO FINAL DA CORRIDA
            if self.estado_jogo == "FINISH":
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
                
                # ---> NOVO: O DELAY DE 5 SEGUNDOS <---
                if tempo_atual - self.timer_finish > 5000:
                    # 1. CALA TODOS OS SONS DA PISTA!
                    self.car.parar_audios() 
                    
                    if hasattr(self, 'som_bot_motor') and self.som_bot_motor:
                        self.som_bot_motor.set_gain(0.0)
                        try: self.som_bot_motor.stop()
                        except: pass

                    # 2. MUDA DE TELA (Apagamos a duplicação daqui!)
                    self.estado_jogo = "RESULTADOS_CORRIDA"
                    continue # Sai do modo corrida e vai para as telas de pontuação!
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()