# track.py
import pygame
from settings import *

class Track:
    def __init__(self):
        # Configurações de Câmera da Pista
        self.cam_height = 1000
        self.draw_distance = 200
        self.bg_x = 0
        self.bg_y = 0 # <-- NOVO: Permite o céu subir e descer!
        
        # Mapa do Rio
        self.track_map = [
                {"length": 1550, "curve": 0.0, "hill": 0.0},       # Reta de Largada/Boxes
                {"length": 80, "curve": 0.04, "hill": 0.0015},     # Curva de Sainte-Devote (Subindo)
                {"length": 250, "curve": 0.0, "hill": 0.002},      # Subida da Beau Rivage
                {"length": 60, "curve": -0.03, "hill": 0.0},      # Curva Massenet
                {"length": 60, "curve": 0.03, "hill": -0.001},     # Praça do Cassino (Descendo)
                {"length": 200, "curve": 0.0, "hill": -0.0015},    # Descida para a Mirabeau
                {"length": 80, "curve": -0.03, "hill": 0.0},        # Curva Mirabeau
                {"length": 250, "curve": 0.0, "hill": 0.0}, 
                {"length": 80, "curve": 0.01, "hill":  0.002},    # O Famoso "Grampo" / Hairpin (Ultra fechado)
                {"length": 100, "curve": 0.0, "hill": 0.0},
                {"length": 50, "curve": -0.02, "hill": 0.0},      # Curva Portier (Entrada do Túnel)
                {"length": 500, "curve": 0.01, "hill": 0.0},      # O Túnel (Reta longa em leve curva)
                {"length": 350, "curve": 0.0, "hill": 0.0}, 
                {"length": 80, "curve": -0.05, "hill": 0.0},      # Nova Chicane após o Túnel
                {"length": 220, "curve": 0.0, "hill": 0.0},       # Reta até a Tabac
                {"length": 60, "curve": -0.04, "hill": 0.0},      # Curva do Tabaco
                {"length": 350, "curve": 0.0, "hill": 0.0}, 
                {"length": 80, "curve": 0.03, "hill": 0.0},       # Chicane Louis Chiron
                {"length": 200, "curve": -0.02, "hill": 0.0},     # Seção das Piscinas
                {"length": 50, "curve": 0.06, "hill": 0.0},       # Curva Rascasse
                {"length": 40, "curve": 0.04, "hill": 0.0},       # Anthony Noghes (Entrada da Reta)
                {"length": 250, "curve": 0.0, "hill": 0.0}        # Reta Final
            ]
        self.total_track_length = sum(seg["length"] for seg in self.track_map)

        # Fundo (Parallax)
        try:
            self.bg_img = pygame.image.load("images/bg_rio.png").convert()
            self.bg_img = pygame.transform.scale(self.bg_img, (WIDTH * 3, HEIGHT // 2))
        except:
            print("AVISO: Imagem de fundo não encontrada. Usando montanhas falsas.")
            self.bg_img = pygame.Surface((WIDTH * 2, HEIGHT // 2))
            self.bg_img.fill((135, 206, 235))
            pygame.draw.polygon(self.bg_img, (34, 139, 34), [(0, HEIGHT//2), (600, 100), (1280, HEIGHT//2)]) 
            pygame.draw.polygon(self.bg_img, (46, 120, 80), [(1000, HEIGHT//2), (1600, 150), (2560, HEIGHT//2)])

    def get_curve(self, position):
        pos_atual = position % self.total_track_length
        dist_acumulada = 0
        for seg in self.track_map:
            dist_acumulada += seg["length"]
            if pos_atual < dist_acumulada:
                return seg["curve"]
        return 0

    def update_parallax(self, speed, curve_intensity, keys):
        if speed > 0:
            # O horizonte gira se o jogador virar o volante
            if keys[pygame.K_LEFT]: 
                self.bg_x += speed * 0.005 
            elif keys[pygame.K_RIGHT]: 
                self.bg_x -= speed * 0.005 
            
            # O horizonte gira naturalmente pela curva da pista
            self.bg_x -= curve_intensity * speed * 0.15

        # Looping infinito do fundo
        if self.bg_x <= -WIDTH:
            self.bg_x += WIDTH
        elif self.bg_x > 0:
            self.bg_x -= WIDTH

    def draw(self, screen, position, player_x):
        # 1. PARALLAX VERTICAL 
        current_hill = 0
        pos_atual = position % self.total_track_length
        dist_acumulada = 0
        for seg in self.track_map:
            dist_acumulada += seg["length"]
            if pos_atual < dist_acumulada:
                current_hill = seg.get("hill", 0.0)
                break
                
        target_bg_y = -current_hill * 1500
        self.bg_y += (target_bg_y - self.bg_y) * 0.05 
        
        screen.fill(GREEN_DARK)
        screen.blit(self.bg_img, (self.bg_x, self.bg_y))
        screen.blit(self.bg_img, (self.bg_x + WIDTH, self.bg_y))

        # 2. VARIÁVEIS DA PISTA
        dx = 0
        curva_x = 0
        dy = 0       
        colina_y = 0 
        pos_frac = position % 1 
        
        # ---> A MÁGICA: A lista que vai rastrear o chão em 3D!
        segmentos_pista = [] 
        
        for n in range(1, self.draw_distance):
            z_near = n - pos_frac
            z_far = n + 1 - pos_frac
            if z_near <= 0.001: z_near = 0.001

            p_near = self.cam_height / z_near
            p_far = self.cam_height / z_far
            
            pos_futura = (position + n) % self.total_track_length
            curva_n = 0
            colina_n = 0 
            dist_check = 0
            for seg in self.track_map:
                dist_check += seg["length"]
                if pos_futura < dist_check:
                    curva_n = seg["curve"]
                    colina_n = seg.get("hill", 0.0) 
                    break
            
            dx += curva_n
            curva_x += dx
            
            dy += colina_n
            colina_y += dy

            fator_cam = 6
            center_near = (WIDTH // 2) + ((curva_x - dx) * p_near) - (player_x * p_near * fator_cam)
            center_far = (WIDTH // 2) + (curva_x * p_far) - (player_x * p_far * fator_cam)

            fator_colina = 0.1
            y_near = (HEIGHT // 2) + p_near - ((colina_y - dy) * p_near * fator_colina)
            y_far = (HEIGHT // 2) + p_far - (colina_y * p_far * fator_colina)
            
            if y_far > y_near:
                y_far = y_near

            width_near = p_near * 6
            width_far = p_far * 6

            # ---> SALVA O PONTO EXATO DO CHÃO NESTE METRO
            segmentos_pista.append({
                "centro": center_near,
                "largura": width_near,
                "y": y_near,
                "escala": p_near
            })

            color_road = GRAY_DARK if (n + int(position)) % 6 > 3 else GRAY_LIGHT
            color_grass = GREEN_DARK if (n + int(position)) % 6 > 3 else GREEN_LIGHT
            color_zebra = RED if (n + int(position)) % 6 > 3 else WHITE
            
            # Linha de Largada
            if pos_futura < 5: 
                color_road = WHITE
                color_zebra = GRAY_DARK 
            
            # Desenha a pista
            altura_grama = max(1, (y_near - y_far) + 1)
            pygame.draw.rect(screen, color_grass, (0, y_far, WIDTH, altura_grama))
            
            pygame.draw.polygon(screen, color_road, [
                (center_near - width_near, y_near), (center_near + width_near, y_near),
                (center_far + width_far, y_far), (center_far - width_far, y_far)
            ])
            
            zebra_w_near = width_near * 0.25 
            zebra_w_far = width_far * 0.25
            pygame.draw.polygon(screen, color_zebra, [(center_near - width_near - zebra_w_near, y_near), (center_near - width_near, y_near), (center_far - width_far, y_far), (center_far - width_far - zebra_w_far, y_far)])
            pygame.draw.polygon(screen, color_zebra, [(center_near + width_near, y_near), (center_near + width_near + zebra_w_near, y_near), (center_far + width_far + zebra_w_far, y_far), (center_far + width_far, y_far)])

        # ---> DEVOLVE A LISTA PARA O MAIN.PY!
        return segmentos_pista