# main.py
import pygame
import sys
import math
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
        
        self.track = Track()
        self.car = Car()

        self.race_finished = False
        self.final_position = 0
        self.lap_limit = 2 # Definimos aqui o limite de 6 voltas

        self.bots = []
        for i in range(10): # Ajuste a quantidade que quiser
            self.bots.append({
                "pos": -100 + (i * 50), 
                "x": (i % 3 - 1) * 0.5,
                "speed": 100, # A velocidade que ele LARGA (pode deixar todos em 100)
                
                # --- A MÁGICA ESTÁ AQUI ---
                # Cada bot terá um motor diferente. O primeiro terá 250km/h, o segundo 255, etc.
                "max_speed": 250 + (i * 5), 
                
                "base_w": 180,
                "base_h": 100,
                "frame_idx": 0,
                "anim_timer": 0,
                "defesa_timer": 0
            })

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

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.car.cleanup() 
                    pygame.quit()
                    sys.exit()

            keys = pygame.key.get_pressed()
            tempo_atual = pygame.time.get_ticks()

            # Pega a curva da pista
            curve_intensity = self.track.get_curve(self.car.position)

            # ==========================================
            # 1. ATUALIZAÇÃO DOS BOTS, IA E COLISÃO
            # ==========================================
            self.steering_locked = False 
            menor_distancia_bot = 9999 # <--- NOVO: Variável para rastrear o som do motor
            
            for bot in self.bots:
                # ==========================================
                # IA BÁSICA (Aceleração Justa)
                # ==========================================
                reducao_curva = abs(curve_intensity) * 4500
                target_speed = max(100, bot["max_speed"] - reducao_curva) 

                # MUDANÇA AQUI: Aceleração realista igual a do Player!
                if bot["speed"] < target_speed: 
                    # Quanto mais perto da velocidade máxima, menos ele acelera (resistência do vento)
                    taxa_aceleracao = 1.0 * (1 - (bot["speed"] / bot["max_speed"]))
                    bot["speed"] += max(0.05, taxa_aceleracao) 
                    
                elif bot["speed"] > target_speed + 15: 
                    bot["speed"] -= 3.5  
                elif bot["speed"] > target_speed: 
                    bot["speed"] -= 0.8  

                bot["pos"] += bot["speed"] * 0.005

                # IA DE DIREÇÃO (Padrão: tentar abrir a curva)
                target_x = curve_intensity * -15.0 
                target_x = max(-0.6, min(0.6, target_x))
                
                dist_relativa = (bot["pos"] - self.car.position) % self.track.total_track_length
                if dist_relativa > self.track.total_track_length / 2:
                    dist_relativa -= self.track.total_track_length
                
                # ==========================================
                # IA DE ULTRAPASSAGEM (Vindo de trás)
                # ==========================================
                if -80 < dist_relativa < 0 and bot["speed"] > self.car.speed:
                    if abs(self.car.player_x - bot["x"]) < 0.8:
                        if self.car.player_x > 0: target_x = self.car.player_x - 0.6 
                        else: target_x = self.car.player_x + 0.6 
                        
                        if dist_relativa > -15 and abs(self.car.player_x - bot["x"]) < 0.4:
                            bot["speed"] -= 3.0 

                # ==========================================
                # IA DE DEFESA (Regra de 1 Movimento)
                # ==========================================
                elif 0 < dist_relativa < 50:
                    # Se ele NÃO estiver no período de punição (cooldown), ele tenta te fechar
                    if tempo_atual > bot["defesa_timer"]:
                        target_x = self.car.player_x 
                        
                        # Se ele conseguiu encostar o carro na mesma faixa que você (te bloqueou):
                        # Ele ganha uma punição de 3 segundos onde ele é obrigado a ceder espaço!
                        if abs(bot["x"] - self.car.player_x) < 0.15:
                            bot["defesa_timer"] = tempo_atual + 3000 # 3000 ms = 3 segundos
                    
                    else:
                        # Está de castigo (cooldown): Ele abre espaço e não tenta te fechar de novo!
                        # Ele volta para a linha padrão de corrida para você passar.
                        pass # O target_x já foi definido lá em cima como a linha de curva!
                
                # ==========================================
                # DIREÇÃO SUAVE (Interpolação Linear)
                # ==========================================
                # O bot vira o volante suavemente em direção ao alvo.
                # A velocidade do volante é 5% da distância restante (0.05)
                # Isso impede que ele "passe do ponto" e fique tremendo!
                velocidade_volante = 0.05
                bot["x"] += (target_x - bot["x"]) * velocidade_volante

                # ==========================================
                # COLISÃO ABSOLUTA (Barreira Impenetrável)
                # ==========================================
                hitbox_z = 3
                hitbox_x = 0.1
                
                dist_abs = abs(dist_relativa)
                
                # NOVO: Atualiza a distância do bot mais próximo para o áudio
                if dist_abs < menor_distancia_bot:
                    menor_distancia_bot = dist_abs
                
                if dist_abs < hitbox_z and abs(self.car.player_x - bot["x"]) < hitbox_x:
                    
                    # --- NOVO: TOCA O SOM DA BATIDA ---
                    # Usa o cooldown de 500ms para o som não repetir 60 vezes por segundo
                    if tempo_atual - self.timer_batida > 500: 
                        if self.som_batida: self.som_batida.play()
                        self.timer_batida = tempo_atual
                        
                    if dist_relativa > 0: 
                        # VOCÊ BATEU NA TRASEIRA DELE
                        self.car.position = bot["pos"] - (hitbox_z + 0.1) 
                        self.car.speed = min(self.car.speed * 0.7, bot["speed"]) 
                    else: 
                        # ELE BATEU NA SUA TRASEIRA
                        # --- A PUNIÇÃO DO BOT ---
                        # Corta a velocidade dele pela METADE! Ele vai ficar muito para trás.
                        bot["speed"] *= 0.5 
                        #Te dá um pequeno "empurrão" de 10 km/h para frente devido à batida
                        self.car.speed = min(self.car.max_speed, self.car.speed + 10)
                        self.steering_locked = True 

                # Animação do pneu
                if tempo_atual - bot["anim_timer"] > 50: 
                    bot["frame_idx"] = (bot["frame_idx"] + 1) % 3
                    bot["anim_timer"] = tempo_atual

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
            self.car.update_physics(keys, tempo_atual, curve_intensity, self.steering_locked)
            self.track.update_parallax(self.car.speed, curve_intensity, keys)
            self.car.update_timer(self.track.total_track_length, self.lap_limit)

            # ==========================================
            # 3. VERIFICAÇÃO DE FIM DE CORRIDA
            # ==========================================
            if not self.race_finished and self.car.laps_completed >= self.lap_limit:
                self.race_finished = True
                # Cálculo da posição: 1 (tu) + quantos bots estão à tua frente
                # Usamos a posição absoluta (metros totais percorridos)
                bots_a_frente = 0
                for bot in self.bots:
                    if bot["pos"] > self.car.position:
                        bots_a_frente += 1
                self.final_position = 1 + bots_a_frente
                
                # Opcional: Reduz a velocidade do carro gradualmente após a meta
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
            if self.race_finished:
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
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()