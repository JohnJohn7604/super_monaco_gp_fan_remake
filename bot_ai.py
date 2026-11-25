import random

class BotAI:
    def __init__(self, game):
        # Recebemos a referência do main.py para aceder à pista e ao carro do jogador
        self.game = game

    def atualizar_bots(self, tempo_atual):
        """ Executa toda a lógica de física, tangência e ultrapassagem da IA. """
        
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
        largada_segura = is_volta_0 and (tempo_volta < 5)
        sprint_largada = is_volta_0 and (tempo_volta < 8)
        largada_linhas = is_volta_0 and (tempo_volta < 15)

        lap_limit = getattr(self.game, 'lap_limit', 1)
        race_finished = getattr(self.game, 'race_finished', False)
        dist_meta = total_len * lap_limit

        # Reseta o combo 1x por frame
        if tempo_atual - self.game.timer_combo > 4000:
            self.game.ultrapassagens_combo = 0

        curve_intensity = get_curve(player_pos)
        self.game.steering_locked = False
        menor_distancia_bot = 9999
        jogador_no_vacuo = False

        equipes_dict = getattr(self.game, "equipes", {})
        ordem_classes = {"D": 1, "C": 2, "B": 3, "A": 4, "S": 5}
        equipe_jogador = getattr(self.game, "equipe_atual_jogador", "")
        classe_jogador = equipes_dict.get(equipe_jogador, {}).get("classe", "D").upper()
        rank_jogador = ordem_classes.get(classe_jogador, 1)

        # Antes do loop "for bot in bots:"
        alerta_cego_esq = None
        alerta_cego_dir = None

        for bot in bots:
            # 1. Distância Circular Perfeita
            dist_bruta = bot["pos"] - player_pos
            dist_relativa = dist_bruta % total_len
            if dist_relativa > half_len:
                dist_relativa -= total_len

            # =================================================================
            # 1.1 SENSOR DE PONTO CEGO (CARRO NA LATERAL / FORA DO CAMPO DE VISÃO)
            # =================================================================
            if -2.5 <= dist_relativa <= 18.0:
                diff_x = bot["x"] - player_x
                # Quanto mais perto de 0m, mais estreito é o campo de visão da câmera
                limite_visivel = 0.22 + (max(0.0, dist_relativa) * 0.035)

                if limite_visivel < abs(diff_x) < 1.35:
                    if diff_x < 0:
                        if alerta_cego_esq is None or dist_relativa < alerta_cego_esq:
                            alerta_cego_esq = dist_relativa
                    else:
                        if alerta_cego_dir is None or dist_relativa < alerta_cego_dir:
                            alerta_cego_dir = dist_relativa

            # =================================================================
            # 1.2 IA DE DEFESA DE POSIÇÃO (BLOQUEIO AGRESSIVO)
            # =================================================================
            if bot.get("aceleracao", 1) > 4 and not largada_segura:
                # A) RECARGA: Afasta-se mais de 300m para recarregar a tentativa
                if dist_relativa > 300 and bot.get("pode_recarregar_bloqueio", False):
                    bot["bloqueios_disponiveis"] = 1
                    bot["pode_recarregar_bloqueio"] = False
                
                # B) O BLOQUEIO SEGURO: Tenta fechar apenas entre 20m e 65m
                if 20 < dist_relativa < 65 and player_speed > bot["speed"] and bot.get("bloqueios_disponiveis", 0) > 0:
                    alvo_bloqueio = player_x
                    velocidade_fechada = 0.018
                    
                    if bot["x"] < alvo_bloqueio:
                        bot["x"] = min(0.8, bot["x"] + velocidade_fechada)
                    elif bot["x"] > alvo_bloqueio:
                        bot["x"] = max(-0.8, bot["x"] - velocidade_fechada)
                        
                    if abs(bot["x"] - player_x) < 0.12:
                        bot["bloqueios_disponiveis"] = 0
                        bot["pode_recarregar_bloqueio"] = True

            # 1.3. EVENTO ALEATÓRIO: "FALHA MECÂNICA LÁ NA FRENTE"
            if not bot.get("falha_mecanica", False):
                if 200 < dist_relativa < half_len:
                    if random.randint(1, 25000) == 1:
                        bot["falha_mecanica"] = True
                        bot["fim_falha"] = tempo_atual + random.randint(5000, 9000)
            else:
                if tempo_atual > bot.get("fim_falha", 0):
                    bot["falha_mecanica"] = False

            # 2. IA de Curvas (Proporcional à intensidade da curva e aderência da equipe)
            curva_do_bot = get_curve(bot["pos"])
            intensidade_curva = abs(curva_do_bot)

            if intensidade_curva > 0.06 and not sprint_largada:
                fator_curva = min(1.0, (intensidade_curva - 0.06) / 0.45)
                # Classe D segura ~80% nas curvas fechadas; Classe A segura ~86%
                limite_direcao = 0.74 + (bot["direcao"] * 0.024)
                multiplicador_curva = 1.0 - (fator_curva * (1.0 - limite_direcao))
                target_speed = max(185, bot["max_speed"] * multiplicador_curva)
            else:
                target_speed = bot["max_speed"]

            # Corte de velocidade em caso de falha mecânica
            if bot.get("falha_mecanica", False):
                target_speed = min(target_speed, 260.0)

            classe_bot = (bot.get("classe") or equipes_dict.get(bot.get("equipe", ""), {}).get("classe", "D")).upper()
            rank_bot = ordem_classes.get(classe_bot, 1)
            bot_classe_maior_atras = (dist_relativa < 0) and (rank_bot > rank_jogador)

            # Buffer de +5% de velocidade para carros de classe superior atrás do jogador
            if bot_classe_maior_atras:
                target_speed *= 1.05

            eh_classe_a = (classe_bot == "A")

            # ---> RADAR DE FRENAGEM INTELIGENTE <---
            if -42 < dist_relativa < 0 and jogador_na_pista:
                if abs(bot["x"] - player_x) < 0.52:
                    piso_vel = 0 if player_speed < 60 else max(80, player_speed * 0.92)
                    target_speed = min(target_speed, piso_vel)

            # =========================================================================
            # 3. PEDAL DE FREIO E ACELERAÇÃO DO MOTOR
            # =========================================================================
            if bot["pos"] >= dist_meta:
                bot["concluiu_chegada"] = True

            if race_finished and bot.get("concluiu_chegada", False):
                target_speed = 100.0
                if bot["speed"] > 100.0:
                    bot["speed"] = max(100.0, bot["speed"] - 2.8)
                elif bot["speed"] < 100.0:
                    bot["speed"] = min(100.0, bot["speed"] + 1.2)
            else:
                if bot["speed"] > target_speed:
                    forca_freio = 4.0 + (bot.get("freio", 3) * 0.6)
                    bot["speed"] = max(target_speed, bot["speed"] - forca_freio)
                elif bot["speed"] < target_speed:
                    forca_motor = 0.22 + (bot["aceleracao"] * 0.09)
                    razao_vel = bot["speed"] / max(1.0, bot["max_speed"])
                    fator_alta = max(0.28, 1.25 - razao_vel)
                    forca_motor *= fator_alta
                    if bot_classe_maior_atras:
                        forca_motor *= 1.08
                    bot["speed"] = min(target_speed, bot["speed"] + forca_motor)

            # 4. O SISTEMA DE LINHAS E TANGÊNCIA (RACING LINE)
            if "linha_reta" not in bot:
                bot["linha_reta"] = random.choice([-0.65, -0.21, 0.0, 0.21, 0.65])
            
            curva_futura = get_curve(bot["pos"] + 30)
            
            if curva_futura > 0.05:
                tracado_ideal = -0.65  
            elif curva_futura < -0.05:
                tracado_ideal = 0.65   
            else:
                tracado_ideal = bot["linha_reta"] 
            
            target_x = tracado_ideal
            bot["pos"] += bot["speed"] * 0.0049

            # SENSOR DE VÁCUO (exige alinhamento fino e proximidade real)
            if 2 < dist_relativa < 22 and player_speed > (player_max_speed * 0.82):
                if abs(player_x - bot["x"]) < 0.24:
                    jogador_no_vacuo = True

            # REGRA DA LARGADA (MANTER AS LINHAS)
            if largada_linhas:
                for outro_bot in bots:
                    if bot is outro_bot:
                        continue
                    dist_entre_bots = (outro_bot["pos"] - bot["pos"]) % total_len
                    if dist_entre_bots > half_len:
                        dist_entre_bots -= total_len
                    
                    if abs(dist_entre_bots) < 8:
                        distancia_lateral = bot["x"] - outro_bot["x"]
                        if abs(distancia_lateral) < 0.35:
                            target_x = bot["x"] + (0.3 if distancia_lateral > 0 else -0.3)

            # =================================================================
            # 5. TÁTICAS CONTRA O JOGADOR (DESVIO SUTIL E ESQUIVA CLASSE A)
            # =================================================================
            desviando_jogador = False
            evasao_emergencia = False

            if not largada_linhas:
                if 0 < dist_relativa < 60:
                    target_x = tracado_ideal

                elif -65 < dist_relativa < 0 and jogador_na_pista and bot["speed"] > player_speed:
                    if eh_classe_a:
                        # CLASSE A: Antecipa a 65m e busca o melhor lado da curva
                        desviando_jogador = True

                        if linha_jogador == 2:
                            if curva_futura > 0.05:
                                target_x = 0.72
                            elif curva_futura < -0.05:
                                target_x = -0.72
                            else:
                                target_x = -0.72 if bot["x"] <= player_x else 0.72
                        elif linha_jogador == 1:
                            target_x = 0.72 if curva_futura > 0.05 else 0.35
                        elif linha_jogador == 3:
                            target_x = -0.72 if curva_futura < -0.05 else -0.35

                        if abs(bot["x"] - player_x) > 0.55:
                            bot["speed"] += 0.35

                        # Esquiva rápida exclusiva da Classe A a menos de 32m
                        if abs(dist_relativa) < 32 and abs(bot["x"] - player_x) < 0.58:
                            evasao_emergencia = True
                            target_x = -0.82 if player_x > 0 else 0.82
                    else:
                        # Carros de classe inferior precisam de +8 km/h de vantagem para abrir ultrapassagem
                        margem_ultrapassagem = 8.0 if rank_bot < rank_jogador else 1.5
                        if (
                            -55 < dist_relativa < 0
                            and abs(bot["x"] - player_x) < 0.55
                            and bot["speed"] > (player_speed + margem_ultrapassagem)
                        ):
                            desviando_jogador = True
                            if linha_jogador == 1:
                                target_x = 0.35
                            elif linha_jogador == 3:
                                target_x = -0.35
                            else:
                                target_x = -0.72 if bot["x"] <= player_x else 0.72

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

                    if abs(dist_entre_bots) < 8:
                        distancia_lateral = bot["x"] - outro_bot["x"]
                        if abs(distancia_lateral) < 0.36:
                            novo_x = bot["x"] + (0.32 if distancia_lateral >= 0 else -0.32)
                            if not (-30 < dist_relativa < 5 and abs(novo_x - player_x) < 0.52):
                                target_x = novo_x

                    elif not largada_linhas and 0 < dist_entre_bots < menor_dist_frente:
                        if abs(bot["x"] - outro_bot["x"]) < 0.45:
                            menor_dist_frente = dist_entre_bots
                            bot_bloqueando = outro_bot

                if bot_bloqueando is not None:
                    novo_x = -0.72 if bot_bloqueando["x"] > 0 else 0.72
                    if not (-40 < dist_relativa < 5 and abs(novo_x - player_x) < 0.52):
                        target_x = novo_x

            # =================================================================
            # 6.5. COMBO DE ULTRAPASSAGEM
            # =================================================================
            if -5 < dist_relativa < 0 and bot["speed"] < player_speed:
                if tempo_atual - bot.get("ultimo_combo_tick", 0) > 5000:
                    bot["ultimo_combo_tick"] = tempo_atual
                    self.game.ultrapassagens_combo += 1
                    self.game.timer_combo = tempo_atual

            if self.game.ultrapassagens_combo >= 3 and 0 < dist_relativa < 40:
                bot["defesa_timer"] = tempo_atual + 2000

            if tempo_atual < bot.get("defesa_timer", 0) and 15 < dist_relativa < 45:
                target_x = player_x

            # =================================================================
            # 7. DIREÇÃO DINÂMICA E MURO INVISÍVEL
            # =================================================================
            limite_pista = 0.90
            target_x = max(-limite_pista, min(limite_pista, target_x))
            velocidade_volante = 0.025 + (bot["direcao"] * 0.005)

            if evasao_emergencia and eh_classe_a:
                velocidade_volante = max(velocidade_volante, 0.14)

            bot["steer_real"] = target_x - bot["x"]
            bot["x"] += bot["steer_real"] * velocidade_volante
            bot["x"] = max(-limite_pista, min(limite_pista, bot["x"]))

            # 8. COLISÃO ABSOLUTA COM O JOGADOR (HITBOX AMPLIADA)
            hitbox_x = 0.30
            
            if dist_relativa > 0:
                bateu = (dist_relativa < 2.5) and (abs(player_x - bot["x"]) < hitbox_x)
            else:
                bateu = (abs(dist_relativa) < 1.5) and (abs(player_x - bot["x"]) < hitbox_x)

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
                    
                    if player_x < bot["x"]:
                        bot["x"] += 0.15
                    else:
                        bot["x"] -= 0.15
                    bot["x"] = max(-0.95, min(0.95, bot["x"]))
                    
                    if tempo_atual - bot.get("tempo_ultima_batida", 0) > 10000:
                        bot["contador_batidas"] = 0
                    bot["contador_batidas"] = bot.get("contador_batidas", 0) + 1
                    bot["tempo_ultima_batida"] = tempo_atual
                    
                    bot["speed"] *= 0.7 if bot["contador_batidas"] == 1 else 0.9  
                else:
                    bot["speed"] *= 0.4
                    # Joga o bot para fora da hitbox (0.32 > 0.30) para o lado livre da pista
                    if bot["x"] > 0.60:
                        bot["x"] -= 0.32
                    elif bot["x"] < -0.60:
                        bot["x"] += 0.32
                    else:
                        bot["x"] += 0.32 if bot["x"] >= player_x else -0.32
                    bot["x"] = max(-limite_pista, min(limite_pista, bot["x"]))
                    carro_jogador.speed = min(player_max_speed, player_speed + 8)
                    self.game.steering_locked = True

            # 9. Animação
            if tempo_atual - bot["anim_timer"] > 50: 
                bot["frame_idx"] = (bot["frame_idx"] + 1) % 3
                bot["anim_timer"] = tempo_atual

        self.game.alerta_cego_esq = alerta_cego_esq
        self.game.alerta_cego_dir = alerta_cego_dir

        return curve_intensity, jogador_no_vacuo, menor_distancia_bot