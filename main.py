import pygame
import random
import math

DEFAULT_GENOME = [(16,16,1,16),(2, 3, 16, 16), (16, 16, 1, 16), (16, 16, 16, 16)]*4

class Particle:
    def __init__(self, x, y, type = 2, genome=DEFAULT_GENOME, active_gene=0, age=0):
        self.x = x
        self.y = y
        self.type = type # 0 = stem, 1 = bud, 2 = seed

        self.energy = 20
        self.age = age
        self.max_age = 200
        self.genome = genome # new active gene for each direction (up down left right), 16 means no growth
        self.active_gene = active_gene
    
    def mutate(self):
        # mutate genome with small random changes

        new_genome = []
        for gene in self.genome:
            new_gene = []
            for g in gene:
                if random.random() < 0.001: 
                    new_g = (g + random.randint(-2, 2)) % 17 # small mutation
                    new_gene.append(new_g)
                else:
                    new_gene.append(g)
            new_genome.append(tuple(new_gene))
        self.genome = new_genome

    def update(self, get_neighbors, new_particle):
        self.x %= 640

        if self.y >= 0:
            return False

        if self.type == 2:
            if self.y < -1:
                self.y += 1
            else:
                self.type = 1

        self.age += 1

        if self.type == 0:
            if self.age > self.max_age:
                return False # die
            return True # stem is passive
        
        if self.energy <= 0:
            return False # die
        
        if self.type == 1:
            neighbors = get_neighbors(self)

            if len(neighbors) == 0 and self.y < -1:
                return False

            if self.energy < 100:
                self.energy += -self.y * (5-len(neighbors))/4 - 4
                return True
            
            if self.age > self.max_age:
                self.energy += 100
                self.age = 0
                self.type = 2 # bud becomes seed if too old
                self.active_gene = 0
                return True

            # bud tries to grow according to active gene
            gene = self.genome[self.active_gene]

            self.mutate() # mutate genome over time

            for idx, attempt in enumerate([(0, -1), (0, 1), (-1, 0), (1, 0)]): # up, down, left, right
                if gene[idx] < 16: # active growth gene
                    new_x = self.x + attempt[0]
                    new_y = self.y + attempt[1]
                    if new_y > 0: # only grow upwards
                        continue
                    if not any(n.x == new_x and n.y == new_y for n in neighbors):
                        # grow new bud
                        part = Particle(new_x, new_y, type=1, genome=self.genome, active_gene=gene[idx], age=self.age)
                        part.energy += self.energy // 2
                        new_particle(part)
            self.type = 0 # bud becomes stem after growing

        return True

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        self.screensize = self.screen.get_size()
        self.clock = pygame.time.Clock()

        # center position of the camera
        self.camx = 0
        self.camy = 0

        self.zoom = 0 # magnitude 2^n

        self.enable_dbg = True

        self.font = pygame.font.SysFont(None, 24)

        self.target_fps = 30

        self.running = True

        self.stem = pygame.Surface((10, 10))
        pygame.draw.rect(self.stem, (0, 128, 0), (0, 0, 10, 10))
        self.bud = pygame.Surface((10, 10))
        pygame.draw.rect(self.bud, (0, 255, 0), (0, 0, 10, 10))
        self.seed = pygame.Surface((10, 10))
        pygame.draw.rect(self.seed, (128, 128, 0), (0, 0, 10, 10))
    
    def start(self):
        # one particle is 10x10 pixels
        self.particles = []
        self.grid = {} # dict: (x, y) -> particle for O(1) collision checks

        def gen_random_genome():
            genome = []
            for _ in range(16):
                gene = tuple(random.randint(0, 16) for _ in range(4))
                genome.append(gene)
            return genome

        for _ in range(10): # start with some random seeds
            x = random.randint(0, 639)
            y = -10
            particle = Particle(x, y, type=2, genome=gen_random_genome())
            particle.energy = 1000
            self.particles.append(particle)
            self.grid[(particle.x, particle.y)] = particle

    def update(self):
        dt = self.clock.get_time() / 1000.0

        keys = pygame.key.get_pressed()
        speed = 500 * dt * (2 ** -self.zoom) # camera speed scales with zoom level
        if keys[pygame.K_w]:
            self.camy -= speed
        if keys[pygame.K_s]:
            self.camy += speed
        if keys[pygame.K_a]:
            self.camx -= speed
        if keys[pygame.K_d]:
            self.camx += speed

        if self.running:
            self.simulate()

    def simulate(self):
        def new_particle(particle):
            self.particles.append(particle)
            self.grid[(particle.x, particle.y)] = particle
        
        def get_neighbors(particle):
            particles = self.particles
            grid = self.grid                 # dict: (x, y) -> particle
            px, py = particle.x, particle.y

            other_at_same = grid.get((px, py))
            if other_at_same is not None and other_at_same is not particle:
                # Remove both particles
                del grid[(px, py)]
                if particle in particles:
                    particles.remove(particle)
                if other_at_same in particles:
                    particles.remove(other_at_same)
                return []

            # Gather neighbors from the four cardinal directions
            neighbors = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = grid.get((px + dx, py + dy))
                if p is not None:
                    neighbors.append(p)

            return neighbors

        self.current_particles = self.particles.copy()
        for particle in self.current_particles:
            if not particle.update(get_neighbors, new_particle):
                self.grid.pop((particle.x, particle.y), None)
                if particle in self.particles:
                    self.particles.remove(particle)

    def render(self):
        screen = self.screen

        zoom = 2 ** self.zoom

        camx = self.camx - self.screensize[0] / 2 / zoom
        camy = self.camy - self.screensize[1] / 2 / zoom

        # floor
        floor_rely = -camy*zoom
        pygame.draw.rect(screen, (100, 100, 100), (0, floor_rely, self.screensize[0], self.screensize[1] - floor_rely))

        # origin
        pygame.draw.circle(screen, (255, 0, 0), (-camx*zoom, -camy*zoom), 5)

        # left boundary
        pygame.draw.line(screen, (255, 255, 0), (-camx*zoom, 0), (-camx*zoom, self.screensize[1]), 2)

        # right boundary
        pygame.draw.line(screen, (255, 255, 0), ((self.screensize[0]*8 - camx) * zoom, 0), ((self.screensize[0]*8 - camx) * zoom, self.screensize[1]), 2)

        stem = pygame.transform.scale(self.stem, (10*zoom+1, 10*zoom+1))
        bud = pygame.transform.scale(self.bud, (10*zoom+1, 10*zoom+1))
        seed = pygame.transform.scale(self.seed, (10*zoom+1, 10*zoom+1))

        for particle in self.particles:
            x = (particle.x * 10 - camx) * zoom
            y = (particle.y * 10 - camy) * zoom
            if 0 <= x < self.screensize[0] and 0 <= y < self.screensize[1]: # only draw if on screen
                if particle.type == 0:
                    screen.blit(stem, (x, y))
                elif particle.type == 1:
                    screen.blit(bud, (x, y))
                else:
                    screen.blit(seed, (x, y))

    def render_debug(self):
        # Render debug information
        debug_texts = [
            "paused" if not self.running else "running",
            f"Camera Position: ({self.camx}, {self.camy})",
            f"Zoom Level: {self.zoom} (scale: {2 ** self.zoom:.2f}x)",
            f"Particles: {len(self.particles)}",
            f"FPS: {self.clock.get_fps():.2f}/{self.target_fps}",
        ]
        for i, text in enumerate(debug_texts):
            debug_surface = self.font.render(text, True, (0, 255, 0))
            self.screen.blit(debug_surface, (10, 10 + i * 20))
    
    def event(self, event:pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                exit()
            if event.key == pygame.K_F3:
                self.enable_dbg = not self.enable_dbg

            if event.key == pygame.K_r:
                self.start() # reset game
            
            if event.key == pygame.K_SPACE:
                self.running = not self.running # toggle simulation
            if event.key == pygame.K_f:
                self.running = False
                self.simulate() # step simulation forward one frame
            
            if event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                self.target_fps += 5
            if event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                self.target_fps = max(5, self.target_fps - 5)
            
            if event.key == pygame.K_m:
                self.target_fps = 1000000 # max fps for benchmarking
            if event.key == pygame.K_n:
                self.target_fps = 30 # reset to default fps
        
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self.zoom += 1
            else:
                self.zoom -= 1

def main():
    game = Game()
    game.start()
    running = True

    clock = game.clock

    game_event = game.event

    update = game.update
    render = game.render
    render_debug = game.render_debug

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                game_event(event)
        update()
        game.screen.fill((0, 0, 0))
        render()
        if game.enable_dbg:
            render_debug()
        pygame.display.flip()
        clock.tick(game.target_fps)

    pygame.quit()

if __name__ == "__main__":
    main()
