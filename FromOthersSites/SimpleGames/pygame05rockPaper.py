
"""
pip install pygame
simple from https://www.youtube.com/watch?v=1SP5m9X4hF8
fammi un gioco in python (e pygame) di "carta, forbice , sasso" con menu grafico, prevedi due modalità: due umani oppure un umano che gioca contro il computer
prevedi che ogni match sia di 3 round, nella modalità PvP metti che un utente non vede quello che ha scelto l'altro

"""
import pygame
import random
import sys
import time

# Inizializzazione Pygame
pygame.init()

# Costanti
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60
ROUNDS_TO_WIN = 3

# Colori
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Configurazione finestra
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Carta, Forbice, Sasso")
clock = pygame.time.Clock()

# Font
font = pygame.font.Font(None, 48)
small_font = pygame.font.Font(None, 36)
tiny_font = pygame.font.Font(None, 24)

class Button:
    def __init__(self, x, y, width, height, text, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.is_hovered = False

    def draw(self, surface):
        color = (min(self.color[0] + 30, 255), 
                min(self.color[1] + 30, 255), 
                min(self.color[2] + 30, 255)) if self.is_hovered else self.color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)
        
        text_surface = font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                return True
        return False

class Game:
    def __init__(self):
        self.state = "menu"
        self.choices = ["Carta", "Forbice", "Sasso"]
        self.reset_game()
        
        # Creazione bottoni
        self.menu_buttons = [
            Button(250, 200, 300, 60, "Giocatore vs Giocatore", GREEN),
            Button(250, 300, 300, 60, "Giocatore vs Computer", GREEN),
            Button(250, 400, 300, 60, "Esci", RED)
        ]
        
        self.game_buttons = [
            Button(100, 400, 150, 60, "Carta", GRAY),
            Button(325, 400, 150, 60, "Forbice", GRAY),
            Button(550, 400, 150, 60, "Sasso", GRAY)
        ]
        
        self.continue_button = Button(250, 400, 300, 60, "Continua", GREEN)
        self.play_again_button = Button(250, 400, 300, 60, "Gioca ancora", GREEN)
        self.menu_button = Button(250, 500, 300, 60, "Menu principale", RED)

    def reset_game(self):
        self.game_mode = ""
        self.player1_choice = ""
        self.player2_choice = ""
        self.round_winner = ""
        self.current_round = 1
        self.player1_score = 0
        self.player2_score = 0
        self.final_winner = ""
        self.display_timer = 0
        self.waiting_for_continue = False

    def handle_menu(self, event):
        for i, button in enumerate(self.menu_buttons):
            if button.handle_event(event):
                if i == 0:
                    self.game_mode = "PvP"
                    self.state = "player1_choice"
                elif i == 1:
                    self.game_mode = "PvC"
                    self.state = "player1_choice"
                elif i == 2:
                    pygame.quit()
                    sys.exit()

    def handle_game(self, event):
        if self.waiting_for_continue:
            if self.continue_button.handle_event(event):
                self.waiting_for_continue = False
                self.player1_choice = ""
                self.player2_choice = ""
                if self.current_round > ROUNDS_TO_WIN * 2 or self.player1_score >= ROUNDS_TO_WIN or self.player2_score >= ROUNDS_TO_WIN:
                    self.determine_final_winner()
                    self.state = "final_result"
                else:
                    self.state = "player1_choice"
            return

        for i, button in enumerate(self.game_buttons):
            if button.handle_event(event):
                if self.state == "player1_choice":
                    self.player1_choice = self.choices[i]
                    if self.game_mode == "PvP":
                        self.state = "player2_choice"
                        # Pulisci lo schermo brevemente per privacy
                        screen.fill(WHITE)
                        pygame.display.flip()
                        time.sleep(0.5)
                    else:
                        self.player2_choice = random.choice(self.choices)
                        self.determine_round_winner()
                        self.waiting_for_continue = True
                elif self.state == "player2_choice":
                    self.player2_choice = self.choices[i]
                    self.determine_round_winner()
                    self.waiting_for_continue = True

    def handle_final_result(self, event):
        if self.play_again_button.handle_event(event):
            self.reset_game()
            if self.game_mode == "PvP":
                self.state = "player1_choice"
            else:
                self.state = "player1_choice"
        elif self.menu_button.handle_event(event):
            self.reset_game()
            self.state = "menu"

    def determine_round_winner(self):
        if self.player1_choice == self.player2_choice:
            self.round_winner = "Pareggio!"
        elif ((self.player1_choice == "Carta" and self.player2_choice == "Sasso") or
              (self.player1_choice == "Forbice" and self.player2_choice == "Carta") or
              (self.player1_choice == "Sasso" and self.player2_choice == "Forbice")):
            self.round_winner = "Giocatore 1 vince il round!"
            self.player1_score += 1
        else:
            self.round_winner = "Giocatore 2 vince il round!" if self.game_mode == "PvP" else "Computer vince il round!"
            self.player2_score += 1
        self.current_round += 1

    def determine_final_winner(self):
        if self.player1_score > self.player2_score:
            self.final_winner = "Giocatore 1 vince la partita!"
        elif self.player2_score > self.player1_score:
            self.final_winner = "Giocatore 2 vince la partita!" if self.game_mode == "PvP" else "Computer vince la partita!"
        else:
            self.final_winner = "Partita terminata in pareggio!"

    def draw(self):
        screen.fill(WHITE)
        
        # Mostra sempre il punteggio durante il gioco
        if self.state != "menu":
            score_text = f"Punteggio - G1: {self.player1_score}  {'G2' if self.game_mode == 'PvP' else 'PC'}: {self.player2_score}"
            score_surface = small_font.render(score_text, True, BLUE)
            screen.blit(score_surface, (10, 10))
            
            round_text = f"Round {self.current_round}/6"
            round_surface = small_font.render(round_text, True, BLUE)
            screen.blit(round_surface, (WINDOW_WIDTH - 150, 10))
        
        if self.state == "menu":
            title = font.render("Carta, Forbice, Sasso", True, BLACK)
            screen.blit(title, (250, 100))
            for button in self.menu_buttons:
                button.draw(screen)

        elif self.state in ["player1_choice", "player2_choice"]:
            player_text = "Giocatore 1" if self.state == "player1_choice" else "Giocatore 2"
            text = font.render(f"Turno {player_text}: Scegli", True, BLACK)
            screen.blit(text, (250, 100))
            
            # In modalità PvP, mostra le scelte precedenti solo al giocatore corrente
            if self.game_mode == "PvP":
                if self.state == "player1_choice" and self.current_round > 1:
                    prev_choice = tiny_font.render(f"La tua scelta precedente: {self.player1_choice}", True, GRAY)
                    screen.blit(prev_choice, (10, 50))
                elif self.state == "player2_choice" and self.current_round > 1:
                    prev_choice = tiny_font.render(f"La tua scelta precedente: {self.player2_choice}", True, GRAY)
                    screen.blit(prev_choice, (10, 50))
            
            for button in self.game_buttons:
                button.draw(screen)

        elif self.state == "final_result":
            text = font.render(self.final_winner, True, BLACK)
            screen.blit(text, (200, 100))
            
            final_score = small_font.render(f"Punteggio finale: {self.player1_score} - {self.player2_score}", True, BLACK)
            screen.blit(final_score, (300, 200))
            
            self.play_again_button.draw(screen)
            self.menu_button.draw(screen)
        
        if self.waiting_for_continue:
            round_result = font.render(self.round_winner, True, BLACK)
            screen.blit(round_result, (200, 100))
            
            choices_text = small_font.render(f"G1: {self.player1_choice} vs {'G2' if self.game_mode == 'PvP' else 'PC'}: {self.player2_choice}", True, BLACK)
            screen.blit(choices_text, (300, 200))
            
            self.continue_button.draw(screen)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    sys.exit()
                
                if self.state == "menu":
                    self.handle_menu(event)
                elif self.state in ["player1_choice", "player2_choice"]:
                    self.handle_game(event)
                elif self.state == "final_result":
                    self.handle_final_result(event)
                elif self.waiting_for_continue:
                    self.handle_game(event)
            
            self.draw()
            clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()