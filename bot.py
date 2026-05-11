import pygame
import os
import math
from utils import carregar_img

class Bot:
    def __init__(self, nome, equipe, pos_z, x, max_speed, aceleracao, pasta_equipe, cor_capacete, skill=5):
        self.nome = nome
        self.equipe = equipe
        self.pos = pos_z
        self.x = x
        self.speed = 0
        
        self.max_speed = max_speed
        self.aceleracao_nivel = aceleracao
        self.cor_capacete = cor_capacete
        self.skill = skill 
        
        self.defesa_timer = 0
        self.target_x = x
        self.frame_idx = 0
        
        # Carregamento de Imagens
        self.pasta = pasta_equipe
        
        # AGORA ELE CARREGA AS DUAS PERSPECTIVAS!
        self.sprites_front = self.carregar_sprites("front")
        self.sprites_rear = self.carregar_sprites("rear")

    def carregar_sprites(self, tipo_visao):
        """O tipo_visao agora recebe a palavra 'front' ou 'rear' e monta o nome do ficheiro"""
        caminho_base_carro = os.path.join("images", "cars", self.pasta)
        caminho_base_piloto = os.path.join("images", "pilotos", self.nome)
        
        # DINÂMICO: Procura por front_reto1.png OU rear_reto1.png
        nomes_carros = [f"{tipo_visao}_reto1.png", f"{tipo_visao}_esq1.png", f"{tipo_visao}_dir1.png"]
        nomes_capacetes = ["front_reto.png", "front_esq.png", "front_dir.png"]
        
        imgs_combinadas = []
        tamanho_cap = (30, 30)

        for i in range(3):
            # 1. CAPACETE
            caminho_capacete = os.path.join(caminho_base_piloto, nomes_capacetes[i])
            img_capacete = carregar_img(caminho_capacete, tamanho_cap)
            
            if not img_capacete:
                img_capacete = carregar_img(os.path.join(caminho_base_piloto, nomes_capacetes[0]), tamanho_cap)

            if not img_capacete:
                img_capacete = pygame.Surface(tamanho_cap, pygame.SRCALPHA)
                pygame.draw.circle(img_capacete, self.cor_capacete, (15, 15), 15)

            # 2. CARRO
            img_carro = carregar_img(os.path.join(caminho_base_carro, nomes_carros[i]), (160, 100)) 
            
            if not img_carro: 
                # Plano B: tenta a imagem reta daquele mesmo tipo (front ou rear)
                img_carro = carregar_img(os.path.join(caminho_base_carro, nomes_carros[0]), (160, 100))
                
            if not img_carro: 
                # Plano C: bot genérico
                img_carro = carregar_img(os.path.join("images", "cars", "bot", nomes_carros[i]), (160, 100))
                
            if not img_carro:
                img_carro = pygame.Surface((160, 100), pygame.SRCALPHA)
                img_carro.fill((200, 200, 200))

            # 3. CHROMA KEY
            img_carro.set_colorkey((255, 0, 255))
            img_final = pygame.Surface((160, 100), pygame.SRCALPHA)
            
            cap_x = (160 // 2) - (tamanho_cap[0] // 2)
            cap_y = int(100 * 0.20) 
            
            img_final.blit(img_capacete, (cap_x, cap_y))
            img_final.blit(img_carro, (0, 0))
            
            imgs_combinadas.append(img_final)
            
        return imgs_combinadas

    def update_fisica(self, curve_intensity):
        """Atualiza a aceleração, curva e movimento base do bot"""
        # IA de Curva (Skill afeta no futuro)
        fator_curva = 5000 - ((self.max_speed - 330) * 20)
        reducao_curva = abs(curve_intensity) * fator_curva
        target_speed = max(130, self.max_speed - reducao_curva)

        # Aceleração com multiplicador
        forca_motor = 0.7 + (self.aceleracao_nivel * 0.1)
        if self.speed < target_speed:
            if self.speed < 100: self.speed += 0.5 * forca_motor
            elif self.speed < 200: self.speed += 0.7 * forca_motor
            elif self.speed < 280: self.speed += 0.5 * forca_motor
            else: self.speed += 0.4 * (1 - (self.speed / (target_speed + 1))) * forca_motor
        elif self.speed > target_speed + 15: self.speed -= 3.5
        elif self.speed > target_speed: self.speed -= 0.8

        # Movimenta o Bot no Eixo Z
        self.pos += self.speed * 0.005

    def update_ia(self, player_car, todos_bots, tempo_atual):
        """Toda a lógica de ultrapassagem, vácuo e defesa"""
        self.target_x = self.x 
        dist_relativa = self.pos - player_car.position 
        
        # 1. IA DE DEFESA
        if 0 < dist_relativa < 60:
            if tempo_atual > self.defesa_timer:
                self.target_x = player_car.player_x * 0.90 
                if abs(self.x - player_car.player_x) < 0.15:
                    self.defesa_timer = tempo_atual + 2000 
        
        # 2. IA DE ULTRAPASSAGEM (Bot atrás do Player)
        elif -80 < dist_relativa < 0 and self.speed > player_car.speed:
            # Pega o vácuo do player
            if dist_relativa < -15 and abs(player_car.player_x - self.x) < 0.4 and self.speed > 200:
                self.speed += 0.5 

            if abs(player_car.player_x - self.x) < 0.4:
                self.target_x = -0.6 if player_car.player_x > 0 else 0.6 
                if dist_relativa > -10:
                    self.speed -= 0.5  
                    if dist_relativa > -3: self.speed = min(self.speed, player_car.speed)

        # 3. RADAR ENTRE BOTS
        for outro_bot in todos_bots:
            if self == outro_bot: continue
            dist_entre_bots = outro_bot.pos - self.pos
            
            # Vácuo entre bots
            if 15 < dist_entre_bots < 80 and self.speed > 200:
                if abs(self.x - outro_bot.x) < 0.4: self.speed += 0.5 

            # Desvio e anti-batida
            if 0 < dist_entre_bots < 40 and self.speed > outro_bot.speed:
                if abs(self.x - outro_bot.x) < 0.45:
                    self.target_x = -0.6 if outro_bot.x > 0 else 0.6
                    if dist_entre_bots < 10:
                        self.speed -= 1.5 
                        if dist_entre_bots < 3: self.speed *= 0.8 

    def aplicar_direcao(self):
        """Move o carro para os lados e ajusta a imagem"""
        velocidade_volante = 0.025 
        diff = self.target_x - self.x
        self.x += diff * velocidade_volante
        
        # Ajusta a animação do sprite
        if diff > 0.1: self.frame_idx = 2    # Virando Direita
        elif diff < -0.1: self.frame_idx = 1 # Virando Esquerda
        else: self.frame_idx = 0             # Reto

    def desenhar(self, screen, rect, no_espelho=False):
        if rect.width <= 0 or rect.height <= 0: return
        
        # ESCOLHE A LISTA CORRETA: Se for espelho, usa FRENTE. Se for pista normal, usa TRASEIRA.
        lista_certa = self.sprites_front if no_espelho else self.sprites_rear
        
        img_redim = pygame.transform.scale(lista_certa[self.frame_idx], (int(rect.width), int(rect.height)))
        
        # EFEITO DE ESPELHO REALISTA: Inverte o lado esquerdo com o direito!
        if no_espelho:
            img_redim = pygame.transform.flip(img_redim, True, False)
            
        screen.blit(img_redim, (rect.x, rect.y))
        
        # Pinta o Capacete no meio do Cockpit
        centro_x = rect.x + (rect.width // 2)
        topo_y = rect.y + int(rect.height * 0.25) # 25% a partir do topo
        raio = max(2, rect.width // 20)
        pygame.draw.circle(screen, self.cor_capacete, (centro_x, topo_y), raio)