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


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Super Monaco GP - Rio Edition")
        self.clock = pygame.time.Clock()
        
        self.estado_jogo = "MENU"
        self.track = None
        self.car = None

        
        self.ultrapassagens_combo = 0
        self.timer_combo = 0

        self.race_finished = False
        self.final_position = 0
        self.lap_limit = 2 # Definimos aqui o limite de 6 voltas

        # ==========================================
        # CARREGAR BANCO DE DADOS VIA JSON
        # ==========================================
        try:
            with open('equipes.json', 'r', encoding='utf-8') as f:
                self.equipes = json.load(f)
        except FileNotFoundError:
            print("ERRO: Ficheiro equipes.json não encontrado!")
            self.equipes = {} # Evita que o jogo crash imediatamente

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

    def carregar_sprites_equipe(self, pasta_equipe):
        """Carrega os 18 frames de uma equipe, usando o bot cinza como plano B (fallback)"""
        tamanho_bot = (self.bot_base_w, self.bot_base_h)
        
        def pegar_img(direcao, tipo, frame):
            nome_arquivo = f"{direcao}_{tipo}{frame}.png"
            caminho_equipe = f"images/cars/{pasta_equipe}/{nome_arquivo}"
            caminho_bot = f"images/cars/bot/{nome_arquivo}"
            
            # Tenta carregar a cor da equipe
            img = carregar_img(caminho_equipe, tamanho_bot)
            if not img:
                # Se não tiver, puxa a imagem original do bot genérico
                img = carregar_img(caminho_bot, tamanho_bot)
            if not img:
                # Segurança máxima anti-crash
                img = pygame.Surface(tamanho_bot, pygame.SRCALPHA)
            return img

        sprites = {}
        perspectivas = ["rear_reto", "front_reto", "front_esq", "front_dir", "rear_esq", "rear_dir"]
        sufixos = ["1", "1a", "1b"] # Os 3 frames da animação
        
        for pers in perspectivas:
            partes = pers.split('_') 
            direcao = partes[0]
            tipo = partes[1]
            
            sprites[pers] = []
            for suf in sufixos:
                sprites[pers].append(pegar_img(direcao, tipo, suf))
                
        return sprites

    def iniciar_corrida(self, track_name):
        # 1. Escolha da pista
        if track_name == "rio":
            self.track = Track()
            
        # Descobre a pasta da equipe do jogador lendo o JSON
        nome_equipe = self.equipe_atual_jogador
        if nome_equipe in self.equipes:
            pasta_do_jogador = self.equipes[nome_equipe]["pasta"]
        else:
            pasta_do_jogador = "minarae" # Segurança caso a equipe não exista

        # 2. Carregar performance da sua equipe
        status = self.equipes[self.equipe_atual_jogador]

        self.car = Car(
            velocidade_maxima=status["velocidade_base"], 
            nivel_aceleracao=status["aceleracao"],
            nivel_freio=status.get("freio", 1),       # Puxa do dict (padrão 1 se esquecer de por)
            nivel_direcao=status.get("direcao", 1),    # Puxa do dict (padrão 1 se esquecer de por)
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
        contador_pos = 0 
        
        for nome_eq, dados in self.equipes.items():
            pasta = dados["pasta"]
            
            # CARREGA OS SPRITES DESTA EQUIPE APENAS UMA VEZ E GUARDA NO ARMÁRIO!
            if pasta not in self.cache_sprites:
                self.cache_sprites[pasta] = self.carregar_sprites_equipe(pasta)
            for i, piloto in enumerate(dados["pilotos"]):
                
                # ZIG-ZAG DA LARGADA: Par = Esquerda (-0.5), Ímpar = Direita (0.5)
                lado_pista = -0.5 if contador_pos % 2 == 0 else 0.5
                
                # INVERSÃO DO GRID: A 1ª equipe (Madonna) ganha a maior posição Z (Lá na frente)
                # A última equipe (Zeroforece) ganha a menor (Lá atrás)
                posicao_z = 100 + ((31 - contador_pos) * 16)

                # ==========================================
                # O SEU CARRO NASCE AQUI!
                # ==========================================
                if nome_eq == self.equipe_atual_jogador and i == 1:
                    self.car.player_x = lado_pista
                    self.car.position = posicao_z
                    contador_pos += 1
                    continue 
                
                if piloto.get("is_player"): 
                    continue
                
                # =========================================================
                # SISTEMA RETRO EQUILIBRADO: MOTOR DA EQUIPE + ATRIBUTOS DO PILOTO
                # =========================================================
                vel_maxima_do_carro = dados["velocidade_base"]
                aceleracao_combinada = dados["aceleracao"] + piloto["aceleracao"]
                
                # --- DIREÇÃO COMBINADA DOS BOTS ---
                direcao_equipe = dados.get("direcao", dados.get("freio", 3))
                direcao_combinada = direcao_equipe + piloto["direcao"]
                
                freio_piloto = piloto.get("freio", 3)

                # === BLOCCO CORRIGIDO: O JOGADOR JÁ FOI CONFIGURADO ACIMA ===
                # Removemos a chamada errada de 'ajustar_atributos_equipe' daqui
                # para não quebrar a física do seu volante!
                if nome_eq == self.equipe_atual_jogador and piloto.get("is_player"):
                    contador_pos += 1
                    continue

                # ADICIONA O BOT COMBINANDO AS DUAS FORÇAS DE DIREÇÃO
                self.bots.append({
                    "equipe": nome_eq,
                    "nome": piloto["nome"],
                    "pos": posicao_z,
                    "x": lado_pista, 
                    "speed": 0,
                    "max_speed": vel_maxima_do_carro, 
                    "aceleracao": aceleracao_combinada,
                    "freio": freio_piloto,             
                    "direcao": direcao_combinada,       # <--- BOT AGORA VIRA BASEADO NO CHASSI + COMPORTAMENTO
                    "cor_capacete": piloto["cor_capacete"],
                    "pasta": dados["pasta"],
                    "frame_idx": 0,
                    "anim_timer": 0,    
                    "defesa_timer": 0   
                })
                contador_pos += 1

        # 4. Iniciar contagem decrescente
        self.timer_countdown = pygame.time.get_ticks()
        self.estado_jogo = "COUNTDOWN"
        self.race_finished = False
        self.lap_limit = 3

    def gerar_resultados(self):
        # 1. Junta você e todos os bots numa lista só
        corredores = [{
            "nome": "VOCÊ",
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

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.car: self.car.cleanup() 
                    pygame.quit()
                    sys.exit()

                # --- NOVO CONTROLE DE MENUS ---
                if event.type == pygame.KEYDOWN:
                    if self.estado_jogo == "MENU":
                        if event.key == pygame.K_RETURN: self.iniciar_corrida("rio")
                        elif event.key == pygame.K_2: self.iniciar_corrida("eua")
                        
                    # Aperta Enter para avançar nos resultados
                    elif self.estado_jogo == "RESULTADOS_CORRIDA" and event.key == pygame.K_RETURN:
                        self.estado_jogo = "RESULTADOS_CONSTRUTORES"
                    elif self.estado_jogo == "RESULTADOS_CONSTRUTORES" and event.key == pygame.K_RETURN:
                        self.estado_jogo = "MENU" # Volta para o Menu Principal

            keys = pygame.key.get_pressed()

            # ==========================================
            # GAVETA 1: DESENHO DO MENU
            # ==========================================
            if self.estado_jogo == "MENU":
                self.screen.fill((20, 20, 50))
                # (Desenha textos do menu aqui...)
                titulo = fonte_menu.render("SUPER MONACO GP\n Pressione 'Enter' para iniciar.", True, (255, 255, 0))
                self.screen.blit(titulo, (WIDTH//2 - titulo.get_width()//2, 150))
                
                pygame.display.flip()
                self.clock.tick(FPS)
                continue 

            # ==========================================
            # GAVETA 2: LÓGICA DO 3, 2, 1, GO! (NOVO)
            # ==========================================
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
                            img_res = pygame.transform.scale(img_atual, (bot_w, bot_h))
                            bx = seg["centro"] + (bot["x"] * seg["largura"]) - (bot_w // 2)
                            by = seg["y"] - bot_h
                            self.screen.blit(img_res, (bx, by))

                # 3. Aceleração no neutro
                self.car.acelerar_neutro(keys)
                
                # 4. Desenha o cockpit
                posicao_inicial = 1 + sum(1 for bot in self.bots if bot["pos"] > self.car.position)
                self.car.draw_cockpit(self.screen, keys, tempo_atual, self.track, self.bots, self.cache_sprites, posicao_inicial)
                
                # 5. Textos do Countdown
                segundos = (tempo_atual - self.timer_countdown) // 1000
                
                if segundos < 3:
                    txt = str(3 - segundos)
                    cor = (255, 0, 0)
                elif segundos == 3:
                    txt = "GO!"
                    cor = (0, 255, 0)
                else:
                    self.estado_jogo = "CORRIDA"
                    self.car.lap_start_tick = pygame.time.get_ticks()
                    continue

                img_txt = fonte_menu.render(txt, True, cor)
                self.screen.blit(img_txt, (WIDTH//2 - img_txt.get_width()//2, HEIGHT//2 - 100))
                
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            # ==========================================
            # GAVETA 4: TELA DE RESULTADOS DOS PILOTOS
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
            # GAVETA 5: TELA DAS CONSTRUTORAS
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
                # Se for a 1ª volta (0) e menos de 40 segundos, a IA entra em modo fúria!
                sprint_largada = True

                # 1. Distância Circular Perfeita
                dist_bruta = bot["pos"] - self.car.position
                dist_relativa = dist_bruta % self.track.total_track_length
                if dist_relativa > self.track.total_track_length / 2:
                    dist_relativa -= self.track.total_track_length

                # 2. IA de Curvas Corajosas
                curva_do_bot = self.track.get_curve(bot["pos"])
                
                # SPRINT: Ignora o limite de velocidade nas primeiras curvas!
                if abs(curva_do_bot) > 0.05 and not sprint_largada:
                    multiplicador_curva = 0.80 + (bot["direcao"] * 0.03)
                    target_speed = bot["max_speed"] * multiplicador_curva
                    target_speed = min(bot["max_speed"], target_speed)
                    target_speed = max(200, target_speed)
                else:
                    target_speed = bot["max_speed"]

                # 3. Aceleração Feroz
                forca_motor = 0.25 + (bot["aceleracao"] * 0.1)
                
                # SPRINT: Dá um "Nitro Invisível" de 50% a mais na potência dos motores!
                if sprint_largada:
                    forca_motor *= 1.5 

                if bot["speed"] < target_speed: 
                    if bot["speed"] < 100: bot["speed"] += 0.6 * forca_motor  
                    elif bot["speed"] < 200: bot["speed"] += 0.5 * forca_motor  
                    elif bot["speed"] < 280: bot["speed"] += 0.3 * forca_motor  
                    else:
                        taxa_acel = 0.6 * (1 - (bot["speed"] / (target_speed + 1)))
                        bot["speed"] += max(0.2 + (bot["aceleracao"] * 0.15), taxa_acel * forca_motor)
                elif bot["speed"] > target_speed + 15: bot["speed"] -= 3.5  
                elif bot["speed"] > target_speed: bot["speed"] -= 0.8 

                # 4. Personalidade e Vácuo
                if "linha_padrao" not in bot:
                    import random
                    bot["linha_padrao"] = random.uniform(-0.45, 0.45)
                
                target_x = bot["linha_padrao"]
                bot["pos"] += bot["speed"] * 0.005 

                if 15 < dist_relativa < 60 and self.car.speed > 150:
                    if abs(self.car.player_x - bot["x"]) < 0.4:
                        jogador_no_vacuo = True

                # 5. Táticas Contra o Jogador
                jogador_na_pista = -1.0 <= self.car.player_x <= 1.0
                # --- SITUAÇÃO A: BOT NA FRENTE (Mantém o traçado ideal) ---
                # A IA ignora o jogador e foca-se apenas em manter a linha de corrida
                if 0 < dist_relativa < 60:
                    # Tenta manter a posição X que definiu como "linha_padrao"
                    target_x = bot["linha_padrao"]
                elif -100 < dist_relativa < 0 and jogador_na_pista:
                    largura_radar = 0.45 if self.car.speed > 80 else 0.85
                    if abs(self.car.player_x - bot["x"]) < largura_radar:
                        if self.car.speed > 80:
                            if dist_relativa > -60: target_x = -0.75 if self.car.player_x > 0 else 0.75
                            if dist_relativa > -15 and abs(self.car.player_x - bot["x"]) < 0.25:
                                target_x = -0.85 if self.car.player_x > 0 else 0.85 
                                bot["speed"] = min(bot["speed"], self.car.speed * 0.95)
                        else:
                            if dist_relativa > -80: target_x = -0.85 if self.car.player_x > 0 else 0.85 
                            if dist_relativa > -15 and abs(self.car.player_x - bot["x"]) < 0.35:
                                bot["speed"] *= 0.85
                    
                    # Se mesmo assim chegar a menos de 10m, força o desvio total
                    elif abs(dist_relativa) < 10 and abs(bot["x"] - self.car.player_x) < 0.25:
                        target_x = -0.9 if self.car.player_x > 0 else 0.9
                        bot["speed"] *= 0.9 # Freio suave apenas em emergência

                # 6. Radar de Tráfego IA vs IA
                for outro_bot in self.bots:
                    if bot == outro_bot: continue
                    
                    dist_bruta_bots = outro_bot["pos"] - bot["pos"]
                    dist_entre_bots = dist_bruta_bots % self.track.total_track_length
                    if dist_entre_bots > self.track.total_track_length / 2:
                        dist_entre_bots -= self.track.total_track_length
                    
                    # Anti-Fantasma (Afasta em X)
                    if abs(dist_entre_bots) < 8:
                        distancia_lateral = bot["x"] - outro_bot["x"]
                        if abs(distancia_lateral) < 0.35:
                            bot["x"] += 0.02 if distancia_lateral > 0 else -0.02
                            bot["x"] = max(-0.85, min(0.85, bot["x"]))

                    # Ultrapassagem
                    if 0 < dist_entre_bots < 45 and abs(bot["x"] - outro_bot["x"]) < 0.45:
                        target_x = -0.65 if outro_bot["x"] > 0 else 0.65
                        
                        # SPRINT: Nos primeiros 40 segundos, a IA é proibida de usar o freio contra outros bots!
                        if dist_entre_bots < 10 and bot["speed"] > 50 and not sprint_largada:
                            bot["speed"] *= 0.95

                # 7. Direção Dinâmica
                velocidade_volante = 0.025 + (bot["direcao"] * 0.005) 
                bot["x"] += (target_x - bot["x"]) * velocidade_volante

                # ==========================================
                # COLISÃO ABSOLUTA E HITBOX 3D
                # ==========================================
                hitbox_x = 0.22 # Aumentamos de 0.15 para 0.22 (Bate roda com roda)
                
                # --- A MÁGICA DA PROFUNDIDADE 3D ---
                if dist_relativa > 0:
                    # VOCÊ batendo na frente. 
                    # A câmera é a sua cabeça! O bico do carro tem quase 4 metros na sua frente.
                    # Subimos a colisão de 2.0 para 5.5 metros!
                    bateu = (dist_relativa < 5.5) and (abs(self.car.player_x - bot["x"]) < hitbox_x)
                else:
                    # ELES batendo na sua traseira.
                    # O motor e a asa traseira estão uns 2 metros atrás de você.
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
                        # --- VOCÊ BATEU NA TRASEIRA DELE ---
                        self.car.position = bot["pos"] - 5.6 
                        
                        # A sua penalidade (Você perde sempre 30% para não abusar de bater)
                        self.car.speed = min(self.car.speed * 0.7, bot["speed"]) 
                        
                        # --- NOVA LÓGICA DE RESISTÊNCIA A PANCADAS DA IA ---
                        # Se passou mais de 10 segundos (10000 ms) desde a última batida, reseta a memória!
                        if tempo_atual - bot.get("tempo_ultima_batida", 0) > 10000:
                            bot["contador_batidas"] = 0
                            
                        # Regista a batida atual
                        bot["contador_batidas"] = bot.get("contador_batidas", 0) + 1
                        bot["tempo_ultima_batida"] = tempo_atual
                        
                        # Aplica o peso da batida
                        if bot["contador_batidas"] == 1:
                            # 1ª Pancada: Punição pesada (perde 30% da velocidade)
                            bot["speed"] *= 0.7  
                        else:
                            # 2ª Pancada em diante: Fica resistente (perde apenas 10% da velocidade)
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
                # Verifica se você ultrapassou alguém recentemente
                if dist_relativa > -5 and dist_relativa < 0 and bot["speed"] < self.car.speed:
                    self.ultrapassagens_combo += 1
                    self.timer_combo = tempo_atual
                
                # Reseta o combo se passar 4 segundos sem ultrapassar
                if tempo_atual - self.timer_combo > 4000:
                    self.ultrapassagens_combo = 0

                # Se o combo chegar a 3, o bot à frente ativa o "Modo Bloqueio"
                if self.ultrapassagens_combo >= 3 and 0 < dist_relativa < 40:
                    # O bot vira agressivamente para o seu X
                    target_x += (self.car.player_x - bot["x"]) * 0.5
                    # E trava o movimento para garantir que você não passa
                    bot["defesa_timer"] = tempo_atual + 2000

            # ==========================================
            # APLICA O EFEITO ESTILINGUE (VÁCUO) NO JOGADOR
            # ==========================================
            if jogador_no_vacuo and self.car.speed > 100: # tem que estar pelomenos a 100 por hora para pegar o vacuo
                self.car.speed += 0.37 # Aceleração extra contínua
                
                # Permite ultrapassar a velocidade máxima real do carro em até 15 km/h!
                # Exemplo: Se o limite é 330, no vácuo ele vai a 345!
                limite_vacuo = self.car.max_speed + 17
                if self.car.speed > limite_vacuo:
                    self.car.speed = limite_vacuo

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
                        img_res = pygame.transform.scale(img_atual, (bot_w, bot_h))
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
                
                fonte_grande = pygame.font.SysFont('Arial', 80, bold=True)
                texto_finish = fonte_grande.render("FINISH!", True, (255, 200, 0))
                
                pos_texto = f"{self.final_position}º PLACE"
                cor_pos = (0, 255, 0) if self.final_position == 1 else (255, 255, 255)
                texto_rank = fonte_grande.render(pos_texto, True, cor_pos)
                
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

                    # 2. GERA AS TABELAS E MUDA DE TELA
                    self.gerar_resultados()
                    self.estado_jogo = "RESULTADOS_CORRIDA"
                    continue # Sai do modo corrida e vai para as telas de pontuação!
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()