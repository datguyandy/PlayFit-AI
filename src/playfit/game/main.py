import cv2
import pygame

from .fighters import ASSETS_DIR, WIN, DEAD, Fighter
from .actions import Actions #importing class from the actions.py file
from .input_keyboard import get_actions_player1 #importing function from input_keyboard.py file
from .bot import FighterAI
from ..gestures.rules import ActionDetector
from ..vision.pose_camera import PoseCamera

#create game window
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
PLAYING = 0
GAME_OVER = 1

#set framerate
#cooldowns, attack timers and speeds are all counted in frames and were tuned at
#webcam speed, so the game ticks at 30 whether or not a camera is connected
FPS = 30

#define colors
YELLOW = (255, 221, 38)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
DARK_RED = (200, 0 , 0)

UI_X_WIN = SCREEN_WIDTH // 2 - 250
UI_Y_WIN = 10

UI_X_OVER = SCREEN_WIDTH // 2 - 200
UI_Y_OVER = -20

KO_X = SCREEN_WIDTH // 2 - 65
KO_Y = -10

def load_image(path, size):
    image = pygame.image.load(ASSETS_DIR / path).convert_alpha()
    return pygame.transform.scale(image, size)

#function to draw fighter health bars
def draw_health_bar(screen, health, x, y):
    ratio = health / 100
    pygame.draw.rect(screen, WHITE, (x-2, y-2, 404, 34)) #draw border
    pygame.draw.rect(screen, RED, (x, y, 400, 30)) #draw background bar
    pygame.draw.rect(screen, YELLOW, (x, y, 400 * ratio, 30)) #draw health

def draw_restart_button(screen, font, mouse_pos):
    button_width = 200
    button_height = 60
    button_x = SCREEN_WIDTH // 2 - button_width // 2
    button_y = SCREEN_HEIGHT - 300

    #hovering button
    button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

    if button_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, RED, button_rect)
    else:
        pygame.draw.rect(screen, DARK_RED, button_rect)

    #white border
    pygame.draw.rect(screen, WHITE, button_rect, 3)

    #text button
    text = font.render("RESTART", True, WHITE)
    text_rect = text.get_rect(center = button_rect.center)
    screen.blit(text, text_rect)

    return button_rect


def fighterOverlap(a,b):
    if not a.rect.colliderect(b.rect):
        return
    overlap_left = a.rect.right - b.rect.left
    overlap_right = b.rect.right - a.rect.left
    push = min(overlap_left, overlap_right)

    if a.rect.centerx < b.rect.centerx:
        a.rect.x -= push // 2
        b.rect.x += push - push // 2
    else:
        a.rect.x += push // 2
        b.rect.x -= push - push // 2

    a.rect.left = max(0, a.rect.left)
    a.rect.right = min(SCREEN_WIDTH, a.rect.right)
    b.rect.left = max(0, b.rect.left)
    b.rect.right = min(SCREEN_WIDTH, b.rect.right)

def create_fighters():
    return Fighter(200, 310, variant="player"), FighterAI(700, 310)

def pose_to_actions(detected_actions) -> Actions:
    actions = Actions()
    for action in detected_actions:
        if action in ["PUNCH_RIGHT", "PUNCH_LEFT", "PUNCH"]:
            actions.punch = True
        elif action in ["KICK_RIGHT", "KICK_LEFT", "KICK"]:
            actions.kick = True
        elif action == "JUMP":
            actions.jump = True
        #frame is mirrored, so mediapipe's LEFT landmarks are the player's right side
        elif action == "MOVE_LEFT":
            actions.movex = 1
        elif action == "MOVE_RIGHT":
            actions.movex = -1
    return actions


