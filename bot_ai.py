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

            # 1.5. EVENTO ALEATÓRIO: "FALHA MECÂNICA LÁ NA FRENTE"
            if not bot.get("falha_mecanica", False):
                if 200 < dist_relativa < (track.total_track_length / 2):
                    import random
                    if random.randint(1, 1500) == 1:
                        bot["falha_mecanica"] = True
                        bot["fim_falha"] = tempo_atual + random.randint(5000, 9000)
            else:
                if tempo_atual > bot.get("fim_falha", 0):
                    bot["falha_mecanica"] = False

            # 2. IA de Curvas Corajosas
            curva_do_bot = track.get_curve(bot["pos"])
            
            if abs(curva_do_bot) > 0.02 and not sprint_largada:
                intensidade_curva = abs(curva_do_bot) * 5.0  
                bonus_direcao = bot.get("direcao", 3) * 0.015 
                multiplicador_curva = 1.0 - intensidade_curva + bonus_direcao
                target_speed = min(bot["max_speed"], bot["max_speed"] * multiplicador_curva)
                target_speed = max(150, target_speed) 
            else:
                target_speed = bot["max_speed"]

            # O PEDAL DE FREIO
            if bot["speed"] > target_speed:
                forca_freio = 4.0 + (bot.get("freio", 3) * 0.6)
                bot["speed"] -= forca_freio 

            # 3. Aceleração Feroz e Controle de Largada
            forca_motor = 0.25 + (bot["aceleracao"] * 0.1)
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

            # 4. O SISTEMA DE 3 LINHAS E TANGÊNCIA (RACING LINE)
            if "linha_reta" not in bot:
                import random
                bot["linha_reta"] = random.choice([-0.65, -0.21, 0.0, 0.21, 0.65])
            
            curva_futura = track.get_curve(bot["pos"] + 30)
            
            if curva_futura > 0.05: tracado_ideal = -0.65  
            elif curva_futura < -0.05: tracado_ideal = 0.65   
            else: tracado_ideal = bot["linha_reta"] 
            
            target_x = tracado_ideal
            bot["pos"] += bot["speed"] * 0.005 

            # SENSOR DE VÁCUO
            if 1 < dist_relativa < 60 and carro_jogador.speed > 100:
                if abs(carro_jogador.player_x - bot["x"]) < 0.5: 
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
            else:
                # 5. Táticas Contra o Jogador
                jogador_na_pista = -1.0 <= carro_jogador.player_x <= 1.0
                
                if carro_jogador.player_x < -0.33: linha_jogador = 1 
                elif carro_jogador.player_x > 0.33: linha_jogador = 3 
                else: linha_jogador = 2 
                
                if 0 < dist_relativa < 60:
                    target_x = tracado_ideal
                    
                elif -150 < dist_relativa < 0 and jogador_na_pista:
                    if abs(dist_relativa) < 150 and bot["speed"] > carro_jogador.speed:
                        
                        if linha_jogador == 2:
                            if curva_futura > 0.05: target_x = 0.65 
                            elif curva_futura < -0.05: target_x = -0.65 
                            else: target_x = -0.65 if bot["x"] < 0 else 0.65 
                        elif linha_jogador == 1:
                            target_x = 0.65 if curva_futura > 0.05 else 0.0
                        elif linha_jogador == 3:
                            target_x = -0.65 if curva_futura < -0.05 else 0.0
                        
                        if abs(bot["x"] - carro_jogador.player_x) > 0.35: 
                            bot["speed"] += 0.5 
                            
                        if abs(dist_relativa) < 25 and abs(bot["x"] - carro_jogador.player_x) < 0.4:
                            target_x = 0.85 if bot["x"] >= carro_jogador.player_x else -0.85
                            bot["speed"] = min(bot["speed"], carro_jogador.speed * 0.95)

                # 6. Radar de Tráfego IA vs IA
                for outro_bot in bots:
                    if bot == outro_bot: continue
                    dist_bruta_bots = outro_bot["pos"] - bot["pos"]
                    dist_entre_bots = dist_bruta_bots % track.total_track_length
                    if dist_entre_bots > track.total_track_length / 2: dist_entre_bots -= track.total_track_length
                    
                    if abs(dist_entre_bots) < 8:
                        distancia_lateral = bot["x"] - outro_bot["x"]
                        if abs(distancia_lateral) < 0.35:
                            target_x = bot["x"] + (0.3 if distancia_lateral > 0 else -0.3)

                    if 0 < dist_entre_bots < 45 and abs(bot["x"] - outro_bot["x"]) < 0.45:
                        target_x = -0.65 if outro_bot["x"] > 0 else 0.65

            # 7. Direção Dinâmica
            velocidade_volante = 0.025 + (bot["direcao"] * 0.005) 
            bot["steer_real"] = target_x - bot["x"]
            bot["x"] += bot["steer_real"] * velocidade_volante

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
                    carro_jogador.speed = min(carro_jogador.max_speed, carro_jogador.speed + 8) 
                    self.game.steering_locked = True

            # 9. Animação
            if tempo_atual - bot["anim_timer"] > 50: 
                bot["frame_idx"] = (bot["frame_idx"] + 1) % 3
                bot["anim_timer"] = tempo_atual

            # 10. COMBO DE ULTRAPASSAGEM
            if dist_relativa > -5 and dist_relativa < 0 and bot["speed"] < carro_jogador.speed:
                self.game.ultrapassagens_combo += 1
                self.game.timer_combo = tempo_atual
            
            if tempo_atual - self.game.timer_combo > 4000:
                self.game.ultrapassagens_combo = 0

            if self.game.ultrapassagens_combo >= 3 and 0 < dist_relativa < 40:
                target_x = carro_jogador.player_x
                bot["defesa_timer"] = tempo_atual + 2000

        # Retorna as variáveis de estado para o main.py usar depois
        return curve_intensity, jogador_no_vacuo, menor_distancia_bot