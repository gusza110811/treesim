import pygame
import random

DEFAULT_GENOME = [(16,16,1,5),(2, 16, 16, 16), (16, 16, 1, 16), (16, 16, 16, 16),
                  (16,16,16,16),(6, 16, 16, 16), (16, 16, 16, 5), (16, 16, 16, 16)]*2

class Particle:
    def __init__(self, x, y, type = 2, genome=DEFAULT_GENOME, active_gene=0, age=0):
        self.x = x
        self.y = y
        self.type = type # 0 = stem, 1 = bud, 2 = seed

        self.energy = 20
        self.age = age
        self.max_age = 100
        self.genome = genome # new active gene for each direction (up down left right), -16 means no growth
        self.active_gene = active_gene
    
    def mutate(self):
        # mutate genome with small random changes

        new_genome = []
        for gene in self.genome:
            new_gene = []
            for g in gene:
                if random.random() < 0.001: 
                    new_g = g + random.randint(-2, 2) % 17 # small mutation
                    new_gene.append(new_g)
                else:
                    new_gene.append(g)
            new_genome.append(tuple(new_gene))
        self.genome = new_genome

    def update(self, get_neighbors, new_particle):
        self.x %= 160 # wrap around horizontally
        neighbors = get_neighbors(self)

        if self.y >= 0:
            return False

        if self.type == 2:
            self.energy -= 0.1 # seed loses energy over time
            if self.y < -1:
                self.y += 1
            else:
                self.type = 1

        self.age += 1

        if self.type == 0:
            if self.age > self.max_age:
                return False # die
            if neighbors:
                return True # stem is passive
            else:
                return False # stem dies if no neighbors (disconnected)
        
        if self.energy <= 0:
            return False # die
        
        if self.type == 1:
            if self.energy < 50:
                self.energy += -self.y
                return True

            if (not neighbors) and self.y != -1:
                self.age = 0
                self.type = 2 # bud becomes seed if no neighbors (disconnected)
                self.active_gene = 0
                return True
            
            if self.age > self.max_age:
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
                    # check if new position is occupied by neighbors
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

        # top-left position of the camera
        self.camx = 0
        self.camy = -300

        self.enable_dbg = True

        self.font = pygame.font.SysFont(None, 24)

        self.target_fps = 30
    
    def start(self):
        # one particle is 10x10 pixels
        self.particles = []
        init_particle = Particle(80, -30) # start with one seed in the middle

        init_particle.energy = 200 # give the initial seed more energy to grow faster
        self.particles.append(init_particle)

    def update(self):
        dt = self.clock.get_time() / 1000.0

        keys = pygame.key.get_pressed()
        speed = 500 * dt
        if keys[pygame.KMOD_SHIFT]:
            speed *= 2
        if keys[pygame.K_w]:
            self.camy -= speed
        if keys[pygame.K_s]:
            self.camy += speed
        if keys[pygame.K_a]:
            self.camx -= speed
        if keys[pygame.K_d]:
            self.camx += speed

        def new_particle(particle):
            self.particles.append(particle)
        
        # 4 neighbors
        def get_neighbors(particle):
            out = []
            for other in self.particles:
                if other is particle:
                    continue
                distx = abs(other.x - particle.x)
                disty = abs(other.y - particle.y)
                if distx <= 1 and disty == 0:
                    out.append(other)
                elif disty <= 1 and distx == 0:
                    out.append(other)
            return out

        self.current_particles = self.particles.copy()
        for particle in self.current_particles:
            if not particle.update(get_neighbors, new_particle):
                self.particles.remove(particle)

    def render(self):

        # floor
        floor_rely = -self.camy
        pygame.draw.rect(self.screen, (100, 100, 100), (0, floor_rely, self.screensize[0], self.screensize[1] - floor_rely))

        # origin
        pygame.draw.circle(self.screen, (255, 0, 0), (-self.camx, -self.camy), 5)

        # left boundary
        pygame.draw.line(self.screen, (255, 255, 0), (-self.camx, 0), (-self.camx, self.screensize[1]), 2)

        # right boundary
        pygame.draw.line(self.screen, (255, 255, 0), (self.screensize[0]*2 - self.camx, 0), (self.screensize[0]*2 - self.camx, self.screensize[1]), 2)

        for particle in self.particles:
            color = (0, 128, 0) if particle.type == 0 else (0, 255, 0) if particle.type == 1 else (255, 255, 0)
            pygame.draw.rect(self.screen, color, (particle.x * 10 - self.camx, particle.y * 10 - self.camy, 10, 10))

    def render_debug(self):
        # Render debug information
        debug_texts = [
            f"Camera Position: ({self.camx}, {self.camy})",
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
            
            if event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                self.target_fps += 5
            if event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                self.target_fps = max(5, self.target_fps - 5)

def main():
    game = Game()
    game.start()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                game.event(event)
        game.update()
        game.screen.fill((0, 0, 0))
        game.render()
        if game.enable_dbg:
            game.render_debug()
        pygame.display.flip()
        game.clock.tick(game.target_fps)

    pygame.quit()

if __name__ == "__main__":
    main()
