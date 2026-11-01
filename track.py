# track.py
import pygame
import json
import os
from settings import *

class Track:
    def __init__(self, track_file="pistas/rio.json"):
        # Configurações de Câmera da Pista
        self.cam_height = 1000
        self.draw_distance = 200
        self.bg_x = 0
        self.bg_y = 0

        # Cores Padrão
        self.color_zebra_1 = RED
        self.color_zebra_2 = WHITE
        self.color_grass_1 = GREEN_DARK
        self.color_grass_2 = GREEN_LIGHT
        self.color_road_1 = GRAY_DARK
        self.color_road_2 = GRAY_LIGHT
        self.bg_image_path = "images/bg_rio.png"
        self.nome_pista = "Rio de Janeiro"

        # Tenta carregar do arquivo JSON (se existir)
        caminho_json = track_file
        if track_file and not track_file.endswith(".json"):
            caminho_json = f"pistas/{track_file}.json"

        carregou_json = False
        if caminho_json and os.path.exists(caminho_json):
            try:
                with open(caminho_json, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                self.nome_pista = dados.get("nome", "Pista")
                self.bg_image_path = dados.get("bg_image", "images/bg_rio.png")
                cores = dados.get("cores", {})
                self.color_zebra_1 = tuple(cores.get("zebra_1", RED))
                self.color_zebra_2 = tuple(cores.get("zebra_2", WHITE))
                self.color_grass_1 = tuple(cores.get("grama_1", GREEN_DARK))
                self.color_grass_2 = tuple(cores.get("grama_2", GREEN_LIGHT))
                self.color_road_1 = tuple(cores.get("asfalto_1", GRAY_DARK))
                self.color_road_2 = tuple(cores.get("asfalto_2", GRAY_LIGHT))

                self.track_map = []
                for s in dados.get("segmentos", []):
                    self.track_map.append({
                        "length": s.get("length", 100),
                        "curve": float(s.get("curve", 0.0)),
                        "hill": float(s.get("hill", 0.0))
                    })
                if self.track_map:
                    carregou_json = True
            except Exception as e:
                print(f"Aviso Track: Erro ao carregar pista de {caminho_json} ({e}). Usando padrão.")

        if not carregou_json:
            # Mapa Padrão de Backup (Rio)
            self.track_map = [
                {"length": 550, "curve": 0.0, "hill": 0.0},
                {"length": 80, "curve": 0.04, "hill": 0.0015},
                {"length": 250, "curve": 0.0, "hill": 0.002},
                {"length": 60, "curve": -0.03, "hill": 0.0},
                {"length": 60, "curve": 0.03, "hill": -0.0015},
                {"length": 156, "curve": 0.0, "hill": -0.002},
                {"length": 80, "curve": -0.03, "hill": 0.0},
                {"length": 150, "curve": 0.0, "hill": 0.001}, 
                {"length": 80, "curve": 0.01, "hill": 0.002},
                {"length": 80, "curve": 0.0, "hill": 0.0},
                {"length": 50, "curve": -0.02, "hill": -0.002},
                {"length": 50, "curve": 0.0, "hill": -0.001},
                {"length": 250, "curve": 0.00, "hill": 0.0},
                {"length": 150, "curve": 0.02, "hill": 0.0},
                {"length": 250, "curve": 0.03, "hill": 0.0016},
                {"length": 100, "curve": 0.0, "hill": 0.0014}, 
                {"length": 80, "curve": -0.05, "hill": 0.0},
                {"length": 120, "curve": 0.0, "hill": 0.0},
                {"length": 60, "curve": -0.04, "hill": 0.0},
                {"length": 150, "curve": 0.0, "hill": -0.0014}, 
                {"length": 150, "curve": 0.002, "hill": -0.0016},
                {"length": 150, "curve": 0.0029, "hill": 0.00},
                {"length": 80, "curve": 0.03, "hill": 0.0},
                {"length": 200, "curve": -0.02, "hill": 0.0},
                {"length": 50, "curve": 0.06, "hill": 0.0},
                {"length": 40, "curve": 0.04, "hill": 0.0},
                {"length": 150, "curve": 0.0, "hill": 0.0},
                {"length": 50, "curve": 0.06, "hill": 0.0},
                {"length": 40, "curve": 0.04, "hill": 0.0},
                {"length": 250, "curve": -0.03, "hill": 0.0}, 
                {"length": 250, "curve": -0.003, "hill": 0.0},
                {"length": 250, "curve": 0.003, "hill": 0.0},
                {"length": 350, "curve": 0.000, "hill": 0.0}
            ]

        self.total_track_length = sum(int(seg["length"]) for seg in self.track_map)
        
        # ==========================================
        # PRÉ-CARREGAMENTO MATEMÁTICO DA PISTA (O(1) Lookup)
        # ==========================================
        self.track_data = []
        for seg in self.track_map:
            for _ in range(int(seg["length"])):
                self.track_data.append({
                    "curve": seg["curve"],
                    "hill": seg.get("hill", 0.0)
                })
        self.total_track_length = len(self.track_data)

        # Fundo (Parallax)
        try:
            self.bg_img = pygame.image.load(self.bg_image_path).convert()
            self.bg_img = pygame.transform.scale(self.bg_img, (WIDTH * 3, HEIGHT // 2))
        except Exception as e:
            print(f"AVISO: Imagem de fundo '{self.bg_image_path}' não encontrada ({e}). Usando montanhas falsas.")
            self.bg_img = pygame.Surface((WIDTH * 2, HEIGHT // 2))
            self.bg_img.fill((135, 206, 235))
            pygame.draw.polygon(self.bg_img, (34, 139, 34), [(0, HEIGHT//2), (600, 100), (1280, HEIGHT//2)]) 
            pygame.draw.polygon(self.bg_img, (46, 120, 80), [(1000, HEIGHT//2), (1600, 150), (2560, HEIGHT//2)])

    def get_curve(self, position):
        indice = int(position) % self.total_track_length
        return self.track_data[indice]["curve"]

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
        
        screen.fill(self.color_grass_1)
        screen.blit(self.bg_img, (self.bg_x, self.bg_y))
        screen.blit(self.bg_img, (self.bg_x + WIDTH, self.bg_y))

        # 2. VARIÁVEIS DA PISTA
        dx = 0
        curva_x = 0
        dy = 0       
        colina_y = 0 
        pos_frac = position % 1 
        
        # ---> Rastreia o chão em 3D
        segmentos_pista = [] 
        
        for n in range(1, self.draw_distance):
            z_near = n - pos_frac
            z_far = n + 1 - pos_frac
            if z_near <= 0.001: z_near = 0.001

            p_near = self.cam_height / z_near
            p_far = self.cam_height / z_far
            
            indice_futuro = int((position + n) % self.total_track_length)
            curva_n = self.track_data[indice_futuro]["curve"]
            colina_n = self.track_data[indice_futuro]["hill"]
            
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

            segmentos_pista.append({
                "centro": center_near,
                "largura": width_near,
                "y": y_near,
                "escala": p_near
            })

            # Cores dinâmicas configuráveis
            color_road = self.color_road_1 if (n + int(position)) % 6 > 3 else self.color_road_2
            color_grass = self.color_grass_1 if (n + int(position)) % 6 > 3 else self.color_grass_2
            color_zebra = self.color_zebra_1 if (n + int(position)) % 6 > 3 else self.color_zebra_2

            # Grid de largada nos primeiros 8 metros
            if indice_futuro < 8: 
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
            
        return segmentos_pista
