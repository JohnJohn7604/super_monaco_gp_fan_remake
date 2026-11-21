import random

class BotAI:
    def __init__(self, game):
        # Recebemos a referência do main.py para aceder à pista e ao carro do jogador
        self.game = game

    def atualizar_bots(self, tempo_atual):
        """ Executa toda a lógica de física, tangência e ultrapassagem da IA. """
        
        # Puxa atalhos para não escrever self.game.car o tempo todo
        carro_jogador = self.game.car
        track = self.game.track
        bots = self.game.bots

        # Atalhos de pista e funções (evita lookup repetido no loop)
        total_len = track.total_track_length
        half_len = total_len * 0.5
        get_curve = track.get_curve

        # Estado do jogador calculado 1x por frame
        player_pos = carro_jogador.position
        player_x = carro_jogador.player_x
        player_speed = carro_jogador.speed
        player_max_speed = carro_jogador.max_speed
        jogador_na_pista = -1.0 <= player_x <= 1.0

        if player_x < -0.33:
            linha_jogador = 1
        elif player_x > 0.33:
            linha_jogador = 3
        else:
            linha_jogador = 2

        # Timers e estados globais calculados 1x por frame
        is_volta_0 = (carro_jogador.laps_completed == 0)
        tempo_volta = carro_jogador.current_lap_time
        sprint_largada = is_volta_0 and (tempo_volta < 8)
        largada_linhas = is_volta_0 and (tempo_volta < 15)

        lap_limit = getattr(self.game, 'lap_limit', 1)
        race_finished = getattr(self.game, 'race_finished', False)
        pos_penultima = carro_jogador.laps_completed >= (lap_limit - 1)
        dist_meta = total_len * lap_limit

        # Reseta o combo 1x por frame (e não N vezes dentro do loop)
        if tempo_atual - self.game.timer_combo > 4000:
            self.game.ultrapassagens_combo = 0

        curve_intensity = get_curve(player_pos)
        self.game.steering_locked = False
        menor_distancia_bot = 9999
        jogador_no_vacuo = False
        
        # Pega a curva da pista para o jogador (usado em algumas lógicas)
        curve_intensity = track.get_curve(carro_jogador.position)
        
        self.game.steering_locked = False 
        menor_distancia_bot = 9999 
        jogador_no_vacuo = False

        for bot in bots:
            
            # ---> A MÁGICA DA LARGADA (MODO SPRINT) <---
            sprint_largada = (carro_jogador.laps_completed == 0 and carro_jogador.current_lap_time < 8)

            # 1. Distância Circular Perfeita
            dist_bruta = bot["pos"] - carro_jogador.position
            dist_relativa = dist_bruta % track.total_track_length
            if dist_relativa > track.total_track_length / 2:
                dist_relativa -= track.total_track_length

            # =================================================================
            # 1.2 NOVO: IA DE DEFESA DE POSIÇÃO (BLOQUEIO AGRESSIVO)
            # =================================================================
            # Verifica se é um piloto de elite (aceleração > 4)
            if bot.get("aceleracao", 1) > 4:
                
                # A) RECARGA: Se o bot conseguiu afastar-se mais de 300 metros de nós, recarrega a tentativa!
                if dist_relativa > 40 and bot.get("pode_recarregar_bloqueio", False):
                    bot["bloqueios_disponiveis"] = 1
                    bot["pode_recarregar_bloqueio"] = False # Trava para não recarregar infinitamente
                
                # B) O BLOQUEIO SEGURO: Só tenta fechar se você estiver entre 20m e 65m!
                # Se você chegar a menos de 20 metros, o bot considera que você já está tão perto
                # que tentar fechar a porta causaria um acidente grave, então ele mantém a linha!
                if 20 < dist_relativa < 65 and carro_jogador.speed > bot["speed"] and bot.get("bloqueios_disponiveis", 0) > 0:
                    
                    alvo_bloqueio = carro_jogador.player_x
                    velocidade_fechada = 0.018  # Volante super suave (era 0.04), dando tempo para você reagir!
                    
                    if bot["x"] < alvo_bloqueio:
                        bot["x"] = min(0.8, bot["x"] + velocidade_fechada)
                    elif bot["x"] > alvo_bloqueio:
                        bot["x"] = max(-0.8, bot["x"] - velocidade_fechada)
                        
                    # Se o bot já se alinhou com o seu bico (fechou a porta com sucesso!), gasta a tentativa
                    if abs(bot["x"] - carro_jogador.player_x) < 0.12:
                        bot["bloqueios_disponiveis"] = 0
                        bot["pode_recarregar_bloqueio"] = True

            # 1.3. EVENTO ALEATÓRIO: "FALHA MECÂNICA LÁ NA FRENTE"
            if not bot.get("falha_mecanica", False):
                if 200 < dist_relativa < (track.total_track_length / 2):
                    if random.randint(1, 8500) == 1:
                        bot["falha_mecanica"] = True
                        bot["fim_falha"] = tempo_atual + random.randint(5000, 9000)
            else:
                # O conserto via rádio: quando o relógio passar do tempo, o carro é consertado!
                if tempo_atual > bot.get("fim_falha", 0):
                    bot["falha_mecanica"] = False

            # 2. IA de Curvas Corajosas
            curva_do_bot = track.get_curve(bot["pos"])
            
            if abs(curva_do_bot) > 0.02 and not sprint_largada:

                if dist_relativa > 0:
                    # Bot à FRENTE do jogador: reduz normalmente na curva para permitir disputas
                    multiplicador_curva = 0.43 + (bot["direcao"] * 0.07)
                else:
                    # Bot ATRÁS do jogador: reduz só um pouco (mantém 93% a 98% da velocidade)
                    multiplicador_curva = 0.80 + (bot["direcao"] * 0.008)

                target_speed = bot["max_speed"] * multiplicador_curva
                target_speed = min(bot["max_speed"], target_speed)
                target_speed = max(200, target_speed)
            else:
                target_speed = bot["max_speed"]

            # =========================================================================
            # [ALTERAÇÃO - IA / FINAL LAP]: BÔNUS DE VELOCIDADE APÓS A PENÚLTIMA VOLTA
            # Quando a penúltima volta é completada e a volta final se inicia:
            # Todos os carros que estiverem ATRÁS do jogador ganham +3% de velocidade máxima.
            # Se um bot ultrapassar o jogador, o bônus dele cessa automaticamente.
            # =========================================================================
            pos_penultima = carro_jogador.laps_completed >= (getattr(self.game, 'lap_limit', 1) - 1)
            carro_atras = bot["pos"] < carro_jogador.position
            if pos_penultima and carro_atras and not getattr(self.game, 'race_finished', False):
                target_speed *= 1.03

            # ---> A CORREÇÃO DA FALHA MECÂNICA <---
            # Se o carro quebrou, a velocidade alvo dele cai para 160 km/h!
            # O sistema de freios existente vai desacelerar suavemente até 160 e travar lá, sem dar ré!
            if bot.get("falha_mecanica", False):
                target_speed = min(target_speed, 260.0)

            # ---> RADAR DE FRENAGEM INTELIGENTE <---
            if -45 < dist_relativa < 0 and jogador_na_pista:
                if abs(bot["x"] - player_x) < 0.42:
                    piso_vel = 0 if player_speed < 60 else max(80, player_speed * 0.92)
                    target_speed = min(target_speed, piso_vel)

            # O PEDAL DE FREIO
            if bot["speed"] > target_speed:
                forca_freio = 4.0 + (bot.get("freio", 3) * 0.6)
                bot["speed"] -= forca_freio 

            # =========================================================================
            # 3. ACELERAÇÃO FEROZ + HANDICAP DE BOOST (+4% ACELERAÇÃO)
            # =========================================================================
            forca_motor = 0.25 + (bot["aceleracao"] * 0.1)

            # Verifica se o bot tem maior velocidade máxima que o player e está até 200m atrás
            bot_mais_rapido = bot["max_speed"] > carro_jogador.max_speed
            atras_ate_200m = (-200 <= dist_relativa < 0)

            if bot_mais_rapido and atras_ate_200m:
                forca_motor *= 1.10
            arrancada_grid = (carro_jogador.laps_completed == 0 and carro_jogador.current_lap_time < 8)

            if bot["speed"] < target_speed: 
                if bot["speed"] < 100: 
                    impulso = 1.5 if arrancada_grid else 0.8
                    bot["speed"] += impulso * forca_motor  
                elif bot["speed"] < 200: 
                    impulso = 1.8 if arrancada_grid else 0.5
                    bot["speed"] += impulso * forca_motor  
                elif bot["speed"] < 280: 
                    bot["speed"] += 0.3 * forca_motor  
                else:
                    taxa_acel = 0.6 * (1 - (bot["speed"] / (target_speed + 1)))
                    bot["speed"] += max(0.2 + (bot["aceleracao"] * 0.15), taxa_acel * forca_motor)
                    
            elif bot["speed"] > target_speed + 15: 
                bot["speed"] -= 3.5  
            elif bot["speed"] > target_speed: 
                bot["speed"] -= 0.8 

            # =========================================================================
            # [ALTERAÇÃO - PÓS-CORRIDA]: CARROS A 100 KM/H APÓS CONCLUÍREM A CHEGADA
            # Após o jogador concluir a corrida, qualquer bot que conclua a chegada
            # desacelera suavemente e mantém velocidade de cruzeiro de exatamente 100 km/h.
            # =========================================================================
            dist_meta = track.total_track_length * getattr(self.game, 'lap_limit', 1)
            if bot["pos"] >= dist_meta:
                bot["concluiu_chegada"] = True

            if getattr(self.game, 'race_finished', False) and bot.get("concluiu_chegada", False):
                target_speed = 100.0
                if bot["speed"] > 100.0:
                    bot["speed"] = max(100.0, bot["speed"] - 2.8)
                elif bot["speed"] < 100.0:
                    bot["speed"] = min(100.0, bot["speed"] + 1.2)

            # 4. O SISTEMA DE 3 LINHAS E TANGÊNCIA (RACING LINE)
            if "linha_reta" not in bot:
                bot["linha_reta"] = random.choice([-0.65, -0.21, 0.0, 0.21, 0.65])
            
            curva_futura = track.get_curve(bot["pos"] + 30)
            
            if curva_futura > 0.05: tracado_ideal = -0.65  
            elif curva_futura < -0.05: tracado_ideal = 0.65   
            else: tracado_ideal = bot["linha_reta"] 
            
            target_x = tracado_ideal
            bot["pos"] += bot["speed"] * 0.005 

            # SENSOR DE VÁCUOvacuo
            if 1 < dist_relativa < 25 and carro_jogador.speed > 290:
                if abs(carro_jogador.player_x - bot["x"]) < 0.3: 
                    jogador_no_vacuo = True

            # REGRA DA LARGADA (MANTER AS LINHAS)
            if carro_jogador.laps_completed == 0 and carro_jogador.current_lap_time < 15:
                for outro_bot in bots:
                    if bot == outro_bot: continue
                    dist_bruta_bots = outro_bot["pos"] - bot["pos"]
                    dist_entre_bots = dist_bruta_bots % track.total_track_length
                    if dist_entre_bots > track.total_track_length / 2: dist_entre_bots -= track.total_track_length
                    
                    if abs(dist_entre_bots) < 8:
                        distancia_lateral = bot["x"] - outro_bot["x"]
                        if abs(distancia_lateral) < 0.35:
                            target_x = bot["x"] + (0.3 if distancia_lateral > 0 else -0.3)
            
            # =================================================================
            # 5. TÁTICAS CONTRA O JOGADOR (ANTECIPAÇÃO DE 55M)
            # =================================================================
            if not largada_linhas:
                if 0 < dist_relativa < 60:
                    target_x = tracado_ideal

                elif -55 < dist_relativa < 0 and jogador_na_pista and bot["speed"] > player_speed:
                    # Escolhe a faixa livre longe do jogador
                    if linha_jogador == 2:
                        if curva_futura > 0.05:
                            target_x = 0.65
                        elif curva_futura < -0.05:
                            target_x = -0.65
                        else:
                            target_x = -0.65 if bot["x"] <= player_x else 0.65
                    elif linha_jogador == 1:
                        target_x = 0.65 if curva_futura > 0.05 else 0.15
                    elif linha_jogador == 3:
                        target_x = -0.65 if curva_futura < -0.05 else -0.15

                    # Ganho leve de embalo quando já está fora da linha do jogador
                    if abs(bot["x"] - player_x) > 0.38:
                        bot["speed"] += 0.35

                    # Evasão de emergência a menos de 20m (sempre para o lado com mais espaço)
                    if abs(dist_relativa) < 20 and abs(bot["x"] - player_x) < 0.42:
                        target_x = -0.75 if player_x > 0 else 0.75

            # =================================================================
            # 5. TÁTICAS CONTRA O JOGADOR (ANTECIPAÇÃO DE 65M)
            # =================================================================
            desviando_jogador = False
            evasao_emergencia = False

            if not largada_linhas:
                if 0 < dist_relativa < 60:
                    target_x = tracado_ideal

                elif -65 < dist_relativa < 0 and jogador_na_pista and bot["speed"] > player_speed:
                    desviando_jogador = True

                    # Escolhe a faixa livre longe do jogador
                    if linha_jogador == 2:
                        if curva_futura > 0.05:
                            target_x = 0.65
                        elif curva_futura < -0.05:
                            target_x = -0.65
                        else:
                            target_x = -0.65 if bot["x"] <= player_x else 0.65
                    elif linha_jogador == 1:
                        target_x = 0.65 if curva_futura > 0.05 else 0.25
                    elif linha_jogador == 3:
                        target_x = -0.65 if curva_futura < -0.05 else -0.25

                    # Ganho leve de embalo apenas quando já está fora da linha do jogador
                    if abs(bot["x"] - player_x) > 0.42:
                        bot["speed"] += 0.35

                    # Evasão de emergência a menos de 28m (sempre para o lado com mais espaço)
                    if abs(dist_relativa) < 28 and abs(bot["x"] - player_x) < 0.45:
                        evasao_emergencia = True
                        target_x = -0.78 if player_x > 0 else 0.78

            # =================================================================
            # 6. RADAR DE TRÁFEGO IA vs IA (RESPEITANDO O DESVIO DO JOGADOR)
            # =================================================================
            if not desviando_jogador:
                menor_dist_frente = 55.0
                bot_bloqueando = None

                for outro_bot in bots:
                    if bot is outro_bot:
                        continue

                    dist_entre_bots = (outro_bot["pos"] - bot["pos"]) % total_len
                    if dist_entre_bots > half_len:
                        dist_entre_bots -= total_len

                    # Separação lateral imediata lado a lado
                    if abs(dist_entre_bots) < 8:
                        distancia_lateral = bot["x"] - outro_bot["x"]
                        if abs(distancia_lateral) < 0.36:
                            novo_x = bot["x"] + (0.32 if distancia_lateral >= 0 else -0.32)
                            if not (-25 < dist_relativa < 5 and abs(novo_x - player_x) < 0.42):
                                target_x = novo_x

                    # Identifica APENAS o carro mais próximo à frente para desviar limpo
                    elif not largada_linhas and 0 < dist_entre_bots < menor_dist_frente:
                        if abs(bot["x"] - outro_bot["x"]) < 0.45:
                            menor_dist_frente = dist_entre_bots
                            bot_bloqueando = outro_bot

                if bot_bloqueando is not None:
                    novo_x = -0.65 if bot_bloqueando["x"] > 0 else 0.65
                    if not (-35 < dist_relativa < 5 and abs(novo_x - player_x) < 0.42):
                        target_x = novo_x

            # 6.5. COMBO DE ULTRAPASSAGEM (CONTAGEM ÚNICA POR CARRO)
            if -5 < dist_relativa < 0 and bot["speed"] < player_speed:
                if tempo_atual - bot.get("ultimo_combo_tick", 0) > 5000:
                    bot["ultimo_combo_tick"] = tempo_atual
                    self.game.ultrapassagens_combo += 1
                    self.game.timer_combo = tempo_atual

            if self.game.ultrapassagens_combo >= 3 and 0 < dist_relativa < 40:
                bot["defesa_timer"] = tempo_atual + 2000

            if tempo_atual < bot.get("defesa_timer", 0) and 15 < dist_relativa < 45:
                target_x = player_x

            # 7. DIREÇÃO DINÂMICA E MURO INVISÍVEL
            limite_pista = 0.90
            target_x = max(-limite_pista, min(limite_pista, target_x))
            velocidade_volante = 0.025 + (bot["direcao"] * 0.005)
            if evasao_emergencia:
                velocidade_volante = max(velocidade_volante, 0.14)
            bot["steer_real"] = target_x - bot["x"]
            bot["x"] += bot["steer_real"] * velocidade_volante
            bot["x"] = max(-limite_pista, min(limite_pista, bot["x"]))

            # ==========================================
            # MURO INVISÍVEL: IMPEDE O OFF-ROAD DOS BOTS
            # ==========================================
            # A pista vai de -1.0 (esquerda) a 1.0 (direita). 
            # Colocamos 0.90 para garantir que nem sequer o pneu deles toca na relva!
            limite_pista = 0.90
            
            # Trava o X do bot para nunca ultrapassar os limites
            bot["x"] = max(-limite_pista, min(limite_pista, bot["x"]))
            
            # Trava também a "intenção" (target) do bot, para ele nem tentar ir para a relva
            if "target_x" in locals():
                target_x = max(-limite_pista, min(limite_pista, target_x))

            # 8. COLISÃO ABSOLUTA COM O JOGADOR
            hitbox_x = 0.22 
            
            if dist_relativa > 0:
                bateu = (dist_relativa < 2.5) and (abs(carro_jogador.player_x - bot["x"]) < hitbox_x)
            else:
                bateu = (abs(dist_relativa) < 1.5) and (abs(carro_jogador.player_x - bot["x"]) < hitbox_x)

            dist_abs = abs(dist_relativa)
            if dist_abs < menor_distancia_bot:
                menor_distancia_bot = dist_abs
            
            if bateu:
                if tempo_atual - self.game.timer_batida > 500: 
                    if hasattr(self.game, 'som_batida') and self.game.som_batida: 
                        self.game.som_batida.play()
                    self.game.timer_batida = tempo_atual
                    
                if dist_relativa > 0: 
                    carro_jogador.position = bot["pos"] - 3.6 
                    carro_jogador.speed = min(carro_jogador.speed * 0.7, bot["speed"]) 
                    
                    if carro_jogador.player_x < bot["x"]: bot["x"] += 0.15
                    else: bot["x"] -= 0.15
                    bot["x"] = max(-0.95, min(0.95, bot["x"]))
                    
                    if tempo_atual - bot.get("tempo_ultima_batida", 0) > 10000:
                        bot["contador_batidas"] = 0
                    bot["contador_batidas"] = bot.get("contador_batidas", 0) + 1
                    bot["tempo_ultima_batida"] = tempo_atual
                    
                    bot["speed"] *= 0.7 if bot["contador_batidas"] == 1 else 0.9  
                else:
                    bot["speed"] *= 0.4
                    # Joga o bot para o lado livre para não bater 5 vezes seguidas na traseira
                    bot["x"] += 0.25 if bot["x"] >= player_x else -0.25
                    bot["x"] = max(-limite_pista, min(limite_pista, bot["x"]))
                    carro_jogador.speed = min(player_max_speed, player_speed + 8)
                    self.game.steering_locked = True

            # 9. Animação
            if tempo_atual - bot["anim_timer"] > 50: 
                bot["frame_idx"] = (bot["frame_idx"] + 1) % 3
                bot["anim_timer"] = tempo_atual

        # Retorna as variáveis de estado para o main.py usar depois
        return curve_intensity, jogador_no_vacuo, menor_distancia_bot