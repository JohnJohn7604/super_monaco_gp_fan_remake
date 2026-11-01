# track_editor.py
import pygame
import sys
import os
import math
import json
from settings import WIDTH, HEIGHT, FPS, WHITE, RED, GREEN_DARK, GREEN_LIGHT, GRAY_DARK, GRAY_LIGHT

# =============================================================================
# CORES E TEMA DA INTERFACE
# =============================================================================
COLOR_BG = (18, 22, 30)
COLOR_PANEL = (25, 32, 44)
COLOR_PANEL_HEADER = (35, 44, 60)
COLOR_BORDER = (45, 58, 80)
COLOR_TEXT_PRIMARY = (235, 240, 250)
COLOR_TEXT_MUTED = (140, 155, 175)
COLOR_ACCENT = (0, 200, 255)
COLOR_ACCENT_HOVER = (60, 220, 255)
COLOR_SUCCESS = (40, 200, 80)
COLOR_WARNING = (255, 180, 20)
COLOR_DANGER = (240, 60, 60)
COLOR_SELECTED = (255, 215, 0)

PRESETS_ZEBRA = [
    {"nome": "Vermelho / Branco", "zebra_1": [220, 20, 20], "zebra_2": [255, 255, 255]},
    {"nome": "Azul / Branco",     "zebra_1": [20, 80, 230],  "zebra_2": [255, 255, 255]},
    {"nome": "Amarelo / Preto",   "zebra_1": [245, 210, 10], "zebra_2": [25, 25, 25]},
    {"nome": "Verde / Amarelo",   "zebra_1": [15, 160, 40],  "zebra_2": [245, 210, 10]},
    {"nome": "Laranja / Branco",  "zebra_1": [245, 110, 10], "zebra_2": [255, 255, 255]},
    {"nome": "Ciano / Laranja",   "zebra_1": [0, 200, 240],  "zebra_2": [245, 110, 10]}
]

# =============================================================================
# COMPONENTES VISUAIS (BOTÕES E CONTROLES)
# =============================================================================
class UIButton:
    def __init__(self, rect, text, callback, color=COLOR_PANEL_HEADER, hover_color=COLOR_BORDER, text_color=COLOR_TEXT_PRIMARY, font_size=16):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font_size = font_size
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def draw(self, screen, font):
        bg = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, bg, self.rect, border_radius=5)
        pygame.draw.rect(screen, COLOR_BORDER, self.rect, width=1, border_radius=5)
        txt = font.render(self.text, True, self.text_color)
        screen.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.centery - txt.get_height() // 2))


