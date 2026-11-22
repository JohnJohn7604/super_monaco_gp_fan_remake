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
    def __init__(self, rect, text, callback, color=COLOR_PANEL_HEADER, hover_color=COLOR_BORDER, text_color=COLOR_TEXT_PRIMARY, font_size=14):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font_size = font_size
        self.is_hovered = False
        self._font_cache = None

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def draw(self, screen, default_font):
        bg = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, bg, self.rect, border_radius=5)
        pygame.draw.rect(screen, COLOR_BORDER, self.rect, width=1, border_radius=5)
        if self.font_size != 14:
            if self._font_cache is None:
                self._font_cache = pygame.font.SysFont('Segoe UI', self.font_size)
            font_to_use = self._font_cache
        else:
            font_to_use = default_font
        txt = font_to_use.render(self.text, True, self.text_color)
        screen.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.centery - txt.get_height() // 2))


# =============================================================================
# APLICAÇÃO DO CRIADOR DE PISTAS
# =============================================================================
class TrackEditor:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF
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
        self.bg_width = WIDTH * 2
        self.bg_height = 135

        # Presets de Zebra
        self.zebra_idx = 0

        # Camada de Referência 2D (Overlay PNG com 60% de transparência)
        self.lista_refs = self.detectar_pngs_referencia()
        self.ref_idx = 0
        self.ref_width = 400
        self.ref_height = 300
        self.ref_offset_x = 0
        self.ref_offset_y = 0
        self.ref_angle = 0
        self.arrastando_ref = False
        self.drag_inicio_mouse = (0, 0)
        self.drag_inicio_offset = (0, 0)
        self.ref_surf_cache = {}

        # Estado da Pista Atual
        self.nome_pista = "Grande Prêmio do Rio"
        self.arquivo_atual = "pistas/rio.json"
        self.segmentos = []
        self.seg_idx = 0

        # =====================================================================
        # SISTEMA DE OBJETOS LATERAIS (MURETAS E PLACAS DE CURVA)
        # =====================================================================
        self.lista_pngs_objetos = self.detectar_pngs_objetos()
        self.obj_png_idx = 0
        self.obj_nome_input = "Mureta Azul"
        self.obj_escala_input = 1.0
        self.obj_offset_ini_input = 1.30
        self.obj_offset_fim_input = 1.30
        self.editando_nome_obj = False

        self.objetos_catalogo = self.carregar_catalogo_objetos_global()
        self.obj_cat_sel_idx = 0

        # Aplicações nos trechos da pista atual:
        # {"seg_idx": int, "objeto": str, "lado": "esq"|"dir"|"ambos", "quantidade": int, "inicio_pct": int}
        self.objetos_pista = []
        self.obj_apl_sel_idx = 0
        self.apl_lado = "esq"       # "esq", "dir", "ambos"
        self.apl_quantidade = 1     # Quantas vezes replicar no trecho
        self.apl_inicio_pct = 0     # Posição inicial % dentro do trecho
        self.apl_espacamento = 0    # 0 = automático pelo trecho | > 0 = distância fixa em metros

        self.scroll_obj_cat = 0
        self.scroll_obj_apl = 0
        self.rect_lista_obj_cat = pygame.Rect(650, 214, WIDTH - 680, 104)
        self.rect_lista_obj_apl = pygame.Rect(650, 520, WIDTH - 680, 145)
        self.rect_input_nome_obj = pygame.Rect(780, 62, 260, 26)

        self.obj_surf_cache = {}
        self.obj_scaled_cache = {}

        # Câmera da Mini-Visualização 3D
        self.cam_pos = 0.0
        self.cam_speed = 0.0
        self.is_playing = False
        self.bg_offset_x = 0.0
        self.bg_surf_cache = {}

        # Notificações / Status Bar
        self.status_msg = "Editor carregado. Pronto para criar circuitos!"
        self.status_timer = pygame.time.get_ticks() + 4000
        self.status_color = COLOR_ACCENT

        # Scroll e Área da lista lateral
        self.scroll_offset = 0
        self.rect_lista = pygame.Rect(640, 468, WIDTH - 640 - 20, 120)

        # Modal de Arquivo (Salvar / Carregar)
        self.modal_aberto = None
        self.nome_input_salvar = "nova_pista"

        # =====================================================================
        # MODO TEMPORADAS (CAMPEONATOS)
        # =====================================================================
        self.modo_editor = "PISTA"  # "PISTA", "OBJETOS" ou "TEMPORADA"
        self.nome_temporada = "Temporada Oficial"
        self.arquivo_temporada = "temporadas/temporada_1.json"
        self.etapas_temporada = []
        self.etapa_sel_idx = 0
        self.pista_disp_idx = 0
        self.lista_pistas_disponiveis = self.detectar_pistas_disponiveis()
        self.scroll_etapas = 0
        self.scroll_pistas_disp = 0
        self.rect_lista_pistas_disp = pygame.Rect(40, 140, 560, 480)
        self.rect_lista_etapas = pygame.Rect(640, 140, WIDTH - 660, 480)

        # Carrega a pista inicial
        if os.path.exists(self.arquivo_atual):
            self.carregar_pista(self.arquivo_atual)
        else:
            self.criar_pista_padrao()

        if self.objetos_catalogo:
            self.sincronizar_form_com_objeto_selecionado()

        # Constrói os botões da interface
        self.setup_ui()

    def detectar_fundos(self):
        fundos = []
        if os.path.exists("images"):
            for f in sorted(os.listdir("images")):
                if f.lower().endswith((".png", ".jpg")):
                    fundos.append(f"images/{f}")
        if not fundos:
            fundos = ["images/bg_rio.png"]
        return fundos

    def detectar_pngs_referencia(self):
        arquivos = ["NENHUMA"]
        for pasta in ["referencias", "images/objects"]:
            if os.path.exists(pasta):
                for f in sorted(os.listdir(pasta)):
                    if f.lower().endswith(".png"):
                        arquivos.append(f"{pasta}/{f}")
        return arquivos

    def detectar_pngs_objetos(self):
        """ Escaneia pastas comuns em busca de PNGs para muretas e placas """
        arquivos = []
        pastas = ["images/objetos", "objetos", "images/track", "images/objects", "assets"]
        for pasta in pastas:
            if os.path.exists(pasta):
                for f in sorted(os.listdir(pasta)):
                    if f.lower().endswith(".png"):
                        caminho = f"{pasta}/{f}"
                        if caminho not in arquivos:
                            arquivos.append(caminho)
        if not arquivos:
            arquivos = ["images/mureta.png"]
        return arquivos

    def carregar_catalogo_objetos_global(self):
        if os.path.exists("objetos_pista.json"):
            try:
                with open("objetos_pista.json", "r", encoding="utf-8") as f:
                    dados = json.load(f)
                if isinstance(dados, list):
                    return dados
            except Exception as e:
                print(f"Aviso ao ler objetos_pista.json: {e}")
        return []

    def salvar_catalogo_objetos_global(self):
        try:
            with open("objetos_pista.json", "w", encoding="utf-8") as f:
                json.dump(self.objetos_catalogo, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.set_status(f"Erro ao salvar biblioteca de objetos: {e}", COLOR_DANGER)

    def obter_surf_objeto(self, png_path):
        if png_path not in self.obj_surf_cache:
            if png_path and os.path.exists(png_path):
                try:
                    self.obj_surf_cache[png_path] = pygame.image.load(png_path).convert_alpha()
                except Exception:
                    surf = pygame.Surface((64, 64), pygame.SRCALPHA)
                    pygame.draw.rect(surf, (220, 50, 50), (4, 4, 56, 40), border_radius=4)
                    pygame.draw.rect(surf, (255, 255, 255), (4, 4, 56, 40), width=2, border_radius=4)
                    self.obj_surf_cache[png_path] = surf
            else:
                surf = pygame.Surface((64, 64), pygame.SRCALPHA)
                pygame.draw.rect(surf, (220, 50, 50), (4, 4, 56, 40), border_radius=4)
                pygame.draw.rect(surf, (255, 255, 255), (4, 4, 56, 40), width=2, border_radius=4)
                self.obj_surf_cache[png_path] = surf
        return self.obj_surf_cache[png_path]

    def obter_surf_objeto_escalado(self, png_path, target_h):
        h_round = max(4, min(420, round(target_h / 4) * 4))
        chave = (png_path, h_round)
        if chave not in self.obj_scaled_cache:
            base = self.obter_surf_objeto(png_path)
            w_round = max(2, int(h_round * (base.get_width() / max(1, base.get_height()))))
            self.obj_scaled_cache[chave] = pygame.transform.scale(base, (w_round, h_round))
        return self.obj_scaled_cache[chave]

    def construir_mapa_objetos_metro(self):
        """ Converte self.objetos_pista em {metro: [objs]} para preview 3D e 2D em tempo real """
        mapa = {}
        if not self.segmentos or not self.objetos_pista:
            return mapa

        total_len = sum(int(s["length"]) for s in self.segmentos)
        if total_len <= 0:
            return mapa

        cat_dict = {item["nome"]: item for item in self.objetos_catalogo}
        inicios = []
        acc = 0
        for s in self.segmentos:
            inicios.append(acc)
            acc += int(s["length"])

        for ap in self.objetos_pista:
            s_idx = int(ap.get("seg_idx", 0))
            if s_idx < 0 or s_idx >= len(self.segmentos):
                continue
            def_obj = cat_dict.get(ap.get("objeto", ""))
            if not def_obj:
                continue

            lado = ap.get("lado", "esq")
            lados = ["esq", "dir"] if lado == "ambos" else [lado]
            qtd = max(1, int(ap.get("quantidade", 1)))
            inicio_pct = max(0.0, min(99.0, float(ap.get("inicio_pct", 0.0))))
            espacamento = float(ap.get("espacamento", 0))

            off_ini = float(def_obj.get("offset", 1.30))
            off_fim = float(def_obj.get("offset_fim", off_ini))

            seg_start = inicios[s_idx]
            seg_len = int(self.segmentos[s_idx]["length"])
            start_off = int(seg_len * (inicio_pct / 100.0))
            usable = max(1, seg_len - start_off)

            if qtd == 1:
                itens_metro = [(0, (seg_start + start_off) % total_len)]
            elif espacamento > 0:
                itens_metro = []
                for k in range(qtd):
                    offset_k = int(k * espacamento)
                    if offset_k <= usable:
                        itens_metro.append((k, (seg_start + start_off + offset_k) % total_len))
            else:
                passo = usable / float(qtd)
                itens_metro = [(k, (seg_start + start_off + int(k * passo)) % total_len) for k in range(qtd)]

            for k, m in itens_metro:
                if qtd > 1:
                    t = k / float(qtd - 1)
                    offset_atual = off_ini + (off_fim - off_ini) * t
                else:
                    offset_atual = off_ini

                if m not in mapa:
                    mapa[m] = []
                for ld in lados:
                    mapa[m].append({
                        "png": def_obj["png"],
                        "escala": float(def_obj.get("escala", 1.0)),
                        "offset": offset_atual,
                        "lado": ld,
                        "seg_idx": s_idx
                    })
        return mapa

    def detectar_pistas_disponiveis(self):
        pistas = []
        if os.path.exists("pistas"):
            for f in sorted(os.listdir("pistas")):
                if f.lower().endswith(".json"):
                    caminho = f"pistas/{f}"
                    nome_pista = os.path.splitext(f)[0].capitalize()
                    try:
                        with open(caminho, 'r', encoding='utf-8') as arq:
                            dados = json.load(arq)
                            nome_pista = dados.get("nome", nome_pista)
                    except Exception:
                        pass
                    pistas.append({"arquivo": caminho, "nome": nome_pista})
        return pistas

    def carregar_ref_surf(self, caminho):
        cache_key = (caminho, self.ref_width, self.ref_height, self.ref_angle)
        if cache_key not in self.ref_surf_cache:
            try:
                img = pygame.image.load(caminho).convert_alpha()
                scaled = pygame.transform.smoothscale(img, (self.ref_width, self.ref_height))
                if self.ref_angle != 0:
                    scaled = pygame.transform.rotozoom(scaled, -self.ref_angle, 1.0)
                surf = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
                surf.blit(scaled, (0, 0))
                surf.set_alpha(153)
                self.ref_surf_cache[cache_key] = surf
            except Exception as e:
                self.set_status(f"Erro ao carregar PNG de referência: {e}", COLOR_DANGER)
                return None
        return self.ref_surf_cache[cache_key]

    def carregar_bg_surf(self, caminho):
        cache_key = (caminho, self.bg_width, self.bg_height)
        if cache_key not in self.bg_surf_cache:
            try:
                img = pygame.image.load(caminho).convert()
                self.bg_surf_cache[cache_key] = pygame.transform.scale(img, (self.bg_width, self.bg_height))
            except Exception:
                surf = pygame.Surface((self.bg_width, self.bg_height))
                surf.fill((135, 206, 235))
                pygame.draw.polygon(surf, (34, 139, 34), [(0, self.bg_height), (self.bg_width // 4, self.bg_height // 4), (self.bg_width, self.bg_height)])
                self.bg_surf_cache[cache_key] = surf
        return self.bg_surf_cache[cache_key]

    def set_status(self, msg, color=COLOR_ACCENT, duration_ms=4000):
        self.status_msg = msg
        self.status_color = color
        self.status_timer = pygame.time.get_ticks() + duration_ms

    def criar_pista_padrao(self):
        self.nome_pista = "Circuito de Treinamento"
        self.arquivo_atual = "pistas/treino.json"
        self.bg_width = WIDTH * 2
        self.bg_height = 135
        self.objetos_pista = []
        self.obj_apl_sel_idx = 0
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
        self.cam_pos = 0.0
        self.bg_offset_x = 0.0
        self.set_status("Nova pista em branco criada com sucesso!")

    def carregar_pista(self, caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            self.nome_pista = dados.get("nome", "Pista Personalizada")
            self.arquivo_atual = caminho

            bg_path = dados.get("bg_image", "images/bg_rio.png")
            if bg_path in self.lista_bgs:
                self.bg_idx = self.lista_bgs.index(bg_path)
            else:
                self.lista_bgs.append(bg_path)
                self.bg_idx = len(self.lista_bgs) - 1

            self.bg_width = int(dados.get("bg_width", WIDTH * 2))
            self.bg_height = int(dados.get("bg_height", 135))

            cores = dados.get("cores", {})
            z1 = cores.get("zebra_1", [220, 20, 20])
            for i, p in enumerate(PRESETS_ZEBRA):
                if p["zebra_1"] == z1:
                    self.zebra_idx = i
                    break

            self.segmentos = []
            for s in dados.get("segmentos", []):
                self.segmentos.append({
                    "length": int(s.get("length", 100)),
                    "curve": round(float(s.get("curve", 0.0)), 4),
                    "hill": round(float(s.get("hill", 0.0)), 4),
                    "desc": s.get("desc", "Trecho da pista")
                })

            # Mescla catálogo embutido na pista com o catálogo global
            nomes_existentes = {item["nome"] for item in self.objetos_catalogo}
            for item in dados.get("objetos_catalogo", []):
                if item.get("nome") and item["nome"] not in nomes_existentes:
                    self.objetos_catalogo.append(item)
                    nomes_existentes.add(item["nome"])

            self.objetos_pista = []
            for ap in dados.get("objetos_pista", []):
                self.objetos_pista.append({
                    "seg_idx": int(ap.get("seg_idx", 0)),
                    "objeto": ap.get("objeto", ""),
                    "lado": ap.get("lado", "esq"),
                    "quantidade": max(1, int(ap.get("quantidade", 1))),
                    "inicio_pct": int(ap.get("inicio_pct", 0)),
                    "espacamento": int(ap.get("espacamento", 0))
                })
            self.obj_apl_sel_idx = 0

            if not self.segmentos:
                self.criar_pista_padrao()
                return

            self.seg_idx = 0
            self.cam_pos = 0.0
            self.bg_offset_x = 0.0
            self.set_status(f"Pista '{self.nome_pista}' carregada de {caminho}!", COLOR_SUCCESS)
        except Exception as e:
            self.set_status(f"Erro ao carregar '{caminho}': {e}", COLOR_DANGER)

    def salvar_pista(self, caminho):
        try:
            os.makedirs("pistas", exist_ok=True)
            preset_z = PRESETS_ZEBRA[self.zebra_idx]

            # Embute no JSON da pista os objetos utilizados nela
            nomes_usados = {ap["objeto"] for ap in self.objetos_pista}
            catalogo_usado = [obj for obj in self.objetos_catalogo if obj["nome"] in nomes_usados]

            dados = {
                "nome": self.nome_pista,
                "bg_image": self.lista_bgs[self.bg_idx],
                "bg_width": self.bg_width,
                "bg_height": self.bg_height,
                "cores": {
                    "zebra_1": preset_z["zebra_1"],
                    "zebra_2": preset_z["zebra_2"],
                    "grama_1": [0, 100, 0],
                    "grama_2": [0, 150, 0],
                    "asfalto_1": [100, 100, 100],
                    "asfalto_2": [105, 105, 105]
                },
                "segmentos": self.segmentos,
                "objetos_catalogo": catalogo_usado,
                "objetos_pista": self.objetos_pista
            }
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            self.salvar_catalogo_objetos_global()
            self.arquivo_atual = caminho
            self.set_status(f"Pista e objetos salvos com sucesso em '{caminho}'!", COLOR_SUCCESS)
        except Exception as e:
            self.set_status(f"Erro ao salvar pista: {e}", COLOR_DANGER)

    def nova_temporada(self):
        self.nome_temporada = "Nova Temporada"
        self.arquivo_temporada = "temporadas/nova_temporada.json"
        self.etapas_temporada = []
        self.etapa_sel_idx = 0
        self.lista_pistas_disponiveis = self.detectar_pistas_disponiveis()
        self.set_status("Nova temporada em branco criada!", COLOR_ACCENT)

    def carregar_temporada(self, caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            self.nome_temporada = dados.get("nome_temporada", "Temporada Carregada")
            self.arquivo_temporada = caminho
            self.etapas_temporada = []
            for item in dados.get("etapas", []):
                self.etapas_temporada.append({
                    "arquivo": item.get("arquivo", ""),
                    "nome": item.get("nome", "Pista"),
                    "voltas": int(item.get("voltas", 3))
                })
            self.etapa_sel_idx = 0
            self.set_status(f"Temporada '{self.nome_temporada}' carregada!", COLOR_SUCCESS)
        except Exception as e:
            self.set_status(f"Erro ao carregar temporada: {e}", COLOR_DANGER)

    def salvar_temporada(self, caminho):
        try:
            os.makedirs("temporadas", exist_ok=True)
            etapas_formatadas = []
            for idx, et in enumerate(self.etapas_temporada):
                etapas_formatadas.append({
                    "etapa": idx + 1,
                    "arquivo": et["arquivo"],
                    "nome": et["nome"],
                    "voltas": et["voltas"]
                })
            dados = {
                "nome_temporada": self.nome_temporada,
                "etapas": etapas_formatadas
            }
            with open(caminho, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            self.arquivo_temporada = caminho
            self.set_status(f"Temporada salva em '{caminho}'!", COLOR_SUCCESS)
        except Exception as e:
            self.set_status(f"Erro ao salvar temporada: {e}", COLOR_DANGER)

    # =========================================================================
    # CONFIGURAÇÃO DA INTERFACE DO USUÁRIO (BOTÕES)
    # =========================================================================
    def setup_ui(self):
        self.buttons = []
        self.buttons_objetos = []
        self.buttons_temporada = []
        self.buttons_globais = []
        p_x = 640

        # --- ABAS DE ALTERNÂNCIA DE MODO (TOPO ESQUERDO) ---
        self.buttons_globais.append(UIButton((20, 12, 155, 26), "EDITOR DE PISTAS", lambda: self.alternar_modo("PISTA"), color=(30, 80, 120), font_size=13))
        self.buttons_globais.append(UIButton((185, 12, 165, 26), "OBJETOS / MURETAS", lambda: self.alternar_modo("OBJETOS"), color=(30, 110, 85), font_size=13))
        self.buttons_globais.append(UIButton((360, 12, 165, 26), "CRIAR TEMPORADAS", lambda: self.alternar_modo("TEMPORADA"), color=(90, 50, 120), font_size=13))

        # --- BARRA SUPERIOR DO PAINEL DIREITO (MODO PISTA) ---
        self.buttons.append(UIButton((p_x, 15, 100, 32), "NOVA", self.action_nova_pista, color=(40, 50, 70)))
        self.buttons.append(UIButton((p_x + 110, 15, 110, 32), "CARREGAR", self.action_abrir_carregar, color=(40, 50, 70)))
        self.buttons.append(UIButton((p_x + 230, 15, 100, 32), "SALVAR", self.action_salvar_atual, color=(20, 120, 60), hover_color=(30, 160, 80)))
        self.buttons.append(UIButton((p_x + 340, 15, 140, 32), "SALVAR COMO...", self.action_abrir_salvar_como, color=(30, 80, 140), hover_color=(40, 110, 190)))

        # Cenário de fundo
        y_bg = 56
        self.buttons.append(UIButton((p_x + 150, y_bg, 30, 24), "<", self.action_prev_bg))
        self.buttons.append(UIButton((p_x + 420, y_bg, 30, 24), ">", self.action_next_bg))
        self.buttons.append(UIButton((p_x + 460, y_bg, 80, 24), "PADRÃO", self.resetar_bg_size, color=(50, 60, 80), hover_color=(70, 85, 110)))

        # Ajustes de Largura do Horizonte (Width)
        y_w = 85
        self.buttons.append(UIButton((p_x + 125, y_w, 48, 24), "-200", lambda: self.modificar_bg_width(-200)))
        self.buttons.append(UIButton((p_x + 177, y_w, 42, 24), "-50", lambda: self.modificar_bg_width(-50)))
        self.buttons.append(UIButton((p_x + 223, y_w, 38, 24), "-10", lambda: self.modificar_bg_width(-10)))
        self.buttons.append(UIButton((p_x + 355, y_w, 38, 24), "+10", lambda: self.modificar_bg_width(10)))
        self.buttons.append(UIButton((p_x + 397, y_w, 42, 24), "+50", lambda: self.modificar_bg_width(50)))
        self.buttons.append(UIButton((p_x + 443, y_w, 48, 24), "+200", lambda: self.modificar_bg_width(200)))

        # Ajustes de Altura do Horizonte (Height)
        y_h = 114
        self.buttons.append(UIButton((p_x + 125, y_h, 48, 24), "-50", lambda: self.modificar_bg_height(-50)))
        self.buttons.append(UIButton((p_x + 177, y_h, 42, 24), "-10", lambda: self.modificar_bg_height(-10)))
        self.buttons.append(UIButton((p_x + 223, y_h, 38, 24), "-2", lambda: self.modificar_bg_height(-2)))
        self.buttons.append(UIButton((p_x + 355, y_h, 38, 24), "+2", lambda: self.modificar_bg_height(2)))
        self.buttons.append(UIButton((p_x + 397, y_h, 42, 24), "+10", lambda: self.modificar_bg_height(10)))
        self.buttons.append(UIButton((p_x + 443, y_h, 48, 24), "+50", lambda: self.modificar_bg_height(50)))

        # Seletor de Zebra
        y_zb = 143
        self.buttons.append(UIButton((p_x + 150, y_zb, 30, 24), "<", self.action_prev_zebra))
        self.buttons.append(UIButton((p_x + 420, y_zb, 30, 24), ">", self.action_next_zebra))

        # Navegação entre segmentos
        y_nav = 181
        self.buttons.append(UIButton((p_x + 170, y_nav, 36, 26), "<<", self.action_primeiro_seg))
        self.buttons.append(UIButton((p_x + 215, y_nav, 36, 26), "<", self.action_prev_seg))
        self.buttons.append(UIButton((p_x + 370, y_nav, 36, 26), ">", self.action_next_seg))
        self.buttons.append(UIButton((p_x + 415, y_nav, 36, 26), ">>", self.action_ultimo_seg))

        # Distância
        y_dist = 238
        self.buttons.append(UIButton((p_x + 10, y_dist, 55, 26), "-100", lambda: self.modificar_length(-100)))
        self.buttons.append(UIButton((p_x + 70, y_dist, 50, 26), "-50", lambda: self.modificar_length(-50)))
        self.buttons.append(UIButton((p_x + 125, y_dist, 45, 26), "-10", lambda: self.modificar_length(-10)))
        self.buttons.append(UIButton((p_x + 400, y_dist, 45, 26), "+10", lambda: self.modificar_length(10)))
        self.buttons.append(UIButton((p_x + 450, y_dist, 50, 26), "+50", lambda: self.modificar_length(50)))
        self.buttons.append(UIButton((p_x + 505, y_dist, 55, 26), "+100", lambda: self.modificar_length(100)))

        # Curvatura
        y_curv = 295
        self.buttons.append(UIButton((p_x + 10, y_curv, 65, 26), "Forte E", lambda: self.definir_curva(-0.05), color=(60, 40, 80)))
        self.buttons.append(UIButton((p_x + 80, y_curv, 65, 26), "Média E", lambda: self.definir_curva(-0.03), color=(40, 60, 90)))
        self.buttons.append(UIButton((p_x + 150, y_curv, 60, 26), "Leve E", lambda: self.definir_curva(-0.015), color=(30, 70, 90)))
        self.buttons.append(UIButton((p_x + 220, y_curv, 65, 26), "RETA (0)", lambda: self.definir_curva(0.0), color=(40, 80, 50)))
        self.buttons.append(UIButton((p_x + 295, y_curv, 60, 26), "Leve D", lambda: self.definir_curva(0.015), color=(30, 70, 90)))
        self.buttons.append(UIButton((p_x + 360, y_curv, 65, 26), "Média D", lambda: self.definir_curva(0.03), color=(40, 60, 90)))
        self.buttons.append(UIButton((p_x + 430, y_curv, 65, 26), "Forte D", lambda: self.definir_curva(0.05), color=(60, 40, 80)))
        self.buttons.append(UIButton((p_x + 505, y_curv, 45, 26), "-0.00059", lambda: self.modificar_curva(-0.00059), font_size=11))
        self.buttons.append(UIButton((p_x + 555, y_curv, 45, 26), "+0.00059", lambda: self.modificar_curva(0.00059), font_size=11))

        # Relevo
        y_hill = 353
        self.buttons.append(UIButton((p_x + 10, y_hill, 95, 26), "Descida Forte", lambda: self.definir_hill(-0.002), color=(90, 40, 40)))
        self.buttons.append(UIButton((p_x + 110, y_hill, 90, 26), "Descida Leve", lambda: self.definir_hill(-0.001), color=(80, 50, 40)))
        self.buttons.append(UIButton((p_x + 205, y_hill, 75, 26), "Plano (0)", lambda: self.definir_hill(0.0), color=(40, 80, 50)))
        self.buttons.append(UIButton((p_x + 285, y_hill, 90, 26), "Subida Leve", lambda: self.definir_hill(0.001), color=(40, 70, 90)))
        self.buttons.append(UIButton((p_x + 380, y_hill, 95, 26), "Subida Forte", lambda: self.definir_hill(0.002), color=(40, 50, 110)))
        self.buttons.append(UIButton((p_x + 485, y_hill, 50, 26), "-0.0005", lambda: self.modificar_hill(-0.0005), font_size=12))
        self.buttons.append(UIButton((p_x + 540, y_hill, 50, 26), "+0.0005", lambda: self.modificar_hill(0.0005), font_size=12))

        # Ações de construção de pista
        y_act = 401
        self.buttons.append(UIButton((p_x + 10, y_act, 105, 28), "+ RETA", self.action_add_reta, color=(25, 90, 50), hover_color=(35, 120, 65)))
        self.buttons.append(UIButton((p_x + 125, y_act, 105, 28), "+ CURVA E", lambda: self.action_add_curva(-0.03), color=(30, 70, 110), hover_color=(40, 90, 140)))
        self.buttons.append(UIButton((p_x + 240, y_act, 105, 28), "+ CURVA D", lambda: self.action_add_curva(0.03), color=(30, 70, 110), hover_color=(40, 90, 140)))
        self.buttons.append(UIButton((p_x + 355, y_act, 115, 28), "+ CHICANE", self.action_add_chicane, color=(60, 50, 95), hover_color=(80, 65, 125)))
        self.buttons.append(UIButton((p_x + 480, y_act, 105, 28), "DUPLICAR", self.action_duplicar_seg, color=(60, 65, 75)))

        y_act2 = 434
        self.buttons.append(UIButton((p_x + 10, y_act2, 105, 26), "SUBIR (Ordem)", lambda: self.action_reordenar(-1), color=(40, 50, 65), font_size=13))
        self.buttons.append(UIButton((p_x + 125, y_act2, 105, 26), "DESCER (Ordem)", lambda: self.action_reordenar(1), color=(40, 50, 65), font_size=13))
        self.buttons.append(UIButton((p_x + 240, y_act2, 115, 26), "EXCLUIR TRECHO", self.action_excluir_seg, color=(120, 30, 30), hover_color=(160, 40, 40), font_size=13))

        # Camada de referência 2D
        y_ref1 = 594
        self.buttons.append(UIButton((p_x + 120, y_ref1, 28, 24), "<", self.action_prev_ref))
        self.buttons.append(UIButton((p_x + 320, y_ref1, 28, 24), ">", self.action_next_ref))
        self.buttons.append(UIButton((p_x + 356, y_ref1, 95, 24), "RECARREGAR", self.action_recarregar_refs, color=(40, 55, 75), font_size=12))
        self.buttons.append(UIButton((p_x + 458, y_ref1, 88, 24), "RESET TUDO", self.action_reset_ref_size, color=(50, 60, 80), font_size=12))

        y_ref2 = 623
        self.buttons.append(UIButton((p_x + 35,  y_ref2, 36, 24), "-50", lambda: self.modificar_ref_size(-50, 0), font_size=12))
        self.buttons.append(UIButton((p_x + 74,  y_ref2, 32, 24), "-10", lambda: self.modificar_ref_size(-10, 0), font_size=12))
        self.buttons.append(UIButton((p_x + 168, y_ref2, 32, 24), "+10", lambda: self.modificar_ref_size(10, 0), font_size=12))
        self.buttons.append(UIButton((p_x + 203, y_ref2, 36, 24), "+50", lambda: self.modificar_ref_size(50, 0), font_size=12))

        self.buttons.append(UIButton((p_x + 295, y_ref2, 36, 24), "-50", lambda: self.modificar_ref_size(0, -50), font_size=12))
        self.buttons.append(UIButton((p_x + 334, y_ref2, 32, 24), "-10", lambda: self.modificar_ref_size(0, -10), font_size=12))
        self.buttons.append(UIButton((p_x + 428, y_ref2, 32, 24), "+10", lambda: self.modificar_ref_size(0, 10), font_size=12))
        self.buttons.append(UIButton((p_x + 463, y_ref2, 36, 24), "+50", lambda: self.modificar_ref_size(0, 50), font_size=12))

        y_ref3 = 652
        self.buttons.append(UIButton((p_x + 35,  y_ref3, 36, 24), "-25", lambda: self.modificar_ref_pos(-25, 0), font_size=12))
        self.buttons.append(UIButton((p_x + 74,  y_ref3, 32, 24), "-5",  lambda: self.modificar_ref_pos(-5, 0), font_size=12))
        self.buttons.append(UIButton((p_x + 168, y_ref3, 32, 24), "+5",  lambda: self.modificar_ref_pos(5, 0), font_size=12))
        self.buttons.append(UIButton((p_x + 203, y_ref3, 36, 24), "+25", lambda: self.modificar_ref_pos(25, 0), font_size=12))

        self.buttons.append(UIButton((p_x + 295, y_ref3, 36, 24), "-25", lambda: self.modificar_ref_pos(0, -25), font_size=12))
        self.buttons.append(UIButton((p_x + 334, y_ref3, 32, 24), "-5",  lambda: self.modificar_ref_pos(0, -5), font_size=12))
        self.buttons.append(UIButton((p_x + 428, y_ref3, 32, 24), "+5",  lambda: self.modificar_ref_pos(0, 5), font_size=12))
        self.buttons.append(UIButton((p_x + 463, y_ref3, 36, 24), "+25", lambda: self.modificar_ref_pos(0, 25), font_size=12))

        y_ref4 = 681
        self.buttons.append(UIButton((p_x + 55,  y_ref4, 44, 24), "-15°", lambda: self.modificar_ref_angle(-15), font_size=12))
        self.buttons.append(UIButton((p_x + 104, y_ref4, 40, 24), "-1°",  lambda: self.modificar_ref_angle(-1), font_size=12))
        self.buttons.append(UIButton((p_x + 215, y_ref4, 40, 24), "+1°",  lambda: self.modificar_ref_angle(1), font_size=12))
        self.buttons.append(UIButton((p_x + 260, y_ref4, 44, 24), "+15°", lambda: self.modificar_ref_angle(15), font_size=12))
        self.buttons.append(UIButton((p_x + 314, y_ref4, 70, 24), "ZERAR 0°", self.action_reset_ref_angle, color=(50, 60, 80), font_size=11))

        # Controles da câmera 3D
        self.buttons.append(UIButton((20, 680, 110, 26), "PULAR P/ TRECHO", self.action_focar_camera_trecho, color=(35, 50, 70), font_size=12))
        self.buttons.append(UIButton((140, 680, 100, 26), "PLAY / PAUSE", self.action_toggle_play, color=(20, 90, 130), font_size=12))
        self.buttons.append(UIButton((250, 680, 70, 26), "RESET", self.action_reset_cam, color=(50, 50, 60), font_size=12))

        # =====================================================================
        # BOTÕES DO MODO OBJETOS / MURETAS
        # =====================================================================
        # Barra superior do painel direito
        self.buttons_objetos.append(UIButton((p_x, 15, 130, 30), "SALVAR PISTA", self.action_salvar_atual, color=(20, 120, 60), hover_color=(30, 160, 80), font_size=13))
        self.buttons_objetos.append(UIButton((p_x + 140, 15, 145, 30), "RECARREGAR PNGs", self.action_recarregar_pngs_obj, color=(40, 55, 75), font_size=13))

        # Seletor de PNG do Objeto
        self.buttons_objetos.append(UIButton((p_x + 140, 92, 28, 24), "<", self.action_prev_obj_png))
        self.buttons_objetos.append(UIButton((p_x + 370, 92, 28, 24), ">", self.action_next_obj_png))

        # Escala do Objeto + Atalhos de Offset
        self.buttons_objetos.append(UIButton((p_x + 85, 122, 38, 24), "-0.2", lambda: self.modificar_obj_escala(-0.2), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 127, 122, 34, 24), "-0.1", lambda: self.modificar_obj_escala(-0.1), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 215, 122, 34, 24), "+0.1", lambda: self.modificar_obj_escala(0.1), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 253, 122, 38, 24), "+0.2", lambda: self.modificar_obj_escala(0.2), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 310, 122, 135, 24), "INVERTER OFFSETS", self.action_inverter_obj_offsets, color=(55, 65, 90), font_size=11))
        self.buttons_objetos.append(UIButton((p_x + 455, 122, 135, 24), "IGUALAR OFFSETS", self.action_igualar_obj_offsets, color=(50, 70, 80), font_size=11))

        # Offset Lateral INICIAL do Objeto
        self.buttons_objetos.append(UIButton((p_x + 82, 152, 40, 24), "-0.10", lambda: self.modificar_obj_offset_ini(-0.10), font_size=11))
        self.buttons_objetos.append(UIButton((p_x + 125, 152, 38, 24), "-0.05", lambda: self.modificar_obj_offset_ini(-0.05), font_size=11))
        self.buttons_objetos.append(UIButton((p_x + 207, 152, 38, 24), "+0.05", lambda: self.modificar_obj_offset_ini(0.05), font_size=11))
        self.buttons_objetos.append(UIButton((p_x + 248, 152, 40, 24), "+0.10", lambda: self.modificar_obj_offset_ini(0.10), font_size=11))

        # Offset Lateral FINAL do Objeto
        self.buttons_objetos.append(UIButton((p_x + 372, 152, 40, 24), "-0.10", lambda: self.modificar_obj_offset_fim(-0.10), font_size=11))
        self.buttons_objetos.append(UIButton((p_x + 415, 152, 38, 24), "-0.05", lambda: self.modificar_obj_offset_fim(-0.05), font_size=11))
        self.buttons_objetos.append(UIButton((p_x + 497, 152, 38, 24), "+0.05", lambda: self.modificar_obj_offset_fim(0.05), font_size=11))
        self.buttons_objetos.append(UIButton((p_x + 538, 152, 40, 24), "+0.10", lambda: self.modificar_obj_offset_fim(0.10), font_size=11))

        # Criar / Atualizar / Excluir Objeto do Catálogo
        self.buttons_objetos.append(UIButton((p_x + 10, 182, 175, 26), "+ CRIAR NOVO OBJETO", self.action_criar_objeto_catalogo, color=(25, 115, 60), hover_color=(35, 150, 80), font_size=13))
        self.buttons_objetos.append(UIButton((p_x + 195, 182, 165, 26), "ATUALIZAR SELEC.", self.action_atualizar_objeto_catalogo, color=(35, 80, 130), font_size=13))
        self.buttons_objetos.append(UIButton((p_x + 370, 182, 145, 26), "EXCLUIR OBJETO", self.action_excluir_objeto_catalogo, color=(130, 35, 35), hover_color=(170, 45, 45), font_size=13))

        # Navegação de Trecho dentro da aba Objetos
        y_apl_seg = 342
        self.buttons_objetos.append(UIButton((p_x + 390, y_apl_seg, 36, 26), "<<", self.action_primeiro_seg))
        self.buttons_objetos.append(UIButton((p_x + 432, y_apl_seg, 36, 26), "<", self.action_prev_seg))
        self.buttons_objetos.append(UIButton((p_x + 474, y_apl_seg, 36, 26), ">", self.action_next_seg))
        self.buttons_objetos.append(UIButton((p_x + 516, y_apl_seg, 36, 26), ">>", self.action_ultimo_seg))

        # Seleção de Lado (Esquerdo, Direito, Ambos)
        y_lado = 376
        self.buttons_objetos.append(UIButton((p_x + 115, y_lado, 105, 26), "ESQUERDO", lambda: self.definir_apl_lado("esq"), color=(45, 60, 85), font_size=13))
        self.buttons_objetos.append(UIButton((p_x + 228, y_lado, 105, 26), "DIREITO", lambda: self.definir_apl_lado("dir"), color=(45, 60, 85), font_size=13))
        self.buttons_objetos.append(UIButton((p_x + 341, y_lado, 105, 26), "AMBOS", lambda: self.definir_apl_lado("ambos"), color=(45, 60, 85), font_size=13))

        # Quantidade de Replicações no Trecho
        y_qtd = 410
        self.buttons_objetos.append(UIButton((p_x + 115, y_qtd, 40, 26), "-10", lambda: self.modificar_apl_qtd(-10), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 159, y_qtd, 36, 26), "-5", lambda: self.modificar_apl_qtd(-5), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 199, y_qtd, 34, 26), "-1", lambda: self.modificar_apl_qtd(-1), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 292, y_qtd, 34, 26), "+1", lambda: self.modificar_apl_qtd(1), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 330, y_qtd, 36, 26), "+5", lambda: self.modificar_apl_qtd(5), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 370, y_qtd, 40, 26), "+10", lambda: self.modificar_apl_qtd(10), font_size=12))

        # Início % no trecho
        self.buttons_objetos.append(UIButton((p_x + 485, y_qtd, 36, 26), "-10%", lambda: self.modificar_apl_inicio(-10), font_size=11))
        self.buttons_objetos.append(UIButton((p_x + 566, y_qtd, 36, 26), "+10%", lambda: self.modificar_apl_inicio(10), font_size=11))

        # Espaçamento (Distância em metros entre réplicas: 0 = Auto, 1 = 1m colado)
        y_esp = 442
        self.buttons_objetos.append(UIButton((p_x + 115, y_esp, 40, 24), "-5m", lambda: self.modificar_apl_espacamento(-5), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 159, y_esp, 36, 24), "-1m", lambda: self.modificar_apl_espacamento(-1), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 275, y_esp, 36, 24), "+1m", lambda: self.modificar_apl_espacamento(1), font_size=12))
        self.buttons_objetos.append(UIButton((p_x + 315, y_esp, 40, 24), "+5m", lambda: self.modificar_apl_espacamento(5), font_size=12))

        # Botão Aplicar/Replicar + Remover Aplicado (desce para 472)
        y_apl_btn = 472
        self.buttons_objetos.append(UIButton((p_x + 10, y_apl_btn, 255, 28), "+ APLICAR / REPLICAR NO TRECHO", self.action_aplicar_objeto_trecho, color=(20, 125, 65), hover_color=(30, 165, 85), font_size=13))
        self.buttons_objetos.append(UIButton((p_x + 275, y_apl_btn, 155, 28), "REMOVER ITEM", self.action_remover_aplicacao, color=(130, 35, 35), hover_color=(170, 45, 45), font_size=13))
        self.buttons_objetos.append(UIButton((p_x + 440, y_apl_btn, 150, 28), "LIMPAR TRECHO", self.action_limpar_objetos_trecho, color=(95, 45, 35), hover_color=(135, 60, 45), font_size=13))

        # Controles de câmera na aba Objetos (mesma posição esquerda)
        self.buttons_objetos.append(UIButton((20, 680, 95, 26), "< TRECHO", self.action_prev_seg, color=(35, 50, 70), font_size=12))
        self.buttons_objetos.append(UIButton((122, 680, 95, 26), "TRECHO >", self.action_next_seg, color=(35, 50, 70), font_size=12))
        self.buttons_objetos.append(UIButton((225, 680, 100, 26), "PLAY / PAUSE", self.action_toggle_play, color=(20, 90, 130), font_size=12))
        self.buttons_objetos.append(UIButton((332, 680, 70, 26), "RESET", self.action_reset_cam, color=(50, 50, 60), font_size=12))

        # =====================================================================
        # BOTÕES DO MODO TEMPORADA
        # =====================================================================
        self.buttons_temporada.append(UIButton((p_x, 15, 100, 32), "NOVA", self.nova_temporada, color=(40, 50, 70)))
        self.buttons_temporada.append(UIButton((p_x + 110, 15, 110, 32), "CARREGAR", lambda: setattr(self, 'modal_aberto', 'CARREGAR_TEMP'), color=(40, 50, 70)))
        self.buttons_temporada.append(UIButton((p_x + 230, 15, 100, 32), "SALVAR", lambda: self.salvar_temporada(self.arquivo_temporada), color=(20, 120, 60), hover_color=(30, 160, 80)))
        self.buttons_temporada.append(UIButton((p_x + 340, 15, 140, 32), "SALVAR COMO...", self.action_abrir_salvar_como_temp, color=(30, 80, 140), hover_color=(40, 110, 190)))

        self.buttons_temporada.append(UIButton((40, 635, 170, 32), "ATUALIZAR LISTA", self.action_atualizar_pistas_temp, color=(40, 55, 75)))
        self.buttons_temporada.append(UIButton((220, 635, 220, 32), "+ ADICIONAR À TEMPORADA", self.action_add_pista_temporada, color=(25, 110, 60), hover_color=(35, 145, 80)))
        self.buttons_temporada.append(UIButton((450, 635, 150, 32), "ABRIR NO EDITOR", self.action_editar_pista_selecionada, color=(50, 60, 85)))

        self.buttons_temporada.append(UIButton((p_x, 635, 100, 32), "SUBIR", lambda: self.action_mover_etapa(-1), color=(40, 50, 65)))
        self.buttons_temporada.append(UIButton((p_x + 110, 635, 100, 32), "DESCER", lambda: self.action_mover_etapa(1), color=(40, 50, 65)))
        self.buttons_temporada.append(UIButton((p_x + 220, 635, 85, 32), "-1 VOLTA", lambda: self.action_alterar_voltas_etapa(-1), color=(45, 65, 85)))
        self.buttons_temporada.append(UIButton((p_x + 315, 635, 85, 32), "+1 VOLTA", lambda: self.action_alterar_voltas_etapa(1), color=(45, 65, 85)))
        self.buttons_temporada.append(UIButton((p_x + 410, 635, 130, 32), "REMOVER ETAPA", self.action_remover_etapa, color=(130, 35, 35), hover_color=(170, 45, 45)))

    # =========================================================================
    # AÇÕES DE OBJETOS / MURETAS E PLACAS
    # =========================================================================
    def sincronizar_form_com_objeto_selecionado(self):
        if 0 <= self.obj_cat_sel_idx < len(self.objetos_catalogo):
            obj = self.objetos_catalogo[self.obj_cat_sel_idx]
            self.obj_nome_input = obj.get("nome", "Objeto")
            self.obj_escala_input = round(float(obj.get("escala", 1.0)), 2)
            off_ini = round(float(obj.get("offset", 1.30)), 2)
            self.obj_offset_ini_input = off_ini
            self.obj_offset_fim_input = round(float(obj.get("offset_fim", off_ini)), 2)
            png = obj.get("png", "")
            if png in self.lista_pngs_objetos:
                self.obj_png_idx = self.lista_pngs_objetos.index(png)
            else:
                self.lista_pngs_objetos.append(png)
                self.obj_png_idx = len(self.lista_pngs_objetos) - 1

    def action_recarregar_pngs_obj(self):
        atual = self.lista_pngs_objetos[self.obj_png_idx] if self.lista_pngs_objetos else ""
        self.lista_pngs_objetos = self.detectar_pngs_objetos()
        self.obj_surf_cache.clear()
        self.obj_scaled_cache.clear()
        self.obj_png_idx = self.lista_pngs_objetos.index(atual) if atual in self.lista_pngs_objetos else 0
        self.set_status(f"{len(self.lista_pngs_objetos)} PNGs disponíveis para objetos!")

    def action_prev_obj_png(self):
        if self.lista_pngs_objetos:
            self.obj_png_idx = (self.obj_png_idx - 1) % len(self.lista_pngs_objetos)

    def action_next_obj_png(self):
        if self.lista_pngs_objetos:
            self.obj_png_idx = (self.obj_png_idx + 1) % len(self.lista_pngs_objetos)

    def modificar_obj_escala(self, delta):
        self.obj_escala_input = round(max(0.2, min(4.0, self.obj_escala_input + delta)), 2)

    def modificar_obj_offset_ini(self, delta):
        self.obj_offset_ini_input = round(max(1.05, min(10.50, self.obj_offset_ini_input + delta)), 2)

    def modificar_obj_offset_fim(self, delta):
        self.obj_offset_fim_input = round(max(1.05, min(10.50, self.obj_offset_fim_input + delta)), 2)

    def action_inverter_obj_offsets(self):
        self.obj_offset_ini_input, self.obj_offset_fim_input = self.obj_offset_fim_input, self.obj_offset_ini_input
        self.set_status(f"Offsets invertidos: {self.obj_offset_ini_input:.2f} -> {self.obj_offset_fim_input:.2f}")

    def action_igualar_obj_offsets(self):
        self.obj_offset_fim_input = self.obj_offset_ini_input
        self.set_status(f"Offset final igualado ao inicial: {self.obj_offset_ini_input:.2f}")

    def action_criar_objeto_catalogo(self):
        nome = self.obj_nome_input.strip()
        if not nome:
            self.set_status("Digite um nome para o objeto antes de criar!", COLOR_WARNING)
            return
        png_atual = self.lista_pngs_objetos[self.obj_png_idx]

        for idx, item in enumerate(self.objetos_catalogo):
            if item["nome"].lower() == nome.lower():
                item["nome"] = nome
                item["png"] = png_atual
                item["escala"] = self.obj_escala_input
                item["offset"] = self.obj_offset_ini_input
                item["offset_fim"] = self.obj_offset_fim_input
                self.obj_cat_sel_idx = idx
                self.salvar_catalogo_objetos_global()
                self.set_status(f"Objeto '{nome}' atualizado!", COLOR_SUCCESS)
                return

        novo_obj = {
            "nome": nome,
            "png": png_atual,
            "escala": self.obj_escala_input,
            "offset": self.obj_offset_ini_input,
            "offset_fim": self.obj_offset_fim_input
        }
        self.objetos_catalogo.append(novo_obj)
        self.obj_cat_sel_idx = len(self.objetos_catalogo) - 1
        self.salvar_catalogo_objetos_global()
        self.set_status(
            f"Objeto '{nome}' criado (Offset {self.obj_offset_ini_input:.2f} -> {self.obj_offset_fim_input:.2f})!",
            COLOR_SUCCESS
        )

    def action_atualizar_objeto_catalogo(self):
        if not (0 <= self.obj_cat_sel_idx < len(self.objetos_catalogo)):
            self.action_criar_objeto_catalogo()
            return
        nome_novo = self.obj_nome_input.strip()
        if not nome_novo:
            self.set_status("O nome do objeto não pode ficar vazio!", COLOR_WARNING)
            return
        obj = self.objetos_catalogo[self.obj_cat_sel_idx]
        nome_antigo = obj["nome"]
        obj["nome"] = nome_novo
        obj["png"] = self.lista_pngs_objetos[self.obj_png_idx]
        obj["escala"] = self.obj_escala_input
        obj["offset"] = self.obj_offset_ini_input
        obj["offset_fim"] = self.obj_offset_fim_input

        if nome_antigo != nome_novo:
            for ap in self.objetos_pista:
                if ap["objeto"] == nome_antigo:
                    ap["objeto"] = nome_novo

        self.salvar_catalogo_objetos_global()
        self.set_status(f"Objeto '{nome_novo}' atualizado!", COLOR_SUCCESS)

    def action_excluir_objeto_catalogo(self):
        if not (0 <= self.obj_cat_sel_idx < len(self.objetos_catalogo)):
            return
        removido = self.objetos_catalogo.pop(self.obj_cat_sel_idx)
        self.objetos_pista = [ap for ap in self.objetos_pista if ap["objeto"] != removido["nome"]]
        self.obj_cat_sel_idx = max(0, min(self.obj_cat_sel_idx, len(self.objetos_catalogo) - 1))
        self.salvar_catalogo_objetos_global()
        if self.objetos_catalogo:
            self.sincronizar_form_com_objeto_selecionado()
        self.set_status(f"Objeto '{removido['nome']}' removido.", COLOR_WARNING)

    def definir_apl_lado(self, lado):
        self.apl_lado = lado

    def modificar_apl_qtd(self, delta):
        self.apl_quantidade = max(1, min(1000, self.apl_quantidade + delta))

    def modificar_apl_espacamento(self, delta):
        self.apl_espacamento = max(0, min(50, self.apl_espacamento + delta))

    def modificar_apl_inicio(self, delta):
        self.apl_inicio_pct = max(0, min(95, self.apl_inicio_pct + delta))

    def action_aplicar_objeto_trecho(self):
        if not self.objetos_catalogo:
            self.set_status("Crie pelo menos 1 objeto primeiro!", COLOR_WARNING)
            return
        if not self.segmentos:
            return

        obj_sel = self.objetos_catalogo[self.obj_cat_sel_idx]
        nova_apl = {
            "seg_idx": self.seg_idx,
            "objeto": obj_sel["nome"],
            "lado": self.apl_lado,
            "quantidade": self.apl_quantidade,
            "inicio_pct": self.apl_inicio_pct,
            "espacamento": self.apl_espacamento
        }
        self.objetos_pista.append(nova_apl)
        self.obj_apl_sel_idx = len(self.objetos_pista) - 1
        lado_str = {"esq": "Esquerdo", "dir": "Direito", "ambos": "Ambos os Lados"}[self.apl_lado]
        self.set_status(
            f"'{obj_sel['nome']}' ({self.apl_quantidade}x) aplicado no Trecho #{self.seg_idx + 1} ({lado_str})!",
            COLOR_SUCCESS
        )

    def action_remover_aplicacao(self):
        if 0 <= self.obj_apl_sel_idx < len(self.objetos_pista):
            rem = self.objetos_pista.pop(self.obj_apl_sel_idx)
            self.obj_apl_sel_idx = max(0, min(self.obj_apl_sel_idx, len(self.objetos_pista) - 1))
            self.set_status(f"Removido '{rem['objeto']}' do Trecho #{rem['seg_idx'] + 1}.", COLOR_WARNING)

    def action_limpar_objetos_trecho(self):
        antes = len(self.objetos_pista)
        self.objetos_pista = [ap for ap in self.objetos_pista if ap["seg_idx"] != self.seg_idx]
        self.obj_apl_sel_idx = max(0, min(self.obj_apl_sel_idx, len(self.objetos_pista) - 1))
        removidos = antes - len(self.objetos_pista)
        self.set_status(f"{removidos} grupo(s) de objetos removidos do Trecho #{self.seg_idx + 1}.", COLOR_WARNING)

    # =========================================================================
    # AÇÕES DOS BOTÕES DA PISTA
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

    def modificar_bg_width(self, delta):
        self.bg_width = max(200, min(10000, self.bg_width + delta))
        self.set_status(f"Largura do BG do Horizonte: {self.bg_width}px")

    def modificar_bg_height(self, delta):
        self.bg_height = max(20, min(1000, self.bg_height + delta))
        self.set_status(f"Altura do BG do Horizonte: {self.bg_height}px")

    def resetar_bg_size(self):
        self.bg_width = WIDTH * 2
        self.bg_height = 135
        self.set_status(f"Tamanho do BG restaurado: {self.bg_width}x{self.bg_height}px")

    def action_prev_zebra(self):
        self.zebra_idx = (self.zebra_idx - 1) % len(PRESETS_ZEBRA)
        self.set_status(f"Cores de Zebra: {PRESETS_ZEBRA[self.zebra_idx]['nome']}")

    def action_next_zebra(self):
        self.zebra_idx = (self.zebra_idx + 1) % len(PRESETS_ZEBRA)
        self.set_status(f"Cores de Zebra: {PRESETS_ZEBRA[self.zebra_idx]['nome']}")

    def action_prev_ref(self):
        self.ref_idx = (self.ref_idx - 1) % len(self.lista_refs)
        nome = os.path.basename(self.lista_refs[self.ref_idx])
        self.set_status(f"Gabarito 2D: {nome}")

    def action_next_ref(self):
        self.ref_idx = (self.ref_idx + 1) % len(self.lista_refs)
        nome = os.path.basename(self.lista_refs[self.ref_idx])
        self.set_status(f"Gabarito 2D: {nome}")

    def action_recarregar_refs(self):
        atual = self.lista_refs[self.ref_idx]
        self.lista_refs = self.detectar_pngs_referencia()
        self.ref_surf_cache.clear()
        self.ref_idx = self.lista_refs.index(atual) if atual in self.lista_refs else 0
        self.set_status(f"{len(self.lista_refs) - 1} PNGs encontrados para gabarito!")

    def modificar_ref_size(self, dw, dh):
        self.ref_width = max(50, min(1200, self.ref_width + dw))
        self.ref_height = max(50, min(1200, self.ref_height + dh))
        self.set_status(f"Tamanho do Gabarito 2D: {self.ref_width}x{self.ref_height}px")

    def modificar_ref_pos(self, dx, dy):
        self.ref_offset_x = max(-1000, min(1000, self.ref_offset_x + dx))
        self.ref_offset_y = max(-1000, min(1000, self.ref_offset_y + dy))
        self.set_status(f"Posição do Gabarito 2D -> X: {self.ref_offset_x} | Y: {self.ref_offset_y}")

    def modificar_ref_angle(self, d_angle):
        self.ref_angle = (self.ref_angle + d_angle)
        if self.ref_angle > 180:
            self.ref_angle -= 360
        elif self.ref_angle < -180:
            self.ref_angle += 360
        sentido = "Horário" if self.ref_angle > 0 else ("Anti-horário" if self.ref_angle < 0 else "Neutro")
        self.set_status(f"Rotação do Gabarito 2D: {self.ref_angle:+d}° ({sentido})")

    def action_reset_ref_angle(self):
        self.ref_angle = 0
        self.set_status("Rotação do Gabarito 2D zerada (0°)")

    def action_reset_ref_size(self):
        self.ref_width = 400
        self.ref_height = 300
        self.ref_offset_x = 0
        self.ref_offset_y = 0
        self.ref_angle = 0
        self.set_status("Gabarito 2D restaurado (400x300px | X: 0, Y: 0 | 0°)")

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
        if not self.segmentos:
            return
        seg = self.segmentos[self.seg_idx]
        seg["length"] = max(20, min(2000, seg["length"] + delta))
        self.set_status(f"Extensão do trecho #{self.seg_idx + 1}: {seg['length']}m")

    def obter_curva_na_posicao(self, pos):
        if not self.segmentos:
            return 0.0
        total_len = sum(s["length"] for s in self.segmentos)
        if total_len <= 0:
            return 0.0
        p = pos % total_len
        dist_acc = 0
        for s in self.segmentos:
            dist_acc += s["length"]
            if p < dist_acc:
                return s["curve"]
        return 0.0

    def sincronizar_bg_offset_com_posicao(self):
        if not self.segmentos:
            self.bg_offset_x = 0.0
            return
        total_len = sum(s["length"] for s in self.segmentos)
        if total_len <= 0:
            self.bg_offset_x = 0.0
            return
        pos = self.cam_pos % total_len
        accum_rot = 0.0
        restante = pos
        for s in self.segmentos:
            l = s["length"]
            c = s["curve"]
            if restante <= l:
                accum_rot += c * restante
                break
            else:
                accum_rot += c * l
                restante -= l
        self.bg_offset_x = -accum_rot * 120.0

    def definir_curva(self, valor):
        if not self.segmentos:
            return
        self.segmentos[self.seg_idx]["curve"] = round(float(valor), 4)
        self.sincronizar_bg_offset_com_posicao()
        self.set_status(f"Curvatura do trecho #{self.seg_idx + 1}: {valor:+.4f}")

    def modificar_curva(self, delta):
        if not self.segmentos:
            return
        seg = self.segmentos[self.seg_idx]
        seg["curve"] = round(max(-0.08, min(0.08, seg["curve"] + delta)), 4)
        self.sincronizar_bg_offset_com_posicao()
        self.set_status(f"Curvatura do trecho #{self.seg_idx + 1}: {seg['curve']:+.4f}")

    def definir_hill(self, valor):
        if not self.segmentos:
            return
        self.segmentos[self.seg_idx]["hill"] = round(float(valor), 4)
        self.set_status(f"Elevação do trecho #{self.seg_idx + 1}: {valor:+.4f}")

    def modificar_hill(self, delta):
        if not self.segmentos:
            return
        seg = self.segmentos[self.seg_idx]
        seg["hill"] = round(max(-0.004, min(0.004, seg["hill"] + delta)), 4)
        self.set_status(f"Elevação do trecho #{self.seg_idx + 1}: {seg['hill']:+.4f}")

    def action_add_reta(self):
        novo = {"length": 150, "curve": 0.0, "hill": 0.0, "desc": "Nova Reta"}
        insert_at = self.seg_idx + 1 if self.segmentos else 0
        self.segmentos.insert(insert_at, novo)
        for ap in self.objetos_pista:
            if ap["seg_idx"] >= insert_at:
                ap["seg_idx"] += 1
        self.seg_idx = insert_at
        self.action_focar_camera_trecho()
        self.set_status(f"Reta inserida na posição #{self.seg_idx + 1}!")

    def action_add_curva(self, curvatura):
        direcao = "Direita" if curvatura > 0 else "Esquerda"
        novo = {"length": 100, "curve": curvatura, "hill": 0.0, "desc": f"Curva para {direcao}"}
        insert_at = self.seg_idx + 1 if self.segmentos else 0
        self.segmentos.insert(insert_at, novo)
        for ap in self.objetos_pista:
            if ap["seg_idx"] >= insert_at:
                ap["seg_idx"] += 1
        self.seg_idx = insert_at
        self.action_focar_camera_trecho()
        self.set_status(f"Curva para {direcao} inserida na posição #{self.seg_idx + 1}!")

    def action_add_chicane(self):
        s1 = {"length": 70, "curve": -0.04, "hill": 0.0, "desc": "Chicane (Esq)"}
        s2 = {"length": 70, "curve": 0.04, "hill": 0.0, "desc": "Chicane (Dir)"}
        insert_at = self.seg_idx + 1 if self.segmentos else 0
        self.segmentos.insert(insert_at, s2)
        self.segmentos.insert(insert_at, s1)
        for ap in self.objetos_pista:
            if ap["seg_idx"] >= insert_at:
                ap["seg_idx"] += 2
        self.seg_idx = insert_at
        self.action_focar_camera_trecho()
        self.set_status(f"Chicane inserida nas posições #{self.seg_idx + 1} e #{self.seg_idx + 2}!")

    def action_duplicar_seg(self):
        if not self.segmentos:
            return
        original = self.segmentos[self.seg_idx]
        copia = original.copy()
        insert_at = self.seg_idx + 1
        self.segmentos.insert(insert_at, copia)
        for ap in self.objetos_pista:
            if ap["seg_idx"] >= insert_at:
                ap["seg_idx"] += 1
        self.seg_idx = insert_at
        self.action_focar_camera_trecho()
        self.set_status(f"Trecho #{self.seg_idx} duplicado com sucesso!")

    def action_excluir_seg(self):
        if len(self.segmentos) <= 1:
            self.set_status("A pista precisa ter pelo menos 1 trecho!", COLOR_WARNING)
            return
        rem_idx = self.seg_idx
        del self.segmentos[rem_idx]
        novas_apls = []
        for ap in self.objetos_pista:
            if ap["seg_idx"] == rem_idx:
                continue
            if ap["seg_idx"] > rem_idx:
                ap["seg_idx"] -= 1
            novas_apls.append(ap)
        self.objetos_pista = novas_apls
        self.seg_idx = min(self.seg_idx, len(self.segmentos) - 1)
        self.action_focar_camera_trecho()
        self.set_status(f"Trecho removido. Restam {len(self.segmentos)} trechos.")

    def action_reordenar(self, direcao):
        if not self.segmentos:
            return
        novo_idx = self.seg_idx + direcao
        if 0 <= novo_idx < len(self.segmentos):
            old_idx = self.seg_idx
            self.segmentos[old_idx], self.segmentos[novo_idx] = self.segmentos[novo_idx], self.segmentos[old_idx]
            for ap in self.objetos_pista:
                if ap["seg_idx"] == old_idx:
                    ap["seg_idx"] = novo_idx
                elif ap["seg_idx"] == novo_idx:
                    ap["seg_idx"] = old_idx
            self.seg_idx = novo_idx
            self.action_focar_camera_trecho()
            self.set_status(f"Trecho movido para a posição #{self.seg_idx + 1}")

    def action_focar_camera_trecho(self):
        if not self.segmentos:
            return
        dist = 0
        for i in range(self.seg_idx):
            dist += self.segmentos[i]["length"]
        self.cam_pos = float(dist)
        self.sincronizar_bg_offset_com_posicao()

    def action_toggle_play(self):
        self.is_playing = not self.is_playing

    def action_reset_cam(self):
        self.cam_pos = 0.0
        self.bg_offset_x = 0.0
        self.is_playing = False

    # =========================================================================
    # RENDERIZAÇÃO 1: PRÉ-VISUALIZAÇÃO AÉREA (TOP-DOWN 2D)
    # =========================================================================
    def desenhar_preview_aereo(self, rect):
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        txt_header = self.font_sub.render("PRÉ-VISUALIZAÇÃO AÉREA (2D)", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_header, (rect.x + 12, rect.y + 8))

        if 0 < self.ref_idx < len(self.lista_refs):
            ref_surf = self.carregar_ref_surf(self.lista_refs[self.ref_idx])
            if ref_surf:
                clip_area = pygame.Rect(rect.x + 2, rect.y + 30, rect.width - 4, rect.height - 52)
                self.screen.set_clip(clip_area)
                img_x = clip_area.centerx - (ref_surf.get_width() // 2) + self.ref_offset_x
                img_y = clip_area.centery - (ref_surf.get_height() // 2) + self.ref_offset_y
                self.screen.blit(ref_surf, (img_x, img_y))
                self.screen.set_clip(None)

                txt_xy_preview = self.font_mono.render(
                    f"PNG X:{self.ref_offset_x:+d} Y:{self.ref_offset_y:+d} R:{self.ref_angle:+d}°",
                    True,
                    COLOR_ACCENT
                )
                self.screen.blit(txt_xy_preview, (rect.right - 225, rect.bottom - 20))

        if not self.segmentos:
            return

        # Traçado dos pontos 2D metro a metro para mapear objetos com precisão
        pontos = []
        seg_indices_pontos = []
        x, y = 0.0, 0.0
        angulo = -math.pi / 2
        pontos.append((x, y))
        seg_indices_pontos.append(0)

        curve_factor = 0.5
        for i, s in enumerate(self.segmentos):
            c = s["curve"]
            l = int(s["length"])
            for _ in range(l):
                angulo += c * 1.0 * curve_factor
                x += math.cos(angulo) * 1.0
                y += math.sin(angulo) * 1.0
                pontos.append((x, y))
            seg_indices_pontos.append(len(pontos) - 1)

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

        pontos_tela = [(int(offset_x + px * scale), int(offset_y + py * scale)) for px, py in pontos]

        # Amostragem para linha suave
        passo_des = max(1, len(pontos_tela) // 350)
        pts_amostra = pontos_tela[::passo_des]
        if pts_amostra[-1] != pontos_tela[-1]:
            pts_amostra.append(pontos_tela[-1])

        if len(pts_amostra) > 1:
            pygame.draw.lines(self.screen, (60, 70, 85), False, pts_amostra, width=7)
            pygame.draw.lines(self.screen, (130, 140, 155), False, pts_amostra, width=3)

        # Destaca o segmento selecionado
        if self.seg_idx < len(seg_indices_pontos) - 1:
            idx_ini = seg_indices_pontos[self.seg_idx]
            idx_fim = seg_indices_pontos[self.seg_idx + 1]
            pts_destaque = pontos_tela[idx_ini:idx_fim + 1]
            if len(pts_destaque) > 1:
                pygame.draw.lines(self.screen, COLOR_SELECTED, False, pts_destaque, width=7)
                pygame.draw.circle(self.screen, (255, 255, 255), pts_destaque[0], 5)
                pygame.draw.circle(self.screen, COLOR_SELECTED, pts_destaque[-1], 5)

        # Desenha marcadores dos objetos laterais no mapa 2D
        mapa_objs = self.construir_mapa_objetos_metro()
        if mapa_objs and len(pontos_tela) > 2:
            for metro, objs in mapa_objs.items():
                if 0 <= metro < len(pontos_tela) - 1:
                    p0 = pontos_tela[metro]
                    p1 = pontos_tela[metro + 1]
                    vx, vy = p1[0] - p0[0], p1[1] - p0[1]
                    mag = math.hypot(vx, vy)
                    if mag > 0.001:
                        # Normal à esquerda (-vy, vx) ou direita (vy, -vx)
                        nx, ny = -vy / mag, vx / mag
                        for obj in objs:
                            sinal = -1 if obj["lado"] == "esq" else 1
                            dist_2d = max(4.0, min(28.0, obj["offset"] * 4.5))
                            ox = int(p0[0] + nx * dist_2d * sinal)
                            oy = int(p0[1] + ny * dist_2d * sinal)
                            cor_dot = (0, 230, 255) if obj["lado"] == "esq" else (255, 130, 50)
                            pygame.draw.circle(self.screen, cor_dot, (ox, oy), 2)

        pt_largada = pontos_tela[0]
        pt_fim = pontos_tela[-1]
        pygame.draw.circle(self.screen, COLOR_SUCCESS, pt_largada, 7)
        pygame.draw.circle(self.screen, COLOR_DANGER, pt_fim, 7)

        total_metros = sum(s["length"] for s in self.segmentos)
        if total_metros > 0 and len(pontos_tela) > 1:
            cam_frac = (self.cam_pos % total_metros) / float(total_metros)
            idx_pt_cam = min(len(pontos_tela) - 1, int(cam_frac * (len(pontos_tela) - 1)))
            pt_cam = pontos_tela[idx_pt_cam]
            pygame.draw.circle(self.screen, (0, 0, 0), pt_cam, 8)
            pygame.draw.circle(self.screen, COLOR_ACCENT, pt_cam, 6)
            pygame.draw.circle(self.screen, (255, 255, 255), pt_cam, 3)

        dist_fechamento = math.sqrt((pontos[-1][0] - pontos[0][0])**2 + (pontos[-1][1] - pontos[0][1])**2)

        if dist_fechamento < 60:
            badge_txt = self.font_small.render("CIRCUITO FECHADO", True, COLOR_SUCCESS)
            badge_color = (20, 80, 40)
        else:
            badge_txt = self.font_small.render(f"ABERTO (Faltam {int(dist_fechamento)}m)", True, COLOR_WARNING)
            badge_color = (90, 70, 20)

        pygame.draw.rect(self.screen, badge_color, (rect.right - 180, rect.y + 7, 168, 22), border_radius=4)
        self.screen.blit(badge_txt, (rect.right - 174, rect.y + 10))

        info_txt = self.font_small.render(f"Extensao: {total_metros}m | Trechos: {len(self.segmentos)} | Selecionado: #{self.seg_idx + 1}", True, COLOR_TEXT_MUTED)
        self.screen.blit(info_txt, (rect.x + 12, rect.bottom - 20))

    # =========================================================================
    # RENDERIZAÇÃO 2: MINI PREVIEW 3D DO COCKPIT / PISTA + OBJETOS
    # =========================================================================
    def desenhar_preview_3d(self, rect):
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        txt_header = self.font_sub.render("PRÉ-VISUALIZAÇÃO 3D (EM TEMPO REAL)", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_header, (rect.x + 12, rect.y + 8))

        if not self.segmentos:
            return

        track_data = []
        for s in self.segmentos:
            for _ in range(int(s["length"])):
                track_data.append({"curve": s["curve"], "hill": s["hill"]})
        if not track_data:
            return

        total_len = len(track_data)
        pos = self.cam_pos % total_len

        view_w, view_h = rect.width - 24, rect.height - 75
        cam_surf = pygame.Surface((view_w, view_h))
        cam_surf.fill(GREEN_DARK)

        bg_surf = self.carregar_bg_surf(self.lista_bgs[self.bg_idx])
        bg_w = bg_surf.get_width()
        draw_offset_x = self.bg_offset_x % bg_w
        if draw_offset_x > 0:
            draw_offset_x -= bg_w
        curr_x = draw_offset_x
        while curr_x < view_w:
            cam_surf.blit(bg_surf, (curr_x, 0))
            curr_x += bg_w

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

        segmentos_3d = []

        for n in range(1, draw_distance):
            z_near = n - pos_frac
            z_far = n + 1 - pos_frac
            if z_near <= 0.001:
                z_near = 0.001

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

            segmentos_3d.append({
                "centro": c_near,
                "largura": w_near,
                "y": y_near,
                "idx_fut": idx_fut
            })

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

        # Renderiza muretas e placas na pré-visualização 3D (de longe para perto)
        mapa_objs = self.construir_mapa_objetos_metro()
        if mapa_objs:
            for n in range(draw_distance - 1, 0, -1):
                seg3d = segmentos_3d[n - 1]
                objs = mapa_objs.get(seg3d["idx_fut"])
                if not objs:
                    continue
                for obj in objs:
                    obj_h = seg3d["largura"] * 0.25 * obj["escala"]
                    if obj_h < 2 or obj_h > 260:
                        continue
                    sp = self.obter_surf_objeto_escalado(obj["png"], obj_h)
                    w_sp, h_sp = sp.get_width(), sp.get_height()
                    if obj["lado"] == "esq":
                        ax = seg3d["centro"] - (obj["offset"] * seg3d["largura"])
                    else:
                        ax = seg3d["centro"] + (obj["offset"] * seg3d["largura"])
                    bx = int(ax - w_sp // 2)
                    by = int(seg3d["y"] - h_sp)
                    if bx + w_sp < 0 or bx > view_w:
                        continue
                    cam_surf.blit(sp, (bx, by))

        self.screen.blit(cam_surf, (rect.x + 12, rect.y + 35))

        status_play = "PLAYING (240 km/h)" if self.is_playing else "PAUSADO"
        cor_play = COLOR_SUCCESS if self.is_playing else COLOR_WARNING
        txt_cam = self.font_small.render(f"Posição: {int(pos)}m / {total_len}m | Status: {status_play}", True, cor_play)
        self.screen.blit(txt_cam, (rect.x + 330, rect.y + 10))

        txt_bg_dim = self.font_small.render(f"BG: {self.bg_width}x{self.bg_height}px", True, COLOR_TEXT_MUTED)
        self.screen.blit(txt_bg_dim, (rect.right - 140, rect.bottom - 22))

    # =========================================================================
    # RENDERIZAÇÃO 3: PAINEL DE EDIÇÃO DE PISTA (DIREITA)
    # =========================================================================
    def desenhar_painel_edicao(self):
        p_x = 640

        y_bg = 56
        lbl_bg = self.font_sub.render("CENÁRIO (BG):", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_bg, (p_x + 10, y_bg + 2))
        nome_bg = os.path.basename(self.lista_bgs[self.bg_idx])
        txt_bg = self.font_ui.render(nome_bg[:24], True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_bg, (p_x + 188, y_bg + 2))

        y_w = 85
        lbl_w = self.font_sub.render("LARGURA BG:", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_w, (p_x + 10, y_w + 2))
        txt_w_val = self.font_mono.render(f"{self.bg_width:4d} px", True, COLOR_SELECTED)
        self.screen.blit(txt_w_val, (p_x + 270, y_w + 3))

        y_h = 114
        lbl_h = self.font_sub.render("ALTURA BG:", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_h, (p_x + 10, y_h + 2))
        txt_h_val = self.font_mono.render(f"{self.bg_height:4d} px", True, COLOR_SELECTED)
        self.screen.blit(txt_h_val, (p_x + 270, y_h + 3))

        y_zb = 143
        lbl_zb = self.font_sub.render("ZEBRAS:", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_zb, (p_x + 10, y_zb + 2))
        p_zb = PRESETS_ZEBRA[self.zebra_idx]
        txt_zb = self.font_ui.render(p_zb["nome"], True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_zb, (p_x + 188, y_zb + 2))

        pygame.draw.rect(self.screen, tuple(p_zb["zebra_1"]), (p_x + 360, y_zb + 4, 20, 16), border_radius=2)
        pygame.draw.rect(self.screen, tuple(p_zb["zebra_2"]), (p_x + 384, y_zb + 4, 20, 16), border_radius=2)
        pygame.draw.rect(self.screen, COLOR_BORDER, (p_x + 360, y_zb + 4, 44, 16), width=1, border_radius=2)

        pygame.draw.line(self.screen, COLOR_BORDER, (p_x, 173), (WIDTH - 20, 173), 1)

        total_segs = len(self.segmentos)
        idx_str = f"Segmento {self.seg_idx + 1} de {total_segs}"
        txt_seg_idx = self.font_title.render(idx_str, True, COLOR_SELECTED)
        self.screen.blit(txt_seg_idx, (p_x + 10, 181))

        if self.segmentos:
            seg = self.segmentos[self.seg_idx]
            desc = seg.get("desc", "Sem descrição")
            txt_desc = self.font_ui.render(f"Descrição: {desc}", True, COLOR_TEXT_MUTED)
            self.screen.blit(txt_desc, (p_x + 10, 212))

            txt_l = self.font_sub.render(f"DISTÂNCIA: {seg['length']} metros", True, COLOR_TEXT_PRIMARY)
            self.screen.blit(txt_l, (p_x + 190, 240))

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
            self.screen.blit(txt_c, (p_x + 10, 272))

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
            self.screen.blit(txt_h, (p_x + 10, 330))

        pygame.draw.line(self.screen, COLOR_BORDER, (p_x, 389), (WIDTH - 20, 389), 1)
        self.desenhar_lista_segmentos(self.rect_lista)

        y_ref1 = 594
        lbl_ref = self.font_sub.render("GABARITO 2D:", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_ref, (p_x + 5, y_ref1 + 2))
        nome_ref = os.path.basename(self.lista_refs[self.ref_idx])
        txt_ref = self.font_ui.render(nome_ref[:22], True, COLOR_ACCENT if self.ref_idx > 0 else COLOR_TEXT_MUTED)
        self.screen.blit(txt_ref, (p_x + 154, y_ref1 + 2))

        y_ref2 = 623
        self.screen.blit(self.font_sub.render("W:", True, COLOR_TEXT_MUTED), (p_x + 10, y_ref2 + 2))
        self.screen.blit(self.font_mono.render(f"{self.ref_width:4d}", True, COLOR_SELECTED), (p_x + 114, y_ref2 + 4))

        self.screen.blit(self.font_sub.render("H:", True, COLOR_TEXT_MUTED), (p_x + 270, y_ref2 + 2))
        self.screen.blit(self.font_mono.render(f"{self.ref_height:4d}", True, COLOR_SELECTED), (p_x + 374, y_ref2 + 4))

        y_ref3 = 652
        self.screen.blit(self.font_sub.render("X:", True, COLOR_TEXT_MUTED), (p_x + 10, y_ref3 + 2))
        self.screen.blit(self.font_mono.render(f"{self.ref_offset_x:+4d}", True, COLOR_ACCENT), (p_x + 114, y_ref3 + 4))

        self.screen.blit(self.font_sub.render("Y:", True, COLOR_TEXT_MUTED), (p_x + 270, y_ref3 + 2))
        self.screen.blit(self.font_mono.render(f"{self.ref_offset_y:+4d}", True, COLOR_ACCENT), (p_x + 374, y_ref3 + 4))

        y_ref4 = 681
        self.screen.blit(self.font_sub.render("ROT:", True, COLOR_TEXT_MUTED), (p_x + 10, y_ref4 + 2))
        self.screen.blit(self.font_mono.render(f"{self.ref_angle:+4d}°", True, COLOR_WARNING), (p_x + 152, y_ref4 + 4))

    def desenhar_lista_segmentos(self, rect):
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, rect, width=1, border_radius=6)

        txt_l = self.font_sub.render("LISTA DE TRECHOS DA PISTA (Clique para selecionar):", True, COLOR_TEXT_MUTED)
        self.screen.blit(txt_l, (rect.x + 12, rect.y + 6))

        item_h = 24
        max_visiveis = (rect.height - 35) // item_h
        total = len(self.segmentos)

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

            qtd_objs = sum(ap["quantidade"] for ap in self.objetos_pista if ap["seg_idx"] == curr_idx)
            tag_obj = f" [{qtd_objs} obj]" if qtd_objs > 0 else ""

            linha_txt = f"#{curr_idx + 1:02d} | {s['length']:4d}m | {tipo:<19} | {elev:<9} | {s.get('desc','')[:14]}{tag_obj}"
            col_txt = COLOR_SELECTED if is_sel else COLOR_TEXT_PRIMARY
            txt_surf = self.font_mono.render(linha_txt, True, col_txt)
            self.screen.blit(txt_surf, (item_rect.x + 8, item_rect.y + 3))

    # =========================================================================
    # RENDERIZAÇÃO 4: PAINEL DE OBJETOS / MURETAS / PLACAS (ABA OBJETOS)
    # =========================================================================
    def desenhar_painel_objetos(self):
        p_x = 640

        txt_pista_info = self.font_sub.render(f"PISTA: {self.nome_pista[:24]}", True, COLOR_SELECTED)
        self.screen.blit(txt_pista_info, (p_x + 295, 20))

        # ---------------------------------------------------------------------
        # SEÇÃO 1: CRIAR / EDITAR OBJETO (CATÁLOGO PNG)
        # ---------------------------------------------------------------------
        card1 = pygame.Rect(p_x, 52, WIDTH - p_x - 20, 272)
        pygame.draw.rect(self.screen, COLOR_PANEL, card1, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, card1, width=1, border_radius=6)

        self.screen.blit(self.font_sub.render("1. NOME OBJETO:", True, COLOR_TEXT_MUTED), (p_x + 10, 65))
        pygame.draw.rect(self.screen, (18, 22, 32), self.rect_input_nome_obj, border_radius=4)
        borda_input = COLOR_SELECTED if self.editando_nome_obj else COLOR_ACCENT
        pygame.draw.rect(self.screen, borda_input, self.rect_input_nome_obj, width=2 if self.editando_nome_obj else 1, border_radius=4)
        cursor_str = "_" if self.editando_nome_obj else ""
        txt_nome_o = self.font_ui.render(self.obj_nome_input + cursor_str, True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_nome_o, (self.rect_input_nome_obj.x + 8, self.rect_input_nome_obj.y + 4))

        thumb_rect = pygame.Rect(p_x + 430, 60, 175, 60)
        pygame.draw.rect(self.screen, (18, 24, 34), thumb_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_BORDER, thumb_rect, width=1, border_radius=4)
        png_atual = self.lista_pngs_objetos[self.obj_png_idx] if self.lista_pngs_objetos else ""
        surf_prev = self.obter_surf_objeto(png_atual)
        if surf_prev:
            pw, ph = surf_prev.get_width(), surf_prev.get_height()
            fator = min(155 / max(1, pw), 48 / max(1, ph))
            nw, nh = max(4, int(pw * fator)), max(4, int(ph * fator))
            sp_mini = pygame.transform.smoothscale(surf_prev, (nw, nh))
            self.screen.blit(sp_mini, (thumb_rect.centerx - nw // 2, thumb_rect.centery - nh // 2))

        self.screen.blit(self.font_sub.render("IMAGEM PNG:", True, COLOR_TEXT_MUTED), (p_x + 10, 94))
        nome_png = os.path.basename(png_atual) if png_atual else "Nenhum"
        txt_png = self.font_mono.render(nome_png[:24], True, COLOR_ACCENT)
        self.screen.blit(txt_png, (p_x + 175, 96))

        self.screen.blit(self.font_sub.render("ESCALA:", True, COLOR_TEXT_MUTED), (p_x + 10, 124))
        self.screen.blit(self.font_mono.render(f"{self.obj_escala_input:.2f}x", True, COLOR_SELECTED), (p_x + 166, 126))

        self.screen.blit(self.font_sub.render("OFF INI:", True, COLOR_TEXT_MUTED), (p_x + 10, 154))
        self.screen.blit(self.font_mono.render(f"{self.obj_offset_ini_input:.2f}", True, COLOR_SELECTED), (p_x + 168, 156))

        self.screen.blit(self.font_sub.render("OFF FIM:", True, COLOR_TEXT_MUTED), (p_x + 300, 154))
        self.screen.blit(self.font_mono.render(f"{self.obj_offset_fim_input:.2f}", True, COLOR_ACCENT), (p_x + 458, 156))

        pygame.draw.rect(self.screen, (20, 26, 36), self.rect_lista_obj_cat, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.rect_lista_obj_cat, width=1, border_radius=4)
        self.screen.blit(self.font_small.render(f"OBJETOS CRIADOS ({len(self.objetos_catalogo)}) - Clique para selecionar:", True, COLOR_TEXT_MUTED), (self.rect_lista_obj_cat.x + 8, self.rect_lista_obj_cat.y + 4))

        item_h = 22
        max_vis_cat = (self.rect_lista_obj_cat.height - 24) // item_h
        for i in range(max_vis_cat):
            idx = self.scroll_obj_cat + i
            if idx >= len(self.objetos_catalogo):
                break
            item = self.objetos_catalogo[idx]
            r = pygame.Rect(self.rect_lista_obj_cat.x + 6, self.rect_lista_obj_cat.y + 22 + i * item_h, self.rect_lista_obj_cat.width - 12, item_h - 2)
            is_sel = (idx == self.obj_cat_sel_idx)
            pygame.draw.rect(self.screen, (45, 65, 95) if is_sel else (30, 38, 52), r, border_radius=3)
            if is_sel:
                pygame.draw.rect(self.screen, COLOR_SELECTED, r, width=1, border_radius=3)

            o_ini = float(item.get("offset", 1.3))
            o_fim = float(item.get("offset_fim", o_ini))
            off_txt = f"{o_ini:.2f}->{o_fim:.2f}" if abs(o_fim - o_ini) > 0.001 else f"{o_ini:.2f}"
            linha = f"{item['nome']:<18} | {os.path.basename(item['png']):<16} | Esc:{item.get('escala', 1.0):.1f}x | Off:{off_txt}"
            txt_it = self.font_mono.render(linha, True, COLOR_SELECTED if is_sel else COLOR_TEXT_PRIMARY)
            self.screen.blit(txt_it, (r.x + 6, r.y + 2))

        # ---------------------------------------------------------------------
        # SEÇÃO 2: REPLICAR OBJETO NOS TRECHOS DA PISTA
        # ---------------------------------------------------------------------
        card2 = pygame.Rect(p_x, 332, WIDTH - p_x - 20, 344)
        pygame.draw.rect(self.screen, COLOR_PANEL, card2, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, card2, width=1, border_radius=6)

        seg_atual = self.segmentos[self.seg_idx] if self.segmentos else {"length": 0, "curve": 0}
        tipo_seg = "Curva Dir" if seg_atual["curve"] > 0.001 else ("Curva Esq" if seg_atual["curve"] < -0.001 else "Reta")
        titulo_s2 = f"2. TRECHO #{self.seg_idx + 1}/{len(self.segmentos)} ({seg_atual['length']}m - {tipo_seg})"
        self.screen.blit(self.font_sub.render(titulo_s2, True, COLOR_SELECTED), (p_x + 10, 345))

        self.screen.blit(self.font_sub.render("LADO PISTA:", True, COLOR_TEXT_MUTED), (p_x + 10, 379))
        lado_rects = {
            "esq": pygame.Rect(p_x + 115, 376, 105, 26),
            "dir": pygame.Rect(p_x + 228, 376, 105, 26),
            "ambos": pygame.Rect(p_x + 341, 376, 105, 26)
        }
        r_ativo = lado_rects.get(self.apl_lado)
        if r_ativo:
            pygame.draw.rect(self.screen, COLOR_ACCENT, r_ativo.inflate(4, 4), width=2, border_radius=6)

        self.screen.blit(self.font_sub.render("REPLICAR:", True, COLOR_TEXT_MUTED), (p_x + 10, 413))
        self.screen.blit(self.font_mono.render(f"{self.apl_quantidade:3d}x", True, COLOR_SELECTED), (p_x + 244, 415))

        self.screen.blit(self.font_sub.render("INÍCIO:", True, COLOR_TEXT_MUTED), (p_x + 422, 413))
        self.screen.blit(self.font_mono.render(f"{self.apl_inicio_pct:2d}%", True, COLOR_ACCENT), (p_x + 528, 415))

        self.screen.blit(self.font_sub.render("DISTÂNCIA:", True, COLOR_TEXT_MUTED), (p_x + 10, 444))
        esp_txt = "AUTO" if self.apl_espacamento == 0 else f"{self.apl_espacamento}m"
        self.screen.blit(self.font_mono.render(f"{esp_txt:^6}", True, COLOR_SUCCESS), (p_x + 205, 446))

        self.screen.blit(self.font_sub.render(f"OBJETOS APLICADOS NA PISTA ({len(self.objetos_pista)} grupos):", True, COLOR_TEXT_MUTED), (p_x + 10, 502))
        pygame.draw.rect(self.screen, (20, 26, 36), self.rect_lista_obj_apl, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.rect_lista_obj_apl, width=1, border_radius=4)

        max_vis_apl = (self.rect_lista_obj_apl.height - 12) // item_h
        for i in range(max_vis_apl):
            idx = self.scroll_obj_apl + i
            if idx >= len(self.objetos_pista):
                break
            ap = self.objetos_pista[idx]
            r = pygame.Rect(self.rect_lista_obj_apl.x + 6, self.rect_lista_obj_apl.y + 6 + i * item_h, self.rect_lista_obj_apl.width - 12, item_h - 2)
            is_sel = (idx == self.obj_apl_sel_idx)
            is_trecho_atual = (ap["seg_idx"] == self.seg_idx)
            bg = (50, 70, 100) if is_sel else ((34, 48, 62) if is_trecho_atual else (28, 35, 48))
            pygame.draw.rect(self.screen, bg, r, border_radius=3)
            if is_sel:
                pygame.draw.rect(self.screen, COLOR_SELECTED, r, width=1, border_radius=3)

            lado_lbl = {"esq": "ESQ", "dir": "DIR", "ambos": "AMBOS"}.get(ap["lado"], "ESQ")
            linha_ap = f"Trecho #{ap['seg_idx'] + 1:02d} | {ap['objeto']:<18} | Lado: {lado_lbl:<5} | {ap['quantidade']:3d}x | Início: {ap.get('inicio_pct', 0):2d}%"
            txt_ap = self.font_mono.render(linha_ap, True, COLOR_SELECTED if is_sel else COLOR_TEXT_PRIMARY)
            self.screen.blit(txt_ap, (r.x + 6, r.y + 2))

    # =========================================================================
    # MODAIS E TEMPORADAS
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

        input_rect = pygame.Rect(m_rect.x + 40, m_rect.y + 90, m_rect.width - 80, 36)
        pygame.draw.rect(self.screen, (20, 25, 35), input_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_ACCENT, input_rect, width=2, border_radius=4)
        txt_val = self.font_title.render(self.nome_input_salvar + "_", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_val, (input_rect.x + 12, input_rect.centery - txt_val.get_height() // 2))

        btn_salvar = pygame.Rect(m_rect.x + 60, m_rect.bottom - 50, 160, 32)
        is_hov_s = btn_salvar.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, (25, 140, 60) if is_hov_s else (20, 100, 50), btn_salvar, border_radius=4)
        txt_s = self.font_sub.render("CONFIRMAR", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_s, (btn_salvar.centerx - txt_s.get_width() // 2, btn_salvar.centery - txt_s.get_height() // 2))

        btn_close = pygame.Rect(m_rect.right - 220, m_rect.bottom - 50, 160, 32)
        is_hov_c = btn_close.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, (80, 35, 35) if is_hov_c else (60, 30, 30), btn_close, border_radius=4)
        txt_c = self.font_sub.render("CANCELAR", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_c, (btn_close.centerx - txt_c.get_width() // 2, btn_close.centery - txt_c.get_height() // 2))

    def desenhar_modal_carregar_temporada(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        m_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 180, 500, 360)
        pygame.draw.rect(self.screen, COLOR_PANEL, m_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_ACCENT, m_rect, width=2, border_radius=8)

        titulo = self.font_title.render("CARREGAR TEMPORADA (temporadas/*.json)", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(titulo, (m_rect.x + 25, m_rect.y + 20))

        arquivos = []
        if os.path.exists("temporadas"):
            arquivos = [f for f in sorted(os.listdir("temporadas")) if f.lower().endswith(".json")]

        if not arquivos:
            aviso = self.font_ui.render("Nenhuma temporada salva na pasta 'temporadas/'.", True, COLOR_WARNING)
            self.screen.blit(aviso, (m_rect.x + 30, m_rect.y + 80))
        else:
            for i, arq in enumerate(arquivos[:7]):
                btn_r = pygame.Rect(m_rect.x + 30, m_rect.y + 60 + (i * 35), m_rect.width - 60, 30)
                pygame.draw.rect(self.screen, (40, 52, 72), btn_r, border_radius=4)
                txt = self.font_mono.render(arq, True, COLOR_TEXT_PRIMARY)
                self.screen.blit(txt, (btn_r.x + 12, btn_r.y + 6))

        btn_close = pygame.Rect(m_rect.centerx - 60, m_rect.bottom - 45, 120, 30)
        pygame.draw.rect(self.screen, (130, 40, 40), btn_close, border_radius=4)
        txt_c = self.font_ui.render("FECHAR", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(txt_c, (btn_close.centerx - txt_c.get_width() // 2, btn_close.centery - txt_c.get_height() // 2))

    def desenhar_modal_salvar_como_temporada(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        m_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 120, 500, 240)
        pygame.draw.rect(self.screen, COLOR_PANEL, m_rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_ACCENT, m_rect, width=2, border_radius=8)

        titulo = self.font_title.render("SALVAR TEMPORADA COMO:", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(titulo, (m_rect.x + 25, m_rect.y + 25))

        box = pygame.Rect(m_rect.x + 30, m_rect.y + 75, m_rect.width - 60, 38)
        pygame.draw.rect(self.screen, (20, 25, 35), box, border_radius=4)
        pygame.draw.rect(self.screen, COLOR_SELECTED, box, width=1, border_radius=4)
        txt_in = self.font_mono.render(f"temporadas/{self.nome_input_salvar}.json", True, COLOR_SELECTED)
        self.screen.blit(txt_in, (box.x + 12, box.y + 9))

        btn_salvar = pygame.Rect(m_rect.x + 60, m_rect.bottom - 50, 160, 32)
        btn_close = pygame.Rect(m_rect.right - 220, m_rect.bottom - 50, 160, 32)
        pygame.draw.rect(self.screen, (25, 120, 60), btn_salvar, border_radius=4)
        pygame.draw.rect(self.screen, (130, 40, 40), btn_close, border_radius=4)

        t_s = self.font_ui.render("SALVAR (ENTER)", True, COLOR_TEXT_PRIMARY)
        t_c = self.font_ui.render("CANCELAR (ESC)", True, COLOR_TEXT_PRIMARY)
        self.screen.blit(t_s, (btn_salvar.centerx - t_s.get_width() // 2, btn_salvar.centery - t_s.get_height() // 2))
        self.screen.blit(t_c, (btn_close.centerx - t_c.get_width() // 2, btn_close.centery - t_c.get_height() // 2))

    def alternar_modo(self, novo_modo):
        self.modo_editor = novo_modo
        self.editando_nome_obj = False
        if novo_modo == "TEMPORADA":
            self.lista_pistas_disponiveis = self.detectar_pistas_disponiveis()
            self.set_status("Modo Temporadas ativado: monte a ordem das corridas!")
        elif novo_modo == "OBJETOS":
            self.lista_pngs_objetos = self.detectar_pngs_objetos()
            self.set_status("Modo Objetos/Muretas: crie objetos PNG e replique nos trechos!")
        else:
            self.set_status("Modo Editor de Pistas ativado!")

    def action_abrir_salvar_como_temp(self):
        self.nome_input_salvar = os.path.splitext(os.path.basename(self.arquivo_temporada))[0]
        self.modal_aberto = "SALVAR_COMO_TEMP"

    def action_atualizar_pistas_temp(self):
        self.lista_pistas_disponiveis = self.detectar_pistas_disponiveis()
        self.pista_disp_idx = 0
        self.set_status(f"{len(self.lista_pistas_disponiveis)} pistas encontradas em 'pistas/'.")

    def action_add_pista_temporada(self):
        if not self.lista_pistas_disponiveis:
            self.set_status("Nenhuma pista disponível na pasta 'pistas/'!", COLOR_WARNING)
            return
        pista = self.lista_pistas_disponiveis[self.pista_disp_idx]
        self.etapas_temporada.append({
            "arquivo": pista["arquivo"],
            "nome": pista["nome"],
            "voltas": 3
        })
        self.etapa_sel_idx = len(self.etapas_temporada) - 1
        self.set_status(f"Etapa #{len(self.etapas_temporada)} adicionada: {pista['nome']}")

    def action_editar_pista_selecionada(self):
        if not self.lista_pistas_disponiveis:
            return
        pista = self.lista_pistas_disponiveis[self.pista_disp_idx]
        self.carregar_pista(pista["arquivo"])
        self.modo_editor = "PISTA"

    def action_mover_etapa(self, direcao):
        novo_idx = self.etapa_sel_idx + direcao
        if 0 <= novo_idx < len(self.etapas_temporada):
            self.etapas_temporada[self.etapa_sel_idx], self.etapas_temporada[novo_idx] = (
                self.etapas_temporada[novo_idx],
                self.etapas_temporada[self.etapa_sel_idx]
            )
            self.etapa_sel_idx = novo_idx

    def action_alterar_voltas_etapa(self, delta):
        if 0 <= self.etapa_sel_idx < len(self.etapas_temporada):
            v = self.etapas_temporada[self.etapa_sel_idx]["voltas"]
            self.etapas_temporada[self.etapa_sel_idx]["voltas"] = max(1, min(99, v + delta))

    def action_remover_etapa(self):
        if 0 <= self.etapa_sel_idx < len(self.etapas_temporada):
            removida = self.etapas_temporada.pop(self.etapa_sel_idx)
            self.etapa_sel_idx = max(0, min(self.etapa_sel_idx, len(self.etapas_temporada) - 1))
            self.set_status(f"Etapa '{removida['nome']}' removida da temporada.")

    def desenhar_tela_temporadas(self):
        txt_titulo = self.font_title.render(f"TEMPORADA: {self.nome_temporada} ({self.arquivo_temporada})", True, COLOR_SELECTED)
        self.screen.blit(txt_titulo, (40, 62))

        txt_dica = self.font_ui.render("Selecione pistas à esquerda para montar o calendário oficial da temporada à direita (digite para renomear a temporada):", True, COLOR_TEXT_MUTED)
        self.screen.blit(txt_dica, (40, 95))

        pygame.draw.rect(self.screen, COLOR_PANEL, self.rect_lista_pistas_disp, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.rect_lista_pistas_disp, width=1, border_radius=6)
        self.screen.blit(self.font_sub.render("1. PISTAS DISPONÍVEIS (pistas/*.json)", True, COLOR_ACCENT), (self.rect_lista_pistas_disp.x + 15, self.rect_lista_pistas_disp.y + 12))

        item_h = 34
        max_vis = (self.rect_lista_pistas_disp.height - 50) // item_h
        for i in range(max_vis):
            idx = self.scroll_pistas_disp + i
            if idx >= len(self.lista_pistas_disponiveis):
                break
            p = self.lista_pistas_disponiveis[idx]
            r = pygame.Rect(self.rect_lista_pistas_disp.x + 12, self.rect_lista_pistas_disp.y + 45 + i * item_h, self.rect_lista_pistas_disp.width - 24, item_h - 4)
            is_sel = (idx == self.pista_disp_idx)
            pygame.draw.rect(self.screen, (45, 65, 95) if is_sel else (32, 40, 55), r, border_radius=4)
            if is_sel:
                pygame.draw.rect(self.screen, COLOR_ACCENT, r, width=1, border_radius=4)
            txt = self.font_mono.render(f"{p['nome']:<28} | {p['arquivo']}", True, COLOR_TEXT_PRIMARY)
            self.screen.blit(txt, (r.x + 10, r.y + 7))

        pygame.draw.rect(self.screen, COLOR_PANEL, self.rect_lista_etapas, border_radius=6)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.rect_lista_etapas, width=1, border_radius=6)
        self.screen.blit(self.font_sub.render(f"2. CALENDÁRIO DO CAMPEONATO ({len(self.etapas_temporada)} Etapas)", True, COLOR_SUCCESS), (self.rect_lista_etapas.x + 15, self.rect_lista_etapas.y + 12))

        if not self.etapas_temporada:
            txt_vazio = self.font_ui.render("Nenhuma etapa adicionada. Clique em '+ ADICIONAR À TEMPORADA'.", True, COLOR_TEXT_MUTED)
            self.screen.blit(txt_vazio, (self.rect_lista_etapas.x + 20, self.rect_lista_etapas.y + 60))
        else:
            for i in range(max_vis):
                idx = self.scroll_etapas + i
                if idx >= len(self.etapas_temporada):
                    break
                et = self.etapas_temporada[idx]
                r = pygame.Rect(self.rect_lista_etapas.x + 12, self.rect_lista_etapas.y + 45 + i * item_h, self.rect_lista_etapas.width - 24, item_h - 4)
                is_sel = (idx == self.etapa_sel_idx)
                pygame.draw.rect(self.screen, (50, 65, 90) if is_sel else (32, 40, 55), r, border_radius=4)
                if is_sel:
                    pygame.draw.rect(self.screen, COLOR_SELECTED, r, width=1, border_radius=4)
                txt = self.font_mono.render(f"Etapa {idx + 1:02d} | {et['nome']:<25} | {et['voltas']:02d} Voltas | {os.path.basename(et['arquivo'])}", True, COLOR_SELECTED if is_sel else COLOR_TEXT_PRIMARY)
                self.screen.blit(txt, (r.x + 10, r.y + 7))

    # =========================================================================
    # LOOP PRINCIPAL E TRATAMENTO DE EVENTOS
    # =========================================================================
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            tempo_atual = pygame.time.get_ticks()

            if self.modo_editor in ("PISTA", "OBJETOS") and self.is_playing and self.segmentos:
                total_len = sum(s["length"] for s in self.segmentos)
                if total_len > 0:
                    ds = 66.0 * (dt / 1000.0)
                    pos_idx = int(self.cam_pos) % total_len
                    curva_atual = self.obter_curva_na_posicao(pos_idx)
                    self.bg_offset_x -= curva_atual * ds * 120.0
                    self.cam_pos = (self.cam_pos + ds) % total_len

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # 1. MODAIS DO MODO PISTA
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

                # 2. MODAIS DO MODO TEMPORADA
                elif self.modal_aberto == "CARREGAR_TEMP":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.modal_aberto = None
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        m_rect = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 180, 500, 360)
                        btn_close = pygame.Rect(m_rect.centerx - 60, m_rect.bottom - 45, 120, 30)
                        if btn_close.collidepoint(event.pos):
                            self.modal_aberto = None
                        else:
                            arquivos = []
                            if os.path.exists("temporadas"):
                                arquivos = [f for f in sorted(os.listdir("temporadas")) if f.lower().endswith(".json")]
                            for i, arq in enumerate(arquivos[:7]):
                                btn_r = pygame.Rect(m_rect.x + 30, m_rect.y + 60 + (i * 35), m_rect.width - 60, 30)
                                if btn_r.collidepoint(event.pos):
                                    self.carregar_temporada(f"temporadas/{arq}")
                                    self.modal_aberto = None
                                    break
                    continue

                elif self.modal_aberto == "SALVAR_COMO_TEMP":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            nome_limpo = self.nome_input_salvar.strip()
                            if nome_limpo:
                                self.salvar_temporada(f"temporadas/{nome_limpo}.json")
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
                                self.salvar_temporada(f"temporadas/{nome_limpo}.json")
                            self.modal_aberto = None
                        elif btn_close.collidepoint(event.pos):
                            self.modal_aberto = None
                    continue

                # 3. BOTÕES DE TROCA DE ABA NO TOPO
                clicou_aba = False
                for b in self.buttons_globais:
                    if b.handle_event(event):
                        clicou_aba = True
                        break
                if clicou_aba:
                    continue

                # 4. EVENTOS ESPECÍFICOS DO MODO ATIVO
                if self.modo_editor == "TEMPORADA":
                    for b in self.buttons_temporada:
                        b.handle_event(event)

                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.rect_lista_pistas_disp.collidepoint(event.pos):
                            rel_y = event.pos[1] - (self.rect_lista_pistas_disp.y + 45)
                            if rel_y >= 0:
                                idx_clicado = self.scroll_pistas_disp + (rel_y // 34)
                                if 0 <= idx_clicado < len(self.lista_pistas_disponiveis):
                                    self.pista_disp_idx = idx_clicado

                        elif self.rect_lista_etapas.collidepoint(event.pos):
                            rel_y = event.pos[1] - (self.rect_lista_etapas.y + 45)
                            if rel_y >= 0:
                                idx_clicado = self.scroll_etapas + (rel_y // 34)
                                if 0 <= idx_clicado < len(self.etapas_temporada):
                                    self.etapa_sel_idx = idx_clicado

                    elif event.type == pygame.MOUSEWHEEL:
                        pos_m = pygame.mouse.get_pos()
                        if self.rect_lista_pistas_disp.collidepoint(pos_m):
                            max_s = max(0, len(self.lista_pistas_disponiveis) - 12)
                            self.scroll_pistas_disp = max(0, min(max_s, self.scroll_pistas_disp - event.y))
                        elif self.rect_lista_etapas.collidepoint(pos_m):
                            max_s = max(0, len(self.etapas_temporada) - 12)
                            self.scroll_etapas = max(0, min(max_s, self.scroll_etapas - event.y))

                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                            self.salvar_temporada(self.arquivo_temporada)
                        elif event.key == pygame.K_BACKSPACE:
                            self.nome_temporada = self.nome_temporada[:-1]
                        elif event.unicode.isprintable() and len(self.nome_temporada) < 35:
                            self.nome_temporada += event.unicode

                elif self.modo_editor == "OBJETOS":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        # Foco no campo de texto "Nome do Objeto"
                        self.editando_nome_obj = self.rect_input_nome_obj.collidepoint(event.pos)

                        # Clique na lista de objetos criados
                        if self.rect_lista_obj_cat.collidepoint(event.pos):
                            rel_y = event.pos[1] - (self.rect_lista_obj_cat.y + 22)
                            if rel_y >= 0:
                                idx_c = self.scroll_obj_cat + (rel_y // 22)
                                if 0 <= idx_c < len(self.objetos_catalogo):
                                    self.obj_cat_sel_idx = idx_c
                                    self.sincronizar_form_com_objeto_selecionado()

                        # Clique na lista de objetos aplicados na pista
                        elif self.rect_lista_obj_apl.collidepoint(event.pos):
                            rel_y = event.pos[1] - (self.rect_lista_obj_apl.y + 6)
                            if rel_y >= 0:
                                idx_a = self.scroll_obj_apl + (rel_y // 22)
                                if 0 <= idx_a < len(self.objetos_pista):
                                    self.obj_apl_sel_idx = idx_a
                                    self.seg_idx = self.objetos_pista[idx_a]["seg_idx"]
                                    self.action_focar_camera_trecho()

                    elif event.type == pygame.MOUSEWHEEL:
                        pos_m = pygame.mouse.get_pos()
                        if self.rect_lista_obj_cat.collidepoint(pos_m):
                            max_s = max(0, len(self.objetos_catalogo) - 3)
                            self.scroll_obj_cat = max(0, min(max_s, self.scroll_obj_cat - event.y))
                        elif self.rect_lista_obj_apl.collidepoint(pos_m):
                            max_s = max(0, len(self.objetos_pista) - 5)
                            self.scroll_obj_apl = max(0, min(max_s, self.scroll_obj_apl - event.y))

                    for b in self.buttons_objetos:
                        b.handle_event(event)

                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                            self.action_salvar_atual()
                        elif self.editando_nome_obj:
                            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                                self.editando_nome_obj = False
                            elif event.key == pygame.K_BACKSPACE:
                                self.obj_nome_input = self.obj_nome_input[:-1]
                            elif event.unicode.isprintable() and len(self.obj_nome_input) < 24:
                                self.obj_nome_input += event.unicode
                        else:
                            if event.key == pygame.K_LEFT:
                                self.action_prev_seg()
                            elif event.key == pygame.K_RIGHT:
                                self.action_next_seg()
                            elif event.key == pygame.K_SPACE:
                                self.action_toggle_play()

                else:
                    # --- MODO PISTA ---
                    rect_preview_aereo = pygame.Rect(20, 45, 600, 355)
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.ref_idx > 0 and rect_preview_aereo.collidepoint(event.pos):
                            self.arrastando_ref = True
                            self.drag_inicio_mouse = event.pos
                            self.drag_inicio_offset = (self.ref_offset_x, self.ref_offset_y)
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        self.arrastando_ref = False
                    elif event.type == pygame.MOUSEMOTION and self.arrastando_ref:
                        dx = event.pos[0] - self.drag_inicio_mouse[0]
                        dy = event.pos[1] - self.drag_inicio_mouse[1]
                        self.ref_offset_x = self.drag_inicio_offset[0] + dx
                        self.ref_offset_y = self.drag_inicio_offset[1] + dy

                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.rect_lista.collidepoint(event.pos):
                            rel_y = event.pos[1] - (self.rect_lista.y + 30)
                            if rel_y >= 0:
                                idx_clicado = self.scroll_offset + (rel_y // 24)
                                if 0 <= idx_clicado < len(self.segmentos):
                                    self.seg_idx = idx_clicado
                                    self.action_focar_camera_trecho()

                    if event.type == pygame.MOUSEWHEEL:
                        if self.rect_lista.collidepoint(pygame.mouse.get_pos()):
                            self.scroll_offset = max(0, min(max(0, len(self.segmentos) - 1), self.scroll_offset - event.y))

                    for b in self.buttons:
                        b.handle_event(event)

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

            for b in self.buttons_globais:
                b.draw(self.screen, self.font_ui)

            if self.modo_editor == "PISTA":
                self.desenhar_preview_aereo(pygame.Rect(20, 45, 600, 355))
                self.desenhar_preview_3d(pygame.Rect(20, 415, 600, 295))
                self.desenhar_painel_edicao()
                for b in self.buttons:
                    b.draw(self.screen, self.font_ui)

            elif self.modo_editor == "OBJETOS":
                self.desenhar_preview_aereo(pygame.Rect(20, 45, 600, 355))
                self.desenhar_preview_3d(pygame.Rect(20, 415, 600, 295))
                self.desenhar_painel_objetos()
                for b in self.buttons_objetos:
                    b.draw(self.screen, self.font_ui)

            else:
                self.desenhar_tela_temporadas()
                for b in self.buttons_temporada:
                    b.draw(self.screen, self.font_ui)

            if tempo_atual < self.status_timer:
                status_surf = self.font_ui.render(self.status_msg, True, self.status_color)
                self.screen.blit(status_surf, (25, HEIGHT - 22))

            if self.modal_aberto == "CARREGAR":
                self.desenhar_modal_carregar()
            elif self.modal_aberto == "SALVAR_COMO":
                self.desenhar_modal_salvar_como()
            elif self.modal_aberto == "CARREGAR_TEMP":
                self.desenhar_modal_carregar_temporada()
            elif self.modal_aberto == "SALVAR_COMO_TEMP":
                self.desenhar_modal_salvar_como_temporada()

            pygame.display.flip()


if __name__ == "__main__":
    app = TrackEditor()
    app.run()