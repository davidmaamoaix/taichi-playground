import taichi as ti


ti.init(debug=True)

particles_limit = 256
mass = 1
ground_y = 0.1
conn_range = 0.1
G = ti.Vector([0, -9.81])
dt = 1e-3

num_particles = ti.field(ti.i32, shape=())
stiffness = ti.field(ti.f32, shape=())
damping = ti.field(ti.f32, shape=())

x = ti.Vector.field(2, ti.f32, shape=particles_limit, needs_grad=True)
v = ti.Vector.field(2, ti.f32, shape=particles_limit)

A = ti.Matrix.field(2, 2, ti.f32, shape=(particles_limit, particles_limit))
b = ti.Vector.field(2, ti.f32, shape=particles_limit)
forces = ti.Vector.field(2, ti.f32, shape=particles_limit, needs_grad=True)

rest_length = ti.field(ti.f32, shape=(particles_limit, particles_limit))
fixed = ti.field(ti.i32, shape=particles_limit)

stiffness[None] = 10000
damping[None] = 15
paused = False


@ti.kernel
def init_grad():
    for i in range(num_particles[None]):
        forces.grad[i] = [1, 1]


@ti.kernel
def get_force(n: ti.i32):
    for i, j in ti.ndrange(n, n):
        if rest_length[i, j] != 0:
            ij = x[j] - x[i]
            magnitude = stiffness[None] * (ij.norm() - rest_length[i, j])
            forces[i] += magnitude * ij.normalized()


@ti.kernel
def init_update():
    n = num_particles[None]

    for i in range(n):
        grad = x.grad[i]

        b[i] = v[i] + dt * forces[i]


@ti.kernel
def make_node(pos_x: ti.f32, pos_y: ti.f32, is_fixed: ti.i32):
    curr = num_particles[None]
    x[curr] = [pos_x, pos_y]
    v[curr] = [0, 0]
    fixed[curr] = is_fixed
    num_particles[None] += 1

    for i in range(curr):
        dist = (x[curr] - x[i]).norm()
        if dist <= conn_range:
            rest_length[i, curr] = dist
            rest_length[curr, i] = dist


gui = ti.GUI('Mass Spring', res=(720, 720), background_color=0x000000)

while True:
    for e in gui.get_events(ti.GUI.PRESS):
        if e.key in [ti.GUI.ESCAPE, ti.GUI.EXIT]:
            exit()
        elif e.key == ti.GUI.LMB and num_particles[None] < particles_limit:
            make_node(e.pos[0], e.pos[1], gui.is_pressed('Shift'))
        elif e.key == gui.SPACE:
            paused = not paused

    if not paused:
        init_grad()

        n = num_particles[None]
        get_force(n)
        get_force.grad(n)
        print(x.grad[0])

        init_update()

    nodes = x.to_numpy()[: num_particles[None]]
    fix_status = fixed.to_numpy()[: num_particles[None]]

    for i in range(num_particles[None]):
        for j in range(i + 1, num_particles[None]):
            if rest_length[i, j] == 0:
                continue

            gui.line(begin=nodes[i], end=nodes[j], radius=2, color=0xAAAAAA)

    non_fixed_nodes = nodes[fix_status == 0]
    fixed_nodes = nodes[fix_status == 1]
    gui.circles(non_fixed_nodes, color=0x5BC2E2, radius=5)
    gui.circles(fixed_nodes, color=0xFF7B5B, radius=5)

    gui.line(
        begin=(0.0, ground_y),
        end=(1.0, ground_y),
        radius=1
    )

    if paused:
        gui.text(
            content='PAUSED',
            pos=(0.05, 0.95),
            font_size=20
        )

    gui.show()
