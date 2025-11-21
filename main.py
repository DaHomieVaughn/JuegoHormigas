# (archivo completo: main.py)
import pygame
import sys
import os
import math
import random
import time
from utils.algoritmo_hormigas import AlgoritmoHormigas

# --- INICIALIZACIÓN ---
pygame.init()
# intenta inicializar mixer, si falla seguimos sin sonido
try:
    pygame.mixer.init()
except Exception:
    print("Aviso: pygame.mixer no pudo inicializarse (sin sonido).")

# --- HELP: cargar rutas compatibles con PyInstaller ---
def cargar_ruta(ruta_relativa):
    """
    Devuelve la ruta absoluta correcta tanto si se ejecuta como script (.py)
    como si está empaquetado con PyInstaller (--onefile).
    """
    try:
        base_path = sys._MEIPASS  # pyinstaller temporal folder
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, ruta_relativa)

# --- CONFIGURACIÓN ---
ANCHO, ALTO = 800, 600
MAPA_ANCHO, MAPA_ALTO = 2000, 2000
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Repartidor de Pizzas 🍕🐜 - Feromonas controladas (visual)")
clock = pygame.time.Clock()

# --- COLORES ---
GRIS_OSCURO = (30, 30, 30)
ASFALTO = (50, 50, 50)
ASFALTO_CLARO = (60, 60, 60)
EDIFICIO = (90, 90, 120)
CASA_COLOR = (230, 200, 100)
PIZZERIA_COLOR = (255, 120, 50)
PIZZERIA_COLOR_ALT = (255, 155, 80)
ROJO = (255, 100, 100)
AMARILLO = (255, 220, 0)
BLANCO = (255, 255, 255)
MINI_BG = (30, 30, 30)
MINI_FRAME = (10, 10, 10)

# --- SONIDOS (carga segura, con try/except) ---
sonido_entrega = None
try:
    sonido_entrega = pygame.mixer.Sound(cargar_ruta("assets/sonidos/entrega.mp3"))
except Exception:
    print("No se encontró o no se pudo cargar 'assets/sonidos/entrega.mp3' (continuando sin sonido de entrega)")

try:
    musica_fondo = cargar_ruta("assets/sonidos/bgmusic.mp3")
    pygame.mixer.music.load(musica_fondo)
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
except Exception:
    print("No se encontró o no se pudo cargar 'assets/sonidos/bgmusic.mp3' (continuando sin música de fondo)")

# --- CARGA DE SPRITES (pizzero y pizza) ---
pizzero_img = None
pizza_img = None
try:
    img_path = cargar_ruta("assets/sprites/pizzero.png")
    pizzero_img_raw = pygame.image.load(img_path).convert_alpha()
    # escalamos a un tamaño razonable (32x32) manteniendo aspecto
    pizzero_img = pygame.transform.smoothscale(pizzero_img_raw, (32, 32))
except Exception:
    print("Aviso: no se encontró 'assets/sprites/pizzero.png' — usando dibujo por defecto para repartidor")

try:
    img_path = cargar_ruta("assets/sprites/pizza.png")
    pizza_img_raw = pygame.image.load(img_path).convert_alpha()
    pizza_img = pygame.transform.smoothscale(pizza_img_raw, (16, 16))
except Exception:
    print("Aviso: no se encontró 'assets/sprites/pizza.png' — usando indicador por defecto para pizza")

