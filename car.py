# car.py
import pygame
import math
import json
from openal import oalOpen, oalQuit
from settings import *
from utils import carregar_img


class Car:
    def __init__(self, velocidade_maxima=330, nivel_aceleracao=1, nivel_freio=1, nivel_direcao=1, pasta_equipe="minarae"):
        self.font = pygame.font.SysFont('Arial', 30, bold=True)

        # --- SISTEMA DE TEMPOS E VOLTAS ---
        self.laps_completed = 0
        self.lap_start_tick = pygame.time.get_ticks()
        self.current_lap_time = 0
        self.last_lap_time = 0
        self.best_lap_time = 0

        # ==========================================
        # FÍSICA DINÂMICA DO MOTOR (COM HANDICAP DO PLAYER)
        # ==========================================
        self.speed = 0
        
        # 1. Ajuste de Velocidade Máxima HANDCAP
        # Corta a velocidade final do jogador em cerca de 3% a 5% em relação à IA
        # ex: self.max_speed = velocidade_maxima * 0.95 corta 5%  
        # para simular o "peso" extra do jogador ou forçá-lo a usar o vácuo.
        self.max_speed = velocidade_maxima * 0.9519
        
        # 2. Ajuste Dinâmico de Aceleração (A Mágica)
        # Se a equipe for muito ruim (nível baixo), o jogador sofre um corte grande.
        # Se a equipe for boa (nível 6 ou 7), o corte é bem menor.
        # Fórmula: Base de 35% + 1% por cada nível da equipe.
        fator_nerf_acel = 0.350 + (nivel_aceleracao * 0.006)
        
        # Trava de segurança para nunca passar de 100% dos status originais
        
        
        self.nivel_aceleracao = nivel_aceleracao * fator_nerf_acel
        # === NOVOS ATRIBUTOS ===
        # Nível 1: Freio fraco (0.5) | Nível 7: Freio de cerâmica (1.4)
        self.brake_power = 0.35 + (nivel_freio * 0.15) 
        
        
        # A inércia atual (começa em 0)
        self.current_steering = 0.1 

        # ==========================================
        # PROPRIEDADES DE DIREÇÃO (CORRIGIDO)
        # ==========================================
        self.steering = 0.0          # Garante que o volante comece reto
        self.max_steering = 0.04     # <--- NOVA: Limite base de ângulo (Evita travar em 0)
        self.steering_speed = 0.1    # <--- NOVA: Velocidade de resposta base
        
        # Variável para o som do motor no neutro (Largada)
        self.rpm_neutro = 0
        self.friction = 0.00003
        self.brake_power = 1.0
        
        self.position = 0.0 
        self.player_x = 0.0 
        
        # Marchas
        self.transmissao = "AUTO"  
        self.marcha_atual = 1
        self.max_marchas = 7
        self.timer_marcha = 0      
        
        # A MÁGICA DAS MARCHAS: Agora elas se adaptam à velocidade máxima do carro!
        self.limite_marchas = {
            1: self.max_speed * 0.18, 
            2: self.max_speed * 0.33,
            3: self.max_speed * 0.48,
            4: self.max_speed * 0.63,
            5: self.max_speed * 0.78,
            6: self.max_speed * 0.90,
            7: self.max_speed * 1.05  
        }
        self.torque_marchas = {1: 1.5, 2: 1.2, 3: 1.0, 4: 0.85, 5: 0.75, 6: 0.62, 7: 0.62}
        
        # ÁUDIO MOTOR DO SEU CARRO
        try:
            self.motor_sound = oalOpen("motor.wav")
            self.motor_sound.set_looping(True)
            self.motor_sound.set_gain(0.2)
            self.motor_sound.set_pitch(0.8)
            self.motor_sound.play()
        except Exception as e:
            print(f"AVISO OpenAL: Erro ao carregar motor.wav -> {e}")
            self.motor_sound = None

        # ==========================================
        # ÁUDIO DE DERRAPAGEM (OPENAL PARA PITCH DINÂMICO)
        # ==========================================
        try:
            self.skid_sound = oalOpen("sounds/skid.wav")
            self.skid_sound.set_looping(True)
            self.skid_sound.set_gain(0.0) # Começa totalmente mudo
            self.skid_sound.play()        # Fica rodando no fundo
            
            # Variável para criar o nosso próprio "Fade In" e "Fade Out" matemático
            self.skid_gain_atual = 0.0 
        except Exception as e:
            print(f"Aviso OpenAL: Erro ao carregar skid.wav -> {e}")
            self.skid_sound = None
            self.skid_gain_atual = 0.0

        # Animação
        self.frame_index = 0
        self.animation_timer = 0
        self.volante_frame = 0
        self.volante_timer = 0
        self.volante_speed = 50 
        self.ultima_direcao = 'reto'

        # Carregamento de Imagens do Cockpit
        tamanho_volante = (380, 95)
        tamanho_pneu = (133, 80)    
        tamanho_painel = (WIDTH / 3, 250)

        self.volante_reto = carregar_img("images/cockpit/volante_reto.png", tamanho_volante)
        self.volantes_esq = [carregar_img(f"images/cockpit/volante_esq{i}.png", tamanho_volante) for i in (1,2,3)]
        self.volantes_dir = [carregar_img(f"images/cockpit/volante_dir{i}.png", tamanho_volante) for i in (1,2,3)]
        
        self.pneus_esq_reto = [
            carregar_img("images/cockpit/pneu_esq_reto1.png", tamanho_pneu),
            carregar_img("images/cockpit/pneu_esq_reto1a.png", tamanho_pneu),
            carregar_img("images/cockpit/pneu_esq_reto1b.png", tamanho_pneu)
        ]
        self.pneus_dir_reto = [pygame.transform.flip(img, True, False) for img in self.pneus_esq_reto]
        
        self.pneus_dir_virando_esq = [
            [carregar_img(f"images/cockpit/pneu_dir_vir_esq1{s}.png", tamanho_pneu) for s in ("","a","b")],
            [carregar_img(f"images/cockpit/pneu_dir_vir_esq2{s}.png", tamanho_pneu) for s in ("","a","b")]
        ]
        self.pneus_esq_virando_esq = [
            [carregar_img(f"images/cockpit/pneu_esq_vir_esq1{s}.png", tamanho_pneu) for s in ("","a","b")],
            [carregar_img(f"images/cockpit/pneu_esq_vir_esq2{s}.png", tamanho_pneu) for s in ("","a","b")]
        ]
        self.pneus_esq_virando_dir = [
            [carregar_img(f"images/cockpit/pneu_esq_vir_dir1{s}.png", tamanho_pneu) for s in ("","a","b")],
            [carregar_img(f"images/cockpit/pneu_esq_vir_dir2{s}.png", tamanho_pneu) for s in ("","a","b")]
        ]
        self.pneus_dir_virando_dir = [
            [carregar_img(f"images/cockpit/pneu_dir_vir_dir1{s}.png", tamanho_pneu) for s in ("","a","b")],
            [carregar_img(f"images/cockpit/pneu_dir_vir_dir2{s}.png", tamanho_pneu) for s in ("","a","b")]
        ]
        
        self.retro_sway_suave = 0 # <-- NOVO: Amortecedor do retrovisor

        # ==========================================
        # CARREGA AS IMAGENS BASEADAS NA EQUIPE
        # ==========================================
        # É ESTA LINHA ABAIXO QUE CRIA O self.retrovisor_img!
        self.carregar_sprites_cockpit(pasta_equipe)

    def carregar_sprites_cockpit(self, pasta_equipe):
        """Lê os PNGs do cockpit buscando primeiro na pasta da equipe. Se não achar, usa os originais."""
        tamanho_volante = (380, 95)
        tamanho_pneu = (133, 80)    
        tamanho_retrovisor = (int(WIDTH // 1.5), 120)
        
        pasta_time = f"images/cockpit"
        pasta_base = "images/cockpit"
        
        def pegar_img(nome_arquivo, tamanho):
            # Tenta pegar a skin da equipe
            img = carregar_img(f"{pasta_time}/{nome_arquivo}", tamanho)
            if not img:
                # Se a equipe não tem essa imagem ainda, usa a padrão cinza/preta
                img = carregar_img(f"{pasta_base}/{nome_arquivo}", tamanho)
            return img

        # 1. Volantes
        self.volante_reto = pegar_img("volante_reto.png", tamanho_volante)
        self.volantes_esq = [pegar_img(f"volante_esq{i}.png", tamanho_volante) for i in (1,2,3)]
        self.volantes_dir = [pegar_img(f"volante_dir{i}.png", tamanho_volante) for i in (1,2,3)]
        
        # 2. Pneus Retos
        self.pneus_esq_reto = [
            pegar_img("pneu_esq_reto1.png", tamanho_pneu),
            pegar_img("pneu_esq_reto1a.png", tamanho_pneu),
            pegar_img("pneu_esq_reto1b.png", tamanho_pneu)
        ]
        self.pneus_dir_reto = [pygame.transform.flip(img, True, False) for img in self.pneus_esq_reto]
        
        # 3. Pneus Virando
        self.pneus_dir_virando_esq = [
            [pegar_img(f"pneu_dir_vir_esq1{s}.png", tamanho_pneu) for s in ("","a","b")],
            [pegar_img(f"pneu_dir_vir_esq2{s}.png", tamanho_pneu) for s in ("","a","b")]
        ]
        self.pneus_esq_virando_esq = [
            [pegar_img(f"pneu_esq_vir_esq1{s}.png", tamanho_pneu) for s in ("","a","b")],
            [pegar_img(f"pneu_esq_vir_esq2{s}.png", tamanho_pneu) for s in ("","a","b")]
        ]
        self.pneus_esq_virando_dir = [
            [pegar_img(f"pneu_esq_vir_dir1{s}.png", tamanho_pneu) for s in ("","a","b")],
            [pegar_img(f"pneu_esq_vir_dir2{s}.png", tamanho_pneu) for s in ("","a","b")]
        ]
        self.pneus_dir_virando_dir = [
            [pegar_img(f"pneu_dir_vir_dir1{s}.png", tamanho_pneu) for s in ("","a","b")],
            [pegar_img(f"pneu_dir_vir_dir2{s}.png", tamanho_pneu) for s in ("","a","b")]
        ]
        
        # 4. Retrovisor (Carregado apenas uma vez para salvar memória!)
        self.retrovisor_img = pegar_img("retrovisor.png", tamanho_retrovisor)

    # Adicionamos o steering_locked=False no final
    def update_physics(self, keys, tempo_atual, curve_intensity, steering_locked=False, no_vacuo=False):
        # 1. Troca de Marchas
        if keys[pygame.K_t] and (tempo_atual - self.timer_marcha > 500):
            self.transmissao = "MANUAL" if self.transmissao == "AUTO" else "AUTO"
            self.timer_marcha = tempo_atual

        if self.transmissao == "MANUAL":
            if keys[pygame.K_DOWN] and (tempo_atual - self.timer_marcha > 250) and self.marcha_atual < self.max_marchas:
                self.marcha_atual += 1
                self.timer_marcha = tempo_atual
            elif keys[pygame.K_UP] and (tempo_atual - self.timer_marcha > 250) and self.marcha_atual > 1:
                self.marcha_atual -= 1
                self.timer_marcha = tempo_atual
        else:
            if self.speed > self.limite_marchas[self.marcha_atual] * 0.95 and self.marcha_atual < self.max_marchas:
                self.marcha_atual += 1
            elif self.marcha_atual > 1 and self.speed < self.limite_marchas[self.marcha_atual - 1] * 0.8:
                self.marcha_atual -= 1

        # 2. Terreno, Aceleração e Freio
        na_grama = abs(self.player_x) > 1.0 

        if keys[pygame.K_s]: 
            # O motor tenta empurrar o carro para frente
            forca_motor = self.torque_marchas[self.marcha_atual]
            
            multiplicador_potencia = 0.4 + (self.nivel_aceleracao * 0.22)
            
            # --- A MÁGICA DA ACELERAÇÃO NO VÁCUO ---
            # Se estiver no vácuo, o motor "pensa" que o limite do carro é 15 km/h maior.
            vel_referencia = self.max_speed + 10 if no_vacuo else self.max_speed
            
            taxa_aceleracao = forca_motor * multiplicador_potencia * (1.5 - (self.speed / vel_referencia))
            
            # O Vácuo tira a resistência do ar: aceleração aumenta 20% para sugar o carro!
            if no_vacuo and self.speed > 300:
                taxa_aceleracao *= 1.6
                
            self.speed += taxa_aceleracao
            
            # A grama "agarra" os pneus
            if na_grama:
                self.speed -= 0.5
        else:
            # Soltou o acelerador: freio motor e inércia do vento
            atrito_terreno = 1.2 if na_grama else (0.05 + (self.speed / self.max_speed) * 0.2)
            self.speed -= atrito_terreno 

        # ==========================================
        # LIMITES, CORTE DE GIRO E PAREDE DE VENTO
        # ==========================================
        limite_atual = self.limite_marchas[self.marcha_atual]
        
        # MÁGICA DO VÁCUO: O teto da última marcha sobe os exatos 15 km/h
        if no_vacuo and self.marcha_atual == self.max_marchas:
            limite_atual += 30

        if not na_grama and self.speed > limite_atual:
            if no_vacuo:
                # Trava cravada no teto do vácuo (+15)
                self.speed = limite_atual 
            else:
                # SAIU DO VÁCUO: A resistência do ar bate como uma parede!
                # O carro perde velocidade super rápido (-1.2 por frame) até voltar ao limite normal.
                self.speed -= 0.8
                
        elif na_grama and self.speed > 120:
            # Tentar voar na grama faz os pneus derraparem em falso (Perde muita velocidade)
            self.speed -= 1.5 
            
        if keys[pygame.K_a]:
            self.speed -= self.brake_power
            
        # Impede a velocidade de ficar negativa
        if self.speed < 0: self.speed = 0

        # =========================================================
        # 3. POSIÇÃO, FORÇA CENTRÍFUGA E DIREÇÃO (CORRIGIDO)
        # =========================================================
        self.position += self.speed * 0.005
        percentual_vel = self.speed / self.max_speed

        # Inicializa a força zerada para garantir segurança absoluta nas retas
        forca_centrifuga = 0.0

        # A força só é calculada se a pista NÃO for uma reta (intensidade diferente de zero)
        if abs(curve_intensity) > 0.001:
            # Multiplica pelo quadrado da velocidade percentual (Física de Arcade)
            forca_centrifuga = (percentual_vel ** 1.04) * curve_intensity * 1.4
            
            # --- APLICA A FORÇA CENTRÍFUGA DIRETO NO CARRO ---
            # Joga o carro para fora da curva automaticamente
            self.player_x -= forca_centrifuga

            # --- ARRASTO DE CURVA ---
            # Reduz a velocidade devido ao atrito dos pneus tentando segurar o chassi
            if self.speed > 100:
                fator_arrasto = 7.0 
                self.speed -= abs(forca_centrifuga) * fator_arrasto

        # --- A MÁGICA DA TRAVA DO VOLANTE (COLISÃO) ---
        if self.speed > 10 and not steering_locked: 
            
            # --- LÓGICA DE DIREÇÃO (Novo Atributo) ---
            target_steering = 0.0
            
            # =========================================================
            # CONTROLE DE DIREÇÃO DO JOGADOR COM RETORNO DINÂMICO
            # =========================================================
            if keys[pygame.K_LEFT]: 
                target_steering = -self.max_steering
                self.steering += (target_steering - self.steering) * self.steering_speed
            elif keys[pygame.K_RIGHT]: 
                target_steering = self.max_steering
                self.steering += (target_steering - self.steering) * self.steering_speed
            else:
                target_steering = 0.0
                # Quando solta o botão, o retorno é 3.5x mais rápido (Fim do efeito gelo)
                self.steering += (target_steering - self.steering) * (self.steering_speed * 3.5)

            # --- A MÁGICA DA AGILIDADE LATERAL (CORRIGIDA) ---
            # Desvinculamos a direção pura da aceleração do motor!
            percentual_vel = self.speed / self.max_speed
            
            # Criamos uma curva suave: O carro tem sempre pelo menos 45% de agilidade garantida 
            # pelas molas da suspensão, mais o bónus da velocidade atual.
            fator_esterco = 0.45 + (percentual_vel * 0.55) 
            
            # Aplica o movimento lateral
            self.player_x += self.steering * fator_esterco * 1.35
            
        elif steering_locked:
            self.current_steering = 0
            
        # Trava para o carro não sair voando muito além da grama
        self.player_x = max(-1.5, min(1.5, self.player_x))

        # 4. Áudio do Motor
        if self.motor_sound:
            # Trava de segurança: impede que o RPM passe de 1.0 no cálculo do áudio
            rpm = min(1.0, self.speed / self.limite_marchas[self.marcha_atual]) 
            
            self.motor_sound.set_gain(0.2 + (rpm * 0.8)) # Volume
            
            # --- MÁGICA DO PITCH (Menos agudo) ---
            # Reduzimos o multiplicador de (rpm * 1.2) para (rpm * 0.5)
            # O pitch base é 0.8. No talo (rpm 1.0), ele vai para 1.3 (mais o bônus de acelerar).
            # Isso deixa o som muito mais "pesado" e realista no limite!
            self.motor_sound.set_pitch(0.5 + (rpm * 1) + (0.05 if keys[pygame.K_s] else 0))

        # ==========================================
        # 5. ÁUDIO DE DERRAPAGEM (PITCH E FADE DINÂMICOS)
        # ==========================================
        if self.skid_sound:
            intensidade_alvo = 0.0
            pitch_alvo = 1.0

            # 1. Cantando Pneu na Curva
            if abs(curve_intensity) > 0.15 and self.speed > 150 and (keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]):
                # Calcula o quão extrema é a curva e a velocidade
                fator_curva = min(1.0, (abs(curve_intensity) - 0.15) / 0.85)
                fator_vel = self.speed / self.max_speed
                
                # A intensidade (volume) sobe se estiver muito rápido e virando muito
                intensidade_alvo = min(1.0, fator_curva + fator_vel)
                
                # O MÁGICO PITCH: Mais rápido e curva mais forte = Pneu grita mais fino!
                pitch_alvo = 0.8 + (fator_vel * 0.7) + (fator_curva * 0.5)

            # 2. Cantando no Freio
            elif keys[pygame.K_a] and self.speed > 100:
                fator_vel = self.speed / self.max_speed
                intensidade_alvo = fator_vel
                # O freio tem um som um pouco mais grave e arrastado
                pitch_alvo = 0.6 + (fator_vel * 0.5)

            # 3. Derrapando na Grama
            elif na_grama and self.speed > 80:
                intensidade_alvo = 0.6
                pitch_alvo = 0.5 + (self.speed / self.max_speed) * 0.3

            # --- O NOSSO FADE IN E FADE OUT PERSONALIZADO ---
            # Se for para aumentar o som (Fade In), ele sobe rápido (0.15).
            # Se for para calar o som (Fade Out), ele desce um pouco mais lento (0.05).
            velocidade_fade = 0.15 if intensidade_alvo > self.skid_gain_atual else 0.05
            self.skid_gain_atual += (intensidade_alvo - self.skid_gain_atual) * velocidade_fade
            
            # Limita o volume máximo para 40% (0.4) para não abafar o motor
            volume_final = self.skid_gain_atual * 0.4
            
            self.skid_sound.set_gain(volume_final)
            
            # Só atualiza a afinação se o som estiver alto o suficiente para ouvir
            if volume_final > 0.01: 
                self.skid_sound.set_pitch(pitch_alvo)

    def tingir_carroceria(self, superficie, mapa_cor):
        """
        Algoritmo de Substituição de Paleta Cirúrgico.
        Encontra os 4 tons exatos de azul do PNG original e substitui-os
        pela paleta personalizada da equipa definida no JSON.
        """
        if not superficie or not mapa_cor:
            return superficie
            
        # Cria uma cópia e garante que o formato de pixel suporta indexação de cores
        imagem_nova = superficie.copy()
        
        # 1. Definição dos 4 azuis fixos do PNG original (em RGB)
        azul_puro     = (0, 0, 255)       # 0000FF
        azul_escuro   = (0, 0, 148)       # 000094
        azul_medio    = (106, 148, 189)   # 6A94BD
        azul_claro    = (189, 222, 255)   # BDDEFF
        
        # 2. Extração das novas cores mapeadas vindas do JSON
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
        
        # Abrimos o PixelArray
        px_array = pygame.PixelArray(imagem_nova)
        
        for cor_antiga, cor_nova in conversoes.items():
            cor_antiga_mapeada = imagem_nova.map_rgb(cor_antiga)
            cor_nova_mapeada = imagem_nova.map_rgb(cor_nova)
            
            # Executa a substituição em lote dos inteiros de 32 bits
            px_array.replace(cor_antiga_mapeada, cor_nova_mapeada)
            
        px_array.close()
        return imagem_nova

    def ajustar_atributos_equipe(self, dados_equipe):
        """
        Atualiza as propriedades do carro com base no JSON da equipe.
        """
        direcao_equipe = dados_equipe.get("direcao", 3.0)
        self.steering_speed = 0.05 + (direcao_equipe * 0.02)
        self.max_steering = 0.025 + (direcao_equipe * 0.003)
        
        lista_marchas = dados_equipe.get("forca_marchas", [1.6, 1.3, 1.05, 0.88, 0.75, 0.65, 0.58])
        
        self.forca_marchas = {
            1: lista_marchas[0],
            2: lista_marchas[1],
            3: lista_marchas[2],
            4: lista_marchas[3],
            5: lista_marchas[4],
            6: lista_marchas[5],
            7: lista_marchas[6]
        }

        # --- CORREGIDO: LEITURA COMPATÍVEL COM O SCRIPT ---
        mapa_cor = dados_equipe.get("mapa_cor", None)
        
        if mapa_cor:
            # Aplica o tingimento usando a cópia modificada
            self.volante_reto = self.tingir_carroceria(self.volante_reto, mapa_cor)
            self.volantes_esq = [self.tingir_carroceria(v, mapa_cor) for v in self.volantes_esq]
            self.volantes_dir = [self.tingir_carroceria(v, mapa_cor) for v in self.volantes_dir]

    def acelerar_neutro(self, keys):
        # Simula o giro do motor (RPM) subindo e caindo no neutro
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.rpm_neutro += 15  # O giro sobe rápido
        else:
            self.rpm_neutro -= 10  # O giro cai rápido quando solta o dedo
            
        # Limita o RPM para não passar do máximo e não ficar negativo
        self.rpm_neutro = max(0, min(self.max_speed, self.rpm_neutro))
        
        # Se você tiver lógica de áudio do motor, aplique o self.rpm_neutro aqui
        # Ex: self.canal_motor.set_volume(0.5 + (self.rpm_neutro / 1000))

    # Adicionamos 'bots' e 'bot_sprites' no final
    def draw_cockpit(self, screen, keys, tempo_atual, track, bots=None, bot_sprites=None, posicao_atual=1):
        # 1. ANIMAÇÃO DOS PNEUS
        if self.speed > 0:
            if self.speed < 50: delay_animacao = 150
            elif self.speed < 100: delay_animacao = 100
            elif self.speed < 170: delay_animacao = 60
            elif self.speed < 250: delay_animacao = 40
            else: delay_animacao = 20

            if tempo_atual - self.animation_timer > delay_animacao:
                self.frame_index += 1
                self.animation_timer = tempo_atual

        # 2. ANIMAÇÃO DO VOLANTE 
        atraso_inicial = 30 
        if keys[pygame.K_LEFT]:
            if self.ultima_direcao == 'dir' and self.volante_frame > 0:
                if tempo_atual > self.volante_timer:
                    self.volante_frame -= 1
                    self.volante_timer = tempo_atual + self.volante_speed
                    if self.volante_frame == 0: self.ultima_direcao = 'reto'
            else:
                if self.ultima_direcao != 'esq' and self.volante_frame == 0:
                    self.ultima_direcao = 'esq'
                    self.volante_timer = tempo_atual + atraso_inicial
                elif self.ultima_direcao == 'esq' and tempo_atual > self.volante_timer and self.volante_frame < 3:
                    self.volante_frame += 1
                    self.volante_timer = tempo_atual + self.volante_speed
                
        elif keys[pygame.K_RIGHT]:
            if self.ultima_direcao == 'esq' and self.volante_frame > 0:
                if tempo_atual > self.volante_timer:
                    self.volante_frame -= 1
                    self.volante_timer = tempo_atual + self.volante_speed
                    if self.volante_frame == 0: self.ultima_direcao = 'reto'
            else:
                if self.ultima_direcao != 'dir' and self.volante_frame == 0:
                    self.ultima_direcao = 'dir'
                    self.volante_timer = tempo_atual + atraso_inicial
                elif self.ultima_direcao == 'dir' and tempo_atual > self.volante_timer and self.volante_frame < 3:
                    self.volante_frame += 1
                    self.volante_timer = tempo_atual + self.volante_speed
        else:
            if tempo_atual > self.volante_timer and self.volante_frame > 0:
                self.volante_frame -= 1
                self.volante_timer = tempo_atual + self.volante_speed
            if self.volante_frame == 0:
                self.ultima_direcao = 'reto'
                
        # 3. SELECIONAR IMAGENS E DESENHAR
        rotacao_atual = self.frame_index % 3 
        if self.ultima_direcao == 'esq' and self.volante_frame > 0:
            volante_atual = self.volantes_esq[self.volante_frame - 1]
            nivel = min(self.volante_frame - 1, len(self.pneus_esq_virando_esq) - 1)
            pneu_esq_img = self.pneus_esq_virando_esq[nivel][rotacao_atual]
            pneu_dir_img = self.pneus_dir_virando_esq[nivel][rotacao_atual]
        elif self.ultima_direcao == 'dir' and self.volante_frame > 0:
            volante_atual = self.volantes_dir[self.volante_frame - 1]
            nivel = min(self.volante_frame - 1, len(self.pneus_esq_virando_dir) - 1)
            pneu_esq_img = self.pneus_esq_virando_dir[nivel][rotacao_atual]
            pneu_dir_img = self.pneus_dir_virando_dir[nivel][rotacao_atual]
        else:
            volante_atual = self.volante_reto
            pneu_esq_img = self.pneus_esq_reto[rotacao_atual]
            pneu_dir_img = self.pneus_dir_reto[rotacao_atual]

        centro_x, fundo_y, margem = WIDTH // 2, HEIGHT, 20

        screen.blit(pneu_esq_img, (centro_x - 180 - pneu_esq_img.get_width(), fundo_y - 80))
        screen.blit(pneu_dir_img, (centro_x + 180, fundo_y - 80)) 
        screen.blit(volante_atual, (centro_x - (volante_atual.get_width() // 2), fundo_y - volante_atual.get_height()))

       # ==========================================
        # 4. PAINEL: CONTA-GIROS (RPM) E VELOCIDADE
        # ==========================================
        centro_relogio_x, centro_relogio_y = margem + 150, margem + 120
        
        # --- A MÁGICA DO RPM ---
        limite_atual = self.limite_marchas[self.marcha_atual]
        
        # Se a velocidade for 0 (no Countdown), o ponteiro lê o giro falso do motor!
        if self.speed == 0 and hasattr(self, 'rpm_neutro'):
            porcentagem_rpm = self.rpm_neutro / self.max_speed
        else:
            porcentagem_rpm = self.speed / limite_atual
            
        # Marcha lenta (Idle): O ponteiro nunca cai para o zero absoluto
        if porcentagem_rpm < 0.1:
            porcentagem_rpm = 0.1
            
        # Trava de segurança: Se o carro embalar numa descida além da marcha, o ponteiro não dá uma volta de 360º!
        porcentagem_rpm = min(1.05, porcentagem_rpm) 

        # O ponteiro vai de 180º (Esquerda) até 0º (Direita)
        angulo_ponteiro = math.pi - (porcentagem_rpm * math.pi)
        ponta_x = centro_relogio_x + math.cos(angulo_ponteiro) * 60
        ponta_y = centro_relogio_y - math.sin(angulo_ponteiro) * 60

        # Muda a cor da ponta do ponteiro para VERMELHO se estiver no "Redline" (pedindo marcha)
        cor_ponteiro = (255, 0, 0) if porcentagem_rpm > 0.95 else (255, 200, 0)

        # Desenha a linha do ponteiro e o pino central
        pygame.draw.line(screen, cor_ponteiro, (centro_relogio_x, centro_relogio_y), (ponta_x, ponta_y), 5)
        pygame.draw.circle(screen, (20, 20, 20), (centro_relogio_x, centro_relogio_y), 10)

        # ==========================================
        # TEXTOS DO HUD (Design Moderno)
        # ==========================================
        
        # 1. Velocímetro e Transmissão (Deslocados um pouco para baixo)
        texto_vel = self.font.render(f"{int(self.speed)} KM/H", True, WHITE)
        cor_trans = (0, 255, 0) if self.transmissao == "AUTO" else (255, 50, 50)
        texto_trans = pygame.font.SysFont('Arial', 20, bold=True).render(self.transmissao, True, cor_trans)
        
        screen.blit(texto_vel, (centro_relogio_x - 45, centro_relogio_y + 40))
        screen.blit(texto_trans, (centro_relogio_x - 30, centro_relogio_y + 70))

        # 2. INDICADOR DE MARCHA (GEAR)
        # Colocamos um número GRANDE bem no meio da parte de baixo do círculo do relógio
        fonte_marcha = pygame.font.SysFont('Arial', 45, bold=True)
        texto_marcha = fonte_marcha.render(str(self.marcha_atual), True, (255, 200, 0))
        
        # Centraliza o número exatamente no meio do eixo X do relógio
        pos_x_marcha = centro_relogio_x - (texto_marcha.get_width() // 2)
        pos_y_marcha = centro_relogio_y + 1 # Fica logo abaixo do pino do ponteiro
        
        screen.blit(texto_marcha, (pos_x_marcha, pos_y_marcha))

        # ==========================================
        # 5. RETROVISOR (VISÃO TRASEIRA)
        # ==========================================
        retro_w = int(WIDTH // 1.5)
        retro_h = 120
        retro_x = (WIDTH - retro_w) // 2
        retro_y = 20
        
        mini_screen = pygame.Surface((retro_w, retro_h))
        
        # --- MÁGICA 1: LERP NO BALANÇO DO ESPELHO ---
        # O reflexo segue o seu carro com 10% de atraso (0.1). 
        # Isso absorve tremedeiras de batidas e do teclado!
        self.retro_sway_suave += (self.player_x - self.retro_sway_suave) * 0.1
            
        try:
            bg_retro = pygame.image.load("images/bg_rio.png").convert()
            bg_retro = pygame.transform.scale(bg_retro, (retro_w, retro_h))
            mini_screen.blit(bg_retro, (0, 0))
        except:
            mini_screen.fill((135, 206, 235)) 
            
        pos_frac = self.position % 1
        cam_h = retro_h // 2  
        dx_retro = 0
        curva_x_retro = 0
        
        bots_no_espelho = []
        if bots:
            for bot in bots:
                dist_behind = (self.position - bot["pos"]) % track.total_track_length
                if 0 < dist_behind < 50: 
                    bots_no_espelho.append((dist_behind, bot))
        
        lista_desenho_espelho = []
        
        for n in range(0, 20): 
            z_near = max(0.1, n + pos_frac)
            z_far = n + 1 + pos_frac
            
            p_near = cam_h / z_near
            p_far = cam_h / z_far
            y_near = (retro_h // 2) + p_near
            y_far = (retro_h // 2) + p_far
            width_near = p_near * 8
            width_far = p_far * 8
            
            pos_passada = (self.position - n) % track.total_track_length
            curva_n_retro = 0
            dist_check = 0
            for seg in track.track_map:
                dist_check += seg["length"]
                if pos_passada < dist_check:
                    curva_n_retro = -seg["curve"] * 8.0 
                    break
            
            dx_retro += curva_n_retro
            curva_x_retro += dx_retro

            # --- MÁGICA 2: USAMOS O SWAY SUAVE PARA CENTRALIZAR A PISTA ---
            fator_cam_retro = 8
            centro_near = (retro_w // 2) + ((curva_x_retro - dx_retro) * p_near) - (self.retro_sway_suave * p_near * fator_cam_retro)
            centro_far = (retro_w // 2) + (curva_x_retro * p_far) - (self.retro_sway_suave * p_far * fator_cam_retro)

            # (Desenho das zebras e asfalto continua igual...)
            color_road = GRAY_DARK if (n - int(self.position)) % 6 > 3 else GRAY_LIGHT
            color_grass = GREEN_DARK if (n - int(self.position)) % 6 > 3 else GREEN_LIGHT
            color_zebra = RED if (n - int(self.position)) % 6 > 3 else WHITE
            pygame.draw.rect(mini_screen, color_grass, (0, y_far, retro_w, max(1, y_near - y_far + 1)))
            pygame.draw.polygon(mini_screen, color_road, [(centro_near - width_near, y_near), (centro_near + width_near, y_near), (centro_far + width_far, y_far), (centro_far - width_far, y_far)])
            pygame.draw.polygon(mini_screen, color_zebra, [(centro_near - width_near - (width_near*0.2), y_near), (centro_near - width_near, y_near), (centro_far - width_far, y_far), (centro_far - width_far - (width_far*0.2), y_far)])
            pygame.draw.polygon(mini_screen, color_zebra, [(centro_near + width_near, y_near), (centro_near + width_near + (width_near*0.2), y_near), (centro_far + width_far + (width_far*0.2), y_far), (centro_far + width_far, y_far)])
            
            # --- MÁGICA 3: RENDERIZAÇÃO DOS BOTS NO RETROVISOR ---
            for dist, bot in bots_no_espelho:
                if int(dist) == n:
                    # ---> LÊ A FÍSICA REAL DO VOLANTE DO BOT <---
                    # O ".get" pega o valor do steer_real que criámos no main.py
                    forca_volante = bot.get("steer_real", 0)
                    
                    # Se ele estiver fazendo força real para mudar de faixa, vira o sprite!
                    if forca_volante < -0.15: 
                        direcao = "esq"  # Ele está virando fisicamente para a esquerda
                    elif forca_volante > 0.15: 
                        direcao = "dir"  # Ele está virando fisicamente para a direita
                    else: 
                        direcao = "reto" # Ele está com o volante reto na pista
                    
                    chave = f"front_{direcao}"
                    img = None
                    
                    if bot_sprites and bot["pasta"] in bot_sprites:
                        img = bot_sprites[bot["pasta"]][chave][bot.get("frame_idx", 0)]
                    
                    if img:
                        img_w, img_h = img.get_width(), img.get_height()
                        bot_h = int(width_near * 0.22) 
                        bot_w = int(bot_h * (img_w / img_h))
                        
                        bx = centro_near + (bot["x"] * width_near) - (bot_w // 2)
                        by = y_near - bot_h
                        
                        img_espelhada = pygame.transform.flip(img, True, False)
                        lista_desenho_espelho.append((img_espelhada, bx, by, bot_w, bot_h, dist))

        # ==========================================
        # ORDENAÇÃO EXATA DE PROFUNDIDADE (Z-SORT)
        # ==========================================
        # Apagamos o lista_desenho_espelho.reverse()!
        # Agora o código ordena do mais LONGE (maior distância) para o mais PERTO (menor distância)
        lista_desenho_espelho.sort(key=lambda item: item[5], reverse=True)

        # Cola os bots e desenha o retrovisor final na tela
        for img, bx, by, bw, bh, dist in lista_desenho_espelho:
            if bw > 0 and bh > 0:
                img_redim = pygame.transform.scale(img, (bw, bh))
                mini_screen.blit(img_redim, (bx, by))

        screen.blit(mini_screen, (retro_x, retro_y))
        screen.blit(self.retrovisor_img, (retro_x, retro_y))

        # ==========================================
        # 6.INDICADOR DE POSIÇÃO (Abaixo do Retrovisor)
        # ==========================================
        # Usamos a mesma lógica de centralização do retrovisor
        retro_w = int(WIDTH // 1.5)
        retro_h = 120
        retro_x = (WIDTH - retro_w) // 2
        retro_y = 20
        
        # Criamos o texto (ex: 1ST, 2ND, 3RD, 4TH...)
        suffix = "TH"
        if posicao_atual == 1: suffix = "ST"
        elif posicao_atual == 2: suffix = "ND"
        elif posicao_atual == 3: suffix = "RD"
        
        fonte_pos = pygame.font.SysFont('Arial', 40, bold=True)
        texto_pos = fonte_pos.render(f"{posicao_atual}{suffix}", True, (255, 255, 0)) # Amarelo
        
        # Centraliza o texto exatamente abaixo da moldura do retrovisor
        pos_x = (WIDTH // 2) - (texto_pos.get_width() // 2)
        pos_y = retro_y + retro_h + 5 # 5 pixels de folga abaixo da moldura
        
        # Desenha uma pequena sombra preta para dar leitura
        texto_sombra = fonte_pos.render(f"{posicao_atual}{suffix}", True, (0, 0, 0))
        screen.blit(texto_sombra, (pos_x + 2, pos_y + 2))
        screen.blit(texto_pos, (pos_x, pos_y))

        # ==========================================
        # 7. CRONÔMETRO E VOLTAS (HUD Lateral)
        # ==========================================
        # Posicionamos no canto superior direito
        cor_hud = (255, 255, 255)
        cor_destaque = (255, 200, 0)
        
        # Função rápida para formatar 00:00.00
        def formatar_tempo(t):
            mins = int(t // 60)
            segs = int(t % 60)
            ms = int((t * 100) % 100)
            return f"{mins:02}:{segs:02}.{ms:02}"

        x_hud, y_hud = WIDTH - 220, 20
        # Fundo preto semi-transparente para o HUD (opcional, mas fica profissional)
        pygame.draw.rect(screen, (0, 0, 0, 150), (x_hud - 10, y_hud - 5, 220, 130))
        
        screen.blit(self.font.render(f"LAP: {self.laps_completed + 1}", True, cor_hud), (x_hud, y_hud))
        screen.blit(self.font.render(f"TIME: {formatar_tempo(self.current_lap_time)}", True, cor_hud), (x_hud, y_hud + 30))
        screen.blit(self.font.render(f"LAST: {formatar_tempo(self.last_lap_time)}", True, cor_hud), (x_hud, y_hud + 60))
        screen.blit(self.font.render(f"BEST:", True, cor_destaque), (x_hud, y_hud + 90))
        screen.blit(self.font.render(formatar_tempo(self.best_lap_time), True, cor_destaque), (x_hud + 80, y_hud + 90))

        # ==========================================
        # 8. MINIMAPA (RADAR OVAL)
        # ==========================================
        mapa_w, mapa_h = 200, 120
        mapa_x, mapa_y = 1000, 250 # Canto superior esquerdo
        
        # Fundo do minimapa (Preto semi-transparente)
        # Como o Pygame antigo não aceita transparência direto no rect, criamos uma Surface
        s_mapa = pygame.Surface((mapa_w, mapa_h), pygame.SRCALPHA)
        s_mapa.fill((0, 0, 0, 150))
        screen.blit(s_mapa, (mapa_x, mapa_y))
        
        # Centro e Raios da elipse
        centro_mx = mapa_x + (mapa_w // 2)
        centro_my = mapa_y + (mapa_h // 2)
        raio_x = (mapa_w // 2) - 15
        raio_y = (mapa_h // 2) - 15
        
        # Desenha a linha da pista (Asfalto do mapa)
        pygame.draw.ellipse(screen, GRAY_LIGHT, (centro_mx - raio_x, centro_my - raio_y, raio_x * 2, raio_y * 2), 3)
        
        # Função interna para pegar a coordenada X e Y no radar
        def get_radar_pos(posicao_z):
            # Descobre qual a % da volta o carro completou
            porcentagem = (posicao_z % track.total_track_length) / track.total_track_length
            
            # Converte a % em um ângulo (Começando no topo = -90 graus)
            angulo = (porcentagem * 2 * math.pi) - (math.pi / 2)
            
            # Geometria para mapear o ângulo na borda da elipse
            px = centro_mx + math.cos(angulo) * raio_x
            py = centro_my + math.sin(angulo) * raio_y
            return px, py
        
        # 1. Desenha os BOTS (Bolinhas Vermelhas)
        if bots:
            for bot in bots:
                bx, by = get_radar_pos(bot["pos"])
                pygame.draw.circle(screen, (255, 50, 50), (int(bx), int(by)), 3)
                
        # 2. Desenha o SEU CARRO (Bolinha Verde Maior e Piscante)
        px, py = get_radar_pos(self.position)
        
        # Efeito piscante: pisca verde e branco a cada 200 milissegundos
        if (tempo_atual // 200) % 2 == 0:
            pygame.draw.circle(screen, (0, 255, 0), (int(px), int(py)), 5)
        else:
            pygame.draw.circle(screen, WHITE, (int(px), int(py)), 5)

        # =========================================================
        # 9. DEBUG VISUAL: VELOCIDADE DOS 3 BOTS À FRENTE
        # =========================================================
        if bots:
            bots_a_frente = []
            for bot in bots:
                # Calcula a distância usando a posição do seu carro
                dist_relativa = (bot["pos"] - self.position) % track.total_track_length
                
                # Só regista se estiver na sua frente (até meia pista de distância)
                if 0 < dist_relativa < (track.total_track_length / 2):
                    bots_a_frente.append((dist_relativa, bot))

            # Ordena a lista pela distância (do mais perto para o mais longe)
            bots_a_frente.sort(key=lambda x: x[0])
            top_3_frente = bots_a_frente[:3]

            fonte_debug = pygame.font.SysFont('Arial', 20, bold=True)
            cor_vermelha = (255, 50, 50)
            
            # Posiciona logo abaixo do minimapa (x=1000, e desce o y para 400)
            pos_x_debug = 1000 
            pos_y_debug = 400 

            # Desenha o Título
            titulo_debug = fonte_debug.render("BOTS À FRENTE:", True, cor_vermelha)
            screen.blit(titulo_debug, (pos_x_debug, pos_y_debug - 25))

            # Desenha as informações dos 3 bots
            for i, (dist, bot) in enumerate(top_3_frente):
                vel_bot = int(bot["speed"])
                dist_bot = int(dist)
                nome_bot = bot.get("pasta", "Bot").capitalize()
                
                texto_linha = f"{i+1}. {nome_bot}: {vel_bot}km/h [{dist_bot}m]"
                surf_texto = fonte_debug.render(texto_linha, True, cor_vermelha)
                screen.blit(surf_texto, (pos_x_debug, pos_y_debug + (i * 25)))


    ## LOGICA DA CRONOMETRAGEM
    def update_timer(self, total_track_length, lap_limit):
        # Só atualiza o tempo se a corrida não tiver terminado
        if self.laps_completed < lap_limit:
            agora = pygame.time.get_ticks()
            self.current_lap_time = (agora - self.lap_start_tick) / 1000.0

            volta_atual = int(self.position // total_track_length)
            if volta_atual > self.laps_completed:
                self.last_lap_time = self.current_lap_time
                
                if self.best_lap_time == 0 or self.last_lap_time < self.best_lap_time:
                    self.best_lap_time = self.last_lap_time
                
                self.laps_completed = volta_atual
                self.lap_start_tick = agora

    def parar_audios(self):
        # Muta o motor e o pneu do jogador
        if hasattr(self, 'motor_sound') and self.motor_sound:
            self.motor_sound.set_gain(0)
        if hasattr(self, 'skid_sound') and self.skid_sound:
            self.skid_sound.set_gain(0)

    def cleanup(self):
        if self.motor_sound: oalQuit()