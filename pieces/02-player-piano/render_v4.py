"""Piece 2 v4: city → slow camera lean toward the convergence → night finishing pass.
(Rain on glass was tried and dropped: the beads read as bubbles, and a proper defocused
rain look would blur the piano-roll windows the piece depends on.)

usage: python render_v4.py OUT.mp4
"""
import subprocess
import sys

sys.path.insert(0, '../..')
import craft  # noqa: E402
import city  # noqa: E402
import glass  # noqa: E402

FIN = craft.finisher('night')
FOCUS = (1450, 600)
out = sys.argv[1]
W, H, FPS = city.W, city.H, city.FPS
cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
       '-i', '-', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-threads', '2', '-pix_fmt', 'yuv420p', out]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
n = int((city.INFO['total'] + 3) * FPS)
for i in range(n):
    t = i / FPS
    img = city.frame(t)
    z, fx, fy = glass.camera(t, city.INFO['t_conv'], city.INFO['total'], FOCUS)
    img = glass.apply_camera(img, z, fx, fy)
    p.stdin.write(craft.finish_u8(FIN, img, i).tobytes())
    if i % 300 == 0:
        print('frame', i, '/', n, flush=True)
p.stdin.close()
p.wait()
