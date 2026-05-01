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
        self.bot_base_w = 170  
        self.bot_base_h = 100  
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
                
                # Aplica a curva do volante
                if bot["x"] < target_x: bot["x"] += 0.04
                elif bot["x"] > target_x: bot["x"] -= 0.04

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
            self.car.update_timer(self.track.total_track_length)

            # ==========================================
            # 3. RENDERIZAÇÃO DOS CARROS E CENÁRIO
            # ==========================================
            segmentos = self.track.draw(self.screen, self.car.position, self.car.player_x)
            
            visiveis = []
            for bot in self.bots:
                dist_view = (bot["pos"] - self.car.position) % self.track.total_track_length
                if 2 < dist_view < self.track.draw_distance:
                    visiveis.append((dist_view, bot))
            
            visiveis.sort(key=lambda x: x[0], reverse=True)
            
            for dist, bot in visiveis:
                if bot["x"] < -0.2: direcao_bot = "esq"
                elif bot["x"] > 0.2: direcao_bot = "dir"
                else: direcao_bot = "reto"

                chave_pista = f"rear_{direcao_bot}"
                if chave_pista not in self.bot_sprites: chave_pista = "rear_reto"
                img_atual = self.bot_sprites[chave_pista][bot["frame_idx"]]

                indice = int(dist) - 1
                if 0 <= indice < len(segmentos):
                    seg = segmentos[indice]
                    
                    escala_na_pista = 0.45 
                    bot_w = int(seg["largura"] * escala_na_pista)
                    bot_h = int(bot_w * (bot["base_h"] / bot["base_w"]))
                    
                    limite_tela_w = 600
                    if bot_w > limite_tela_w:
                        bot_w = limite_tela_w
                        bot_h = int(bot_w * (bot["base_h"] / bot["base_w"]))
                    
                    if bot_w > 0 and bot_h > 0:
                        img_res = pygame.transform.scale(img_atual, (bot_w, bot_h))
                        bx = seg["centro"] + (bot["x"] * seg["largura"]) - (bot_w // 2)
                        by = seg["y"] - bot_h
                        self.screen.blit(img_res, (bx, by))

            # HUD e Espelho por último
            self.car.draw_cockpit(self.screen, keys, tempo_atual, self.track, self.bots, self.bot_sprites)
            
            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()