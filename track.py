# track.py
import pygame
import json
import os
import math
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
        self.nome_pista = "Brazil"

        # Estruturas de Objetos Laterais (Muretas e Placas)
        self.objetos_por_metro = {}
        self.obj_scale_cache = {}
        self.obj_base_surfaces = {}

        # Tenta carregar do arquivo JSON (se existir)
        caminho_json = track_file
        if track_file and not track_file.endswith(".json"):
            caminho_json = f"pistas/{track_file}.json"

        carregou_json = False
        dados = {}
        if caminho_json and os.path.exists(caminho_json):
            try:
                with open(caminho_json, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                self.nome_pista = dados.get("nome", "Pista")
                self.bg_image_path = dados.get("bg_image", "images/bg_rio.png")
                self.bg_custom_w = dados.get("bg_width", None)
                self.bg_custom_h = dados.get("bg_height", None)
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

        # Carrega e mapeia os objetos laterais (muretas e placas) da pista
        if carregou_json:
            catalogo = dados.get("objetos_catalogo", [])
            aplicacoes = dados.get("objetos_pista", [])
            self.carregar_objetos_pista(catalogo, aplicacoes)

        # Fundo (Parallax)
        if hasattr(self, 'bg_custom_w') and self.bg_custom_w is not None and hasattr(self, 'bg_custom_h') and self.bg_custom_h is not None:
            if self.bg_custom_h <= 200:
                final_bg_w = int(self.bg_custom_w * ((WIDTH * 3) / 2560))
                final_bg_h = int(self.bg_custom_h * ((HEIGHT // 2) / 135))
            else:
                final_bg_w = int(self.bg_custom_w)
                final_bg_h = int(self.bg_custom_h)
        else:
            final_bg_w = WIDTH * 3
            final_bg_h = HEIGHT // 2

        try:
            self.bg_img = pygame.image.load(self.bg_image_path).convert()
            self.bg_img = pygame.transform.scale(self.bg_img, (final_bg_w, final_bg_h))
        except Exception as e:
            print(f"AVISO: Imagem de fundo '{self.bg_image_path}' não encontrada ({e}). Usando montanhas falsas.")
            self.bg_img = pygame.Surface((final_bg_w, final_bg_h))
            self.bg_img.fill((135, 206, 235))
            pygame.draw.polygon(self.bg_img, (34, 139, 34), [(0, final_bg_h), (final_bg_w // 4, final_bg_h // 4), (final_bg_w, final_bg_h)])
            pygame.draw.polygon(self.bg_img, (46, 120, 80), [(final_bg_w // 3, final_bg_h), (final_bg_w // 2, final_bg_h // 3), (final_bg_w, final_bg_h)])

        # =========================================================================
        # GERAÇÃO DA GEOMETRIA 2D E MINIMAPA REAL
        # =========================================================================
        self.gerar_geometria_2d()
        self.preparar_minimapa(mapa_w=280, mapa_h=195, padding=18)

    def _carregar_surface_objeto(self, png_path):
        if png_path in self.obj_base_surfaces:
            return self.obj_base_surfaces[png_path]

        if png_path and os.path.exists(png_path):
            try:
                surf = pygame.image.load(png_path).convert_alpha()
                self.obj_base_surfaces[png_path] = surf
                return surf
            except Exception as e:
                print(f"Aviso Track: Falha ao carregar objeto '{png_path}': {e}")

        # Fallback visual caso o PNG não exista
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.rect(surf, (230, 40, 40), (4, 4, 56, 40), border_radius=4)
        pygame.draw.rect(surf, (255, 255, 255), (4, 4, 56, 40), width=3, border_radius=4)
        pygame.draw.rect(surf, (120, 120, 130), (28, 44, 8, 20))
        self.obj_base_surfaces[png_path] = surf
        return surf

    def carregar_objetos_pista(self, catalogo, aplicacoes):
        """ Mapeia os objetos replicados por trecho para cada metro exato da pista """
        self.objetos_por_metro = {}
        if not aplicacoes or self.total_track_length <= 0:
            return

        # Indexa catálogo por nome (combinando com biblioteca global se existir)
        mapa_catalogo = {}
        if os.path.exists("objetos_pista.json"):
            try:
                with open("objetos_pista.json", "r", encoding="utf-8") as f:
                    for item in json.load(f):
                        mapa_catalogo[item["nome"]] = item
            except Exception:
                pass

        for item in catalogo:
            mapa_catalogo[item["nome"]] = item

        # Calcula o metro inicial de cada segmento
        inicios_segmentos = []
        acc = 0
        for seg in self.track_map:
            inicios_segmentos.append(acc)
            acc += int(seg["length"])

        for ap in aplicacoes:
            seg_idx = int(ap.get("seg_idx", 0))
            if seg_idx < 0 or seg_idx >= len(self.track_map):
                continue

            nome_obj = ap.get("objeto", "")
            def_obj = mapa_catalogo.get(nome_obj)
            if not def_obj:
                continue

            png_path = def_obj.get("png", "")
            escala = float(def_obj.get("escala", 1.0))
            offset = float(def_obj.get("offset", 1.30))
            surf = self._carregar_surface_objeto(png_path)
            orig_w, orig_h = surf.get_width(), surf.get_height()

            lado = ap.get("lado", "esq")
            lados = ["esq", "dir"] if lado == "ambos" else [lado]
            quantidade = max(1, int(ap.get("quantidade", 1)))
            inicio_pct = max(0.0, min(99.0, float(ap.get("inicio_pct", 0.0))))

            seg_start = inicios_segmentos[seg_idx]
            seg_len = int(self.track_map[seg_idx]["length"])
            start_offset = int(seg_len * (inicio_pct / 100.0))
            usable_len = max(1, seg_len - start_offset)

            if quantidade == 1:
                metros_alvo = [(seg_start + start_offset) % self.total_track_length]
            else:
                passo = usable_len / float(quantidade)
                metros_alvo = [
                    (seg_start + start_offset + int(k * passo)) % self.total_track_length
                    for k in range(quantidade)
                ]

            for m in metros_alvo:
                if m not in self.objetos_por_metro:
                    self.objetos_por_metro[m] = []
                for ld in lados:
                    self.objetos_por_metro[m].append({
                        "png": png_path,
                        "surf": surf,
                        "orig_w": orig_w,
                        "orig_h": orig_h,
                        "lado": ld,
                        "escala": escala,
                        "offset": offset
                    })

    def _obter_sprite_objeto_escalado(self, obj, target_h):
        h_round = max(4, min(460, round(target_h / 4) * 4))
        chave = (obj["png"], h_round)
        if chave not in self.obj_scale_cache:
            w_round = max(2, int(h_round * (obj["orig_w"] / max(1, obj["orig_h"]))))
            self.obj_scale_cache[chave] = pygame.transform.scale(obj["surf"], (w_round, h_round))
        return self.obj_scale_cache[chave]

    def gerar_geometria_2d(self):
        raw_pts = []
        x, y = 0.0, 0.0
        ang = -math.pi / 2
        curve_factor = 0.5
        for seg in self.track_map:
            c = float(seg.get("curve", 0.0))
            l = int(seg.get("length", 100))
            for _ in range(l):
                ang += c * 1.0 * curve_factor
                x += math.cos(ang)
                y += math.sin(ang)
                raw_pts.append((x, y))

        self.total_track_length = len(raw_pts)
        if self.total_track_length == 0:
            self.pontos_2d_metros = [(0.0, 0.0)]
            self.circuito_fechado = False
            return

        dx = raw_pts[0][0] - raw_pts[-1][0]
        dy = raw_pts[0][1] - raw_pts[-1][1]
        dist_fechamento = math.hypot(dx, dy)
        self.circuito_fechado = (dist_fechamento < 150)

        self.pontos_2d_metros = []
        for i, (px, py) in enumerate(raw_pts):
            if self.circuito_fechado:
                frac = i / float(self.total_track_length)
                self.pontos_2d_metros.append((px + dx * frac, py + dy * frac))
            else:
                self.pontos_2d_metros.append((px, py))

    def preparar_minimapa(self, mapa_w=280, mapa_h=195, padding=18):
        self.mapa_w = mapa_w
        self.mapa_h = mapa_h

        if not hasattr(self, 'pontos_2d_metros') or not self.pontos_2d_metros:
            self.gerar_geometria_2d()

        xs = [p[0] for p in self.pontos_2d_metros]
        ys = [p[1] for p in self.pontos_2d_metros]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max(1.0, max_x - min_x)
        h = max(1.0, max_y - min_y)

        avail_w = max(10, mapa_w - padding * 2)
        avail_h = max(10, mapa_h - padding * 2)
        scale = min(avail_w / w, avail_h / h)

        off_x = (mapa_w / 2) - ((min_x + max_x) / 2) * scale
        off_y = (mapa_h / 2) - ((min_y + max_y) / 2) * scale

        self.pontos_minimapa = [(off_x + px * scale, off_y + py * scale) for px, py in self.pontos_2d_metros]

        self.minimap_surface = pygame.Surface((mapa_w, mapa_h), pygame.SRCALPHA)
        self.minimap_surface.fill((10, 14, 24, 180))
        pygame.draw.rect(self.minimap_surface, (45, 60, 85), (0, 0, mapa_w, mapa_h), width=1, border_radius=8)

        passo = max(1, len(self.pontos_minimapa) // 250)
        pts_linha = [self.pontos_minimapa[k] for k in range(0, len(self.pontos_minimapa), passo)]
        if not self.circuito_fechado or (pts_linha and pts_linha[-1] != self.pontos_minimapa[-1]):
            pts_linha.append(self.pontos_minimapa[-1])

        if len(pts_linha) > 1:
            pygame.draw.lines(self.minimap_surface, (30, 42, 60), self.circuito_fechado, pts_linha, width=6)
            pygame.draw.lines(self.minimap_surface, (160, 180, 210), self.circuito_fechado, pts_linha, width=2)

        if self.pontos_minimapa:
            p0 = self.pontos_minimapa[0]
            idx_next = min(len(self.pontos_minimapa) - 1, 10)
            p1 = self.pontos_minimapa[idx_next]
            vx = p1[0] - p0[0]
            vy = p1[1] - p0[1]
            mag = math.hypot(vx, vy)
            if mag > 0.001:
                nx, ny = -vy / mag, vx / mag
                larg_x1 = int(p0[0] + nx * 5)
                larg_y1 = int(p0[1] + ny * 5)
                larg_x2 = int(p0[0] - nx * 5)
                larg_y2 = int(p0[1] - ny * 5)
                pygame.draw.line(self.minimap_surface, (255, 220, 0), (larg_x1, larg_y1), (larg_x2, larg_y2), 3)

        try:
            fonte_rotulo = pygame.font.SysFont('Segoe UI', 11, bold=True)
            txt_pista = fonte_rotulo.render(self.nome_pista.upper(), True, (130, 155, 185))
            self.minimap_surface.blit(txt_pista, (10, 6))
        except Exception:
            pass

    def get_minimap_pos(self, pos):
        if not hasattr(self, 'pontos_minimapa') or not self.pontos_minimapa:
            return 0.0, 0.0
        total = len(self.pontos_minimapa)
        if total == 0:
            return 0.0, 0.0
        pos_mod = pos % total
        idx1 = int(pos_mod)
        idx2 = (idx1 + 1) % total
        frac = pos_mod - idx1
        x1, y1 = self.pontos_minimapa[idx1]
        x2, y2 = self.pontos_minimapa[idx2]
        return x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac

    def get_curve(self, position):
        indice = int(position) % self.total_track_length
        return self.track_data[indice]["curve"]

    def update_parallax(self, speed, curve_intensity, keys=None):
        if speed > 0 and curve_intensity != 0:
            self.bg_x -= curve_intensity * speed * 0.15

        img_w = self.bg_img.get_width()
        if self.bg_x <= -img_w:
            self.bg_x += img_w
        elif self.bg_x > 0:
            self.bg_x -= img_w

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
        bg_w = self.bg_img.get_width()
        bg_draw_x = self.bg_x % bg_w
        if bg_draw_x > 0:
            bg_draw_x -= bg_w
        curr_x = bg_draw_x
        while curr_x < WIDTH:
            screen.blit(self.bg_img, (curr_x, self.bg_y))
            curr_x += bg_w

        # 2. VARIÁVEIS DA PISTA
        dx = 0
        curva_x = 0
        dy = 0
        colina_y = 0
        pos_frac = position % 1

        segmentos_pista = []

        for n in range(1, self.draw_distance):
            z_near = n - pos_frac
            z_far = n + 1 - pos_frac
            if z_near <= 0.001:
                z_near = 0.001

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
                "escala": p_near,
                "indice_metro": indice_futuro
            })

            color_road = self.color_road_1 if (n + int(position)) % 6 > 3 else self.color_road_2
            color_grass = self.color_grass_1 if (n + int(position)) % 6 > 3 else self.color_grass_2
            color_zebra = self.color_zebra_1 if (n + int(position)) % 6 > 3 else self.color_zebra_2

            if indice_futuro < 8:
                color_road = WHITE
                color_zebra = GRAY_DARK

            altura_grama = max(1, (y_near - y_far) + 1)
            pygame.draw.rect(screen, color_grass, (0, y_far, WIDTH, altura_grama))

            pygame.draw.polygon(screen, color_road, [
                (center_near - width_near, y_near), (center_near + width_near, y_near),
                (center_far + width_far, y_far), (center_far - width_far, y_far)
            ])

            zebra_w_near = width_near * 0.25
            zebra_w_far = width_far * 0.25
            pygame.draw.polygon(screen, color_zebra, [
                (center_near - width_near - zebra_w_near, y_near), (center_near - width_near, y_near),
                (center_far - width_far, y_far), (center_far - width_far - zebra_w_far, y_far)
            ])
            pygame.draw.polygon(screen, color_zebra, [
                (center_near + width_near, y_near), (center_near + width_near + zebra_w_near, y_near),
                (center_far + width_far + zebra_w_far, y_far), (center_far + width_far, y_far)
            ])

        # 3. RENDERIZAÇÃO DE MURETAS E PLACAS (DE LONGE PARA PERTO / PAINTER'S ALGORITHM)
        if self.objetos_por_metro:
            for n in range(self.draw_distance - 1, 0, -1):
                seg = segmentos_pista[n - 1]
                objs = self.objetos_por_metro.get(seg["indice_metro"])
                if not objs:
                    continue

                for obj in objs:
                    obj_h = seg["largura"] * 0.25 * obj["escala"]
                    if obj_h < 3 or obj_h > 460:
                        continue

                    sprite = self._obter_sprite_objeto_escalado(obj, obj_h)
                    w_sp, h_sp = sprite.get_width(), sprite.get_height()

                    if obj["lado"] == "esq":
                        anchor_x = seg["centro"] - (obj["offset"] * seg["largura"])
                    else:
                        anchor_x = seg["centro"] + (obj["offset"] * seg["largura"])

                    blit_x = int(anchor_x - (w_sp // 2))
                    blit_y = int(seg["y"] - h_sp)

                    if blit_x + w_sp < 0 or blit_x > WIDTH:
                        continue

                    screen.blit(sprite, (blit_x, blit_y))

        return segmentos_pista