def main():
    pygame.init() #initialized pygame

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)) #create window with set dimensions
    pygame.display.set_caption("StreetFighter Pose Control") #set window title
    clock = pygame.time.Clock()

    #load images once, already scaled
    background_image = load_image("backgrounds/background.jpg", (SCREEN_WIDTH, SCREEN_HEIGHT))
    ko_img = load_image("sprites/GameOver/KO.png", (150, 100))
    gameOver_img = load_image("sprites/GameOver/GameOver.png", (400, 400))
    winner_img = load_image("sprites/GameOver/YouWin.png", (500, 300))
    button_font = pygame.font.Font(None, 48)

    #create fighter instance
    fighter1, fighter2 = create_fighters()
    game_state = PLAYING
    winner = None
    game_over_time = None
    restart_button = None

    #Initialize webcam detection
    camera = PoseCamera()
    action_detector = ActionDetector()
    pose_movex = 0 #held between camera frames so walking stays smooth

    #MAIN GAME LOOP
    run = True
    while run:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        actions_p1 = Actions()

        pose_frame = camera.poll()
        if pose_frame is not None:
            image, landmarks = pose_frame
            pose_movex = 0

            if landmarks:
                facing = "right" if fighter2.rect.centerx > fighter1.rect.centerx else "left"
                detected_actions = action_detector.update(landmarks, facing)

                #convert detected actions to Actions instance
                actions_p1 = pose_to_actions(detected_actions)
                pose_movex = actions_p1.movex

            cv2.imshow("MediaPipe Feed", image) #pop up on the screen showing the frame

        actions_p1.movex = pose_movex

        #draw background
        screen.blit(background_image, (0, 0)) #draw background at top-left corner

        #show health bars
        draw_health_bar(screen, fighter1.health, 20, 20)
        draw_health_bar(screen, fighter2.health, 580, 20)

        #show ko image
        screen.blit(ko_img, (KO_X, KO_Y))

        if game_state == PLAYING:
            #keyboard fallback (works without a webcam)
            actions_kb = get_actions_player1()
            actions_p1.movex = actions_p1.movex or actions_kb.movex
            actions_p1.punch = actions_p1.punch or actions_kb.punch
            actions_p1.kick = actions_p1.kick or actions_kb.kick
            actions_p1.jump = actions_p1.jump or actions_kb.jump

            fighter1.movex(actions_p1, fighter2)
            fighter1.movey(actions_p1)
            fighter1.handle_attack(actions_p1)
            fighter1.attack(screen, fighter2)

            #update bot fighter
            actions_p2 = fighter2.getActions(fighter1)
            fighter2.movex(actions_p2, fighter1)
            fighter2.movey(actions_p2)
            fighter2.handle_attack(actions_p2)
            fighter2.attack(screen, fighter1)

            fighterOverlap(fighter1, fighter2)

            #check game over
            if fighter1.health <= 0:
                game_state = GAME_OVER
                winner = "Player 2"
                fighter1.set_action(DEAD)
                fighter2.set_action(WIN)
                game_over_time = pygame.time.get_ticks()

            elif fighter2.health <= 0:
                game_state = GAME_OVER
                winner = "Player 1"
                fighter2.set_action(DEAD)
                fighter1.set_action(WIN)
                game_over_time = pygame.time.get_ticks()

        if game_state == GAME_OVER:
            if winner == "Player 1":
                screen.blit(winner_img, (UI_X_WIN, UI_Y_WIN))
            else:
                screen.blit(gameOver_img, (UI_X_OVER, UI_Y_OVER))

            #show restart button after 3 seconds
            if (pygame.time.get_ticks() - game_over_time) / 1000 >= 3:
                restart_button = draw_restart_button(screen, button_font, mouse_pos)

        #draw fighters
        fighter1.draw(screen)
        fighter2.draw(screen)

        #event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            if event.type == pygame.MOUSEBUTTONDOWN and restart_button is not None:
                if restart_button.collidepoint(event.pos):
                    #reset game
                    fighter1, fighter2 = create_fighters()
                    game_state = PLAYING
                    winner = None
                    game_over_time = None
                    restart_button = None

        if cv2.waitKey(1) & 0xFF == ord("q"): #exit if 'q' is pressed (also lets the opencv window refresh)
            break
        #update display
        pygame.display.update()

    #exit pygame
    camera.close()
    cv2.destroyAllWindows()
    pygame.quit()


if __name__ == "__main__":
    main()
