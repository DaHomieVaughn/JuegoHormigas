import math
import random

class Hormiga:
    def __init__(self, nodos, distancias):
        self.nodos = nodos
        self.distancias = distancias
        self.recorrido = []
        self.longitud_total = 0

    def elegir_ruta(self, nodo_actual, feromonas, alpha=1, beta=2):
        # Lista de nodos aún no visitados
        no_visitados = [n for n in self.nodos if n not in self.recorrido]

        if not no_visitados:
            return None

        # Probabilidad de elegir cada nodo según feromonas y distancia
        probabilidades = []
        for nodo in no_visitados:
            tau = feromonas[nodo_actual][nodo] ** alpha
            eta = (1 / self.distancias[nodo_actual][nodo]) ** beta
            probabilidades.append(tau * eta)

        total = sum(probabilidades)
        probabilidades = [p / total for p in probabilidades]

        # Elegir el próximo nodo según las probabilidades
        return random.choices(no_visitados, weights=probabilidades, k=1)[0]

    def construir_recorrido(self, feromonas, alpha, beta):
        self.recorrido = [0]  # Nodo inicial (por ejemplo, el repartidor)
        while len(self.recorrido) < len(self.nodos):
            nodo_actual = self.recorrido[-1]
            siguiente = self.elegir_ruta(nodo_actual, feromonas, alpha, beta)
            if siguiente is None:
                break
            self.recorrido.append(siguiente)
        self.longitud_total = self.calcular_longitud()
        return self.recorrido

    def calcular_longitud(self):
        total = 0
        for i in range(len(self.recorrido) - 1):
            a, b = self.recorrido[i], self.recorrido[i + 1]
            total += self.distancias[a][b]
        return total


class AlgoritmoHormigas:
    def __init__(self, nodos, distancias, n_hormigas=10, iteraciones=50, rho=0.5, alpha=1, beta=2):
        self.nodos = nodos
        self.distancias = distancias
        self.n_hormigas = n_hormigas
        self.iteraciones = iteraciones
        self.rho = rho  # tasa de evaporación
        self.alpha = alpha
        self.beta = beta
        self.feromonas = [[1 for _ in range(len(nodos))] for _ in range(len(nodos))]

    def ejecutar(self):
        mejor_ruta = None
        mejor_distancia = float("inf")

        for _ in range(self.iteraciones):
            hormigas = [Hormiga(self.nodos, self.distancias) for _ in range(self.n_hormigas)]

            for hormiga in hormigas:
                ruta = hormiga.construir_recorrido(self.feromonas, self.alpha, self.beta)
                distancia = hormiga.longitud_total
                if distancia < mejor_distancia:
                    mejor_ruta = ruta
                    mejor_distancia = distancia

            self.actualizar_feromonas(hormigas)

        return mejor_ruta, mejor_distancia

    def actualizar_feromonas(self, hormigas):
        # Evaporación
        for i in range(len(self.nodos)):
            for j in range(len(self.nodos)):
                self.feromonas[i][j] *= (1 - self.rho)

        # Depósito de feromonas según calidad del recorrido
        for hormiga in hormigas:
            for i in range(len(hormiga.recorrido) - 1):
                a, b = hormiga.recorrido[i], hormiga.recorrido[i + 1]
                self.feromonas[a][b] += 1 / hormiga.longitud_total
                self.feromonas[b][a] += 1 / hormiga.longitud_total  # simetría
