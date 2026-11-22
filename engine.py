import pygame
import sys
import math
import json
import random
import os
from settings import *
from openal import oalOpen, oalQuit
from track import Track
from car import Car
from utils import carregar_img
from ui import MenuUI
from bot_ai import BotAI

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        pygame.mixer.init()
        flags = pygame.SCALED | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, pygame.KEYUP])
        pygame.display.set_caption("Super Monaco GP - Fan Remake")
        self.clock = pygame.time.Clock()
        self.imagem_cache = {}

        #dinamica relogio preliminary race
        self.grid_hud_visivel = False
        self.grid_pos_hud_atual = 16
        self.grid_pos_relogio_atual = 16

        # Interface de Menus e bots
        self.ui = MenuUI(self)
        self.ai = BotAI(self)

        self.fonte_grande = pygame.font.SysFont('Arial', 75, bold=True)
        self.fonte_normal = pygame.font.SysFont('Arial', 30)
        self.fonte_pequena = pygame.font.SysFont('Arial', 17)
        self.fonte_sub = pygame.font.SysFont('Arial', 20, bold=True)
        self.fonte_banner = pygame.font.SysFont('Arial', 54, bold=True)

        # Fontes reutilizáveis (criadas apenas uma vez ao iniciar o jogo)
        self.fonte_menu = pygame.font.SysFont('Arial', 50, bold=True)
        self.fonte_lista = pygame.font.SysFont('Arial', 24, bold=True)
        # Configuração do Semáforo de Largada (tamanho e posição ajustáveis)
        self.sinal_tamanho = (450, 195)   # (largura, altura) em pixels — altere aqui para redimensionar
        self.sinal_pos = (45, 175)         # (x, y) canto superior esquerdo — altere aqui para reposicionar

        # Tenta carregar de 'images/sinal.png' (ou da raiz 'sinal.png' como alternativa)
        self.img_sinal = carregar_img("images/sinal.png", self.sinal_tamanho)
        if not self.img_sinal:
            self.img_sinal = carregar_img("sinal.png", self.sinal_tamanho)
            self.img_sinal.fill((40, 40, 40, 220))

        mascara_base = carregar_img("images/mascara.png", self.sinal_tamanho)
        if not mascara_base:
            # Fallback caso mascara.png ainda não tenha sido criada
            mascara_base = pygame.Surface(self.sinal_tamanho, pygame.SRCALPHA)
            pygame.draw.circle(
                mascara_base, (255, 255, 255, 255),
                (self.sinal_tamanho[0] // 2, self.sinal_tamanho[1] // 2), 26
            )

        # Pré-gera as camadas coloridas uma única vez (zero peso de CPU na corrida)
        self.mascara_vermelha = self._tingir_mascara(mascara_base, (255, 0, 0))
        self.mascara_verde = self._tingir_mascara(mascara_base, (0, 255, 0))

        # Áudios do semáforo
        try:
            self.som_sinal_vermelho = pygame.mixer.Sound("sounds/vermelho.wav")
            self.som_sinal_vermelho.set_volume(0.9)
        except Exception as e:
            print(f"Aviso Mixer: Erro ao carregar vermelho.wav -> {e}")
            self.som_sinal_vermelho = None

        try:
            self.som_sinal_verde = pygame.mixer.Sound("sounds/verde.wav")
            self.som_sinal_verde.set_volume(0.9)
        except Exception as e:
            print(f"Aviso Mixer: Erro ao carregar verde.wav -> {e}")
            self.som_sinal_verde = None

        self.sinal_ativo = False
        self.sinal_vermelho_tocou = False
        self.sinal_verde_tocou = False
        self.pos_inicial_largada = 0

        # Superfícies de overlay reutilizáveis (evita recriar Surface a cada frame)
        self.overlay_finish = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.overlay_finish.fill((0, 0, 0, 180))

        self.banner_final_lap = pygame.Surface((WIDTH, 96), pygame.SRCALPHA)
        self.banner_final_lap.fill((0, 0, 0, 195))

        self.estado_jogo = "INPUT_NAME"

        # Controle de Pause
        self.estado_antes_pause = None
        self.inicio_pause_tick = 0
        self.tela_pausada = None
        self.pause_sel_idx = 0  # 0 = CONTINUAR | 1 = SAIR

        # --- CONTROLE DE MODO DE JOGO E TEMPORADA ---
        self.modo_jogo = "RAPIDA"          # "RAPIDA" ou "TEMPORADA"
        self.modo_jogo_sel_idx = 0         # 0 = Corrida Rápida | 1 = Temporada
        self.etapas_temporada = []         # Lista de etapas lidas do JSON da temporada
        self.etapa_atual_idx = 0           # Índice da corrida atual na temporada
        self.nome_temporada_atual = ""

        # --- CONTROLE DE PRELIMINARY RACE ---
        self.melhor_volta_preliminary = None
        self.posicao_qualificada = 16
        self.prox_spawn_preliminary = 0
        self.asd_hold_start = None
        self.prelim_last_lap_count = 0
        self.prelim_lap_start_time = 0
        self.tempos_qualificacao = self.carregar_tempos_qualificacao()

        self.grid_hud_visivel = False
        self.grid_pos_hud_atual = 16

        self.nome_digitado = ""

        # Catálogo de pistas disponíveis (Corrida Rápida)
        self.lista_pistas = [
            {"nome": "BRAZIL", "arquivo": "rio"},
            {"nome": "SAN MARINO", "arquivo": "san_marino"},
            {"nome": "BELGIUM", "arquivo": "belgium"}
        ]
        self.pista_sel_idx = 0
        self.track = None
        self.car = None

        self.ultrapassagens_combo = 0
        self.timer_combo = 0

        self.race_finished = False
        self.final_position = 0
        self.lap_limit = 1

        # ==========================================
        # CARREGAR BANCO DE DADOS VIA JSON E MESCLAR
        # ==========================================
        try:
            with open('equipes.json', 'r', encoding='utf-8') as f:
                self.equipes = json.load(f)

            with open('pilotos.json', 'r', encoding='utf-8') as f:
                pilotos_externos = json.load(f)

            pilotos_por_equipe = {}
            for p in pilotos_externos:
                eq = p["equipe"]
                if eq not in pilotos_por_equipe:
                    pilotos_por_equipe[eq] = []
                pilotos_por_equipe[eq].append(p)

            for eq_nome, pilotos_lista in pilotos_por_equipe.items():
                if eq_nome in self.equipes:
                    self.equipes[eq_nome]["pilotos"] = pilotos_lista

        except FileNotFoundError as e:
            print(f"ERRO: Ficheiro JSON não encontrado! Detalhes: {e}")
            if not hasattr(self, 'equipes'):
                self.equipes = {}

        # Placares acumulados do campeonato
        self.pontos_campeonato_construtores = {nome: 0 for nome in self.equipes.keys()}
        self.pontos_campeonato_pilotos = {}
        self.classificacao_pilotos = []
        self.classificacao_construtoras = []

        # Variáveis de Carreira
        self.equipe_atual_jogador = "Blanche"
        self.rival_atual = None
        self.vitorias_contra_rival = 0

        # ==========================================
        # ÁUDIO 3D VIA OPENAL (Batida e Motor dos Bots)
        # ==========================================
        self.timer_batida = 0

        try:
            self.som_batida = oalOpen("sounds/batida.wav")

            self.canais_motor_bot = []
            for _ in range(5):
                som = oalOpen("sounds/bot_motor.wav")
                som.set_looping(True)
                som.set_gain(0.0)
                self.canais_motor_bot.append(som)

        except Exception as e:
            print(f"Aviso OpenAL: Erro ao carregar audios! Detalhes: {e}")
            self.som_batida = None
            self.canais_motor_bot = []

        try:
            self.som_final_lap = pygame.mixer.Sound("sounds/final_lap.wav")
            self.som_final_lap.set_volume(0.9)
        except Exception as e:
            print(f"Aviso Mixer: Erro ao carregar final_lap.wav -> {e}")
            self.som_final_lap = None

        self.final_lap_triggered = False
        self.timer_final_lap = 0
        self.steering_locked = False

        self.bot_base_w = 140
        self.bot_base_h = 54
        self.bot_anim_timer = 0
        self.bot_frame_idx = 0
        self.cache_sprites = {}

    def _tingir_mascara(self, mascara_base, cor_rgb):
        surf = mascara_base.copy()
        tinta = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        tinta.fill((*cor_rgb, 255))
        surf.blit(tinta, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return surf

    def carregar_tempos_qualificacao(self, caminho="qualifying_times.json"):
        """ Carrega os 16 tempos alvo da Preliminary Race do JSON """
        padrao = {
            "default": [
                42.0, 43.0, 44.0, 45.0,
                46.0, 47.0, 48.0, 49.0,
                50.5, 52.0, 53.5, 55.0,
                57.0, 59.0, 61.0, 65.0
            ]
        }
        if not os.path.exists(caminho):
            try:
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(padrao, f, indent=2)
            except Exception:
                pass
            return padrao
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler {caminho}: {e}")
            return padrao

    def obter_lista_tempos_pista(self, track_name):
        chave = track_name.lower()
        lista = self.tempos_qualificacao.get(chave, self.tempos_qualificacao.get("default", []))
        if len(lista) < 16:
            ultimo = lista[-1] if lista else 60.0
            lista = lista + [ultimo + (i + 1) * 1.5 for i in range(16 - len(lista))]
        return lista[:16]

    def calcular_posicao_preliminary(self, track_name, melhor_tempo):
        if melhor_tempo is None:
            return 16
        tempos_alvo = self.obter_lista_tempos_pista(track_name)
        for idx, tempo_meta in enumerate(tempos_alvo):
            if melhor_tempo <= tempo_meta:
                return idx + 1
        return 16

    def inicializar_placares_campeonato(self):
        """ Zera os pontos de construtores e pilotos no início da temporada/corrida """
        self.pontos_campeonato_construtores = {nome: 0 for nome in self.equipes.keys()}
        self.pontos_campeonato_pilotos = {}

        nome_eq_jogador = self.lista_equipes_nomes[self.equipe_sel_idx]
        nome_jogador = self.nome_digitado.strip().upper() or "PILOTO"

        for eq_nome, dados_eq in self.equipes.items():
            for idx_p, piloto in enumerate(dados_eq.get("pilotos", [])):
                if eq_nome == nome_eq_jogador and idx_p == 0:
                    nome_p = nome_jogador
                    eh_player = True
                else:
                    nome_p = piloto["nome"].upper()
                    eh_player = False

                self.pontos_campeonato_pilotos[nome_p] = {
                    "nome": nome_p,
                    "equipe": eq_nome,
                    "pontos": 0,
                    "is_player": eh_player
                }

    def carregar_dados_temporada(self, caminho="temporadas/temporada_1.json"):
        """ Lê o arquivo JSON da primeira temporada e prepara a fila de etapas """
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            self.nome_temporada_atual = dados.get("nome_temporada", "Temporada Oficial")
            self.etapas_temporada = dados.get("etapas", [])
            self.etapa_atual_idx = 0
        except Exception as e:
            print(f"Erro ao carregar temporada ({caminho}): {e}")
            self.nome_temporada_atual = "Temporada Padrão"
            self.etapas_temporada = [
                {"etapa": 1, "arquivo": "pistas/rio.json", "nome": "Rio", "voltas": 3}
            ]
            self.etapa_atual_idx = 0

    def silenciar_audios_corrida(self):
        """ Garante que todos os sons de motor (player e bots) parem fora da pista """
        if hasattr(self, 'car') and self.car:
            try:
                self.car.parar_audios()
            except Exception:
                pass
        if hasattr(self, 'canais_motor_bot'):
            for canal in self.canais_motor_bot:
                try:
                    canal.set_gain(0.0)
                    canal.stop()
                except Exception:
                    pass

    def iniciar_preliminary_etapa_atual(self):
        """ Inicia a Preliminary Race (voltas infinitas) antes da corrida da etapa atual """
        etapa = self.etapas_temporada[self.etapa_atual_idx]
        arq_pista = os.path.splitext(os.path.basename(etapa["arquivo"]))[0]
        self.pista_preliminary_atual = arq_pista

        # Inicia a pista no modo treino/preliminary (sem grid de 16 carros inicialmente)
        self.iniciar_corrida(arq_pista, modo_preliminary=True)
        self.estado_jogo = "LOADING_PRELIMINARY"

    def spawnar_carro_aleatorio_preliminary(self, tempo_atual):
        """ Faz aparecer um carro de outra equipe na pista em intervalo mínimo de 1 minuto """
        if not self.equipes or not self.car or not self.track:
            return

        equipes_disponiveis = [eq for eq in self.equipes.keys() if eq != self.equipe_atual_jogador]
        if not equipes_disponiveis:
            equipes_disponiveis = list(self.equipes.keys())

        eq_escolhida = random.choice(equipes_disponiveis)
        dados = self.equipes[eq_escolhida]
        pilotos = dados.get("pilotos", [])
        if not pilotos:
            return
        piloto = random.choice(pilotos)

        pasta = dados["pasta"]
        mapa_cor = dados.get("mapa_cor", None)
        if pasta not in self.cache_sprites:
            self.cache_sprites[pasta] = self.carregar_sprites_equipe(pasta, mapa_cor)


        ##SOMA DA ACELERACAO E DIRECAO DO CARRO E O PILOTO
        vel_maxima_do_carro = dados["velocidade_base"] + piloto.get("speed", 0)
        aceleracao_combinada = dados.get("aceleracao", 0) + piloto.get("aceleracao", 0)
        direcao_equipe = dados.get("direcao", dados.get("freio", 3))
        direcao_combinada = direcao_equipe + piloto.get("direcao", 3)
        freio_piloto = piloto.get("freio", 3)

        # Aparece 140m à frente do jogador correndo na pista
        pos_spawn = (self.car.position + 140) % self.track.total_track_length
        faixa_x = random.choice([-0.33, 0.33])

        novo_bot = {
            "equipe": eq_escolhida,
            "nome": piloto["nome"],
            "speed": vel_maxima_do_carro * 0.80,
            "max_speed": vel_maxima_do_carro,
            "aceleracao": aceleracao_combinada,
            "freio": freio_piloto,
            "direcao": direcao_combinada,
            "cor_capacete": piloto.get("cor_capacete", [255, 255, 255]),
            "pasta": pasta,
            "frame_idx": 0,
            "anim_timer": 0,
            "defesa_timer": 0,
            "pos": pos_spawn,
            "x": faixa_x,
            "linha_padrao": faixa_x,
            "bloqueios_disponiveis": 0,
            "pode_recarregar_bloqueio": False,
            "pos_inicial_grid": 16,
            "velocidade_maxima_corrida": 0,
            "fator_sorte_qualificacao": 0
        }

        # Mantém no máximo 3 carros simultâneos na preliminary
        if len(self.bots) >= 3:
            self.bots.pop(0)
        self.bots.append(novo_bot)

        # Agenda próximo carro aleatoriamente com intervalo mínimo de 40s (40.000 ms)
        self.prox_spawn_preliminary = tempo_atual + random.randint(40000, 90000)

    def tingir_carroceria(self, superficie, mapa_cor):
        if not superficie or not mapa_cor:
            return superficie

        imagem_nova = superficie.copy()
        azul_puro     = (0, 0, 255)
        azul_escuro   = (0, 0, 148)
        azul_medio    = (106, 148, 189)
        azul_claro    = (189, 222, 255)

        nova_pura   = tuple(mapa_cor.get("puro", [0, 0, 255]))
        nova_escura = tuple(mapa_cor.get("escuro", [0, 0, 148]))
        nova_media  = tuple(mapa_cor.get("medio", [106, 148, 189]))
        nova_clara  = tuple(mapa_cor.get("claro", [189, 222, 255]))

        conversoes = {
            azul_puro: nova_pura,
            azul_escuro: nova_escura,
            azul_medio: nova_media,
            azul_claro: nova_clara
        }

        px_array = pygame.PixelArray(imagem_nova)
        for cor_antiga, cor_nova in conversoes.items():
            cor_antiga_mapeada = imagem_nova.map_rgb(cor_antiga)
            cor_nova_mapeada = imagem_nova.map_rgb(cor_nova)
            px_array.replace(cor_antiga_mapeada, cor_nova_mapeada)

        px_array.close()
        return imagem_nova

    def carregar_sprites_equipe(self, pasta_equipe, mapa_cor=None):
        tamanho_bot = (self.bot_base_w, self.bot_base_h)

        def pegar_img(direcao, tipo, frame):
            nome_arquivo = f"{direcao}_{tipo}{frame}.png"
            caminho_equipe = f"images/cars/{pasta_equipe}/{nome_arquivo}"
            caminho_bot = f"images/cars/bot/{nome_arquivo}"

            img = carregar_img(caminho_equipe, tamanho_bot)
            if not img:
                img = carregar_img(caminho_bot, tamanho_bot)
                if img and mapa_cor:
                    img = self.tingir_carroceria(img, mapa_cor)

            if not img:
                img = pygame.Surface(tamanho_bot, pygame.SRCALPHA)
            return img

        sprites = {}
        perspectivas = ["rear_reto", "front_reto", "front_esq", "front_dir", "rear_esq", "rear_dir"]
        sufixos = ["1", "1a", "1b"]

        for pers in perspectivas:
            partes = pers.split('_')
            direcao = partes[0]
            tipo = partes[1]

            sprites[pers] = []
            for suf in sufixos:
                sprites[pers].append(pegar_img(direcao, tipo, suf))

        return sprites

    def redimensionar_bot_otimizado(self, img_original, pasta, perspectiva, frame, w, h):
        passo = 5 if perspectiva == "rear_reto" else 15
        h_arredondado = max(10, min(332, round(h / passo) * passo))
        w_arredondado = int(h_arredondado * (img_original.get_width() / img_original.get_height()))
        if w_arredondado <= 0:
            w_arredondado = 1

        chave = (pasta, perspectiva, frame, w_arredondado, h_arredondado)
        img = self.imagem_cache.get(chave)
        if img is None:
            img = pygame.transform.scale(img_original, (w_arredondado, h_arredondado))
            self.imagem_cache[chave] = img

        return img

    def pre_aquecer_cache(self):
        for pasta, sprites_pasta in self.cache_sprites.items():
            perspectiva = "rear_reto"
            for frame in range(3):
                img_original = sprites_pasta[perspectiva][frame]
                ratio = img_original.get_width() / img_original.get_height()

                for h in range(10, 334, 5):
                    w = int(h * ratio)
                    if w > 0:
                        chave = f"{pasta}_{perspectiva}_{frame}_{w}x{h}"
                        if chave not in self.imagem_cache:
                            self.imagem_cache[chave] = pygame.transform.scale(img_original, (w, h))

    def iniciar_corrida(self, track_name="rio", modo_preliminary=False):
        self.silenciar_audios_corrida()
        self.track = Track(track_name)

        # Mantém o nome do jogador intacto durante todas as corridas!
        nome_limpo = getattr(self, 'nome_digitado', "").strip().upper()
        self.nome_jogador_formatado = nome_limpo if nome_limpo else "PILOTO"

        # 1. Puxa a equipa selecionada no Menu
        nome_equipe = self.lista_equipes_nomes[self.equipe_sel_idx]
        self.equipe_atual_jogador = nome_equipe

        # 2. Desmarca qualquer "is_player" antigo
        for eq_nome, dados_eq in self.equipes.items():
            for p in dados_eq.get("pilotos", []):
                p["is_player"] = False

        # 3. Injeta o jogador no piloto titular
        pilotos_da_equipe = self.equipes[nome_equipe]["pilotos"]
        self.dados_do_meu_piloto = pilotos_da_equipe[0].copy()
        pilotos_da_equipe[0]["nome"] = self.nome_jogador_formatado
        pilotos_da_equipe[0]["is_player"] = True

        # 4. Aplica limite de voltas
        if modo_preliminary:
            self.lap_limit = 999999  # Voltas infinitas
        elif self.modo_jogo == "RAPIDA":
            self.lap_limit = self.opcoes_voltas[self.volta_sel_idx]

        pasta_do_jogador = self.equipes[nome_equipe]["pasta"] if nome_equipe in self.equipes else "minarae"
        status = self.equipes[self.equipe_atual_jogador]
        velocidade_final_jogador = status["velocidade_base"] + self.dados_do_meu_piloto.get("speed", 0)

        self.car = Car(
            velocidade_maxima = velocidade_final_jogador,
            nivel_aceleracao  = status.get("aceleracao", 1),
            nivel_freio       = self.dados_do_meu_piloto.get("freio", 3),
            nivel_direcao     = status.get("direcao", 3),
            pasta_equipe      = pasta_do_jogador
        )
        self.car.ajustar_atributos_equipe(status)

        self.bots = []
        self.cache_sprites = {}

        # Pré-carrega sprites de todas as equipes (necessário também para spawns da Preliminary)
        for nome_eq, dados in self.equipes.items():
            pasta = dados["pasta"]
            mapa_cor = dados.get("mapa_cor", None)
            # Carrega e tinge os sprites das equipes APENAS UMA VEZ na sessão
            if not self.cache_sprites:
                for nome_eq, dados in self.equipes.items():
                    pasta = dados["pasta"]
                    mapa_cor = dados.get("mapa_cor", None)
                    if pasta not in self.cache_sprites:
                        self.cache_sprites[pasta] = self.carregar_sprites_equipe(pasta, mapa_cor)

        if modo_preliminary:
            # Começa exatamente no início da pista atual
            self.car.position = 100
            self.car.player_x = 0.0
            self.car.pos_inicial_grid = 16
            self.car.velocidade_maxima_corrida = 0

            now = pygame.time.get_ticks()
            self.melhor_volta_preliminary = None
            self.posicao_qualificada = 16
            self.melhor_volta_preliminary = None
            self.posicao_qualificada = 16
            self.grid_hud_visivel = False
            self.grid_pos_hud_atual = 16
            self.grid_pos_relogio_atual = 16
            self.asd_hold_start = None
            self.prelim_last_lap_count = 0
            self.prelim_lap_start_time = now
            # Primeiro carro aleatório aparece após intervalo mínimo de (40.000 ms)
            self.prox_spawn_preliminary = now + random.randint(40000, 90000)

            self.race_finished = False
            self.final_lap_triggered = False
            self.timer_final_lap = 0
            return

        # =========================================================
        # CONFIGURAÇÃO DO GRID OFICIAL (16 CARROS)
        # =========================================================
        posicao_jogador = getattr(self, 'posicao_jogador', 16)
        espaco_grid = 8

        self.car.position = 100 + ((16 - posicao_jogador) * espaco_grid)
        self.car.player_x = 0.33 if posicao_jogador % 2 == 0 else -0.33
        self.car.pos_inicial_grid = posicao_jogador
        self.car.velocidade_maxima_corrida = 0

        bots_temporarios = []
        for nome_eq, dados in self.equipes.items():
            pasta = dados["pasta"]
            for i, piloto in enumerate(dados["pilotos"]):
                if piloto.get("is_player", False):
                    continue

                vel_maxima_do_carro = dados["velocidade_base"] + piloto.get("speed", 0)
                aceleracao_combinada = dados.get("aceleracao", 0) + piloto.get("aceleracao", 0)
                direcao_equipe = dados.get("direcao", dados.get("freio", 3))
                direcao_combinada = direcao_equipe + piloto["direcao"]
                freio_piloto = piloto.get("freio", 3)

                forca_total = vel_maxima_do_carro + (aceleracao_combinada * 15) + (direcao_combinada * 15)

                bots_temporarios.append({
                    "equipe": nome_eq,
                    "classe": dados_eq.get("classe", "D"),
                    "nome": piloto["nome"],
                    "speed": 0,
                    "max_speed": vel_maxima_do_carro,
                    "aceleracao": aceleracao_combinada,
                    "freio": freio_piloto,
                    "direcao": direcao_combinada,
                    "cor_capacete": piloto["cor_capacete"],
                    "pasta": pasta,
                    "frame_idx": 0,
                    "anim_timer": 0,
                    "defesa_timer": 0,
                    "forca_total": forca_total
                })

        for bot in bots_temporarios:
            fator_sorte = random.randint(-8, 8)
            bot["forca_qualificacao"] = bot["forca_total"] + fator_sorte

        bots_temporarios.sort(key=lambda b: b["forca_qualificacao"], reverse=True)
        posicoes_disponiveis = [p for p in range(1, 17) if p != posicao_jogador]

        for i, bot in enumerate(bots_temporarios):
            if i >= len(posicoes_disponiveis):
                break

            posicao_final = posicoes_disponiveis[i]
            bot["pos"] = 100 + ((16 - posicao_final) * espaco_grid)
            bot["x"] = 0.33 if posicao_final % 2 == 0 else -0.33
            bot["linha_padrao"] = bot["x"]

            bot["bloqueios_disponiveis"] = 1 if bot.get("aceleracao", 1) > 4 else 0
            bot["pode_recarregar_bloqueio"] = False
            bot["pos_inicial_grid"] = posicao_final
            bot["velocidade_maxima_corrida"] = 0
            bot["fator_sorte_qualificacao"] = bot.get("forca_qualificacao", 0) - bot.get("forca_total", 0)

            self.bots.append(bot)

        self.timer_countdown = pygame.time.get_ticks()
        self.estado_jogo = "COUNTDOWN"
        self.race_finished = False
        self.final_lap_triggered = False
        self.timer_final_lap = 0

        self.sinal_ativo = True
        self.sinal_vermelho_tocou = False
        self.sinal_verde_tocou = False
        self.pos_inicial_largada = self.car.position

    def gerar_resultados(self):
        # 1. Junta você e todos os bots numa lista só
        meu_nome_upper = getattr(self, "nome_jogador_formatado", "PILOTO").upper()
        corredores = [{
            "nome": meu_nome_upper,
            "equipe": self.equipe_atual_jogador,
            "pos": self.car.position,
            "is_player": True
        }]
        for bot in self.bots:
            corredores.append({
                "nome": bot["nome"].upper(),
                "equipe": bot["equipe"],
                "pos": bot["pos"],
                "is_player": False
            })

        # 2. Ordena pela posição final (distância total percorrida)
        corredores.sort(key=lambda x: x["pos"], reverse=True)
        self.classificacao_final = corredores

        # 3. Tabela de pontuação oficial (1º ao 6º)
        pontuacao = [10, 6, 4, 3, 2, 1]
        self.pontos_construtoras = {nome: 0 for nome in self.equipes.keys()}

        if not self.pontos_campeonato_pilotos:
            self.inicializar_placares_campeonato()

        for i, piloto in enumerate(corredores):
            pts = pontuacao[i] if i < len(pontuacao) else 0
            p_nome = piloto["nome"]
            p_eq = piloto["equipe"]

            # Garante registro no dicionário de pilotos
            if p_nome not in self.pontos_campeonato_pilotos:
                self.pontos_campeonato_pilotos[p_nome] = {
                    "nome": p_nome,
                    "equipe": p_eq,
                    "pontos": 0,
                    "is_player": piloto.get("is_player", False)
                }

            if pts > 0:
                self.pontos_construtoras[p_eq] = self.pontos_construtoras.get(p_eq, 0) + pts
                if self.modo_jogo == "TEMPORADA":
                    self.pontos_campeonato_construtores[p_eq] = (
                        self.pontos_campeonato_construtores.get(p_eq, 0) + pts
                    )
                    self.pontos_campeonato_pilotos[p_nome]["pontos"] += pts
                else:
                    # Na corrida rápida mostra os pontos apenas dessa corrida
                    self.pontos_campeonato_pilotos[p_nome]["pontos"] = pts
            elif self.modo_jogo != "TEMPORADA":
                self.pontos_campeonato_pilotos[p_nome]["pontos"] = 0

        # 4. Ordena classificação de Pilotos
        self.classificacao_pilotos = sorted(
            self.pontos_campeonato_pilotos.values(),
            key=lambda x: x["pontos"],
            reverse=True
        )

        # 5. Ordena classificação de Construtoras
        tabela_base = (
            self.pontos_campeonato_construtores
            if self.modo_jogo == "TEMPORADA"
            else self.pontos_construtoras
        )
        self.classificacao_construtoras = sorted(
            tabela_base.items(),
            key=lambda x: x[1],
            reverse=True
        )

    def renderizar_corrida(self, tempo_atual, keys):
        segmentos = self.track.draw(self.screen, self.car.position, self.car.player_x)

        visiveis = []
        for bot in self.bots:
            dist_view = (bot["pos"] - self.car.position) % self.track.total_track_length
            if 2 < dist_view < self.track.draw_distance:
                visiveis.append((dist_view, bot))
        visiveis.sort(key=lambda x: x[0], reverse=True)

        for dist, bot in visiveis:
            diferenca_x = bot["x"] - self.car.player_x
            if diferenca_x < -0.35:
                direcao_bot = "esq"
            elif diferenca_x > 0.35:
                direcao_bot = "dir"
            else:
                direcao_bot = "reto"

            chave_pista = f"rear_{direcao_bot}"
            pasta_bot = bot["pasta"]
            if chave_pista not in self.cache_sprites[pasta_bot]:
                chave_pista = "rear_reto"

            img_atual = self.cache_sprites[pasta_bot][chave_pista][bot["frame_idx"]]
            indice = int(dist) - 1
            if 0 <= indice < len(segmentos):
                seg = segmentos[indice]
                img_w, img_h = img_atual.get_width(), img_atual.get_height()
                bot_h = int(seg["largura"] * 0.159)
                bot_w = int(bot_h * (img_w / img_h))

                limite_tela_h = 333
                if bot_h > limite_tela_h:
                    bot_h = limite_tela_h
                    bot_w = int(bot_h * (img_w / img_h))

                if bot_w > 0 and bot_h > 0:
                    img_res = self.redimensionar_bot_otimizado(img_atual, pasta_bot, chave_pista, bot["frame_idx"], bot_w, bot_h)
                    bx = seg["centro"] + (bot["x"] * seg["largura"]) - (bot_w // 2)
                    by = seg["y"] - bot_h
                    self.screen.blit(img_res, (bx, by))

        bots_a_frente = sum(1 for bot in self.bots if bot["pos"] > self.car.position)
        posicao_atual = 1 + bots_a_frente

        eh_preliminary = (
            self.estado_jogo == "PRELIMINARY"
            or (self.estado_jogo == "PAUSE" and self.estado_antes_pause == "PRELIMINARY")
        )

        self.car.draw_cockpit(
            self.screen, keys, tempo_atual, self.track,
            self.bots, self.cache_sprites, posicao_atual,
            lap_limit=self.lap_limit,
            modo_preliminary=eh_preliminary,
            grid_hud_visivel=self.grid_hud_visivel,
            grid_pos_hud=self.grid_pos_hud_atual,
            grid_pos_relogio=self.grid_pos_relogio_atual
        )

        if hasattr(self, 'cockpit_img') and self.cockpit_img:
            self.screen.blit(self.cockpit_img, (0, 0))

        if hasattr(self, 'car') and self.car and self.estado_jogo != "PRELIMINARY":
            self.car.draw_debug(self.screen, self.bots, self.track.total_track_length)

        self.car.draw_alerta_ponto_cego(
            self.screen,
            tempo_atual,
            getattr(self, "alerta_cego_esq", None),
            getattr(self, "alerta_cego_dir", None),
        )

    def despausar_jogo(self):
        tempo_pausado = pygame.time.get_ticks() - self.inicio_pause_tick

        if hasattr(self, 'timer_countdown'):
            self.timer_countdown += tempo_pausado
        if hasattr(self, 'timer_final_lap') and self.final_lap_triggered:
            self.timer_final_lap += tempo_pausado
        if hasattr(self, 'timer_finish') and self.race_finished:
            self.timer_finish += tempo_pausado
        if self.car and hasattr(self.car, 'lap_start_tick'):
            self.car.lap_start_tick += tempo_pausado
        if hasattr(self, 'prelim_lap_start_time'):
            self.prelim_lap_start_time += tempo_pausado
        if hasattr(self, 'prox_spawn_preliminary'):
            self.prox_spawn_preliminary += tempo_pausado

        pygame.mixer.unpause()
        self.tela_pausada = None
        self.estado_jogo = self.estado_antes_pause

    def eventos_teclado(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.silenciar_audios_corrida()
                if self.car:
                    self.car.cleanup()
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and (pygame.key.get_mods() & pygame.KMOD_ALT):
                    pygame.display.toggle_fullscreen()
                    continue

                # ------------------------------------------
                # PAUSE / DESPAUSE (TECLA 'P')
                # ------------------------------------------
                if event.key == pygame.K_p:
                    if self.estado_jogo in ["COUNTDOWN", "RACING", "FINISH", "PRELIMINARY"]:
                        self.estado_antes_pause = self.estado_jogo
                        self.inicio_pause_tick = pygame.time.get_ticks()
                        self.tela_pausada = self.screen.copy()
                        self.pause_sel_idx = 0  # Sempre inicia apontando para "CONTINUAR"

                        self.silenciar_audios_corrida()
                        pygame.mixer.pause()

                        self.estado_jogo = "PAUSE"
                        continue

                    elif self.estado_jogo == "PAUSE":
                        self.despausar_jogo()
                        continue

                # ------------------------------------------
                # MENU DE PAUSE (SETA CIMA/BAIXO + ENTER)
                # ------------------------------------------
                if self.estado_jogo == "PAUSE":
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        self.pause_sel_idx = 1 - self.pause_sel_idx
                    elif event.key == pygame.K_RETURN:
                        if self.pause_sel_idx == 0:
                            # Opção 0: CONTINUAR
                            self.despausar_jogo()
                        else:
                            # Opção 1: SAIR (encerra sons e volta ao menu inicial)
                            pygame.mixer.stop()
                            self.silenciar_audios_corrida()
                            self.bots = []
                            self.car = None
                            self.tela_pausada = None
                            self.sinal_ativo = False
                            self.final_lap_triggered = False
                            self.race_finished = False
                            self.estado_jogo = "INPUT_NAME"
                    continue

                # ------------------------------------------
                # TELA 1: DIGITAR NOME
                # ------------------------------------------
                if self.estado_jogo == "INPUT_NAME":
                    if event.key == pygame.K_RETURN:
                        if self.nome_digitado.strip() == "":
                            self.nome_digitado = "PILOTO"
                        self.pista_sel_idx = 0
                        self.estado_jogo = "SELECT_MODE"
                    elif event.key == pygame.K_BACKSPACE:
                        self.nome_digitado = self.nome_digitado[:-1]
                    else:
                        if len(self.nome_digitado) < 12 and event.unicode.isprintable():
                            self.nome_digitado += event.unicode.upper()

                # ------------------------------------------
                # TELA 1.25: SELEÇÃO DE MODO
                # ------------------------------------------
                elif self.estado_jogo == "SELECT_MODE":
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        self.modo_jogo_sel_idx = 1 - self.modo_jogo_sel_idx
                    elif event.key == pygame.K_RETURN:
                        self.lista_equipes_nomes = list(self.equipes.keys())
                        self.equipe_sel_idx = 0
                        self.piloto_sel_idx = 0
                        if self.modo_jogo_sel_idx == 0:
                            self.modo_jogo = "RAPIDA"
                            self.estado_jogo = "SELECT_TRACK"
                        else:
                            self.modo_jogo = "TEMPORADA"
                            self.carregar_dados_temporada("temporadas/temporada_1.json")
                            self.estado_jogo = "SELECT_TEAM"

                # ------------------------------------------
                # TELA 1.5: SELEÇÃO DE PISTA (CORRIDA RÁPIDA)
                # ------------------------------------------
                elif self.estado_jogo == "SELECT_TRACK":
                    if event.key in [pygame.K_DOWN, pygame.K_RIGHT]:
                        self.pista_sel_idx = (self.pista_sel_idx + 1) % len(self.lista_pistas)
                    elif event.key in [pygame.K_UP, pygame.K_LEFT]:
                        self.pista_sel_idx = (self.pista_sel_idx - 1) % len(self.lista_pistas)
                    elif event.key == pygame.K_RETURN:
                        self.lista_equipes_nomes = list(self.equipes.keys())
                        self.equipe_sel_idx = 0
                        self.piloto_sel_idx = 0
                        self.estado_jogo = "SELECT_TEAM"

                # ------------------------------------------
                # TELA 2: SELEÇÃO DE EQUIPE
                # ------------------------------------------
                elif self.estado_jogo == "SELECT_TEAM":
                    if event.key in [pygame.K_RIGHT, pygame.K_DOWN]:
                        self.equipe_sel_idx = (self.equipe_sel_idx + 1) % len(self.lista_equipes_nomes)
                    elif event.key in [pygame.K_LEFT, pygame.K_UP]:
                        self.equipe_sel_idx = (self.equipe_sel_idx - 1) % len(self.lista_equipes_nomes)
                    elif event.key == pygame.K_RETURN:
                        self.piloto_sel_idx = 0
                        self.inicializar_placares_campeonato()
                        if self.modo_jogo == "TEMPORADA":
                            # Inicia a Preliminary Race antes da 1ª corrida da temporada
                            self.iniciar_preliminary_etapa_atual()
                        else:
                            self.posicao_jogador = 16
                            self.estado_jogo = "SELECT_POS"

                # ------------------------------------------
                # TELA 3: ESCOLHER POSIÇÃO (APENAS CORRIDA RÁPIDA)
                # ------------------------------------------
                elif self.estado_jogo == "SELECT_POS" and self.modo_jogo == "RAPIDA":
                    if not hasattr(self, 'posicao_jogador'):
                        self.posicao_jogador = 16

                    if event.key == pygame.K_RIGHT:
                        self.posicao_jogador = 1 if self.posicao_jogador >= 16 else self.posicao_jogador + 1
                    elif event.key == pygame.K_LEFT:
                        self.posicao_jogador = 16 if self.posicao_jogador <= 1 else self.posicao_jogador - 1
                    elif event.key == pygame.K_DOWN:
                        self.posicao_jogador = self.posicao_jogador - 8 if self.posicao_jogador > 8 else self.posicao_jogador + 8
                    elif event.key == pygame.K_UP:
                        self.posicao_jogador = self.posicao_jogador + 8 if self.posicao_jogador <= 8 else self.posicao_jogador - 8
                    elif event.key == pygame.K_RETURN:
                        self.opcoes_voltas = [1, 3, 5, 10, 15, 30]
                        self.volta_sel_idx = 1
                        self.estado_jogo = "SELECT_LAPS"

                # ------------------------------------------
                # TELA 4: SELEÇÃO DE VOLTAS (APENAS CORRIDA RÁPIDA)
                # ------------------------------------------
                elif self.estado_jogo == "SELECT_LAPS" and self.modo_jogo == "RAPIDA":
                    if event.key == pygame.K_DOWN:
                        self.volta_sel_idx = (self.volta_sel_idx + 1) % len(self.opcoes_voltas)
                    elif event.key == pygame.K_UP:
                        self.volta_sel_idx = (self.volta_sel_idx - 1) % len(self.opcoes_voltas)
                    elif event.key == pygame.K_RETURN:
                        pista_escolhida = self.lista_pistas[self.pista_sel_idx]["arquivo"]
                        self.iniciar_corrida(pista_escolhida, modo_preliminary=False)
                        self.estado_jogo = "LOADING"

                elif self.estado_jogo == "DEBUG_REPORT":
                    if event.key == pygame.K_RETURN:
                        self.estado_jogo = "RESULTADOS_CORRIDA"

                # ------------------------------------------
                # TELA 5: RESULTADOS DA CORRIDA
                # ------------------------------------------
                elif self.estado_jogo == "RESULTADOS_CORRIDA":
                    if event.key == pygame.K_RETURN:
                        # NÃO zera self.nome_digitado aqui para não perder seu nome na 2ª corrida!
                        self.estado_jogo = "RESULTADOS_PILOTOS"

                # ------------------------------------------
                # TELA 6: CLASSIFICAÇÃO DO CAMPEONATO DE PILOTOS
                # ------------------------------------------
                elif self.estado_jogo == "RESULTADOS_PILOTOS":
                    if event.key == pygame.K_RETURN:
                        self.estado_jogo = "RESULTADOS_CONSTRUTORES"

                # ------------------------------------------
                # TELA 7: CLASSIFICAÇÃO DAS CONSTRUTORAS
                # ------------------------------------------
                elif self.estado_jogo == "RESULTADOS_CONSTRUTORES":
                    if event.key == pygame.K_RETURN:
                        self.silenciar_audios_corrida()
                        self.bots = []
                        self.car = None

                        if self.modo_jogo == "TEMPORADA":
                            self.etapa_atual_idx += 1
                            if self.etapa_atual_idx < len(self.etapas_temporada):
                                # Vai para a Preliminary Race da PRÓXIMA pista da temporada!
                                self.iniciar_preliminary_etapa_atual()
                            else:
                                # Acabou a temporada -> Reseta e volta ao menu inicial
                                self.etapa_atual_idx = 0
                                self.nome_digitado = ""
                                self.estado_jogo = "INPUT_NAME"
                        else:
                            self.nome_digitado = ""
                            self.estado_jogo = "INPUT_NAME"

    def telas_menu(self, fonte_menu):
        if self.estado_jogo == "PAUSE":
            if self.tela_pausada:
                self.screen.blit(self.tela_pausada, (0, 0))
            self.screen.blit(self.overlay_finish, (0, 0))

            # Dimensões e posição centralizada do quadradinho azul
            box_w, box_h = 260, 150
            box_x = WIDTH // 2 - box_w // 2
            box_y = HEIGHT // 2 - box_h // 2
            box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

            # Fundo azul arcade
            pygame.draw.rect(self.screen, (15, 45, 145), box_rect)

            # Bordas cinzas brilhantes (dupla camada para efeito metálico)
            pygame.draw.rect(self.screen, (180, 185, 195), box_rect, 5)
            pygame.draw.rect(self.screen, (240, 245, 255), box_rect.inflate(-4, -4), 2)

            # Opções do menu
            opcoes = ["CONTINUAR", "SAIR"]
            texto_x = box_x + 75
            inicio_y = box_y + 38
            espacamento_y = 48

            for i, texto_opcao in enumerate(opcoes):
                selecionado = (i == self.pause_sel_idx)
                cor_texto = (255, 255, 255) if selecionado else (175, 185, 210)
                img_opcao = self.fonte_lista.render(texto_opcao, True, cor_texto)

                pos_y = inicio_y + (i * espacamento_y)
                self.screen.blit(img_opcao, (texto_x, pos_y))

                # Desenha a setinha vermelha apontando para a direita ao lado da opção ativa
                if selecionado:
                    seta_x = texto_x - 28
                    seta_cy = pos_y + img_opcao.get_height() // 2
                    pontos_seta = [
                        (seta_x, seta_cy - 9),
                        (seta_x + 15, seta_cy),
                        (seta_x, seta_cy + 9)
                    ]
                    pygame.draw.polygon(self.screen, (255, 25, 25), pontos_seta)
                    pygame.draw.polygon(self.screen, (255, 200, 200), pontos_seta, 1)

            pygame.display.flip()
            self.clock.tick(FPS)
            return True

        if self.estado_jogo == "INPUT_NAME":
            self.ui.desenhar_tela_nome()
            pygame.display.flip()
            self.clock.tick(FPS)
            return True

        if self.estado_jogo == "SELECT_MODE":
            self.ui.desenhar_tela_modo()
            pygame.display.flip()
            self.clock.tick(FPS)
            return True

        if self.estado_jogo == "SELECT_TRACK":
            self.ui.desenhar_tela_pistas()
            pygame.display.flip()
            self.clock.tick(FPS)
            return True

        if self.estado_jogo == "SELECT_POS" and self.modo_jogo == "RAPIDA":
            self.ui.desenhar_tela_posicao()
            pygame.display.flip()
            self.clock.tick(FPS)
            return True

        if self.estado_jogo == "LOADING_PRELIMINARY":
            self.screen.fill((20, 20, 25))
            texto = self.fonte_grande.render("LOADING PRELIMINARY...", True, (255, 200, 0))
            self.screen.blit(texto, (WIDTH // 2 - texto.get_width() // 2, HEIGHT // 2 - 40))
            pygame.display.flip()

            self.pre_aquecer_cache()
            now = pygame.time.get_ticks()
            self.car.lap_start_tick = now
            self.prelim_lap_start_time = now
            self.prox_spawn_preliminary = now + random.randint(40000, 90000)
            self.estado_jogo = "PRELIMINARY"
            return True

        if self.estado_jogo == "LOADING":
            self.screen.fill((20, 20, 25))
            texto = self.fonte_grande.render("LOADING ENGINE...", True, (255, 200, 0))
            self.screen.blit(texto, (WIDTH // 2 - texto.get_width() // 2, HEIGHT // 2 - 40))
            pygame.display.flip()

            self.pre_aquecer_cache()

            self.timer_countdown = pygame.time.get_ticks()
            self.sinal_ativo = True
            self.sinal_vermelho_tocou = False
            self.sinal_verde_tocou = False
            self.pos_inicial_largada = self.car.position
            self.estado_jogo = "COUNTDOWN"
            return True

        if self.estado_jogo == "RESULTADOS_CORRIDA":
            self.screen.fill((20, 20, 50))
            titulo = fonte_menu.render("RACE RESULTS", True, (255, 255, 0))
            self.screen.blit(titulo, (WIDTH // 2 - titulo.get_width() // 2, 30))

            meu_nome = getattr(self, "nome_jogador_formatado", "PILOTO").upper()

            for i, piloto in enumerate(self.classificacao_final):
                sigla = piloto["equipe"][:3].upper()
                texto = f"{i+1:2d}. {piloto['nome']} ({sigla})"

                cor = (0, 255, 0) if piloto["nome"].upper() == meu_nome else (255, 255, 255)
                img_txt = self.fonte_lista.render(texto, True, cor)

                if i < 8:
                    x, y = WIDTH // 4 - 100, 120 + (i * 45)
                else:
                    x, y = 3 * (WIDTH // 4) - 100, 120 + ((i - 8) * 45)

                self.screen.blit(img_txt, (x, y))

            aviso = self.fonte_lista.render("PRESS ENTER TO CONTINUE", True, (255, 0, 0))
            self.screen.blit(aviso, (WIDTH // 2 - aviso.get_width() // 2, HEIGHT - 50))

            pygame.display.flip()
            self.clock.tick(FPS)
            return True

        if self.estado_jogo == "RESULTADOS_PILOTOS":
            self.ui.desenhar_tela_resultados_pilotos()
            pygame.display.flip()
            self.clock.tick(FPS)
            return True

        if self.estado_jogo == "RESULTADOS_CONSTRUTORES":
            self.ui.desenhar_tela_resultados_construtores()
            pygame.display.flip()
            self.clock.tick(FPS)
            return True

        return False

    def fisica_colisao_bots(self, tempo_atual, keys):
        curve_intensity, jogador_no_vacuo, menor_distancia_bot = self.ai.atualizar_bots(tempo_atual)
        self.car.update_physics(keys, tempo_atual, curve_intensity, self.steering_locked, no_vacuo=jogador_no_vacuo)

        if not self.final_lap_triggered and self.estado_jogo == "RACING":
            if self.car.laps_completed >= self.lap_limit - 1:
                self.final_lap_triggered = True
                self.timer_final_lap = tempo_atual
                if hasattr(self, 'som_final_lap') and self.som_final_lap:
                    try:
                        self.som_final_lap.play()
                    except Exception as e:
                        print(f"Erro ao tocar final_lap.wav: {e}")

        if self.car.speed > getattr(self.car, 'velocidade_maxima_corrida', 0):
            self.car.velocidade_maxima_corrida = self.car.speed

        for bot in self.bots:
            if bot["speed"] > bot.get("velocidade_maxima_corrida", 0):
                bot["velocidade_maxima_corrida"] = bot["speed"]

        self.track.update_parallax(self.car.speed, curve_intensity, keys)
        self.car.update_timer(self.track.total_track_length, self.lap_limit)

    def audio_dinamico(self, tempo_atual):
        bots_audiveis = []
        raio_audicao = 50

        for bot in self.bots:
            dist_bruta = (bot["pos"] - self.car.position) % self.track.total_track_length
            if dist_bruta > self.track.total_track_length / 2:
                dist_bruta -= self.track.total_track_length

            dist_abs = abs(dist_bruta)
            if dist_abs < raio_audicao:
                bots_audiveis.append((dist_abs, bot))

        bots_audiveis.sort(key=lambda x: x[0])

        for i, canal in enumerate(self.canais_motor_bot):
            if i < len(bots_audiveis):
                dist, bot_som = bots_audiveis[i]
                fator = dist / raio_audicao

                volume_calculado = ((1.0 - fator) ** 2) * 0.4
                volume_seguro = max(0.0, volume_calculado)

                if self.estado_jogo == "COUNTDOWN":
                    ritmo = 0.005 + ((bot_som["pos"] % 4) * 0.001)
                    fase_desalinhada = bot_som["pos"] * 3.7
                    onda_rpm = math.sin((tempo_atual * ritmo) + fase_desalinhada)
                    pitch_alvo = 0.75 + (onda_rpm * 0.15)
                else:
                    pitch_alvo = 0.6 + (1.0 - fator) * 0.35

                canal.set_gain(volume_seguro)
                canal.set_pitch(max(0.4, pitch_alvo))

                if canal.get_state() != 4114:
                    canal.play()
            else:
                canal.set_gain(0.0)

    def countdown_tela(self, tempo_atual):
        tempo_passado = tempo_atual - self.timer_countdown

        # Libera os carros exatamente aos 5.0s (5000 ms), junto com o sinal verde
        if tempo_passado >= 5000 and self.estado_jogo == "COUNTDOWN":
            self.estado_jogo = "RACING"
            self.car.lap_start_tick = tempo_atual

            rpm_ratio = self.car.rpm_neutro / self.car.max_speed
            if rpm_ratio > 0.7:
                self.car.speed = (self.car.max_speed * 0.08)
            else:
                self.car.speed = (self.car.rpm_neutro * 0.1)

            if self.lap_limit == 1 and not self.final_lap_triggered:
                self.final_lap_triggered = True
                self.timer_final_lap = tempo_atual
                if hasattr(self, 'som_final_lap') and self.som_final_lap:
                    try:
                        self.som_final_lap.play()
                    except Exception as e:
                        print(f"Erro ao tocar final_lap.wav: {e}")

    def desenhar_sinal_largada(self, tempo_atual):
        if not self.sinal_ativo:
            return

        tempo_passado = tempo_atual - self.timer_countdown
        duracao_fade = 350.0  # Duração do fade em milissegundos (0.35s)

        # Desenha a estrutura base do semáforo
        self.screen.blit(self.img_sinal, self.sinal_pos)

        # 1. Aos 3.5s (3500 ms): Fade para VERMELHO + toca vermelho.wav
        if 3500 <= tempo_passado < 5000:
            if not self.sinal_vermelho_tocou:
                self.sinal_vermelho_tocou = True
                if self.som_sinal_vermelho:
                    try:
                        self.som_sinal_vermelho.play()
                    except Exception as e:
                        print(f"Erro ao tocar vermelho.wav: {e}")

            progresso_verm = min(1.0, (tempo_passado - 3500) / duracao_fade)
            self.mascara_vermelha.set_alpha(int(255 * progresso_verm))
            self.screen.blit(self.mascara_vermelha, self.sinal_pos)

        # 2. Aos 5.0s (5000 ms): Fade para VERDE + toca verde.wav
        elif tempo_passado >= 5000:
            if not self.sinal_verde_tocou:
                self.sinal_verde_tocou = True
                if self.som_sinal_verde:
                    try:
                        self.som_sinal_verde.play()
                    except Exception as e:
                        print(f"Erro ao tocar verde.wav: {e}")

            progresso_verde = min(1.0, (tempo_passado - 5000) / duracao_fade)

            # Crossfade suave do vermelho apagando e o verde acendendo
            if progresso_verde < 1.0:
                self.mascara_vermelha.set_alpha(int(255 * (1.0 - progresso_verde)))
                self.screen.blit(self.mascara_vermelha, self.sinal_pos)

            self.mascara_verde.set_alpha(int(255 * progresso_verde))
            self.screen.blit(self.mascara_verde, self.sinal_pos)

            # Só esconde o sinal após o jogador se afastar 200m do ponto de largada
            if self.estado_jogo == "RACING" and self.sinal_verde_tocou:
                dist_percorrida = (self.car.position - self.pos_inicial_largada) % self.track.total_track_length
                if dist_percorrida >= 200:
                    self.sinal_ativo = False

    def desenhar_aviso_final_lap(self, tempo_atual):
        tempo_decorrido = tempo_atual - self.timer_final_lap
        if tempo_decorrido >= 2800:
            return

        banner_h = 96
        banner_y = (HEIGHT // 3) - (banner_h // 2)
        self.screen.blit(self.banner_final_lap, (0, banner_y))

        pisca = (tempo_atual // 150) % 2 == 0
        cor_borda = (255, 215, 0) if pisca else (255, 50, 50)
        pygame.draw.line(self.screen, cor_borda, (0, banner_y), (WIDTH, banner_y), 4)
        pygame.draw.line(self.screen, cor_borda, (0, banner_y + banner_h), (WIDTH, banner_y + banner_h), 4)

        cor_texto = (255, 230, 0) if pisca else (255, 255, 255)
        txt_banner = self.fonte_banner.render(">>> FINAL LAP! <<<", True, cor_texto)
        txt_sombra = self.fonte_sub.render(">>> FINAL LAP! <<<", True, (0, 0, 0))

        cx = WIDTH // 2
        cy = banner_y + 30
        self.screen.blit(txt_sombra, (cx - txt_banner.get_width() // 2 + 3, cy - txt_banner.get_height() // 2 + 3))
        self.screen.blit(txt_banner, (cx - txt_banner.get_width() // 2, cy - txt_banner.get_height() // 2))

        txt_sub = self.fonte_sub.render("LAST CHANCE - PUSH TO THE LIMIT!", True, (240, 240, 255))
        self.screen.blit(txt_sub, (cx - txt_sub.get_width() // 2, banner_y + 66))

    def final_corrida(self, tempo_atual):
        self.screen.blit(self.overlay_finish, (0, 0))

        texto_finish = self.fonte_grande.render("FINISH!", True, (255, 200, 0))
        pos_texto = f"{self.final_position}º PLACE"
        cor_pos = (0, 255, 0) if self.final_position == 1 else (255, 255, 255)
        texto_rank = self.fonte_grande.render(pos_texto, True, cor_pos)

        self.screen.blit(texto_finish, (WIDTH // 2 - texto_finish.get_width() // 2, HEIGHT // 2 - 100))
        self.screen.blit(texto_rank, (WIDTH // 2 - texto_rank.get_width() // 2, HEIGHT // 2))

        if tempo_atual - self.timer_finish > 5000:
            self.silenciar_audios_corrida()

            self.dados_relatorio_corrida = []
            for b in self.bots:
                self.dados_relatorio_corrida.append({
                    "nome": b["nome"],
                    "is_player": False,
                    "pos_inicial": b["pos_inicial_grid"],
                    "pos_final": 16,
                    "vmax": b.get("velocidade_maxima_corrida", 0),
                    "sorte": b.get("fator_sorte_qualificacao", 0),
                    "distancia": b["pos"]
                })

            self.dados_relatorio_corrida.sort(key=lambda x: x["distancia"], reverse=True)

            posicao_atual_livre = 1
            for bot_data in self.dados_relatorio_corrida:
                if posicao_atual_livre == self.final_position:
                    posicao_atual_livre += 1
                bot_data["pos_final"] = posicao_atual_livre
                posicao_atual_livre += 1

            self.dados_relatorio_corrida.append({
                "nome": self.nome_jogador_formatado,
                "is_player": True,
                "pos_inicial": self.car.pos_inicial_grid,
                "pos_final": self.final_position,
                "vmax": self.car.velocidade_maxima_corrida,
                "sorte": 0
            })

            self.dados_relatorio_corrida.sort(key=lambda x: x["pos_final"])
            self.estado_jogo = "DEBUG_REPORT"
            return True

    def run(self):
        while True:
            tempo_atual = pygame.time.get_ticks()
            keys = pygame.key.get_pressed()

            self.eventos_teclado()

            if self.telas_menu(self.fonte_menu):
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            # ==========================================
            # MODO PRELIMINARY RACE (VOLTAS INFINITAS)
            # ==========================================
            if self.estado_jogo == "PRELIMINARY":
                self.fisica_colisao_bots(tempo_atual, keys)
                self.audio_dinamico(tempo_atual)

                # Spawna carros aleatórios com intervalo mínimo de 40s
                if tempo_atual >= self.prox_spawn_preliminary:
                    self.spawnar_carro_aleatorio_preliminary(tempo_atual)

                # Só exibe o mostrador após completar pelo menos 1 volta cronometrada
                if self.car.laps_completed >= 1 and self.car.last_lap_time > 0:
                    if self.melhor_volta_preliminary is None or self.car.last_lap_time < self.melhor_volta_preliminary:
                        self.melhor_volta_preliminary = self.car.last_lap_time

                    self.posicao_qualificada = self.calcular_posicao_preliminary(
                        self.pista_preliminary_atual, self.melhor_volta_preliminary
                    )
                    self.grid_pos_hud_atual = self.posicao_qualificada
                    self.grid_pos_relogio_atual = self.calcular_posicao_preliminary(
                        self.pista_preliminary_atual, self.car.current_lap_time
                    )
                    self.grid_hud_visivel = True

                # Verifica se segurou A + S + D por 2 segundos (2000 ms) para sair
                progresso_saida = 0.0
                if keys[pygame.K_a] and keys[pygame.K_s] and keys[pygame.K_d]:
                    if self.asd_hold_start is None:
                        self.asd_hold_start = tempo_atual
                    decorrido_hold = tempo_atual - self.asd_hold_start
                    progresso_saida = decorrido_hold / 2000.0

                    if decorrido_hold >= 2000:
                        self.silenciar_audios_corrida()
                        etapa = self.etapas_temporada[self.etapa_atual_idx]
                        self.lap_limit = etapa.get("voltas", 3)
                        self.posicao_jogador = self.posicao_qualificada
                        arq_pista = os.path.splitext(os.path.basename(etapa["arquivo"]))[0]
                        self.iniciar_corrida(arq_pista, modo_preliminary=False)
                        self.estado_jogo = "LOADING"
                        continue
                else:
                    self.asd_hold_start = None

                self.renderizar_corrida(tempo_atual, keys)

                # Barra discreta apenas quando o jogador estiver segurando A+S+D para sair
                if progresso_saida > 0:
                    bar_w, bar_h = 260, 14
                    bx = WIDTH // 2 - bar_w // 2
                    by = HEIGHT - 32
                    pygame.draw.rect(self.screen, (20, 20, 20), (bx - 2, by - 2, bar_w + 4, bar_h + 4))
                    pygame.draw.rect(self.screen, (255, 200, 0), (bx, by, int(bar_w * min(1.0, progresso_saida)), bar_h))

                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            # ==========================================
            # FÍSICA, IA E COLISÃO DOS BOTS (CORRIDA OFICIAL)
            # ==========================================
            if self.estado_jogo in ["RACING", "FINISH"]:
                self.fisica_colisao_bots(tempo_atual, keys)

                if not self.race_finished and self.car.laps_completed >= self.lap_limit:
                    self.race_finished = True
                    self.estado_jogo = "FINISH"
                    self.timer_finish = tempo_atual
                    self.gerar_resultados()
                    bots_a_frente = sum(1 for bot in self.bots if bot["pos"] > self.car.position)
                    self.final_position = 1 + bots_a_frente
                    self.car.speed = max(100.0, self.car.speed * 0.85)

            if self.estado_jogo == "SELECT_TEAM":
                self.ui.desenhar_tela_equipes()
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            if self.estado_jogo == "SELECT_LAPS" and self.modo_jogo == "RAPIDA":
                self.ui.desenhar_tela_voltas()
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            if self.estado_jogo == "DEBUG_REPORT":
                self.ui.desenhar_tela_debug_relatorio()
                pygame.display.flip()
                self.clock.tick(FPS)
                continue

            # ==========================================
            # RENDERIZAÇÃO VISUAL DA PISTA E COCKPIT
            # ==========================================
            if self.estado_jogo in ["COUNTDOWN", "RACING", "FINISH"]:
                self.audio_dinamico(tempo_atual)

                if self.estado_jogo == "COUNTDOWN":
                    self.car.acelerar_neutro(keys)

                    if hasattr(self.car, 'motor_sound') and self.car.motor_sound:
                        rpm_falso = self.car.rpm_neutro / self.car.max_speed
                        self.car.motor_sound.set_gain(0.3 + (rpm_falso * 0.5))
                        self.car.motor_sound.set_pitch(0.6 + (rpm_falso * 0.8))
                        if self.car.motor_sound.get_state() != 4114:
                            self.car.motor_sound.play()

                self.renderizar_corrida(tempo_atual, keys)

                if self.estado_jogo == "COUNTDOWN":
                    self.countdown_tela(tempo_atual)

                if self.sinal_ativo:
                    self.desenhar_sinal_largada(tempo_atual)

                if self.final_lap_triggered and (tempo_atual - self.timer_final_lap < 2800):
                    self.desenhar_aviso_final_lap(tempo_atual)

            if self.estado_jogo == "FINISH":
                if self.final_corrida(tempo_atual):
                    continue

            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    Game().run()