# --- CLASES ---
class Repartidor:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.velocidad = 5
        self.rect = pygame.Rect(self.x - 10, self.y - 10, 20, 20)
        self.entregando = False
        self.tiene_pizza = False
        self.nodo_previo = None

    def mover(self, teclas, colisiones):
        dx, dy = 0, 0
        if teclas[pygame.K_UP]: dy -= self.velocidad
        if teclas[pygame.K_DOWN]: dy += self.velocidad
        if teclas[pygame.K_LEFT]: dx -= self.velocidad
        if teclas[pygame.K_RIGHT]: dx += self.velocidad

        nuevo_rect = self.rect.move(dx, dy)
        if not any(nuevo_rect.colliderect(c) for c in colisiones):
            self.x += dx
            self.y += dy
            self.rect = nuevo_rect

        self.x = max(0, min(MAPA_ANCHO, self.x))
        self.y = max(0, min(MAPA_ALTO, self.y))
        self.rect.topleft = (self.x - 10, self.y - 10)

    def dibujar(self, pantalla, cam_x, cam_y):
        # Si tenemos imagen de pizzero, la mostramos centrada; si no, fallback al dibujo anterior
        if pizzero_img:
            w, h = pizzero_img.get_width(), pizzero_img.get_height()
            pantalla.blit(pizzero_img, (self.x - w//2 - cam_x, self.y - h//2 - cam_y))
        else:
            # sombra
            pygame.draw.ellipse(pantalla, (15,15,15), (self.x - 8 - cam_x, self.y - 6 - cam_y, 24, 8))
            pygame.draw.rect(pantalla, ROJO, (self.x - 10 - cam_x, self.y - 10 - cam_y, 20, 20))
            pygame.draw.rect(pantalla, (180, 30, 30), (self.x + 4 - cam_x, self.y - 4 - cam_y, 6, 6))

        # Indicador visual de pizza: si existe pizza_img lo usamos, si no fallback al cuadrado blanco
        if self.tiene_pizza:
            if pizza_img:
                pw, ph = pizza_img.get_width(), pizza_img.get_height()
                pantalla.blit(pizza_img, (self.x - pw//2 - cam_x, self.y - h//2 - 6 - cam_y))
            else:
                # cuadrado blanco por defecto
                pantalla.blit(pygame.Surface((10,10)), (self.x - 5 - cam_x, self.y - 25 - cam_y))
                pygame.draw.rect(pantalla, BLANCO, (self.x - 5 - cam_x, self.y - 25 - cam_y, 10, 10))

class Casa:
    def __init__(self, x, y, id_casa, base_id=None):
        self.x = x
        self.y = y
        # id_casa es el id mostrado (puede cambiar por rotaciones)
        self.id = id_casa
        # base_id permanece fijo (1..N) y se usa para decidir el bloque a rotar
        self.base_id = base_id if base_id is not None else id_casa
        self.entregada = False

    def dibujar(self, pantalla, cam_x, cam_y, highlight=False):
        pygame.draw.rect(pantalla, (30,30,30), (self.x - 12 - cam_x, self.y - 8 - cam_y, 24, 10))
        base_color = (100, 180, 100) if self.entregada else CASA_COLOR
        color = base_color
        if highlight and not self.entregada:
            brillo = int(40 * (0.5 + 0.5 * math.sin(time.time() * 3.0)))
            r = min(255, base_color[0] + brillo)
            g = min(255, base_color[1] + brillo)
            b = min(255, base_color[2] + (brillo // 3))
            color = (r, g, b)
        pygame.draw.rect(pantalla, color, (self.x - 10 - cam_x, self.y - 10 - cam_y, 20, 20))
        pygame.draw.polygon(pantalla, (200, 160, 80),
            [(self.x - 12 - cam_x, self.y - 10 - cam_y),
             (self.x + 12 - cam_x, self.y - 10 - cam_y),
             (self.x - cam_x, self.y - 25 - cam_y)])
        font = pygame.font.SysFont(None, 18)
        texto = font.render(str(self.id), True, (0, 0, 0))
        pantalla.blit(texto, (self.x - 6 - cam_x, self.y - 8 - cam_y))

class Pizzeria:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def dibujar(self, pantalla, cam_x, cam_y, parpadeo=False):
        pygame.draw.rect(pantalla, (20,20,20), (self.x - 26 - cam_x, self.y + 22 - cam_y, 52, 12), border_radius=6)
        color = PIZZERIA_COLOR_ALT if parpadeo else PIZZERIA_COLOR
        pygame.draw.rect(pantalla, (40,40,40), (self.x - 22 - cam_x, self.y - 22 - cam_y, 44, 44), border_radius=4)
        pygame.draw.rect(pantalla, color, (self.x - 20 - cam_x, self.y - 20 - cam_y, 40, 40), border_radius=3)
        font = pygame.font.SysFont(None, 20)
        texto = font.render("PIZZA", True, (255, 255, 255))
        pantalla.blit(texto, (self.x - 22 - cam_x, self.y - 35 - cam_y))

# --- MAPA Y COLISIONES ---
pizzeria = Pizzeria(1000, 1000)
repartidor = Repartidor(pizzeria.x, pizzeria.y)
colisiones = []

def dibujar_fondo(pantalla, cam_x, cam_y, colisiones):
    pantalla.fill((200, 200, 200))  # color base de fondo (beige claro o cemento)
    colisiones.clear()

    # --- Dibujar parques (zonas verdes) ---
    random.seed(1)  # fijo para consistencia
    for _ in range(15):
        px = random.randint(0, MAPA_ANCHO - 300)
        py = random.randint(0, MAPA_ALTO - 300)
        w = random.randint(150, 300)
        h = random.randint(100, 250)
        color_verde = (random.randint(120, 160), random.randint(170, 200), random.randint(120, 160))
        pygame.draw.rect(pantalla, color_verde, (px - cam_x, py - cam_y, w, h))

    # --- Calles principales ---
    for i in range(0, MAPA_ANCHO, 200):
        # gradiente vertical en calles
        for k in range(80):
            color = (40 + k // 3, 40 + k // 3, 40 + k // 3)
            pygame.draw.line(pantalla, color, (i - cam_x, 0 - cam_y + k), (i + 80 - cam_x, MAPA_ALTO - cam_y))
        pygame.draw.rect(pantalla, (60, 60, 60), (i - cam_x, 0 - cam_y, 80, MAPA_ALTO))

        # líneas blancas o amarillas en medio
        for y in range(0, MAPA_ALTO, 60):
            color_linea = (255, 255, 255) if i % 400 == 0 else (255, 220, 0)
            pygame.draw.line(pantalla, color_linea, (i + 40 - cam_x, y - cam_y),
                             (i + 40 - cam_x, y + 20 - cam_y), 2)

    # --- Calles horizontales ---
    for j in range(0, MAPA_ALTO, 200):
        for k in range(80):
            color = (45 + k // 3, 45 + k // 3, 45 + k // 3)
            pygame.draw.line(pantalla, color, (0 - cam_x, j - cam_y + k), (MAPA_ANCHO - cam_x, j - cam_y + k))
        pygame.draw.rect(pantalla, (65, 65, 65), (0 - cam_x, j - cam_y, MAPA_ANCHO, 80))

        # líneas amarillas centrales
        for x in range(0, MAPA_ANCHO, 60):
            pygame.draw.line(pantalla, (255, 220, 0), (x - cam_x, j + 40 - cam_y),
                             (x + 20 - cam_x, j + 40 - cam_y), 2)

    # --- Aceras (bordes de calles más claros) ---
    for i in range(0, MAPA_ANCHO, 200):
        pygame.draw.rect(pantalla, (120, 120, 120), (i - cam_x - 8, 0 - cam_y, 8, MAPA_ALTO))
        pygame.draw.rect(pantalla, (120, 120, 120), (i + 80 - cam_x, 0 - cam_y, 8, MAPA_ALTO))
    for j in range(0, MAPA_ALTO, 200):
        pygame.draw.rect(pantalla, (130, 130, 130), (0 - cam_x, j - cam_y - 8, MAPA_ANCHO, 8))
        pygame.draw.rect(pantalla, (130, 130, 130), (0 - cam_x, j + 80 - cam_y, MAPA_ANCHO, 8))

    # --- Edificios (bloques oscuros) ---
    for i in range(100, MAPA_ANCHO, 200):
        for j in range(100, MAPA_ALTO, 200):
            rect = pygame.Rect(i, j, 60, 60)
            colisiones.append(rect)

            # sombra sutil debajo
            pygame.draw.ellipse(pantalla, (30, 30, 30), (i - cam_x + 6, j - cam_y + 6, 60, 14))
            color_base = (70, 70, 90)
            color_techo = (90, 90, 120)
            # gradiente vertical en el edificio
            for y in range(60):
                r = int(color_base[0] + (color_techo[0] - color_base[0]) * (y / 60))
                g = int(color_base[1] + (color_techo[1] - color_base[1]) * (y / 60))
                b = int(color_base[2] + (color_techo[2] - color_base[2]) * (y / 60))
                pygame.draw.line(pantalla, (r, g, b), (i - cam_x, j - cam_y + y), (i + 60 - cam_x, j - cam_y + y))

            pygame.draw.rect(pantalla, (40, 40, 60), (i - cam_x, j - cam_y, 60, 60), 2, border_radius=3)


def generar_casas(num, colisiones):
    casas = []
    esquinas_edificios = []
    # importante: colisiones debe estar previamente poblada (dibujar_fondo se invocó antes)
    for rect in colisiones:
        esquinas_edificios.extend([
            (rect.left - 12, rect.top - 12),
            (rect.right + 12, rect.top - 12),
            (rect.left - 12, rect.bottom + 12),
            (rect.right + 12, rect.bottom + 12)
        ])
    for i in range(1, num + 1):
        intentos = 0
        # Elegimos esquinas de edificios para posicionar casas
        while intentos < 300 and esquinas_edificios:
            x, y = random.choice(esquinas_edificios)
            casa_rect = pygame.Rect(x - 12, y - 12, 24, 24)
            col_ok = not any(casa_rect.colliderect(c) for c in colisiones)
            lejos_de_pizza = math.hypot(x - pizzeria.x, y - pizzeria.y) > 200
            lejos_otras = all(math.hypot(x - cx, y - cy) > 80 for cx, cy in [(c.x, c.y) for c in casas])
            if col_ok and lejos_de_pizza and lejos_otras:
                casas.append(Casa(x, y, i, base_id=i))
                break
            intentos += 1
        if intentos >= 300 or not esquinas_edificios:
            casas.append(Casa(100 + i * 60, 100 + i * 60, i, base_id=i))
    return casas

# initialize map and casas (populate colisiones first)
dibujar_fondo(pantalla, 0, 0, colisiones)
# generamos 10 casas como pediste
casas = generar_casas(10, colisiones)

# --- FEROMONAS ---
nodos = list(range(len(casas) + 1))
posiciones = [(pizzeria.x, pizzeria.y)] + [(c.x, c.y) for c in casas]
feromonas = [[0.0 for _ in nodos] for _ in nodos]
direcciones = {}

def dibujar_flecha(pantalla, x1, y1, x2, y2, color, grosor, offset, cam_x, cam_y):
    dx = x2 - x1
    dy = y2 - y1
    distancia = math.hypot(dx, dy)
    if distancia < 5: return
    pasos = int(distancia // 25)
    for i in range(pasos):
        pos = (i * 25 + offset) % distancia
        t = pos / distancia
        px = x1 + dx * t - cam_x
        py = y1 + dy * t - cam_y
        pygame.draw.circle(pantalla, color, (int(px), int(py)), grosor)
        angulo = math.atan2(dy, dx)
        punta_x = px + math.cos(angulo) * 8
        punta_y = py + math.sin(angulo) * 8
        pygame.draw.line(pantalla, color, (px, py), (punta_x, punta_y), 2)

def nodo_mas_cercano(x, y, posiciones):
    min_dist = float("inf")
    nodo_id = None
    for i, (nx, ny) in enumerate(posiciones):
        d = math.hypot(nx - x, ny - y)
        if d < min_dist:
            min_dist = d
            nodo_id = i
    return nodo_id

def dibujar_minimapa(pantalla, pizzeria, casas, repartidor):
    mini_w, mini_h = 180, 140
    margin = 12
    x0, y0 = ANCHO - mini_w - margin, margin
    pygame.draw.rect(pantalla, MINI_FRAME, (x0-2, y0-2, mini_w+4, mini_h+4), border_radius=6)
    pygame.draw.rect(pantalla, MINI_BG, (x0, y0, mini_w, mini_h), border_radius=6)
    escala_x = mini_w / MAPA_ANCHO
    escala_y = mini_h / MAPA_ALTO
    px = int(x0 + pizzeria.x * escala_x)
    py = int(y0 + pizzeria.y * escala_y)
    pygame.draw.circle(pantalla, PIZZERIA_COLOR, (px, py), 5)
    for casa in casas:
        cx = int(x0 + casa.x * escala_x)
        cy = int(y0 + casa.y * escala_y)
        color = (100,180,100) if casa.entregada else CASA_COLOR
        pygame.draw.rect(pantalla, color, (cx-2, cy-2, 4, 4))
    rx = int(x0 + repartidor.x * escala_x)
    ry = int(y0 + repartidor.y * escala_y)
    pygame.draw.rect(pantalla, ROJO, (rx-2, ry-2, 4, 4))

# --- NUEVO: función para construir ruta siguiendo feromonas (greedy) ---
def construir_ruta_de_feromonas(origen_idx, destino_idx, feromonas, posiciones):
    """
    Construye una ruta (lista de puntos (x,y)) desde origen_idx hasta destino_idx
    siguiendo de forma greedy las feromonas. Si no hay feromonas útiles, va directo.
    """
    total = len(feromonas)
    current = origen_idx
    visited = set([current])
    ruta = [posiciones[current]]
    pasos = 0
    max_pasos = total + 10
    while current != destino_idx and pasos < max_pasos:
        pasos += 1
        candidatos = []
        for j in range(total):
            if j in visited:
                continue
            candidatos.append((j, feromonas[current][j]))
        if not candidatos:
            # sin candidatos, ir directo al destino
            ruta.append(posiciones[destino_idx])
            break
        # elegir vecino con más feromona
        j_max, val_max = max(candidatos, key=lambda x: x[1])
        if val_max <= 0.0:
            ruta.append(posiciones[destino_idx])
            break
        ruta.append(posiciones[j_max])
        visited.add(j_max)
        current = j_max
    if ruta[-1] != posiciones[destino_idx]:
        ruta.append(posiciones[destino_idx])
    return ruta

# --- NUEVO: Clase PizzeroAuto (sale de la pizzería y sigue la ruta) ---
class PizzeroAuto:
    def __init__(self, ruta_puntos, velocidad=3.5):
        # ruta_puntos: lista de (x,y) coordenadas absolutas
        self.ruta = [(float(x), float(y)) for (x, y) in ruta_puntos]
        # posición inicial en la pizzería (primer punto de ruta)
        self.x, self.y = self.ruta[0]
        self.indice = 1  # siguiente punto objetivo en ruta
        self.vel = velocidad
        self.vivo = True
        self.tiene_pizza = True

    def update(self):
        if not self.vivo:
            return
        if self.indice >= len(self.ruta):
            self.vivo = False
            self.tiene_pizza = False
            return
        tx, ty = self.ruta[self.indice]
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 2.5:
            self.indice += 1
            if self.indice >= len(self.ruta):
                self.vivo = False
                self.tiene_pizza = False
            return
        # moverse hacia el objetivo
        self.x += (dx / dist) * self.vel
        self.y += (dy / dist) * self.vel

    def dibujar(self, pantalla, cam_x, cam_y):
        if not self.vivo:
            return
        if pizzero_img:
            w, h = pizzero_img.get_width(), pizzero_img.get_height()
            pantalla.blit(pizzero_img, (self.x - w//2 - cam_x, self.y - h//2 - cam_y))
        else:
            pygame.draw.rect(pantalla, ROJO, (self.x - 10 - cam_x, self.y - 10 - cam_y, 20, 20))
        if self.tiene_pizza:
            if pizza_img:
                pw, ph = pizza_img.get_width(), pizza_img.get_height()
                pantalla.blit(pizza_img, (self.x - pw//2 - cam_x, self.y - ph//2 - 8 - cam_y))
            else:
                pygame.draw.rect(pantalla, BLANCO, (self.x - 5 - cam_x, self.y - 25 - cam_y, 10, 10))

# lista global de pizzeros automáticos
pizzeros_auto = []

# --- VARIABLES ---
desplazamiento_flechas = 0
mensaje = "Recoge una pizza en la pizzería 🍕"
casa_objetivo = None
tiempo_inicio = 0.0
tiempo_limite = 0.0
tiempo_restante = 0.0

# --- NUEVO: contadores para rotación por bloque de 5 (se usa base_id para decidir bloque) ---
# deliveries_in_block[block_start_base] = contador de entregas en ese bloque
deliveries_in_block = {}  # ejemplo keys serán 1,6 para bloques 1-5 y 6-10
# inicializa contadores en base a base_ids presentes
for c in casas:
    block_start = ((c.base_id - 1) // 5) * 5 + 1
    deliveries_in_block.setdefault(block_start, 0)

def rotate_block_by_base_start(block_start):
    """
    Rota los IDs de las casas cuyo base_id pertenece al bloque que comienza en block_start.
    Suma +10 al id mostrado y realiza wrap modulo 20 para que el ciclo sea repetible.
    Además marca entregada=False para que vuelvan a estar activas.
    """
    for c in casas:
        base_block = ((c.base_id - 1) // 5) * 5 + 1
        if base_block == block_start:
            # sumar 10 con wrap entre 1..20
            new_id = ((c.id + 10 - 1) % 20) + 1
            c.id = new_id
            c.entregada = False

# --- BUCLE PRINCIPAL ---
ejecutando = True
while ejecutando:
    dt = clock.tick(60) / 1000.0
    teclas = pygame.key.get_pressed()
    desplazamiento_flechas = (desplazamiento_flechas + 2) % 25

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            ejecutando = False

    repartidor.mover(teclas, colisiones)
    cam_x = max(0, min(MAPA_ANCHO - ANCHO, repartidor.x - ANCHO // 2))
    cam_y = max(0, min(MAPA_ALTO - ALTO, repartidor.y - ALTO // 2))

    dibujar_fondo(pantalla, cam_x, cam_y, colisiones)
    posiciones = [(pizzeria.x, pizzeria.y)] + [(c.x, c.y) for c in casas]

    nodo_actual = nodo_mas_cercano(repartidor.x, repartidor.y, posiciones)
    if repartidor.nodo_previo is not None and repartidor.nodo_previo != nodo_actual:
        a, b = repartidor.nodo_previo, nodo_actual
        if (a == 0 or b == 0) and a != b:
            feromonas[a][b] += 1.0
            feromonas[b][a] += 1.0
            direcciones[(a, b)] = (posiciones[a], posiciones[b])
    repartidor.nodo_previo = nodo_actual

    for i in range(len(nodos)):
        for j in range(len(nodos)):
            feromonas[i][j] = max(0.0, feromonas[i][j] * 0.995)

    for (a, b), (p1, p2) in list(direcciones.items()):
        if a == 0 or b == 0:
            intensidad = feromonas[a][b]
            if intensidad > 0.2:
                grosor = min(6, max(1, int(intensidad)))
                dibujar_flecha(pantalla, p1[0], p1[1], p2[0], p2[1], AMARILLO, grosor, desplazamiento_flechas, cam_x, cam_y)

    # --- LÓGICA DE ENTREGA ---
    if not repartidor.entregando:
        if math.hypot(repartidor.x - pizzeria.x, repartidor.y - pizzeria.y) < 30:
            pendientes = [c for c in casas if not c.entregada]
            if pendientes:
                pendientes_ordenadas = sorted(pendientes, key=lambda c: c.id)
                casa_objetivo = pendientes_ordenadas[0]
                repartidor.entregando = True
                repartidor.tiene_pizza = True
                tiempo_inicio = time.time()
                tiempo_limite = 20.0
                mensaje = f"Entrega la pizza a la Casa #{casa_objetivo.id}"
            else:
                mensaje = "No hay pedidos pendientes. ¡Buen trabajo!"
    else:
        elapsed = time.time() - tiempo_inicio
        tiempo_restante = max(0.0, tiempo_limite - elapsed)
        if tiempo_restante <= 0.0:
            mensaje = "¡Tiempo agotado! Pedido cancelado. Vuelve a la pizzería."
            repartidor.entregando = False
            repartidor.tiene_pizza = False
            casa_objetivo = None
        else:
            if casa_objetivo and math.hypot(repartidor.x - casa_objetivo.x, repartidor.y - casa_objetivo.y) < 25:
                # entrega del jugador
                casa_objetivo.entregada = True
                repartidor.entregando = False
                repartidor.tiene_pizza = False
                mensaje = f"Pizza entregada en Casa #{casa_objetivo.id}! Vuelve a la pizzería."
                if sonido_entrega:
                    try:
                        sonido_entrega.play()
                    except Exception:
                        pass

                # --- ACTUALIZAR CONTADOR DE ENTREGAS POR BLOQUE (usando base_id) ---
                base = casa_objetivo.base_id
                block_start = ((base - 1) // 5) * 5 + 1

                # si alcanzamos 5 entregas en ese bloque base, rotamos ese bloque
                if deliveries_in_block[block_start] == 5:
                    casa_entregada = casa_objetivo
                    try:
                        rotate_block_by_base_start(block_start)
                    except Exception as e:
                        print("Error rotando bloque:", e)
                        deliveries_in_block[block_start] = 0
                        casa_objetivo = casa_entregada
                    
                base = casa_objetivo.base_id
                block_start = ((base - 1) // 5) * 5 + 1
                deliveries_in_block.setdefault(block_start, 0)
                deliveries_in_block[block_start] += 1

                # si alcanzamos 5 entregas en ese bloque base, rotamos ese bloque
                if deliveries_in_block[block_start] >= 5:
                    try:
                        rotate_block_by_base_start(block_start)
                        deliveries_in_block[block_start] = 0
                    except Exception:
                        # no romper el loop por error en rotación
                        pass
                    # resetear contador para ese bloque (permite repetir el ciclo)
                    deliveries_in_block[block_start] = 0

                # --- CREAR PIZZERO AUTOMÁTICO (sale desde la pizzería hacia la casa entregada,
                # siguiendo la ruta construida por feromonas si existe) ---
                try:
                    # reconstruir posiciones/nodos por si cambiaron
                    nodos = list(range(len(casas) + 1))
                    posiciones = [(pizzeria.x, pizzeria.y)] + [(c.x, c.y) for c in casas]

                    destino_idx = None
                    # encontrar índice del nodo que coincide con la casa entregada (por coordenadas)
                    for idx, pos in enumerate(posiciones):
                        if idx == 0:
                            continue
                        if pos[0] == casa_objetivo.x and pos[1] == casa_objetivo.y:
                            destino_idx = idx
                            break
                    if destino_idx is None:
                        # fallback: ruta directa pizzeria -> casa
                        ruta_directa = [(pizzeria.x, pizzeria.y), (casa_objetivo.x, casa_objetivo.y)]
                        pizzeros_auto.append(PizzeroAuto(ruta_directa, velocidad=3.5))
                    else:
                        ruta = construir_ruta_de_feromonas(0, destino_idx, feromonas, posiciones)
                        # si la ruta es corta o vacía, forzar ruta directa
                        if not ruta or len(ruta) < 2:
                            ruta = [(pizzeria.x, pizzeria.y), (casa_objetivo.x, casa_objetivo.y)]
                        pizzeros_auto.append(PizzeroAuto(ruta, velocidad=3.5))
                except Exception:
                    # Siempre evitar romper el loop por errores en creación de automáticos
                    try:
                        pizzeros_auto.append(PizzeroAuto([(pizzeria.x, pizzeria.y), (casa_objetivo.x, casa_objetivo.y)], velocidad=3.5))
                    except Exception:
                        pass

                # mantenemos la casa_objetivo un breve momento para resaltarla
                tiempo_restante = 3.0  # mostrar highlight por 3 segundos

    # --- ACTUALIZAR PIZZEROS AUTOMÁTICOS ---
    for pa in list(pizzeros_auto):
        pa.update()
        if not pa.vivo:
            try:
                pizzeros_auto.remove(pa)
            except ValueError:
                pass

    # --- DIBUJAR ENTIDADES Y HUD ---
    pendientes_existentes = any(not c.entregada for c in casas)
    pizzeria_parpadeo = (not repartidor.entregando) and pendientes_existentes
    pizzeria_parpadeo = pizzeria_parpadeo and (math.sin(time.time() * 3.0) > 0.0)
    pizzeria.dibujar(pantalla, cam_x, cam_y, parpadeo=pizzeria_parpadeo)

    for casa in casas:
        highlight = (casa is casa_objetivo and (repartidor.entregando or tiempo_restante > 0))
        casa.dibujar(pantalla, cam_x, cam_y, highlight=highlight)

    # dibujar pizzeros automáticos (si los hay)
    for pa in pizzeros_auto:
        pa.dibujar(pantalla, cam_x, cam_y)

    repartidor.dibujar(pantalla, cam_x, cam_y)
    dibujar_minimapa(pantalla, pizzeria, casas, repartidor)

    # Mensaje + temporizador
    font = pygame.font.SysFont(None, 26)
    mensaje_mostrar = mensaje
    if repartidor.entregando and tiempo_restante > 0:
        mensaje_mostrar += f" | Tiempo restante: {int(tiempo_restante)}s"
    texto = font.render(mensaje_mostrar, True, BLANCO)
    fondo_rect = pygame.Surface((texto.get_width()+12, texto.get_height()+6), pygame.SRCALPHA)
    fondo_rect.fill((0,0,0,150))
    pantalla.blit(fondo_rect, (12, ALTO - 40))
    pantalla.blit(texto, (16, ALTO - 37))

    pygame.display.flip()

pygame.quit()
sys.exit()
