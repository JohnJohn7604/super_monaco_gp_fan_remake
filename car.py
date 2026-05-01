# car.py
import pygame
import math
from openal import oalOpen, oalQuit
from settings import *
from utils import carregar_img

class Car:
    def __init__(self):
        self.font = pygame.font.SysFont('Arial', 30, bold=True)

        # --- SISTEMA DE TEMPOS E VOLTAS ---
        self.laps_completed = 0
        self.lap_start_tick = pygame.time.get_ticks()
        self.current_lap_time = 0
        self.last_lap_time = 0
        self.best_lap_time = 0

        # Física 
        self.speed = 0
        self.max_speed = 330 
        self.accel = 0.5     
        self.friction = 0.00003
        self.brake_power = 1.0
        self.position = 0
        self.player_x = 0.0 

        #Variável para suavizar o volante ---
        self.direcao_atual = 0.0
        self.tempo_folga = 0 # <-- NOVO: Cronômetro do delay do volante
        
        # Marchas
        self.transmissao = "AUTO"  
        self.marcha_atual = 1
        self.max_marchas = 7
        self.timer_marcha = 0      
        self.limite_marchas = {1: 60, 2: 110, 3: 160, 4: 210, 5: 260, 6: 300, 7: 335}
        self.torque_marchas = {1: 1.5, 2: 0.5, 3: 0.5, 4: 0.3, 5: 0.25, 6: 0.1, 7: 0.15}
        
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
        

    # Adicionamos o steering_locked=False no final
    def update_physics(self, keys, tempo_atual, curve_intensity, steering_locked=False):
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
            taxa_aceleracao = forca_motor * (1.5 - (self.speed / self.max_speed))
            self.speed += taxa_aceleracao
            
            # --- A MÁGICA DO ATOLAMENTO ---
            # A grama agora "agarra" os pneus constantemente enquanto você acelera!
            # Se a força da marcha for menor que 1.2, o carro perde velocidade e morre.
            if na_grama:
                self.speed -= 0.5
        else:
            # Soltou o acelerador: freio motor e inércia do vento
            atrito_terreno = 1.2 if na_grama else (0.05 + (self.speed / self.max_speed) * 0.2)
            self.speed -= atrito_terreno 

        # --- Limites e Corte de Giro ---
        limite_atual = self.limite_marchas[self.marcha_atual]
        if not na_grama and self.speed > limite_atual:
            # Chegou no limite da marcha no asfalto (Corta o giro)
            self.speed = limite_atual - 2
        elif na_grama and self.speed > 120:
            # Tentar voar na grama faz os pneus derraparem em falso (Perde muita velocidade)
            self.speed -= 1.5 
            
        if keys[pygame.K_a]:
            self.speed -= self.brake_power
            
        # Impede a velocidade de ficar negativa ou passar do limite absoluto
        if self.speed < 0: self.speed = 0
        if self.speed > self.max_speed: self.speed = self.max_speed

        # 3. Posição, Força Centrífuga e Direção
        self.position += self.speed * 0.005
        percentual_vel = self.speed / self.max_speed

        forca_centrifuga = (percentual_vel ** 2) * curve_intensity * 2.8
        self.player_x -= forca_centrifuga

        if abs(curve_intensity) > 0 and self.speed > 100:
            fator_arrasto = 5.0 
            self.speed -= abs(forca_centrifuga) * fator_arrasto

        # --- A MÁGICA DA TRAVA DO VOLANTE (COLISÃO) ---
        if self.speed > 10 and not steering_locked: 
            poder_maximo = 0.03 + (percentual_vel * 0.015)
            peso_direcao = 0.005 
            delay_frames = 3 
            
            if keys[pygame.K_LEFT]: 
                self.tempo_folga += 1
                if self.tempo_folga > delay_frames: self.direcao_atual -= peso_direcao
            elif keys[pygame.K_RIGHT]: 
                self.tempo_folga += 1
                if self.tempo_folga > delay_frames: self.direcao_atual += peso_direcao
            else:
                self.tempo_folga = 0 
                if self.direcao_atual > 0:
                    self.direcao_atual -= peso_direcao
                    if self.direcao_atual < 0: self.direcao_atual = 0
                elif self.direcao_atual < 0:
                    self.direcao_atual += peso_direcao
                    if self.direcao_atual > 0: self.direcao_atual = 0

            self.direcao_atual = max(-poder_maximo, min(poder_maximo, self.direcao_atual))
            self.player_x += self.direcao_atual
        
        elif steering_locked:
            # Se bateram na sua traseira, você solta o volante de susto!
            self.tempo_folga = 0

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
        
        # --- NOVO: IMAGEM DO RETROVISOR ---
        # DICA: Crie um PNG transparente no meio, com apenas a borda de plástico!
        tamanho_retrovisor = (WIDTH // 1.5, 120)
        self.retrovisor_img = carregar_img("images/cockpit/retrovisor.png", tamanho_retrovisor)

       # ==========================================
        # 4. PAINEL: CONTA-GIROS (RPM) E VELOCIDADE
        # ==========================================
        centro_relogio_x, centro_relogio_y = margem + 150, margem + 120
        
        # --- A MÁGICA DO RPM ---
        # RPM é a porcentagem da sua velocidade atual em relação ao limite da marcha engatada.
        limite_atual = self.limite_marchas[self.marcha_atual]
        porcentagem_rpm = self.speed / limite_atual
        
        # Marcha lenta (Idle): O ponteiro nunca cai para o zero absoluto se o carro estiver parado
        if self.speed == 0:
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
        # Mudamos os valores para o vidro ficar EXATAMENTE do tamanho da sua moldura!
        retro_w = int(WIDTH // 1.5)
        retro_h = 120
        retro_x = (WIDTH - retro_w) // 2
        retro_y = 20
        
        mini_screen = pygame.Surface((retro_w, retro_h))
        
        # --- NOVO: O CÉU DO RETROVISOR ---
        # Ele tenta carregar e espremer a sua imagem bg_rio para caber no espelho
        try:
            bg_retro = pygame.image.load("images/bg_rio.png").convert()
            bg_retro = pygame.transform.scale(bg_retro, (retro_w, retro_h))
            mini_screen.blit(bg_retro, (0, 0))
        except:
            # Plano B: Se der erro na imagem, pinta de azul claro para não ficar preto!
            mini_screen.fill((135, 206, 235)) 
            
        pos_frac = self.position % 1
        cam_h = retro_h // 2  
        dx_retro = 0
        curva_x_retro = 0
        
        # 1. Filtra quem está atrás de você
        bots_no_espelho = []
        if bots:
            for bot in bots:
                dist_behind = (self.position - bot["pos"]) % track.total_track_length
                # Mostra no espelho se estiver a até 20 metros atrás
                if 0 < dist_behind < 50: 
                    bots_no_espelho.append((dist_behind, bot))
        
        lista_desenho_espelho = []
        
        for n in range(0, 20): 
            # 1. DIREÇÃO: O sinal de '+' faz o chão se AFASTAR de você
            z_near = n + pos_frac
            z_far = n + 1 + pos_frac
            
            # Trava de segurança importantíssima agora que usamos n=0
            if z_near <= 0.1: 
                z_near = 0.1
            
            p_near = cam_h / z_near
            p_far = cam_h / z_far
            
            y_near = (retro_h // 2) + p_near
            y_far = (retro_h // 2) + p_far
            
            width_near = p_near * 8
            width_far = p_far * 8
            
            # 2. OLHANDO PARA O PASSADO: Lemos os trechos que ficaram para trás
            pos_passada = (self.position - n) % track.total_track_length
            curva_n_retro = 0
            dist_check = 0
            for seg in track.track_map:
                dist_check += seg["length"]
                if pos_passada < dist_check:
                    # O sinal de '-' inverte a curva magicamente!
                    curva_n_retro = -seg["curve"] * 8.0 #o quao a pista vai dobrar nas curvaS
                    break
            
            dx_retro += curva_n_retro
            curva_x_retro += dx_retro

            # 3. LÓGICA DO REFLEXO: O player_x é somado (+) em vez de subtraído
            fator_cam_retro = 8
            centro_near = (retro_w // 2) + ((curva_x_retro - dx_retro) * p_near) - (self.player_x * p_near * fator_cam_retro)
            centro_far = (retro_w // 2) + (curva_x_retro * p_far) - (self.player_x * p_far * fator_cam_retro)

            # As cores alternam com o sinal de '-' para acompanhar a pista fugindo
            color_road = GRAY_DARK if (n - int(self.position)) % 6 > 3 else GRAY_LIGHT
            color_grass = GREEN_DARK if (n - int(self.position)) % 6 > 3 else GREEN_LIGHT
            color_zebra = RED if (n - int(self.position)) % 6 > 3 else WHITE
            
            # Desenha a Grama
            pygame.draw.rect(mini_screen, color_grass, (0, y_far, retro_w, max(1, y_near - y_far + 1)))
            
            # Desenha o Asfalto
            pygame.draw.polygon(mini_screen, color_road, [
                (centro_near - width_near, y_near), (centro_near + width_near, y_near),
                (centro_far + width_far, y_far), (centro_far - width_far, y_far)
            ])
            
            # Desenha as Zebras
            zw_near = width_near * 0.2
            zw_far = width_far * 0.2
            pygame.draw.polygon(mini_screen, color_zebra, [(centro_near - width_near - zw_near, y_near), (centro_near - width_near, y_near), (centro_far - width_far, y_far), (centro_far - width_far - zw_far, y_far)])
            pygame.draw.polygon(mini_screen, color_zebra, [(centro_near + width_near, y_near), (centro_near + width_near + zw_near, y_near), (centro_far + width_far + zw_far, y_far), (centro_far + width_far, y_far)])

            # 2. Captura os bots para desenhar depois do chão
            for dist, bot in bots_no_espelho:
                if int(dist) == n:
                    bot_w = int(width_near * 0.8) 
                    bot_h = int(bot_w * (bot["base_h"] / bot["base_w"]))
                    bx = centro_near + (bot["x"] * width_near) - (bot_w // 2)
                    by = y_near - bot_h
                    
                    # Define a perspectiva frontal
                    if bot["x"] < -0.2: direcao = "esq"
                    elif bot["x"] > 0.2: direcao = "dir"
                    else: direcao = "reto"
                    
                    chave = f"front_{direcao}"
                    img = None
                    if bot_sprites and chave in bot_sprites:
                        img = bot_sprites[chave][bot["frame_idx"]]
                    elif bot_sprites and "front_reto" in bot_sprites:
                        # O BUG ESTAVA AQUI! Mudamos de "rear_reto" para "front_reto".
                        # Agora, se ele não achar a curva, ele usa a vista frontal padrão!
                        img = bot_sprites["front_reto"][bot["frame_idx"]]
                        
                    if img:
                        lista_desenho_espelho.append((img, bx, by, bot_w, bot_h))

        # 3. Cola os carros por cima do asfalto do espelho
        for img, bx, by, bw, bh in lista_desenho_espelho:
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

    def cleanup(self):
        if self.motor_sound: oalQuit()