# =============================================================================
# APLICAÇÃO DO CRIADOR DE PISTAS
# =============================================================================
class TrackEditor:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = pygame.SCALED | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.display.set_caption("Super Monaco GP - Criador e Editor de Pistas")
        self.clock = pygame.time.Clock()

        # Fontes
        self.font_title = pygame.font.SysFont('Segoe UI', 22, bold=True)
        self.font_sub = pygame.font.SysFont('Segoe UI', 16, bold=True)
        self.font_ui = pygame.font.SysFont('Segoe UI', 14)
        self.font_small = pygame.font.SysFont('Segoe UI', 12)
        self.font_mono = pygame.font.SysFont('Consolas', 13)

        # Imagens de fundo disponíveis na pasta images/
        self.lista_bgs = self.detectar_fundos()
        self.bg_idx = 0

        # Presets de Zebra
        self.zebra_idx = 0

        # Estado da Pista Atual
        self.nome_pista = "Grande Prêmio do Rio"
        self.arquivo_atual = "pistas/rio.json"
        self.segmentos = []
        self.seg_idx = 0

        # Câmera da Mini-Visualização 3D
        self.cam_pos = 0.0
        self.cam_speed = 0.0
        self.is_playing = False
        self.bg_surf_cache = {}

        # Notificações / Status Bar
        self.status_msg = "Editor carregado. Pronto para criar circuitos!"
        self.status_timer = pygame.time.get_ticks() + 4000
        self.status_color = COLOR_ACCENT

        # Scroll da lista lateral
        self.scroll_offset = 0

        # Modal de Arquivo (Salvar / Carregar)
        self.modal_aberto = None # 'CARREGAR', 'SALVAR_COMO', 'NOVO'
        self.nome_input_salvar = "nova_pista"

        # Carrega a pista inicial
        if os.path.exists(self.arquivo_atual):
            self.carregar_pista(self.arquivo_atual)
        else:
            self.criar_pista_padrao()

        # Constrói os botões da interface
        self.setup_ui()

    def detectar_fundos(self):
        """ Escaneia a pasta images/ procurando fundos panorâmicos compatíveis """
        fundos = []
        if os.path.exists("images"):
            for f in sorted(os.listdir("images")):
                if f.lower().endswith((".png", ".jpg")):
                    fundos.append(f"images/{f}")
        if not fundos:
            fundos = ["images/bg_rio.png"]
        return fundos

    def carregar_bg_surf(self, caminho):
        if caminho not in self.bg_surf_cache:
            try:
                img = pygame.image.load(caminho).convert()
                self.bg_surf_cache[caminho] = pygame.transform.scale(img, (WIDTH * 2, 135))
            except Exception:
                surf = pygame.Surface((WIDTH * 2, 135))
                surf.fill((135, 206, 235))
                pygame.draw.polygon(surf, (34, 139, 34), [(0, 135), (400, 30), (800, 135)])
                self.bg_surf_cache[caminho] = surf
        return self.bg_surf_cache[caminho]

    def set_status(self, msg, color=COLOR_ACCENT, duration_ms=4000):
        self.status_msg = msg
        self.status_color = color
        self.status_timer = pygame.time.get_ticks() + duration_ms

    def criar_pista_padrao(self):
        """ Cria um circuito oval simples de demonstração """
        self.nome_pista = "Circuito de Treinamento"
        self.arquivo_atual = "pistas/treino.json"
        self.segmentos = [
            {"length": 400, "curve": 0.0, "hill": 0.0, "desc": "Reta Principal"},
            {"length": 80,  "curve": 0.03, "hill": 0.0, "desc": "Entrada Curva 1"},
            {"length": 80,  "curve": 0.05, "hill": 0.0, "desc": "Curva 1"},
            {"length": 80,  "curve": 0.03, "hill": 0.0, "desc": "Saída Curva 1"},
            {"length": 350, "curve": 0.0, "hill": 0.001, "desc": "Reta Oposta (Aclive)"},
            {"length": 80,  "curve": 0.03, "hill": 0.0, "desc": "Entrada Curva 2"},
            {"length": 80,  "curve": 0.05, "hill": -0.001, "desc": "Curva 2 (Declive)"},
            {"length": 80,  "curve": 0.03, "hill": 0.0, "desc": "Saída Curva 2"}
        ]
        self.seg_idx = 0
        self.set_status("Nova pista em branco criada com sucesso!")

    def carregar_pista(self, caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            self.nome_pista = dados.get("nome", "Pista Personalizada")
            self.arquivo_atual = caminho

            # Fundo
            bg_path = dados.get("bg_image", "images/bg_rio.png")
            if bg_path in self.lista_bgs:
                self.bg_idx = self.lista_bgs.index(bg_path)
            else:
                self.lista_bgs.append(bg_path)
                self.bg_idx = len(self.lista_bgs) - 1

            # Cor da zebra
            cores = dados.get("cores", {})
            z1 = cores.get("zebra_1", [220, 20, 20])
            for i, p in enumerate(PRESETS_ZEBRA):
                if p["zebra_1"] == z1:
                    self.zebra_idx = i
                    break

            # Segmentos
            self.segmentos = []
            for s in dados.get("segmentos", []):
                self.segmentos.append({
                    "length": int(s.get("length", 100)),
                    "curve": round(float(s.get("curve", 0.0)), 4),
                    "hill": round(float(s.get("hill", 0.0)), 4),
                    "desc": s.get("desc", "Trecho da pista")
                })

            if not self.segmentos:
                self.criar_pista_padrao()
                return

            self.seg_idx = 0
            self.cam_pos = 0.0
            self.set_status(f"Pista '{self.nome_pista}' carregada de {caminho}!", COLOR_SUCCESS)
        except Exception as e:
            self.set_status(f"Erro ao carregar '{caminho}': {e}", COLOR_DANGER)

    def salvar_pista(self, caminho):
        try:
            os.makedirs("pistas", exist_ok=True)
            preset_z = PRESETS_ZEBRA[self.zebra_idx]
            dados = {
                "nome": self.nome_pista,
                "bg_image": self.lista_bgs[self.bg_idx],
                "cores": {
                    "zebra_1": preset_z["zebra_1"],
                    "zebra_2": preset_z["zebra_2"],
                    "grama_1": [0, 100, 0],
                    "grama_2": [0, 150, 0],
                    "asfalto_1": [100, 100, 100],
                    "asfalto_2": [105, 105, 105]
                },
                "segmentos": self.segmentos
            }
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            self.arquivo_atual = caminho
            self.set_status(f"Pista salva com sucesso em '{caminho}'!", COLOR_SUCCESS)
        except Exception as e:
            self.set_status(f"Erro ao salvar pista: {e}", COLOR_DANGER)

    # =========================================================================
    # CONFIGURAÇÃO DA INTERFACE DO USUÁRIO (BOTÕES)
    # =========================================================================
    def setup_ui(self):
        self.buttons = []
        p_x = 640

        # --- BARRA SUPERIOR DO PAINEL DIREITO ---
        self.buttons.append(UIButton((p_x, 15, 100, 32), "NOVA", self.action_nova_pista, color=(40, 50, 70)))
        self.buttons.append(UIButton((p_x + 110, 15, 110, 32), "CARREGAR", self.action_abrir_carregar, color=(40, 50, 70)))
        self.buttons.append(UIButton((p_x + 230, 15, 100, 32), "SALVAR", self.action_salvar_atual, color=(20, 120, 60), hover_color=(30, 160, 80)))
        self.buttons.append(UIButton((p_x + 340, 15, 140, 32), "SALVAR COMO...", self.action_abrir_salvar_como, color=(30, 80, 140), hover_color=(40, 110, 190)))

        # --- SELETORES GERAIS: CENÁRIO E ZEBRA ---
        y_gen = 65
        self.buttons.append(UIButton((p_x + 160, y_gen, 30, 26), "<", self.action_prev_bg))
        self.buttons.append(UIButton((p_x + 440, y_gen, 30, 26), ">", self.action_next_bg))

        self.buttons.append(UIButton((p_x + 160, y_gen + 32, 30, 26), "<", self.action_prev_zebra))
        self.buttons.append(UIButton((p_x + 440, y_gen + 32, 30, 26), ">", self.action_next_zebra))

        # --- NAVEGAÇÃO ENTRE SEGMENTOS ---
        y_nav = 145
        self.buttons.append(UIButton((p_x + 170, y_nav, 36, 28), "<<", self.action_primeiro_seg))
        self.buttons.append(UIButton((p_x + 215, y_nav, 36, 28), "<", self.action_prev_seg))
        self.buttons.append(UIButton((p_x + 370, y_nav, 36, 28), ">", self.action_next_seg))
        self.buttons.append(UIButton((p_x + 415, y_nav, 36, 28), ">>", self.action_ultimo_seg))

        # --- AJUSTES DO SEGMENTO SELECIONADO: DISTÂNCIA ---
        y_dist = 220
        self.buttons.append(UIButton((p_x + 10, y_dist, 55, 26), "-100", lambda: self.modificar_length(-100)))
        self.buttons.append(UIButton((p_x + 70, y_dist, 50, 26), "-50", lambda: self.modificar_length(-50)))
        self.buttons.append(UIButton((p_x + 125, y_dist, 45, 26), "-10", lambda: self.modificar_length(-10)))
        self.buttons.append(UIButton((p_x + 400, y_dist, 45, 26), "+10", lambda: self.modificar_length(10)))
        self.buttons.append(UIButton((p_x + 450, y_dist, 50, 26), "+50", lambda: self.modificar_length(50)))
        self.buttons.append(UIButton((p_x + 505, y_dist, 55, 26), "+100", lambda: self.modificar_length(100)))

        # --- AJUSTES DO SEGMENTO SELECIONADO: CURVATURA ---
        y_curv = 285
        self.buttons.append(UIButton((p_x + 10, y_curv, 65, 26), "Forte E", lambda: self.definir_curva(-0.05), color=(60, 40, 80)))
        self.buttons.append(UIButton((p_x + 80, y_curv, 65, 26), "Média E", lambda: self.definir_curva(-0.03), color=(40, 60, 90)))
        self.buttons.append(UIButton((p_x + 150, y_curv, 60, 26), "Leve E", lambda: self.definir_curva(-0.015), color=(30, 70, 90)))
        self.buttons.append(UIButton((p_x + 220, y_curv, 65, 26), "RETA (0)", lambda: self.definir_curva(0.0), color=(40, 80, 50)))
        self.buttons.append(UIButton((p_x + 295, y_curv, 60, 26), "Leve D", lambda: self.definir_curva(0.015), color=(30, 70, 90)))
        self.buttons.append(UIButton((p_x + 360, y_curv, 65, 26), "Média D", lambda: self.definir_curva(0.03), color=(40, 60, 90)))
        self.buttons.append(UIButton((p_x + 430, y_curv, 65, 26), "Forte D", lambda: self.definir_curva(0.05), color=(60, 40, 80)))

        # Ajuste fino curva (-0.005 / +0.005)
        self.buttons.append(UIButton((p_x + 505, y_curv, 45, 26), "-0.00059", lambda: self.modificar_curva(-0.00059)))
        self.buttons.append(UIButton((p_x + 555, y_curv, 45, 26), "+0.00059", lambda: self.modificar_curva(0.00059)))

        # --- AJUSTES DO SEGMENTO SELECIONADO: RELEVO (ACLIVE / DECLIVE) ---
        y_hill = 350
        self.buttons.append(UIButton((p_x + 10, y_hill, 95, 26), "Descida Forte", lambda: self.definir_hill(-0.002), color=(90, 40, 40)))
        self.buttons.append(UIButton((p_x + 110, y_hill, 90, 26), "Descida Leve", lambda: self.definir_hill(-0.001), color=(80, 50, 40)))
        self.buttons.append(UIButton((p_x + 205, y_hill, 75, 26), "Plano (0)", lambda: self.definir_hill(0.0), color=(40, 80, 50)))
        self.buttons.append(UIButton((p_x + 285, y_hill, 90, 26), "Subida Leve", lambda: self.definir_hill(0.001), color=(40, 70, 90)))
        self.buttons.append(UIButton((p_x + 380, y_hill, 95, 26), "Subida Forte", lambda: self.definir_hill(0.002), color=(40, 50, 110)))

        # Ajuste fino hill (-0.0005 / +0.0005)
        self.buttons.append(UIButton((p_x + 485, y_hill, 50, 26), "-0.0005", lambda: self.modificar_hill(-0.0005)))
        self.buttons.append(UIButton((p_x + 540, y_hill, 50, 26), "+0.0005", lambda: self.modificar_hill(0.0005)))

        # --- AÇÕES DE CONSTRUÇÃO DE PISTA ---
        y_act = 415
        self.buttons.append(UIButton((p_x + 10, y_act, 105, 30), "+ RETA", self.action_add_reta, color=(25, 90, 50), hover_color=(35, 120, 65)))
        self.buttons.append(UIButton((p_x + 125, y_act, 105, 30), "+ CURVA E", lambda: self.action_add_curva(-0.03), color=(30, 70, 110), hover_color=(40, 90, 140)))
        self.buttons.append(UIButton((p_x + 240, y_act, 105, 30), "+ CURVA D", lambda: self.action_add_curva(0.03), color=(30, 70, 110), hover_color=(40, 90, 140)))
        self.buttons.append(UIButton((p_x + 355, y_act, 115, 30), "+ CHICANE", self.action_add_chicane, color=(60, 50, 95), hover_color=(80, 65, 125)))
        self.buttons.append(UIButton((p_x + 480, y_act, 105, 30), "DUPLICAR", self.action_duplicar_seg, color=(60, 65, 75)))

        y_act2 = 452
        self.buttons.append(UIButton((p_x + 10, y_act2, 105, 28), "SUBIR (Ordem)", lambda: self.action_reordenar(-1), color=(40, 50, 65)))
        self.buttons.append(UIButton((p_x + 125, y_act2, 105, 28), "DESCER (Ordem)", lambda: self.action_reordenar(1), color=(40, 50, 65)))
        self.buttons.append(UIButton((p_x + 240, y_act2, 105, 28), "EXCLUIR TRECHO", self.action_excluir_seg, color=(120, 30, 30), hover_color=(160, 40, 40)))

        # --- CONTROLES DA CÂMERA 3D (EMBAIXO DO PREVIEW) ---
        self.buttons.append(UIButton((20, 680, 110, 26), "PULAR P/ TRECHO", self.action_focar_camera_trecho, color=(35, 50, 70)))
        self.buttons.append(UIButton((140, 680, 100, 26), "PLAY / PAUSE", self.action_toggle_play, color=(20, 90, 130)))
        self.buttons.append(UIButton((250, 680, 70, 26), "RESET", self.action_reset_cam, color=(50, 50, 60)))

    # =========================================================================
    # AÇÕES DOS BOTÕES
    # =========================================================================
    def action_nova_pista(self):
        self.criar_pista_padrao()

    def action_abrir_carregar(self):
        self.modal_aberto = "CARREGAR"

    def action_salvar_atual(self):
        self.salvar_pista(self.arquivo_atual)

    def action_abrir_salvar_como(self):
        self.nome_input_salvar = os.path.splitext(os.path.basename(self.arquivo_atual))[0]
        self.modal_aberto = "SALVAR_COMO"

    def action_prev_bg(self):
        self.bg_idx = (self.bg_idx - 1) % len(self.lista_bgs)
        self.set_status(f"Cenário alterado: {os.path.basename(self.lista_bgs[self.bg_idx])}")

    def action_next_bg(self):
        self.bg_idx = (self.bg_idx + 1) % len(self.lista_bgs)
        self.set_status(f"Cenário alterado: {os.path.basename(self.lista_bgs[self.bg_idx])}")

    def action_prev_zebra(self):
        self.zebra_idx = (self.zebra_idx - 1) % len(PRESETS_ZEBRA)
        self.set_status(f"Cores de Zebra: {PRESETS_ZEBRA[self.zebra_idx]['nome']}")

    def action_next_zebra(self):
        self.zebra_idx = (self.zebra_idx + 1) % len(PRESETS_ZEBRA)
        self.set_status(f"Cores de Zebra: {PRESETS_ZEBRA[self.zebra_idx]['nome']}")

    def action_primeiro_seg(self):
        self.seg_idx = 0
        self.action_focar_camera_trecho()

    def action_ultimo_seg(self):
        self.seg_idx = max(0, len(self.segmentos) - 1)
        self.action_focar_camera_trecho()

    def action_prev_seg(self):
        if self.segmentos:
            self.seg_idx = (self.seg_idx - 1) % len(self.segmentos)
            self.action_focar_camera_trecho()

    def action_next_seg(self):
        if self.segmentos:
            self.seg_idx = (self.seg_idx + 1) % len(self.segmentos)
            self.action_focar_camera_trecho()

    def modificar_length(self, delta):
        if not self.segmentos: return
        seg = self.segmentos[self.seg_idx]
        seg["length"] = max(20, min(2000, seg["length"] + delta))
        self.set_status(f"Extensão do trecho #{self.seg_idx + 1}: {seg['length']}m")

    def definir_curva(self, valor):
        if not self.segmentos: return
        self.segmentos[self.seg_idx]["curve"] = round(float(valor), 4)
        self.set_status(f"Curvatura do trecho #{self.seg_idx + 1}: {valor:+.4f}")

    def modificar_curva(self, delta):
        if not self.segmentos: return
        seg = self.segmentos[self.seg_idx]
        seg["curve"] = round(max(-0.08, min(0.08, seg["curve"] + delta)), 4)
        self.set_status(f"Curvatura do trecho #{self.seg_idx + 1}: {seg['curve']:+.4f}")

    def definir_hill(self, valor):
        if not self.segmentos: return
        self.segmentos[self.seg_idx]["hill"] = round(float(valor), 4)
        self.set_status(f"Elevação do trecho #{self.seg_idx + 1}: {valor:+.4f}")

    def modificar_hill(self, delta):
        if not self.segmentos: return
        seg = self.segmentos[self.seg_idx]
        seg["hill"] = round(max(-0.004, min(0.004, seg["hill"] + delta)), 4)
        self.set_status(f"Elevação do trecho #{self.seg_idx + 1}: {seg['hill']:+.4f}")

    def action_add_reta(self):
        novo = {"length": 150, "curve": 0.0, "hill": 0.0, "desc": "Nova Reta"}
        insert_at = self.seg_idx + 1 if self.segmentos else 0
        self.segmentos.insert(insert_at, novo)
        self.seg_idx = insert_at
        self.action_focar_camera_trecho()
        self.set_status(f"Reta inserida na posição #{self.seg_idx + 1}!")

    def action_add_curva(self, curvatura):
        direcao = "Direita" if curvatura > 0 else "Esquerda"
        novo = {"length": 100, "curve": curvatura, "hill": 0.0, "desc": f"Curva para {direcao}"}
        insert_at = self.seg_idx + 1 if self.segmentos else 0
        self.segmentos.insert(insert_at, novo)
        self.seg_idx = insert_at
        self.action_focar_camera_trecho()
        self.set_status(f"Curva para {direcao} inserida na posição #{self.seg_idx + 1}!")

    def action_add_chicane(self):
        s1 = {"length": 70, "curve": -0.04, "hill": 0.0, "desc": "Chicane (Esq)"}
        s2 = {"length": 70, "curve": 0.04, "hill": 0.0, "desc": "Chicane (Dir)"}
        insert_at = self.seg_idx + 1 if self.segmentos else 0
        self.segmentos.insert(insert_at, s2)
        self.segmentos.insert(insert_at, s1)
        self.seg_idx = insert_at
        self.action_focar_camera_trecho()
        self.set_status(f"Chicane inserida nas posições #{self.seg_idx + 1} e #{self.seg_idx + 2}!")

    def action_duplicar_seg(self):
        if not self.segmentos: return
        original = self.segmentos[self.seg_idx]
        copia = original.copy()
        insert_at = self.seg_idx + 1
        self.segmentos.insert(insert_at, copia)
        self.seg_idx = insert_at
        self.action_focar_camera_trecho()
        self.set_status(f"Trecho #{self.seg_idx} duplicado com sucesso!")

    def action_excluir_seg(self):
        if len(self.segmentos) <= 1:
            self.set_status("A pista precisa ter pelo menos 1 trecho!", COLOR_WARNING)
            return
        del self.segmentos[self.seg_idx]
        self.seg_idx = min(self.seg_idx, len(self.segmentos) - 1)
        self.action_focar_camera_trecho()
        self.set_status(f"Trecho removido. Restam {len(self.segmentos)} trechos.")

    def action_reordenar(self, direcao):
        if not self.segmentos: return
        novo_idx = self.seg_idx + direcao
        if 0 <= novo_idx < len(self.segmentos):
            self.segmentos[self.seg_idx], self.segmentos[novo_idx] = self.segmentos[novo_idx], self.segmentos[self.seg_idx]
            self.seg_idx = novo_idx
            self.action_focar_camera_trecho()
            self.set_status(f"Trecho movido para a posição #{self.seg_idx + 1}")

    def action_focar_camera_trecho(self):
        if not self.segmentos: return
        dist = 0
        for i in range(self.seg_idx):
            dist += self.segmentos[i]["length"]
        self.cam_pos = float(dist)

    def action_toggle_play(self):
        self.is_playing = not self.is_playing

    def action_reset_cam(self):
        self.cam_pos = 0.0
        self.is_playing = False

    # =========================================================================
    # RENDERIZAÇÃO 1: PRÉ-VISUALIZAÇÃO AÉREA (TOP-DOWN 2D)
    # =========================================================================
    def desenhar_preview_aereo(self, rect):
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        # Cabeçalho da caixa
        txt_header = self.font_sub.render("PRÉ-VISUALIZAÇÃO AÉREA (2D)", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_header, (rect.x + 12, rect.y + 8))

        if not self.segmentos:
            return

        # 1. Traçado dos pontos 2D
        pontos = []
        seg_indices_pontos = []
        x, y = 0.0, 0.0
        angulo = -math.pi / 2 # Aponta para o norte
        pontos.append((x, y))
        seg_indices_pontos.append(0)

        curve_factor = 0.5 # Fator de conversão da curvatura
        for i, s in enumerate(self.segmentos):
            c = s["curve"]
            l = s["length"]
            passo = 8 # Avalia a cada 8m
            num_passos = max(1, int(l // passo))
            d_passo = l / num_passos
            for _ in range(num_passos):
                angulo += c * d_passo * curve_factor
                x += math.cos(angulo) * d_passo
                y += math.sin(angulo) * d_passo
                pontos.append((x, y))
            seg_indices_pontos.append(len(pontos) - 1)

        # 2. Ajuste de escala e centralização
        xs = [p[0] for p in pontos]
        ys = [p[1] for p in pontos]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        largura_pista = max(1.0, max_x - min_x)
        altura_pista = max(1.0, max_y - min_y)

        area_desenho = pygame.Rect(rect.x + 20, rect.y + 35, rect.width - 40, rect.height - 55)
        scale_x = area_desenho.width / largura_pista
        scale_y = area_desenho.height / altura_pista
        scale = min(scale_x, scale_y) * 0.90

        offset_x = area_desenho.centerx - ((min_x + max_x) / 2) * scale
        offset_y = area_desenho.centery - ((min_y + max_y) / 2) * scale

        pontos_tela = []
        for px, py in pontos:
            pontos_tela.append((int(offset_x + px * scale), int(offset_y + py * scale)))

        # 3. Desenho dos segmentos
        # Pista completa em cinza
        if len(pontos_tela) > 1:
            pygame.draw.lines(self.screen, (60, 70, 85), False, pontos_tela, width=7)
            pygame.draw.lines(self.screen, (130, 140, 155), False, pontos_tela, width=3)

        # Destaca o segmento selecionado
        if self.seg_idx < len(seg_indices_pontos) - 1:
            idx_ini = seg_indices_pontos[self.seg_idx]
            idx_fim = seg_indices_pontos[self.seg_idx + 1]
            pts_destaque = pontos_tela[idx_ini:idx_fim + 1]
            if len(pts_destaque) > 1:
                pygame.draw.lines(self.screen, COLOR_SELECTED, False, pts_destaque, width=7)
                pygame.draw.circle(self.screen, (255, 255, 255), pts_destaque[0], 5)
                pygame.draw.circle(self.screen, COLOR_SELECTED, pts_destaque[-1], 5)

        # Marcadores de Largada (Verde) e Fim (Vermelho)
        pt_largada = pontos_tela[0]
        pt_fim = pontos_tela[-1]
        pygame.draw.circle(self.screen, COLOR_SUCCESS, pt_largada, 7)
        pygame.draw.circle(self.screen, COLOR_DANGER, pt_fim, 7)

        # Distância entre largada e chegada para avaliar fechamento
        dist_fechamento = math.sqrt((pontos[-1][0] - pontos[0][0])**2 + (pontos[-1][1] - pontos[0][1])**2)
        total_metros = sum(s["length"] for s in self.segmentos)

        # Selo de Status da Pista
        if dist_fechamento < 60:
            badge_txt = self.font_small.render("CIRCUITO FECHADO", True, COLOR_SUCCESS)
            badge_color = (20, 80, 40)
        else:
            badge_txt = self.font_small.render(f"ABERTO (Faltam {int(dist_fechamento)}m)", True, COLOR_WARNING)
            badge_color = (90, 70, 20)

        pygame.draw.rect(self.screen, badge_color, (rect.right - 180, rect.y + 7, 168, 22), border_radius=4)
        self.screen.blit(badge_txt, (rect.right - 174, rect.y + 10))

        # Legenda inferior
        info_txt = self.font_small.render(f"Extensao: {total_metros}m | Trechos: {len(self.segmentos)} | Selecionado: #{self.seg_idx + 1}", True, COLOR_TEXT_MUTED)
        self.screen.blit(info_txt, (rect.x + 12, rect.bottom - 20))

    # =========================================================================
    # RENDERIZAÇÃO 2: MINI PREVIEW 3D DO COCKPIT / PISTA
    # =========================================================================
    def desenhar_preview_3d(self, rect):
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        txt_header = self.font_sub.render("PRÉ-VISUALIZAÇÃO 3D (EM TEMPO REAL)", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_header, (rect.x + 12, rect.y + 8))

        if not self.segmentos:
            return

        # Monta a pista em array metro a metro
        track_data = []
        for s in self.segmentos:
            for _ in range(int(s["length"])):
                track_data.append({"curve": s["curve"], "hill": s["hill"]})
        if not track_data:
            return

        total_len = len(track_data)
        pos = self.cam_pos % total_len

        # Cria uma superfície isolada para a câmera 3D
        view_w, view_h = rect.width - 24, rect.height - 75
        cam_surf = pygame.Surface((view_w, view_h))
        cam_surf.fill(GREEN_DARK)

        # Fundo / Horizonte Parallax
        bg_surf = self.carregar_bg_surf(self.lista_bgs[self.bg_idx])
        indice_atual = int(pos) % total_len
        curva_atual = track_data[indice_atual]["curve"]
        bg_offset_x = (-pos * 0.2) % view_w
        cam_surf.blit(bg_surf, (bg_offset_x - view_w, 0))
        cam_surf.blit(bg_surf, (bg_offset_x, 0))

        # Configurações de projeção 3D
        cam_height = 800
        draw_distance = 120
        dx = 0
        curva_x = 0
        dy = 0
        colina_y = 0
        pos_frac = pos % 1

        preset_z = PRESETS_ZEBRA[self.zebra_idx]
        cor_z1 = tuple(preset_z["zebra_1"])
        cor_z2 = tuple(preset_z["zebra_2"])

        for n in range(1, draw_distance):
            z_near = n - pos_frac
            z_far = n + 1 - pos_frac
            if z_near <= 0.001: z_near = 0.001

            p_near = cam_height / z_near
            p_far = cam_height / z_far

            idx_fut = int((pos + n) % total_len)
            c_n = track_data[idx_fut]["curve"]
            h_n = track_data[idx_fut]["hill"]

            dx += c_n
            curva_x += dx
            dy += h_n
            colina_y += dy

            c_near = (view_w // 2) + ((curva_x - dx) * p_near)
            c_far = (view_w // 2) + (curva_x * p_far)

            fator_colina = 0.08
            y_near = (view_h // 2) + p_near - ((colina_y - dy) * p_near * fator_colina)
            y_far = (view_h // 2) + p_far - (colina_y * p_far * fator_colina)

            if y_far > y_near:
                y_far = y_near

            w_near = p_near * 4.5
            w_far = p_far * 4.5

            alt_grama = max(1, int(y_near - y_far) + 1)
            pygame.draw.rect(cam_surf, GREEN_LIGHT if (n + int(pos)) % 6 > 3 else GREEN_DARK, (0, int(y_far), view_w, alt_grama))

            col_road = GRAY_DARK if (n + int(pos)) % 6 > 3 else GRAY_LIGHT
            col_zebra = cor_z1 if (n + int(pos)) % 6 > 3 else cor_z2

            if idx_fut < 8:
                col_road = WHITE
                col_zebra = GRAY_DARK

            pygame.draw.polygon(cam_surf, col_road, [
                (c_near - w_near, y_near), (c_near + w_near, y_near),
                (c_far + w_far, y_far), (c_far - w_far, y_far)
            ])

            zw_near = w_near * 0.25
            zw_far = w_far * 0.25
            pygame.draw.polygon(cam_surf, col_zebra, [
                (c_near - w_near - zw_near, y_near), (c_near - w_near, y_near),
                (c_far - w_far, y_far), (c_far - w_far - zw_far, y_far)
            ])
            pygame.draw.polygon(cam_surf, col_zebra, [
                (c_near + w_near, y_near), (c_near + w_near + zw_near, y_near),
                (c_far + w_far + zw_far, y_far), (c_far + w_far, y_far)
            ])

        self.screen.blit(cam_surf, (rect.x + 12, rect.y + 35))

        # Informações da Câmera
        status_play = "PLAYING (240 km/h)" if self.is_playing else "PAUSADO"
        cor_play = COLOR_SUCCESS if self.is_playing else COLOR_WARNING
        txt_cam = self.font_small.render(f"Posição: {int(pos)}m / {total_len}m | Status: {status_play}", True, cor_play)
        self.screen.blit(txt_cam, (rect.x + 330, rect.y + 10))

    # =========================================================================
    # RENDERIZAÇÃO 3: PAINEL DE CONTROLE (DIREITA)
    # =========================================================================
    def desenhar_painel_edicao(self):
        p_x = 640
        y_gen = 65

        # 1. Informações de Cenário e Cores
        lbl_bg = self.font_sub.render("CENÁRIO (BG):", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_bg, (p_x + 10, y_gen + 3))
        nome_bg = os.path.basename(self.lista_bgs[self.bg_idx])
        txt_bg = self.font_ui.render(nome_bg[:28], True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_bg, (p_x + 200, y_gen + 3))

        lbl_zb = self.font_sub.render("ZEBRAS:", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_zb, (p_x + 10, y_gen + 35))
        p_zb = PRESETS_ZEBRA[self.zebra_idx]
        txt_zb = self.font_ui.render(p_zb["nome"], True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_zb, (p_x + 200, y_gen + 35))

        # Amostra das cores da zebra
        pygame.draw.rect(self.screen, tuple(p_zb["zebra_1"]), (p_x + 380, y_gen + 36, 20, 16), border_radius=2)
        pygame.draw.rect(self.screen, tuple(p_zb["zebra_2"]), (p_x + 404, y_gen + 36, 20, 16), border_radius=2)
        pygame.draw.rect(self.screen, COLOR_BORDER, (p_x + 380, y_gen + 36, 44, 16), width=1, border_radius=2)

        # 2. Navegação do Segmento
        pygame.draw.line(self.screen, COLOR_BORDER, (p_x, 130), (WIDTH - 20, 130), 1)

        total_segs = len(self.segmentos)
        idx_str = f"Segmento {self.seg_idx + 1} de {total_segs}"
        txt_seg_idx = self.font_title.render(idx_str, True, COLOR_SELECTED)
        self.screen.blit(txt_seg_idx, (p_x + 10, 145))

        if self.segmentos:
            seg = self.segmentos[self.seg_idx]
            desc = seg.get("desc", "Sem descrição")
            txt_desc = self.font_ui.render(f"Descrição: {desc}", True, COLOR_TEXT_MUTED)
            self.screen.blit(txt_desc, (p_x + 10, 175))

            # 3. Métricas do Segmento Atual (Comprimento, Curvatura, Relevo)
            # A) COMPRIMENTO
            txt_l = self.font_sub.render(f"DISTÂNCIA: {seg['length']} metros", True, COLOR_TEXT_PRIMARY)
            self.screen.blit(txt_l, (p_x + 190, 222))

            # B) CURVATURA
            curva = seg["curve"]
            if curva > 0:
                tipo_c = f"Curva para DIREITA (+{curva:.4f})"
                cor_c = (100, 220, 255)
            elif curva < 0:
                tipo_c = f"Curva para ESQUERDA ({curva:.4f})"
                cor_c = (255, 160, 100)
            else:
                tipo_c = "RETA (0.0000)"
                cor_c = COLOR_SUCCESS

            txt_c = self.font_sub.render(f"CURVATURA: {tipo_c}", True, cor_c)
            self.screen.blit(txt_c, (p_x + 10, 260))

            # C) RELEVO / COLINAS
            hill = seg["hill"]
            if hill > 0:
                tipo_h = f"SUBIDA / ACLIVE (+{hill:.4f})"
                cor_h = (120, 200, 255)
            elif hill < 0:
                tipo_h = f"DESCIDA / DECLIVE ({hill:.4f})"
                cor_h = (255, 120, 120)
            else:
                tipo_h = "PLANO (0.0000)"
                cor_h = COLOR_SUCCESS

            txt_h = self.font_sub.render(f"ELEVAÇÃO: {tipo_h}", True, cor_h)
            self.screen.blit(txt_h, (p_x + 10, 325))

        # Divisor
        pygame.draw.line(self.screen, COLOR_BORDER, (p_x, 395), (WIDTH - 20, 395), 1)

        # 4. Lista Rolável de Todos os Segmentos
        self.desenhar_lista_segmentos(pygame.Rect(p_x, 495, WIDTH - p_x - 20, 215))

    def desenhar_lista_segmentos(self, rect):
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        txt_l = self.font_sub.render("LISTA DE TRECHOS DA PISTA (Clique para selecionar):", True, COLOR_TEXT_MUTED)
        self.screen.blit(txt_l, (rect.x + 12, rect.y + 6))

        item_h = 24
        max_visiveis = (rect.height - 35) // item_h
        total = len(self.segmentos)

        # Ajusta scroll
        if self.seg_idx < self.scroll_offset:
            self.scroll_offset = self.seg_idx
        elif self.seg_idx >= self.scroll_offset + max_visiveis:
            self.scroll_offset = self.seg_idx - max_visiveis + 1

        for i in range(max_visiveis):
            curr_idx = self.scroll_offset + i
            if curr_idx >= total:
                break

            s = self.segmentos[curr_idx]
            item_rect = pygame.Rect(rect.x + 8, rect.y + 30 + (i * item_h), rect.width - 16, item_h - 2)

            is_sel = (curr_idx == self.seg_idx)
            bg_col = (45, 60, 85) if is_sel else (30, 38, 52)
            pygame.draw.rect(self.screen, bg_col, item_rect, border_radius=3)
            if is_sel:
                pygame.draw.rect(self.screen, COLOR_SELECTED, item_rect, width=1, border_radius=3)

            # Texto resumo do trecho
            if s["curve"] > 0.001:
                tipo = f"Curva Dir (+{s['curve']:.3f})"
            elif s["curve"] < -0.001:
                tipo = f"Curva Esq ({s['curve']:.3f})"
            else:
                tipo = "Reta"

            if s["hill"] > 0.0001:
                elev = "▲ Subida"
            elif s["hill"] < -0.0001:
                elev = "▼ Descida"
            else:
                elev = "Plano"

            linha_txt = f"#{curr_idx + 1:02d} | {s['length']:4d}m | {tipo:<20} | {elev:<10} | {s.get('desc','')[:20]}"
            col_txt = COLOR_SELECTED if is_sel else COLOR_TEXT_PRIMARY
            txt_surf = self.font_mono.render(linha_txt, True, col_txt)
            self.screen.blit(txt_surf, (item_rect.x + 8, item_rect.y + 3))

    # =========================================================================
    # MODAL DE ARQUIVOS (SALVAR / CARREGAR)
    # =========================================================================
    def desenhar_modal_carregar(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        m_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 180, 500, 360)
        pygame.draw.rect(self.screen, COLOR_PANEL, m_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_BORDER, m_rect, width=2, border_radius=8)

        txt_t = self.font_title.render("CARREGAR PISTA EXISTENTE", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_t, (m_rect.centerx - txt_t.get_width() // 2, m_rect.y + 15))

        # Lista arquivos em pistas/
        arquivos = []
        if os.path.exists("pistas"):
            arquivos = [f for f in sorted(os.listdir("pistas")) if f.lower().endswith(".json")]

        if not arquivos:
            txt_vazio = self.font_ui.render("Nenhuma pista encontrada em 'pistas/'.", True, COLOR_WARNING)
            self.screen.blit(txt_vazio, (m_rect.centerx - txt_vazio.get_width() // 2, m_rect.y + 100))
        else:
            for i, arq in enumerate(arquivos[:7]):
                btn_r = pygame.Rect(m_rect.x + 30, m_rect.y + 60 + (i * 35), m_rect.width - 60, 30)
                mouse_pos = pygame.mouse.get_pos()
                is_hov = btn_r.collidepoint(mouse_pos)
                pygame.draw.rect(self.screen, (45, 60, 85) if is_hov else (35, 45, 60), btn_r, border_radius=4)
                pygame.draw.rect(self.screen, COLOR_BORDER, btn_r, width=1, border_radius=4)
                txt_arq = self.font_ui.render(arq, True, COLOR_TEXT_PRIMARY)
                self.screen.blit(txt_arq, (btn_r.x + 15, btn_r.centery - txt_arq.get_height() // 2))

        # Botão Fechar Modal
        btn_close = pygame.Rect(m_rect.centerx - 60, m_rect.bottom - 45, 120, 30)
        is_hov = btn_close.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, (80, 35, 35) if is_hov else (60, 30, 30), btn_close, border_radius=4)
        txt_c = self.font_ui.render("CANCELAR", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_c, (btn_close.centerx - txt_c.get_width() // 2, btn_close.centery - txt_c.get_height() // 2))

    def desenhar_modal_salvar_como(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        m_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 120, 500, 240)
        pygame.draw.rect(self.screen, COLOR_PANEL, m_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_BORDER, m_rect, width=2, border_radius=8)

        txt_t = self.font_title.render("SALVAR PISTA COMO...", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_t, (m_rect.centerx - txt_t.get_width() // 2, m_rect.y + 15))

        txt_instrucao = self.font_ui.render("Digite o nome do arquivo JSON (sem .json):", True, COLOR_TEXT_MUTED)
        self.screen.blit(txt_instrucao, (m_rect.x + 40, m_rect.y + 60))

        # Caixa de Texto
        input_rect = pygame.Rect(m_rect.x + 40, m_rect.y + 90, m_rect.width - 80, 36)
        pygame.draw.rect(self.screen, (20, 25, 35), input_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_ACCENT, input_rect, width=2, border_radius=4)
        txt_val = self.font_title.render(self.nome_input_salvar + "_", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_val, (input_rect.x + 12, input_rect.centery - txt_val.get_height() // 2))

        # Botão Salvar
        btn_salvar = pygame.Rect(m_rect.x + 60, m_rect.bottom - 50, 160, 32)
        is_hov_s = btn_salvar.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, (25, 140, 60) if is_hov_s else (20, 100, 50), btn_salvar, border_radius=4)
        txt_s = self.font_sub.render("CONFIRMAR", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_s, (btn_salvar.centerx - txt_s.get_width() // 2, btn_salvar.centery - txt_s.get_height() // 2))

        # Botão Cancelar
        btn_close = pygame.Rect(m_rect.right - 220, m_rect.bottom - 50, 160, 32)
        is_hov_c = btn_close.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, (80, 35, 35) if is_hov_c else (60, 30, 30), btn_close, border_radius=4)
        txt_c = self.font_sub.render("CANCELAR", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_c, (btn_close.centerx - txt_c.get_width() // 2, btn_close.centery - txt_c.get_height() // 2))

    # =========================================================================
    # LOOP PRINCIPAL E TRATAMENTO DE EVENTOS
    # =========================================================================
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            tempo_atual = pygame.time.get_ticks()

            # Atualização da câmera 3D em modo PLAY
            if self.is_playing and self.segmentos:
                total_len = sum(s["length"] for s in self.segmentos)
                if total_len > 0:
                    # Velocidade de ~240 km/h (cerca de 66 m/s)
                    self.cam_pos = (self.cam_pos + (66 * (dt / 1000.0))) % total_len

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Se houver modal aberto, trata eventos do modal primeiro
                if self.modal_aberto == "CARREGAR":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        m_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 180, 500, 360)
                        btn_close = pygame.Rect(m_rect.centerx - 60, m_rect.bottom - 45, 120, 30)
                        if btn_close.collidepoint(event.pos):
                            self.modal_aberto = None
                        else:
                            arquivos = []
                            if os.path.exists("pistas"):
                                arquivos = [f for f in sorted(os.listdir("pistas")) if f.lower().endswith(".json")]
                            for i, arq in enumerate(arquivos[:7]):
                                btn_r = pygame.Rect(m_rect.x + 30, m_rect.y + 60 + (i * 35), m_rect.width - 60, 30)
                                if btn_r.collidepoint(event.pos):
                                    self.carregar_pista(f"pistas/{arq}")
                                    self.modal_aberto = None
                                    break
                    continue

                elif self.modal_aberto == "SALVAR_COMO":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            nome_limpo = self.nome_input_salvar.strip()
                            if nome_limpo:
                                self.salvar_pista(f"pistas/{nome_limpo}.json")
                            self.modal_aberto = None
                        elif event.key == pygame.K_ESCAPE:
                            self.modal_aberto = None
                        elif event.key == pygame.K_BACKSPACE:
                            self.nome_input_salvar = self.nome_input_salvar[:-1]
                        else:
                            if len(self.nome_input_salvar) < 24 and (event.unicode.isalnum() or event.unicode in "_-"):
                                self.nome_input_salvar += event.unicode
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        m_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 120, 500, 240)
                        btn_salvar = pygame.Rect(m_rect.x + 60, m_rect.bottom - 50, 160, 32)
                        btn_close = pygame.Rect(m_rect.right - 220, m_rect.bottom - 50, 160, 32)
                        if btn_salvar.collidepoint(event.pos):
                            nome_limpo = self.nome_input_salvar.strip()
                            if nome_limpo:
                                self.salvar_pista(f"pistas/{nome_limpo}.json")
                            self.modal_aberto = None
                        elif btn_close.collidepoint(event.pos):
                            self.modal_aberto = None
                    continue

                # Clique na lista lateral de segmentos para seleção rápida
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    rect_lista = pygame.Rect(640, 495, WIDTH - 640 - 20, 215)
                    if rect_lista.collidepoint(event.pos):
                        rel_y = event.pos[1] - (rect_lista.y + 30)
                        if rel_y >= 0:
                            idx_clicado = self.scroll_offset + (rel_y // 24)
                            if 0 <= idx_clicado < len(self.segmentos):
                                self.seg_idx = idx_clicado
                                self.action_focar_camera_trecho()

                # Eventos dos botões da interface
                for b in self.buttons:
                    b.handle_event(event)

                # Teclado (Atalhos rápidos)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.action_prev_seg()
                    elif event.key == pygame.K_RIGHT:
                        self.action_next_seg()
                    elif event.key == pygame.K_SPACE:
                        self.action_toggle_play()
                    elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.action_salvar_atual()

            # =================================================================
            # DESENHO DA TELA
            # =================================================================
            self.screen.fill(COLOR_BG)

            # 1. Painel Esquerdo (Pré-visualizações)
            self.desenhar_preview_aereo(pygame.Rect(20, 15, 600, 385))
            self.desenhar_preview_3d(pygame.Rect(20, 415, 600, 295))

            # 2. Painel Direito (Controles de Edição)
            self.desenhar_painel_edicao()

            # 3. Desenho de todos os botões UI
            for b in self.buttons:
                b.draw(self.screen, self.font_ui)

            # 4. Barra de Notificações / Status (Rodapé)
            if tempo_atual < self.status_timer:
                status_surf = self.font_ui.render(self.status_msg, True, self.status_color)
                self.screen.blit(status_surf, (25, HEIGHT - 22))

            # 5. Modais (se abertos)
            if self.modal_aberto == "CARREGAR":
                self.desenhar_modal_carregar()
            elif self.modal_aberto == "SALVAR_COMO":
                self.desenhar_modal_salvar_como()

            pygame.display.flip()

if __name__ == "__main__":
    app = TrackEditor()
    app.run()

