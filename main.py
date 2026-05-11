# main.py
import pygame
import sys
import math
import json
from settings import *
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
        self.equipe_atual_jogador = "Minarae"
        self.rival_atual = None
        self.vitorias_contra_rival = 0


        # ==========================================
        # ÁUDIO (Batida e Motor do Bot)
        # ==========================================
        self.timer_batida = 0 # Cronômetro para o som de amassar lata não bugar
        try:
            self.som_batida = pygame.mixer.Sound("sounds/batida.wav")
            self.som_bot_motor = pygame.mixer.Sound("sounds/bot_motor.wav")
            
            # O motor dos inimigos fica tocando em loop infinito (-1), 
            # mas começa mudo (volume 0). Nós vamos controlar o volume pela distância!
            self.som_bot_motor.play(-1) 
            self.som_bot_motor.set_volume(0) 
        except:
            print("Aviso: batida.wav ou bot_motor.wav não encontrados na pasta sounds!")
            self.som_batida = None
            self.som_bot_motor = None

        self.steering_locked = False
        
        # Define o tamanho original do seu PNG
        self.bot_base_w = 140  
        self.bot_base_h = 54  
        tamanho_bot = (self.bot_base_w, self.bot_base_h)
        
        self.bot_anim_timer = 0
        self.bot_frame_idx = 0

        # Dicionário de Animações
        self.bot_sprites = {
            "rear_reto": [
                carregar_img("images/cars/bot/rear_reto1.png", tamanho_bot),
                carregar_img("images/cars/bot/rear_reto1a.png", tamanho_bot),
                carregar_img("images/cars/bot/rear_reto1b.png", tamanho_bot)
            ],
            "front_reto": [
                carregar_img("images/cars/bot/front_reto1.png", tamanho_bot),
                carregar_img("images/cars/bot/front_reto1a.png", tamanho_bot),
                carregar_img("images/cars/bot/front_reto1b.png", tamanho_bot)
            ],
            "front_esq": [
                carregar_img("images/cars/bot/front_esq1.png", tamanho_bot),
                carregar_img("images/cars/bot/front_esq1a.png", tamanho_bot),
                carregar_img("images/cars/bot/front_esq1b.png", tamanho_bot)
            ],
            "front_dir": [
                carregar_img("images/cars/bot/front_dir1.png", tamanho_bot),
                carregar_img("images/cars/bot/front_dir1a.png", tamanho_bot),
                carregar_img("images/cars/bot/front_dir1b.png", tamanho_bot)
            ],
            "rear_esq": [
                carregar_img("images/cars/bot/rear_esq1.png", tamanho_bot),
                carregar_img("images/cars/bot/rear_esq1a.png", tamanho_bot),
                carregar_img("images/cars/bot/rear_esq1b.png", tamanho_bot)
            ],
            "rear_dir": [
                carregar_img("images/cars/bot/rear_dir1.png", tamanho_bot),
                carregar_img("images/cars/bot/rear_dir1a.png", tamanho_bot),
                carregar_img("images/cars/bot/rear_dir1b.png", tamanho_bot)
            ]
        }

        # --- A CORREÇÃO DO ERRO ---
        # Inicializa as variáveis no Frame Zero para o jogo não crashar na largada!
        self.bot_img_atual = self.bot_sprites["rear_reto"][0]
        self.bot_img_retro = self.bot_sprites["front_reto"][0]

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
            pasta_equipe = pasta_do_jogador  # <-- A MÁGICA ENTRA AQUI!
        )
            
        
        
        # 3. Limpa a lista e cria os Adversários (Bots) novos
        self.bots = []
        contador_pos = 0 
        
        for nome_eq, dados in self.equipes.items():
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
                
                # ADICIONA O BOT COM TODAS AS CHAVES OBRIGATÓRIAS
                self.bots.append({
                    "equipe": nome_eq,
                    "nome": piloto["nome"],
                    "pos": posicao_z,
                    "x": lado_pista, 
                    "speed": 0,
                    "max_speed": dados["velocidade_base"],
                    "aceleracao": dados.get("aceleracao", 1),
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
                    img_atual = self.bot_sprites["rear_reto"][0] # Na largada estão todos retos!
                    
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
                
                # 4. Desenha o cockpit (Adicionamos os parâmetros extras para o retrovisor funcionar na largada!)
                posicao_inicial = 1 + sum(1 for bot in self.bots if bot["pos"] > self.car.position)
                self.car.draw_cockpit(self.screen, keys, tempo_atual, self.track, self.bots, self.bot_sprites, posicao_inicial)
                
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
            # GAVETA 3: LÓGICA DO 3, 2, 1, GO! (NOVO)
            # ==========================================

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

            # Pega a curva da pista
            curve_intensity = self.track.get_curve(self.car.position)

            # ==========================================
            # 1. ATUALIZAÇÃO DOS BOTS, IA E COLISÃO
            # ==========================================
            self.steering_locked = False 
            menor_distancia_bot = 9999 # <--- NOVO: Variável para rastrear o som do motor
            
            jogador_no_vacuo = False

            for bot in self.bots:
                # ==========================================
                # IA BÁSICA (Aceleração Explosiva de F1)
                # ==========================================
                fator_curva = 5000 - ((bot["max_speed"] - 330) * 20)
                reducao_curva = abs(curve_intensity) * fator_curva
                target_speed = max(130, bot["max_speed"] - reducao_curva) 

                distancia_para_voce = self.car.position - bot["pos"]
                if bot["max_speed"] >= 380:
                    if distancia_para_voce > 200:
                        target_speed += 15  
                        if bot["speed"] > 160: bot["speed"] += 0.8 
                elif -100 < distancia_para_voce < 0 and bot["max_speed"] >= 370:
                    target_speed += 5

                # ==========================================
                # ACELERAÇÃO COM MOTORES REAIS (Física Corrigida)
                # ==========================================
                # O multiplicador agora é muito mais suave:
                # Nível 1: Força de 0.8x | Nível 7: Força de 1.4x
                forca_motor = 0.7 + (bot["aceleracao"] * 0.1)

                if bot["speed"] < target_speed: 
                    # Valores base reduzidos para mais de metade para simular o peso real do carro!
                    if bot["speed"] < 100: 
                        bot["speed"] += 0.5 * forca_motor  # 1ª Marcha pesada
                    elif bot["speed"] < 200: 
                        bot["speed"] += 0.7 * forca_motor  # 2ª e 3ª ganham tração
                    elif bot["speed"] < 280: 
                        bot["speed"] += 0.5 * forca_motor  # 4ª e 5ª perdem fôlego
                    else:
                        taxa_aceleracao = 0.4 * (1 - (bot["speed"] / (target_speed + 1)))
                        bot["speed"] += max(0.05, taxa_aceleracao * forca_motor) 
                        
                elif bot["speed"] > target_speed + 15: 
                    bot["speed"] -= 3.5  
                elif bot["speed"] > target_speed: 
                    bot["speed"] -= 0.8 

                # ==========================================
                # INTELIGÊNCIA DE DIREÇÃO E TRÁFEGO
                # ==========================================
                target_x = bot["x"] 
                
                dist_relativa = bot["pos"] - self.car.position 
                bot["pos"] += bot["speed"] * 0.005
                
                # --- NOVO: 1. VOCÊ PEGA O VÁCUO DESTE BOT ---
                # Se ele está entre 15 e 80 metros na sua frente e você a mais de 150 km/h
                if 15 < dist_relativa < 60 and self.car.speed > 150:
                    if abs(self.car.player_x - bot["x"]) < 0.4:
                        jogador_no_vacuo = True

                # 2. IA DE DEFESA 
                if 0 < dist_relativa < 60:
                    if tempo_atual > bot["defesa_timer"]:
                        target_x = self.car.player_x * 0.90 
                        if abs(bot["x"] - self.car.player_x) < 0.15:
                            bot["defesa_timer"] = tempo_atual + 2000 
                
                # 3. IA DE ULTRAPASSAGEM (Bot atrás de você)
                elif -80 < dist_relativa < 0 and bot["speed"] > self.car.speed:
                    
                    # --- NOVO: O BOT PEGA O SEU VÁCUO ANTES DE DESVIAR ---
                    if dist_relativa < -15 and abs(self.car.player_x - bot["x"]) < 0.4 and bot["speed"] > 200:
                        bot["speed"] += 0.5 # Ele ganha velocidade extra sugando o seu ar!

                    if abs(self.car.player_x - bot["x"]) < 0.4:
                        target_x = -0.6 if self.car.player_x > 0 else 0.6 
                        if dist_relativa > -10:
                            bot["speed"] -= 0.5  
                            if dist_relativa > -3: bot["speed"] = min(bot["speed"], self.car.speed)

                # 4. RADAR DE TRÁFEGO (Entre Bots)
                for outro_bot in self.bots:
                    if bot == outro_bot: continue
                    
                    dist_entre_bots = outro_bot["pos"] - bot["pos"]
                    
                    # --- NOVO: UM BOT PEGA VÁCUO DO OUTRO BOT ---
                    if 15 < dist_entre_bots < 80 and bot["speed"] > 200:
                        if abs(bot["x"] - outro_bot["x"]) < 0.4:
                            bot["speed"] += 0.5 

                    # Ultrapassagem Agressiva entre Bots
                    if 0 < dist_entre_bots < 40 and bot["speed"] > outro_bot["speed"]:
                        if abs(bot["x"] - outro_bot["x"]) < 0.45:
                            target_x = -0.6 if outro_bot["x"] > 0 else 0.6
                            if dist_entre_bots < 10:
                                bot["speed"] -= 1.5 
                                if dist_entre_bots < 3:
                                    bot["speed"] *= 0.8

                # ==========================================
                # DIREÇÃO SUAVE (Aplica o volante ao carro)
                # ==========================================
                # Aumentamos a velocidade do volante para eles desviarem mais rápido
                velocidade_volante = 0.018 
                bot["x"] += (target_x - bot["x"]) * velocidade_volante

                # ==========================================
                # COLISÃO ABSOLUTA (Barreira Impenetrável)
                # ==========================================
                hitbox_x = 0.15 # Largura lateral para bater
                
                # --- NOVO: HITBOX CIRÚRGICA ---
                # A distância de colisão agora muda se é você batendo neles, ou eles em você
                if dist_relativa > 0:
                    # VOCÊ batendo na frente (Hitbox maior por causa do bico)
                    bateu = (dist_relativa < 2.0) and (abs(self.car.player_x - bot["x"]) < hitbox_x)
                else:
                    # ELES batendo atrás (Hitbox minúscula, precisam encostar na asa!)
                    bateu = (abs(dist_relativa) < 0.8) and (abs(self.car.player_x - bot["x"]) < hitbox_x)

                dist_abs = abs(dist_relativa)
                if dist_abs < menor_distancia_bot:
                    menor_distancia_bot = dist_abs
                
                if bateu:
                    # Toca o som da batida
                    if tempo_atual - self.timer_batida > 500: 
                        if hasattr(self, 'som_batida') and self.som_batida: 
                            self.som_batida.play()
                        self.timer_batida = tempo_atual
                        
                    if dist_relativa > 0: 
                        # VOCÊ BATEU NA TRASEIRA DELE
                        self.car.position = bot["pos"] - 2.1 
                        self.car.speed = min(self.car.speed * 0.7, bot["speed"]) 
                    else: 
                        # ELE BATEU NA SUA TRASEIRA
                        # PUNIÇÃO SEVERA: O bot cometeu um erro e destrói a própria aerodinâmica!
                        bot["speed"] *= 0.4  # Ele perde 60% da velocidade na mesma hora!
                        
                        # O empurrão físico que você recebe ao tomar a batida
                        self.car.speed = min(self.car.max_speed, self.car.speed + 8) 
                        self.steering_locked = True 

                # Animação do pneu
                if tempo_atual - bot["anim_timer"] > 50: 
                    bot["frame_idx"] = (bot["frame_idx"] + 1) % 3
                    bot["anim_timer"] = tempo_atual

            # ==========================================
            # APLICA O EFEITO ESTILINGUE (VÁCUO) NO JOGADOR
            # ==========================================
            if jogador_no_vacuo and self.car.speed > 200:
                self.car.speed += 0.6 # Aceleração extra contínua
                
                # Permite ultrapassar a velocidade máxima real do carro em até 15 km/h!
                # Exemplo: Se o limite é 330, no vácuo ele vai a 345!
                limite_vacuo = self.car.max_speed + 15
                if self.car.speed > limite_vacuo:
                    self.car.speed = limite_vacuo

            # --- NOVO: SOM DINÂMICO DO MOTOR INIMIGO ---
            # Fica alinhado fora do 'for bot in self.bots:', logo antes de atualizar a SUA física
            if self.som_bot_motor:
                if menor_distancia_bot < 80: # Se tiver algum inimigo a menos de 80 metros
                    # A matemática mágica: 80m = Mudo. 0m (Colado em você) = Volume 0.5
                    volume_bot = (1.0 - (menor_distancia_bot / 80.0)) * 0.1
                    self.som_bot_motor.set_volume(volume_bot)
                else:
                    self.som_bot_motor.set_volume(0) # Fica mudo se todos estiverem longe

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
                if chave_pista not in self.bot_sprites: chave_pista = "rear_reto"
                img_atual = self.bot_sprites[chave_pista][bot["frame_idx"]]

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
                    bot_h = int(seg["largura"] * 0.188)
                    
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
            self.car.draw_cockpit(self.screen, keys, tempo_atual, self.track, self.bots, self.bot_sprites, posicao_atual)

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
                        self.som_bot_motor.set_volume(0)
                    if hasattr(self, 'som_batida') and self.som_batida:
                        self.som_batida.stop() # Para qualquer batida que esteja tocando

                    # 2. GERA AS TABELAS E MUDA DE TELA
                    self.gerar_resultados()
                    self.estado_jogo = "RESULTADOS_CORRIDA"
                    continue # Sai do modo corrida e vai para as telas de pontuação!
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()